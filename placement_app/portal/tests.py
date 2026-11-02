from datetime import timedelta
from decimal import Decimal
from tempfile import TemporaryDirectory
from django.test import TestCase, Client, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone
from django.db import IntegrityError, transaction
from .models import User, Job, Application, Interview
from .services import report_data, safe_cell

PASSWORD = 'TestCampus@2027!'

class PlacementWorkflows(TestCase):
    @classmethod
    def setUpTestData(cls):
        def user(email, role, **kwargs):
            return User.objects.create_user(username=email, email=email, password=PASSWORD, role=role, display_name=email.split('@')[0].title(), approval='approved', **kwargs)
        cls.admin = user('officer@example.com', 'admin')
        cls.student = user('student@example.com', 'student', roll_no='CS001', branch='CSE', cgpa=Decimal('8.5'))
        cls.other_student = user('otherstudent@example.com', 'student', roll_no='ME001', branch='ME', cgpa=Decimal('7.5'))
        cls.company = user('recruiter@example.com', 'company')
        cls.other_company = user('otherrecruiter@example.com', 'company')
        cls.job = Job.objects.create(company=cls.company, title='Graduate Engineer', location='Pune', package=12, min_cgpa=7, max_backlogs=0, branches=['CSE','IT'], deadline=timezone.localdate()+timedelta(days=10), description='Build good things.', status='open')

    def as_user(self, user): self.client.force_login(user)
    def post_state(self, a, state): return self.client.post(reverse('application_state', args=[a.pk]), {'status':state})
    def new_application(self, **kwargs):
        job = kwargs.pop('job', self.job)
        if kwargs.get('status') == 'selected':
            kwargs.update(selection_package=job.package, selection_title=job.title, selection_company=job.company.display_name, selected_at=timezone.now())
        return Application.objects.create(student=kwargs.pop('student', self.student), job=job, **kwargs)
    def job_payload(self):
        return {'title':'New Product Engineer','location':'Remote','job_type':'Full-time','package':'14','min_cgpa':'7.5','max_backlogs':'0','branches':['CSE','IT'],'deadline':str(timezone.localdate()+timedelta(days=20)),'description':'Design reliable products.'}
    def interview_payload(self, when=None):
        when = when or timezone.now()+timedelta(days=3)
        return {'starts_at':timezone.localtime(when).strftime('%Y-%m-%dT%H:%M'),'duration':45,'mode':'Online','venue':'https://example.com/meeting','notes':'Bring a resume.'}

    def test_login_accepts_case_insensitive_email_and_logout_is_post_only(self):
        response = self.client.post(reverse('login'), {'username':'STUDENT@EXAMPLE.COM','password':PASSWORD})
        self.assertRedirects(response, reverse('dashboard'))
        self.assertEqual(self.client.get(reverse('logout')).status_code, 405)
        self.assertRedirects(self.client.post(reverse('logout')), reverse('login'))
        self.assertRedirects(self.client.get(reverse('jobs')), reverse('login')+'?next=/jobs/')

    def test_all_role_workspaces_render(self):
        for user in (self.admin, self.student, self.company):
            self.as_user(user)
            for route in ('dashboard','jobs','applications','interviews','profile','password_change'):
                with self.subTest(role=user.role, route=route): self.assertEqual(self.client.get(reverse(route)).status_code, 200)
        self.as_user(self.admin)
        for path in (reverse('people',args=['students']),reverse('people',args=['companies']),reverse('reports')):
            self.assertEqual(self.client.get(path).status_code, 200)

    def test_registration_student_pending_and_cannot_self_assign_admin(self):
        payload = {'role':'student','display_name':'New Student','email':'new@example.com','roll_no':'CSNEW','branch':'CSE','cgpa':'8.7','graduation_year':2027,'password1':PASSWORD,'password2':PASSWORD}
        response = self.client.post(reverse('register'), payload)
        self.assertRedirects(response, reverse('dashboard'))
        u = User.objects.get(email='new@example.com')
        self.assertEqual(u.approval, 'pending'); self.assertTrue(u.check_password(PASSWORD))
        self.assertFalse(u.is_staff)
        self.client.post(reverse('apply', args=[self.job.pk])); self.assertFalse(u.applications.exists())
        self.client.logout(); payload.update(email='adminhack@example.com',roll_no='EVIL',role='admin')
        self.assertEqual(self.client.post(reverse('register'), payload).status_code, 200)
        self.assertFalse(User.objects.filter(email='adminhack@example.com').exists())

    def test_company_registration_does_not_require_student_fields(self):
        response = self.client.post(reverse('register'), {'role':'company','display_name':'Fresh Company','email':'fresh@example.com','website':'https://example.com','password1':PASSWORD,'password2':PASSWORD})
        self.assertRedirects(response, reverse('dashboard'))
        u = User.objects.get(email='fresh@example.com'); self.assertIsNone(u.roll_no); self.assertEqual(u.cgpa, 0)
        self.assertEqual(u.approval, 'pending')
        self.client.post(reverse('job_create'), self.job_payload())
        self.assertFalse(u.jobs.exists())

    def test_registration_rejects_duplicate_email_and_bad_academics(self):
        p = {'role':'student','display_name':'Duplicate','email':'STUDENT@EXAMPLE.COM','roll_no':'NEW','branch':'CSE','cgpa':11,'graduation_year':2027,'password1':PASSWORD,'password2':PASSWORD}
        response = self.client.post(reverse('register'), p)
        self.assertContains(response, 'An account already uses this email.')
        self.assertContains(response, 'Ensure this value is less than or equal to 10.')

    def test_complete_recruitment_workflow(self):
        self.as_user(self.company)
        self.client.post(reverse('job_create'), self.job_payload())
        j = Job.objects.get(title='New Product Engineer'); self.assertEqual(j.status,'pending')
        self.as_user(self.student); self.assertEqual(self.client.get(reverse('job_detail',args=[j.pk])).status_code,404)
        self.as_user(self.admin); self.client.post(reverse('job_state',args=[j.pk]),{'status':'open'})
        self.as_user(self.student); self.client.post(reverse('apply',args=[j.pk]),{'cover_note':'I would love to contribute.'})
        a = Application.objects.get(job=j,student=self.student)
        self.assertEqual(a.cover_note,'I would love to contribute.')
        self.as_user(self.company); self.post_state(a,'shortlisted')
        a.refresh_from_db(); self.assertEqual(a.status,'shortlisted')
        self.client.post(reverse('schedule_interview',args=[a.pk]),self.interview_payload())
        self.assertTrue(Interview.objects.filter(application=a).exists())
        self.as_user(self.student); self.assertContains(self.client.get(reverse('interviews')),'Join meeting')
        self.as_user(self.company); self.post_state(a,'selected')
        a.refresh_from_db(); self.assertEqual(a.status,'selected')
        self.as_user(self.student)
        response = self.client.get(reverse('selection_record',args=[a.pk])); self.assertEqual(response['Content-Type'],'application/pdf'); self.assertTrue(response.content.startswith(b'%PDF'))
        self.as_user(self.admin); self.assertEqual(report_data()['placed'],1)
        self.client.logout(); self.as_user(self.student)
        self.assertContains(self.client.get(reverse('applications')),'Selected')

    def test_duplicate_application_is_idempotent_and_unique_in_database(self):
        self.as_user(self.student)
        for _ in range(2): self.client.post(reverse('apply',args=[self.job.pk]))
        self.assertEqual(Application.objects.count(),1)
        with self.assertRaises(IntegrityError), transaction.atomic(): self.new_application()

    def test_each_eligibility_requirement_blocks_application(self):
        self.as_user(self.student)
        for field, value in [('approval','pending'),('cgpa',Decimal('5.0')),('backlogs',2),('branch','ME')]:
            original = getattr(self.student,field); setattr(self.student,field,value); self.student.save()
            self.client.post(reverse('apply',args=[self.job.pk]))
            self.assertFalse(Application.objects.exists(),field)
            setattr(self.student,field,original); self.student.save()

    def test_closed_expired_and_revoked_company_jobs_block_application(self):
        self.as_user(self.student)
        for field,value in [('status','closed'),('deadline',timezone.localdate()-timedelta(days=1))]:
            original=getattr(self.job,field); setattr(self.job,field,value); self.job.save()
            self.client.post(reverse('apply',args=[self.job.pk])); self.assertFalse(Application.objects.exists())
            setattr(self.job,field,original); self.job.save()
        self.company.approval='rejected'; self.company.save()
        self.client.post(reverse('apply',args=[self.job.pk])); self.assertFalse(Application.objects.exists())
        self.assertNotContains(self.client.get(reverse('jobs')), 'Graduate Engineer')

    def test_role_and_company_boundaries(self):
        a=self.new_application()
        self.as_user(self.other_company)
        for route in ('job_detail','job_edit','job_state'):
            url=reverse(route,args=[self.job.pk])
            response=self.client.post(url,{'status':'closed'}) if route=='job_state' else self.client.get(url)
            self.assertEqual(response.status_code,404)
        self.assertEqual(self.post_state(a,'shortlisted').status_code,404)
        self.assertEqual(self.client.get(reverse('schedule_interview',args=[a.pk])).status_code,404)
        self.as_user(self.student)
        for route in ('reports','job_create'):
            self.assertEqual(self.client.get(reverse(route)).status_code,403)
        self.assertEqual(self.client.post(reverse('approve_user',args=[self.company.pk]),{'approval':'approved'}).status_code,403)
        self.post_state(a,'selected'); a.refresh_from_db(); self.assertEqual(a.status,'applied')
        self.as_user(self.other_student); self.assertEqual(self.post_state(a,'withdrawn').status_code,404)

    def test_final_status_and_invalid_transition_are_preserved(self):
        a=self.new_application(); self.as_user(self.company)
        self.post_state(a,'selected'); a.refresh_from_db(); self.assertEqual(a.status,'applied')
        self.post_state(a,'shortlisted'); self.post_state(a,'selected'); self.post_state(a,'rejected')
        a.refresh_from_db(); self.assertEqual(a.status,'selected')

    def test_withdrawal_cancels_upcoming_schedule_and_cannot_reapply(self):
        a=self.new_application(status='shortlisted'); Interview.objects.create(application=a,starts_at=timezone.now()+timedelta(days=1),mode='On campus',venue='Room 2')
        self.as_user(self.student); self.post_state(a,'withdrawn'); a.refresh_from_db(); self.assertEqual(a.status,'withdrawn')
        self.assertNotContains(self.client.get(reverse('interviews')),'Room 2')
        self.client.post(reverse('apply',args=[self.job.pk])); a.refresh_from_db(); self.assertEqual(a.status,'withdrawn')
        self.as_user(self.company); self.assertRedirects(self.client.get(reverse('schedule_interview',args=[a.pk])),reverse('applications'))

    def test_interview_requires_shortlist_future_time_and_safe_url(self):
        a=self.new_application(); self.as_user(self.company)
        self.assertRedirects(self.client.get(reverse('schedule_interview',args=[a.pk])),reverse('applications'))
        self.post_state(a,'shortlisted')
        p=self.interview_payload(timezone.now()-timedelta(days=1)); p['venue']='javascript:alert(1)'
        response=self.client.post(reverse('schedule_interview',args=[a.pk]),p)
        self.assertContains(response,'Schedule interviews in the future.')
        self.assertContains(response,'Enter a valid public http:// or https:// meeting URL without credentials.')
        self.assertFalse(Interview.objects.exists())

    def test_interview_overlap_is_blocked_but_reschedule_is_allowed(self):
        a=self.new_application(status='shortlisted')
        other_job=Job.objects.create(company=self.other_company,title='Other',location='Remote',package=8,min_cgpa=6,branches=['CSE'],deadline=self.job.deadline,status='open')
        other=self.new_application(job=other_job,status='shortlisted')
        when=timezone.now()+timedelta(days=3)
        Interview.objects.create(application=other,starts_at=when,duration=60,mode='On campus',venue='Room 3')
        self.as_user(self.company)
        response=self.client.post(reverse('schedule_interview',args=[a.pk]),self.interview_payload(when+timedelta(minutes=30)))
        self.assertContains(response,'This student has another interview during that time.')
        self.assertFalse(Interview.objects.filter(application=a).exists())
        self.client.post(reverse('schedule_interview',args=[a.pk]),self.interview_payload(when+timedelta(hours=2)))
        self.assertTrue(Interview.objects.filter(application=a).exists())
        self.client.post(reverse('schedule_interview',args=[a.pk]),self.interview_payload(when+timedelta(hours=3)))
        self.assertEqual(Interview.objects.filter(application=a).count(),1)

    def test_profile_changes_revoke_approval_but_contact_only_changes_do_not(self):
        self.as_user(self.student)
        p={'display_name':self.student.display_name,'roll_no':'CS001','branch':'CSE','cgpa':'8.5','backlogs':0,'graduation_year':2027,'phone':'1234567890','bio':'Hello'}
        self.client.post(reverse('profile'),p); self.student.refresh_from_db(); self.assertEqual(self.student.approval,'approved')
        p['cgpa']='9.5'; self.client.post(reverse('profile'),p); self.student.refresh_from_db(); self.assertEqual(self.student.approval,'pending')
        self.as_user(self.admin); self.client.post(reverse('approve_user',args=[self.student.pk]),{'approval':'approved'})
        self.student.refresh_from_db(); self.assertEqual(self.student.approval,'approved')

    def test_resume_validation_private_access_and_replacement_cleanup(self):
        with TemporaryDirectory() as directory, override_settings(MEDIA_ROOT=directory):
            p={'display_name':self.student.display_name,'roll_no':'CS001','branch':'CSE','cgpa':'8.5','backlogs':0,'graduation_year':2027}
            self.as_user(self.student)
            p['resume']=SimpleUploadedFile('bad.pdf',b'not a pdf',content_type='application/pdf')
            self.assertContains(self.client.post(reverse('profile'),p),'Upload a valid PDF document.')
            p['resume']=SimpleUploadedFile('resume.pdf',b'%PDF-1.4 demo',content_type='application/pdf')
            self.client.post(reverse('profile'),p); self.student.refresh_from_db(); old=self.student.resume.name
            url=reverse('resume',args=[self.student.pk]); response=self.client.get(url)
            self.assertEqual(response.status_code,200); self.assertIn('attachment',response['Content-Disposition']); response.close()
            self.as_user(self.other_student); self.assertEqual(self.client.get(url).status_code,404)
            self.as_user(self.company); self.assertEqual(self.client.get(url).status_code,404)
            self.new_application(); self.assertEqual(self.client.get(url).status_code,200)
            self.as_user(self.other_company); self.assertEqual(self.client.get(url).status_code,404)
            self.as_user(self.student); p['resume']=SimpleUploadedFile('resume.pdf',b'%PDF-1.4 updated',content_type='application/pdf')
            with self.captureOnCommitCallbacks(execute=True): self.client.post(reverse('profile'),p)
            self.assertFalse(self.student.resume.storage.exists(old))

    def test_oversize_resume_is_rejected(self):
        self.as_user(self.student)
        p={'display_name':self.student.display_name,'roll_no':'CS001','branch':'CSE','cgpa':'8.5','backlogs':0,'graduation_year':2027,'resume':SimpleUploadedFile('large.pdf',b'%PDF-'+b'0'*(5*1024*1024),content_type='application/pdf')}
        self.assertContains(self.client.post(reverse('profile'),p),'Resume must be 5 MB or smaller.')

    def test_reports_deduplicate_placements_and_respect_filters(self):
        self.new_application(status='selected')
        j=Job.objects.create(company=self.other_company,title='Second',location='Remote',package=20,min_cgpa=6,branches=['CSE'],deadline=self.job.deadline,status='open')
        self.new_application(job=j,status='selected')
        data=report_data(); self.assertEqual(data['placed'],1); self.assertEqual(data['total'],2); self.assertEqual(data['rate'],50); self.assertEqual(data['average'],20)
        self.as_user(self.admin)
        response=self.client.get(reverse('reports'),{'branch':'CSE','export':'csv'})
        self.assertIn(b'CS001',response.content); self.assertNotIn(b'ME001',response.content)
        response=self.client.get(reverse('reports'),{'export':'pdf'}); self.assertTrue(response.content.startswith(b'%PDF'))
        self.as_user(self.company); self.assertEqual(self.client.get(reverse('reports'),{'export':'csv'}).status_code,403)

    def test_csv_neutralizes_formula_inputs(self):
        for value in ('=HYPERLINK("bad")','+cmd','-cmd','@SUM(1)','  =cmd'):
            self.assertTrue(safe_cell(value).startswith("'"))
        self.assertEqual(safe_cell('Aarav Mehta'),'Aarav Mehta')

    def test_mutations_require_csrf_and_post(self):
        client=Client(enforce_csrf_checks=True); client.force_login(self.student)
        response=client.post(reverse('apply',args=[self.job.pk])); self.assertEqual(response.status_code,403)
        self.as_user(self.student); self.assertEqual(self.client.get(reverse('apply',args=[self.job.pk])).status_code,405)
        self.assertFalse(Application.objects.exists())

    def test_user_supplied_text_is_escaped(self):
        self.student.display_name='<script>alert(1)</script>'; self.student.save()
        self.new_application(cover_note='<img src=x onerror=alert(1)>')
        self.as_user(self.company); response=self.client.get(reverse('applications'))
        self.assertContains(response,'&lt;script&gt;'); self.assertNotContains(response,'<img src=x')

    def test_opening_edits_require_renewed_approval_and_preserve_applications(self):
        a=self.new_application(); self.as_user(self.company)
        self.client.post(reverse('job_edit',args=[self.job.pk]),self.job_payload())
        self.job.refresh_from_db(); self.assertEqual(self.job.status,'pending'); self.assertTrue(Application.objects.filter(pk=a.pk).exists())
        self.as_user(self.admin); self.client.post(reverse('job_state',args=[self.job.pk]),{'status':'open'})
        self.job.refresh_from_db(); self.assertEqual(self.job.status,'open')

    def test_pending_company_cannot_advance_candidates(self):
        a=self.new_application(); self.company.approval='pending'; self.company.save()
        self.as_user(self.company); self.post_state(a,'shortlisted')
        a.refresh_from_db(); self.assertEqual(a.status,'applied')
        self.assertEqual(self.client.get(reverse('schedule_interview',args=[a.pk])).status_code,403)

    def test_search_filters_and_empty_states(self):
        self.as_user(self.student)
        self.assertContains(self.client.get(reverse('jobs'),{'q':'graduate','branch':'CSE','eligible':'1'}),'Graduate Engineer')
        self.assertNotContains(self.client.get(reverse('jobs'),{'branch':'ME'}),'Graduate Engineer')
        self.assertContains(self.client.get(reverse('jobs'),{'q':'no-such-company'}),'No opportunities found')

    def test_selection_download_is_owner_scoped_and_only_after_selection(self):
        a=self.new_application(); self.as_user(self.student)
        self.assertEqual(self.client.get(reverse('selection_record',args=[a.pk])).status_code,404)
        a.status='selected'; a.save(); self.as_user(self.other_student)
        self.assertEqual(self.client.get(reverse('selection_record',args=[a.pk])).status_code,404)
        self.as_user(self.other_company); self.assertEqual(self.client.get(reverse('selection_record',args=[a.pk])).status_code,404)

    def test_selection_facts_survive_job_and_company_edits(self):
        a=self.new_application(status='shortlisted'); self.as_user(self.company)
        self.post_state(a,'selected'); a.refresh_from_db()
        original_company=a.selection_company
        self.job.package=99; self.job.title='Renamed role'; self.job.save()
        self.company.display_name='Renamed company'; self.company.save()
        a.refresh_from_db()
        self.assertEqual(a.selection_package,12)
        self.assertEqual(a.selection_title,'Graduate Engineer')
        self.assertEqual(a.selection_company,original_company)
        self.assertEqual(report_data()['average'],12)
