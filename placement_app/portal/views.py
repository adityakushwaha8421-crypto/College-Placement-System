from datetime import timedelta
from functools import wraps
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import transaction, IntegrityError
from django.db.models import Q, Count, Max
from django.http import FileResponse, Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST
from .models import User, Job, Application, Interview, Activity, PendingResumeDeletion, BRANCHES
from .forms import LoginForm, RegistrationForm, StudentProfileForm, CompanyProfileForm, OfficerProfileForm, JobForm, InterviewForm
from .services import application_scope, report_data, csv_response, pdf_response
from .uploads import retry_resume_deletions, discard_rolled_back_upload

class SignIn(LoginView):
    template_name = 'registration/login.html'
    authentication_form = LoginForm
    redirect_authenticated_user = True

class SignOut(LogoutView):
    pass

def roles(*allowed):
    def decorator(fn):
        @login_required
        @wraps(fn)
        def wrapped(request, *args, **kwargs):
            if request.user.role not in allowed: raise PermissionDenied
            return fn(request, *args, **kwargs)
        return wrapped
    return decorator

def activity(user, message, application=None):
    Activity.objects.create(actor=user, message=message, application=application)

def page(request, queryset, count=10):
    return Paginator(queryset, count).get_page(request.GET.get('page'))

def application_redirect(request):
    from django.http import QueryDict
    filters = QueryDict(mutable=True)
    for key in ('q', 'job', 'status', 'page'):
        if key in request.GET: filters[key] = request.GET[key]
    url = reverse('applications')
    return redirect(url + ('?' + filters.urlencode() if filters else ''))


def register(request):
    if request.user.is_authenticated: return redirect('dashboard')
    form = RegistrationForm(request.POST if request.method == 'POST' else None)
    if request.method == 'POST':
        try:
            # Validation and insertion share SQLite's write transaction: two signup
            # requests cannot both pass uniqueness checks before either inserts.
            with transaction.atomic():
                if form.is_valid():
                    user = form.save()
                    activity(user, f'{user} registered as a {user.get_role_display().lower()}.')
                else:
                    user = None
        except IntegrityError:
            form.add_error(None, 'That email or roll number was just registered. Please check your details.')
            user = None
        if user is not None:
            login(request, user, backend='portal.auth.EmailBackend')
            messages.success(request, 'Welcome! Your account is waiting for placement-office approval.')
            return redirect('dashboard')
    return render(request, 'registration/register.html', {'form': form})

@login_required
def dashboard(request):
    user = request.user
    applications = application_scope(user)
    interviews = Interview.objects.select_related('application__student', 'application__job__company').filter(application__in=applications, application__status='shortlisted', starts_at__gte=timezone.now())[:4]
    if user.role == 'admin':
        summary = report_data()
        stats = [('Approved students', summary['total'], 'Across all departments'), ('Students placed', summary['placed'], f"{summary['rate']}% placement rate"), ('Open opportunities', Job.objects.filter(status='open', deadline__gte=timezone.localdate(), company__approval='approved', company__is_active=True).count(), 'Accepting applications'), ('Awaiting approval', User.objects.exclude(role='admin').filter(approval='pending').count() + Job.objects.filter(status='pending').count(), 'Profiles and openings')]
        activities = Activity.objects.select_related('actor')[:6]
        jobs = Job.objects.select_related('company').filter(status='open', deadline__gte=timezone.localdate(), company__approval='approved', company__is_active=True)[:4]
    elif user.role == 'student':
        applied_ids = set(user.applications.values_list('job_id', flat=True))
        eligible_jobs = [j for j in Job.objects.select_related('company').filter(status='open', deadline__gte=timezone.localdate(), company__approval='approved', company__is_active=True) if not j.eligibility_reasons(user) and j.pk not in applied_ids]
        stats = [('Eligible openings', len(eligible_jobs), 'Matched to your academics'), ('Applications sent', applications.count(), 'Your placement journey'), ('Shortlisted', applications.filter(status='shortlisted').count(), 'You are on their radar'), ('Selections', applications.filter(status='selected').count(), 'Confirmed by recruiters')]
        jobs = eligible_jobs[:4]
        activities = Activity.objects.select_related('actor').filter(Q(application__student=user) | Q(actor=user))[:6]
        summary = None
    else:
        stats = [('Your openings', user.jobs.count(), 'All recruitment campaigns'), ('Applications received', applications.count(), 'Students interested in you'), ('Shortlisted', applications.filter(status='shortlisted').count(), 'Ready for interviews'), ('Selected candidates', applications.filter(status='selected').values('student').distinct().count(), 'Your next generation of talent')]
        jobs = user.jobs.select_related('company')[:4]
        activities = Activity.objects.select_related('actor').filter(Q(application__job__company=user) | Q(actor=user))[:6]
        summary = None
    return render(request, 'portal/dashboard.html', {'nav': 'dashboard', 'stats': stats, 'jobs': jobs, 'interviews': interviews, 'activities': activities, 'summary': summary, 'recent_apps': applications[:5]})

@login_required
def jobs(request):
    qs = Job.objects.select_related('company')
    if request.user.role == 'student':
        qs = qs.filter(status='open', company__approval='approved', company__is_active=True, deadline__gte=timezone.localdate())
    elif request.user.role == 'company': qs = qs.filter(company=request.user)
    q = request.GET.get('q', '').strip()
    if q: qs = qs.filter(Q(title__icontains=q) | Q(company__display_name__icontains=q) | Q(location__icontains=q))
    branch = request.GET.get('branch', '')
    if branch in dict(BRANCHES): qs = [j for j in qs if branch in j.branches]
    state = request.GET.get('status', '')
    if state in dict(Job.STATUSES) and request.user.role != 'student':
        qs = [j for j in qs if j.status == state]
    applied_ids = set(request.user.applications.values_list('job_id', flat=True)) if request.user.role == 'student' else set()
    items = []
    for job in qs:
        job.reasons = job.eligibility_reasons(request.user) if request.user.role == 'student' else []
        job.already_applied = job.pk in applied_ids
        if request.GET.get('eligible') == '1' and request.user.role == 'student' and job.reasons: continue
        items.append(job)
    return render(request, 'portal/jobs.html', {'nav': 'jobs', 'page_obj': page(request, items, 9), 'q': q, 'branch': branch, 'branches': BRANCHES, 'state': state})

@login_required
def job_detail(request, pk):
    job = get_object_or_404(Job.objects.select_related('company'), pk=pk)
    user = request.user
    if user.role == 'company' and job.company_id != user.pk: raise Http404
    application = Application.objects.filter(student=user, job=job).first() if user.role == 'student' else None
    if user.role == 'student' and not application and (job.status != 'open' or not job.company.is_active or job.company.approval != 'approved'):
        raise Http404
    reasons = job.eligibility_reasons(user) if user.role == 'student' else []
    return render(request, 'portal/job_detail.html', {'nav': 'jobs', 'job': job, 'application': application, 'reasons': reasons})

@roles('company', 'admin')
def job_form(request, pk=None):
    job = get_object_or_404(Job, pk=pk) if pk else None
    user = request.user
    if job and user.role == 'company' and job.company_id != user.pk: raise Http404
    if user.role == 'company' and user.approval != 'approved':
        messages.error(request, 'Your company must be approved before posting an opening.')
        return redirect('jobs')
    if not job and user.role == 'admin':
        messages.info(request, 'Openings are created by recruiters, then reviewed by placement officers.')
        return redirect('jobs')
    form = JobForm(request.POST if request.method == 'POST' else None, instance=job)
    if request.method == 'POST':
        with transaction.atomic():
            user = User.objects.get(pk=user.pk)
            if user.role == 'company' and user.approval != 'approved': raise PermissionDenied
            job = Job.objects.select_for_update().get(pk=pk) if pk else None
            form = JobForm(request.POST, instance=job)
            if form.is_valid():
                saved = form.save(commit=False)
                if not job: saved.company = user
                # Recruiter edits always go back through officer review.
                saved.status = 'pending' if user.role == 'company' else saved.status
                saved.save()
                activity(user, f'{"Updated" if pk else "Submitted"} opening: {saved.title}.')
                messages.success(request, 'Opening saved.' + (' It is waiting for officer approval.' if user.role == 'company' else ''))
                return redirect('job_detail', pk=saved.pk)
    return render(request, 'portal/form.html', {'nav': 'jobs', 'form': form, 'heading': 'Edit opportunity' if job else 'Post an opportunity', 'eyebrow': 'Recruitment workspace', 'description': 'A clear role description helps the right students find you. Recruiter changes are reviewed by the placement office.', 'button': 'Save opportunity', 'cancel_url': reverse('jobs')})

@roles('admin', 'company')
@require_POST
def job_state(request, pk):
    with transaction.atomic():
        job = get_object_or_404(Job.objects.select_for_update(), pk=pk)
        target = request.POST.get('status')
        if request.user.role == 'company':
            if job.company_id != request.user.pk: raise Http404
            if target != 'closed': raise PermissionDenied
        elif target not in ('open', 'closed'): raise PermissionDenied
        if target == 'open' and (not job.company.is_active or job.company.approval != 'approved' or job.deadline < timezone.localdate()):
            messages.error(request, 'Approval requires an approved company and a current application deadline.')
        else:
            job.status = target; job.save(update_fields=['status'])
            activity(request.user, f'{job.title}: {job.get_status_display()}.')
            messages.success(request, 'Opening status updated.')
    return redirect('job_detail', pk=pk)

@roles('student')
@require_POST
def apply(request, pk):
    with transaction.atomic():
        job = get_object_or_404(Job.objects.select_for_update().select_related('company'), pk=pk)
        student = User.objects.get(pk=request.user.pk)
        reasons = job.eligibility_reasons(student)
        note = request.POST.get('cover_note', '').strip()
        if reasons:
            messages.error(request, ' '.join(reasons))
        elif len(note) > 1500:
            messages.error(request, 'Your cover note must be 1,500 characters or fewer.')
        else:
            application, created = Application.objects.get_or_create(student=student, job=job, defaults={'cover_note': note})
            if created: activity(request.user, f'{request.user} applied for {job.title}.', application)
            messages.success(request, 'Application sent. Good luck!' if created else 'You already applied for this opening.')
    return redirect('applications')

@login_required
def applications(request):
    qs = application_scope(request.user)
    status = request.GET.get('status', '')
    job_id = request.GET.get('job', '')
    if job_id:
        if job_id.isascii() and job_id.isdecimal() and len(job_id) <= 19 and 0 < int(job_id) <= 9223372036854775807:
            qs = qs.filter(job_id=int(job_id))
        else:
            qs = qs.none()
    q = request.GET.get('q', '').strip()
    if q: qs = qs.filter(Q(student__display_name__icontains=q) | Q(student__roll_no__icontains=q) | Q(job__title__icontains=q) | Q(job__company__display_name__icontains=q))
    counts = list(qs.order_by().values('status').annotate(total=Count('id')).order_by('status'))
    if status in dict(Application.STATUSES): qs = qs.filter(status=status)
    return render(request, 'portal/applications.html', {'nav': 'applications', 'page_obj': page(request, qs), 'status': status, 'statuses': Application.STATUSES, 'q': q, 'counts': counts, 'job_id': job_id})

@login_required
@require_POST
def application_state(request, pk):
    with transaction.atomic():
        actor = User.objects.get(pk=request.user.pk)
        a = get_object_or_404(application_scope(actor).select_for_update(), pk=pk)
        target = request.POST.get('status')
        allowed = {'applied': ['shortlisted', 'rejected'], 'shortlisted': ['selected', 'rejected']}
        if request.user.role == 'student':
            valid = actor.is_active and target == 'withdrawn' and a.can_withdraw
        else:
            valid = actor.is_active and actor.approval == 'approved' and target in allowed.get(a.status, [])
        if not valid:
            messages.error(request, 'This status change is not allowed. Refresh to see the current application state.')
        else:
            a.status = target
            if target == 'selected':
                a.selection_package = a.job.package
                a.selection_title = a.job.title
                a.selection_company = a.job.company.display_name
                a.selected_at = timezone.now()
            a.save()
            activity(request.user, f'{a.student}: {a.get_status_display()} for {a.job.title}.', a)
            messages.success(request, 'Application updated.')
    return application_redirect(request)

@login_required
def interviews(request):
    qs = Interview.objects.select_related('application__student', 'application__job__company').filter(application__in=application_scope(request.user)).exclude(application__status='withdrawn')
    return render(request, 'portal/interviews.html', {'nav': 'interviews', 'page_obj': page(request, qs), 'now': timezone.now()})

@roles('admin', 'company')
def schedule_interview(request, pk):
    a = get_object_or_404(application_scope(request.user), pk=pk)
    if request.user.approval != 'approved': raise PermissionDenied
    if a.status != 'shortlisted':
        messages.error(request, 'Shortlist the candidate before scheduling an interview.')
        return redirect('applications')
    existing = Interview.objects.filter(application=a).first()
    form = InterviewForm(request.POST if request.method == 'POST' else None, instance=existing)
    if request.method == 'POST':
        with transaction.atomic():
            actor = User.objects.get(pk=request.user.pk)
            if not actor.is_active or actor.approval != 'approved': raise PermissionDenied
            locked = get_object_or_404(application_scope(actor).select_for_update(), pk=a.pk)
            if locked.status != 'shortlisted':
                messages.error(request, 'The application status changed. Interview was not saved.')
                return redirect('applications')
            # Re-read the one-to-one record under the same write transaction.
            existing = Interview.objects.filter(application=locked).first()
            form = InterviewForm(request.POST, instance=existing)
            if form.is_valid():
                interview = form.save(commit=False); interview.application = locked
                starts, duration = interview.starts_at, interview.duration
                others = Interview.objects.filter(application__student=locked.student, application__status='shortlisted', starts_at__lt=starts + timedelta(minutes=duration)).exclude(application=locked)
                conflict = any(i.starts_at + timedelta(minutes=i.duration) > starts for i in others)
                if conflict:
                    form.add_error('starts_at', 'This student has another interview during that time.')
                else:
                    interview.save()
                    activity(actor, f'Interview scheduled for {locked.student} at {locked.job.company}.', locked)
                    messages.success(request, 'Interview scheduled. The student can see it in their workspace.')
                    return redirect('interviews')
    return render(request, 'portal/form.html', {'nav': 'interviews', 'form': form, 'heading': 'Schedule interview', 'eyebrow': str(a.job.company), 'description': f'{a.student} · {a.job.title}. Times use India Standard Time.', 'button': 'Save interview', 'cancel_url': reverse('applications')})

@roles('admin')
def people(request, kind):
    if kind not in ('students', 'companies'): raise Http404
    qs = User.objects.filter(role='student' if kind == 'students' else 'company').order_by('-date_joined')
    q = request.GET.get('q', '').strip()
    if q: qs = qs.filter(Q(display_name__icontains=q) | Q(email__icontains=q) | Q(roll_no__icontains=q))
    state = request.GET.get('status', '')
    if state in dict(User.APPROVAL): qs = qs.filter(approval=state)
    return render(request, 'portal/people.html', {'nav': kind, 'kind': kind, 'page_obj': page(request, qs), 'q': q, 'state': state})

@roles('admin')
@require_POST
def approve_user(request, pk):
    target = get_object_or_404(User.objects.exclude(role='admin'), pk=pk)
    status = request.POST.get('approval')
    if status not in dict(User.APPROVAL): raise PermissionDenied
    with transaction.atomic():
        target.approval = status; target.save(update_fields=['approval'])
        activity(request.user, f'{target}: account {target.get_approval_display().lower()}.')
    messages.success(request, f'{target} — {target.get_approval_display().lower()}.')
    return redirect('people', kind='students' if target.role == 'student' else 'companies')

@login_required
def profile(request):
    user = request.user
    form_type = {'student': StudentProfileForm, 'company': CompanyProfileForm, 'admin': OfficerProfileForm}[user.role]
    form = form_type(instance=user)
    if request.method == 'POST':
        saved = None
        old_resume = ''
        try:
            with transaction.atomic():
                # Bind to a current account, not a stale object from authentication.
                user = User.objects.select_for_update().get(pk=request.user.pk)
                if not user.is_active: raise PermissionDenied
                old_resume = user.resume.name
                form = form_type(request.POST, request.FILES, instance=user)
                if form.is_valid():
                    saved = form.save(commit=False)
                    sensitive = {'display_name', 'roll_no', 'branch', 'cgpa', 'backlogs', 'graduation_year'} if user.role == 'student' else {'display_name', 'website'}
                    changed = bool(sensitive.intersection(form.changed_data))
                    if changed and user.role != 'admin': saved.approval = 'pending'
                    # Update only submitted profile fields. Preserve credentials,
                    # sign-in metadata, role and any unrelated account state.
                    fields = [name for name in form.changed_data if name in form._meta.fields]
                    if changed and user.role != 'admin': fields.append('approval')
                    if fields: saved.save(update_fields=fields)
                    if old_resume and saved.resume.name != old_resume:
                        PendingResumeDeletion.objects.get_or_create(name=old_resume)
                        transaction.on_commit(lambda: retry_resume_deletions([old_resume]))
                    activity(user, f'{user} updated their profile.')
                    messages.success(request, 'Profile saved.' + (' Identity or academic changes are awaiting officer review.' if changed and user.role != 'admin' else ''))
                    return redirect('profile')
        except Exception:
            # File storage is outside the database transaction. Remove an upload
            # which was written before a later DB/audit failure rolled back.
            if saved is not None and saved.resume.name != old_resume and saved.resume._committed:
                discard_rolled_back_upload(saved.resume.name)
            raise
    return render(request, 'portal/profile.html', {'nav': 'profile', 'form': form})

@login_required
def resume(request, pk):
    student = get_object_or_404(User, role='student', pk=pk)
    user = request.user
    allowed = user.role == 'admin' or user.pk == student.pk or (user.role == 'company' and user.approval == 'approved' and Application.objects.filter(student=student, job__company=user).exists())
    if not allowed: raise Http404
    if not student.resume: raise Http404
    try: stream = student.resume.open('rb')
    except FileNotFoundError: raise Http404
    response = FileResponse(stream, as_attachment=True, filename=f'resume-{student.roll_no or student.pk}.pdf', content_type='application/pdf')
    response['Cache-Control'] = 'private, no-store'
    return response

@roles('admin')
def reports(request):
    branch = request.GET.get('branch', '')
    if branch not in dict(BRANCHES): branch = ''
    data = report_data(branch)
    data.update({'nav': 'reports', 'branch': branch, 'branch_options': BRANCHES})
    students = User.objects.filter(role='student', approval='approved', is_active=True).order_by('display_name')
    if branch: students = students.filter(branch=branch)
    best = {r['student_id']: r['best'] for r in data['selected'].values('student_id').annotate(best=Max('selection_package'))}
    records = [{'student': s, 'placed': s.pk in best, 'package': best.get(s.pk, '')} for s in students]
    export = request.GET.get('export')
    if export in ('csv', 'pdf'):
        rows = [[r['student'].display_name, r['student'].roll_no, r['student'].branch, 'Placed' if r['placed'] else 'Seeking', r['package']] for r in records]
        headers = ['Student', 'Roll number', 'Branch', 'Placement status', 'Best CTC (LPA)']
        if export == 'csv': return csv_response('placement-report.csv', headers, rows)
        return pdf_response('placement-report.pdf', 'Campus placement report', f"{data['placed']} of {data['total']} approved students placed · {data['rate']}% placement rate · Branch: {branch or 'All'}", headers, rows)
    data['page_obj'] = page(request, records)
    return render(request, 'portal/reports.html', data)

@login_required
def selection_record(request, pk):
    a = get_object_or_404(application_scope(request.user), pk=pk, status='selected')
    return pdf_response(f'selection-{a.pk}.pdf', 'Placement selection confirmation', 'A record issued by the campus placement portal.', ['Student', 'Company', 'Position', 'CTC (LPA)', 'Recorded'], [[a.student.display_name, a.selection_company, a.selection_title, a.selection_package, timezone.localtime(a.selected_at).strftime('%d %b %Y')]], footer='This confirms the selection recorded in the college portal. It is not an employment offer or a signed company offer letter.')
