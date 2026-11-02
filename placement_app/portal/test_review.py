"""Regressions reproduced during the project review."""
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from django.core.exceptions import PermissionDenied
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from .forms import RegistrationForm
from .models import User, Application, Job, Interview
from .services import application_scope, report_data
from . import tests as baseline

class ReviewRegressions(TestCase):
    @classmethod
    def setUpTestData(cls):
        baseline.PlacementWorkflows.setUpTestData.__func__(cls)

    def registration(self, **changes):
        return {'role':'company','display_name':'New company','email':'new-company@example.com','website':'https://example.com','password1':'NewCampus@2027!','password2':'NewCampus@2027!',**changes}

    def test_malformed_interview_url_shows_validation_error(self):
        a=Application.objects.create(student=self.student,job=self.job,status='shortlisted')
        self.client.force_login(self.company)
        for url in ('https://[invalid','https://example.com:notaport','https://','https://user:pass@example.com'):
            with self.subTest(url=url):
                payload=baseline.PlacementWorkflows.interview_payload(self)
                payload['venue']=url
                response=self.client.post(reverse('schedule_interview',args=[a.pk]),payload)
                self.assertEqual(response.status_code,200)
                self.assertContains(response,'Enter a valid public http:// or https:// meeting URL without credentials.')
        self.assertFalse(Interview.objects.exists())

    def test_invalid_job_filter_never_crashes_or_exposes_other_results(self):
        Application.objects.create(student=self.student,job=self.job)
        self.client.force_login(self.admin)
        for value in ('²','9'*100,'1.1','-1','0','9223372036854775808'):
            with self.subTest(value=value):
                response=self.client.get(reverse('applications'),{'job':value})
                self.assertEqual(response.status_code,200)
                self.assertEqual(response.context['page_obj'].paginator.count,0)

    def test_registration_ignores_fields_from_the_other_role(self):
        form=RegistrationForm(self.registration(roll_no=self.student.roll_no,branch='invalid',cgpa='invalid',graduation_year='invalid'))
        self.assertTrue(form.is_valid(),form.errors)
        response=self.client.post(reverse('register'),self.registration(roll_no=self.student.roll_no,branch='CSE',cgpa='invalid',graduation_year='invalid'))
        self.assertRedirects(response,reverse('dashboard'))
        self.assertIsNone(User.objects.get(email='new-company@example.com').roll_no)
        self.client.logout()
        data=self.registration(role='student',email='new-student@example.com',roll_no='CSNEW',branch='CSE',cgpa='8.2',graduation_year='2027',website='not-a-url')
        self.assertRedirects(self.client.post(reverse('register'),data),reverse('dashboard'))
        self.assertEqual(User.objects.get(email='new-student@example.com').website,'')

    def test_long_valid_email_preserves_username_constraints(self):
        email='a'*64+'@'+'b'*60+'.'+'c'*40+'.com'
        self.assertRedirects(self.client.post(reverse('register'),self.registration(email=email)),reverse('dashboard'))
        u=User.objects.get(email=email)
        self.assertLessEqual(len(u.username),User._meta.get_field('username').max_length)
        self.client.logout()
        self.assertTrue(self.client.login(username=email,password='NewCampus@2027!'))

    def test_email_uniqueness_matches_case_insensitive_login(self):
        with self.assertRaises(IntegrityError),transaction.atomic():
            User.objects.create_user(username='another-username',email='STUDENT@EXAMPLE.COM',password='x')

    def test_unknown_roles_cannot_read_all_applications(self):
        self.student.role='unexpected'
        with self.assertRaises(PermissionDenied): application_scope(self.student)

    def test_existing_applicant_can_view_closed_or_pending_job(self):
        Application.objects.create(student=self.student,job=self.job)
        self.client.force_login(self.student)
        for state in ('closed','pending'):
            self.job.status=state;self.job.save()
            self.assertEqual(self.client.get(reverse('job_detail',args=[self.job.pk])).status_code,200)
        self.client.force_login(self.other_student)
        self.assertEqual(self.client.get(reverse('job_detail',args=[self.job.pk])).status_code,404)

    def test_application_filters_survive_status_actions_and_chips(self):
        a=Application.objects.create(student=self.student,job=self.job)
        self.client.force_login(self.company)
        query=f'job={self.job.pk}&q=Student&page=1'
        response=self.client.get(reverse('applications')+'?'+query)
        self.assertContains(response,f'job={self.job.pk}&amp;q=Student')
        response=self.client.post(reverse('application_state',args=[a.pk])+'?'+query,{'status':'shortlisted'})
        self.assertIn('job=',response.url);self.assertIn('q=Student',response.url)

    def test_rejected_and_selected_interviews_do_not_offer_join_links(self):
        a=Application.objects.create(student=self.student,job=self.job,status='rejected')
        Interview.objects.create(application=a,starts_at=timezone.now()+timedelta(days=2),mode='Online',venue='https://example.com/meeting')
        self.client.force_login(self.student)
        response=self.client.get(reverse('interviews'))
        self.assertNotContains(response,'Join meeting')
        self.assertContains(response,'Rejected')

    def test_empty_profile_post_is_bound_and_reports_errors(self):
        self.client.force_login(self.student)
        response=self.client.post(reverse('profile'),{})
        self.assertTrue(response.context['form'].is_bound)
        self.assertTrue(response.context['form'].errors)

    def test_authenticated_pages_and_downloads_prevent_shared_caching(self):
        self.client.force_login(self.admin)
        for url in ('/','/applications/','/reports/?export=csv','/reports/?export=pdf'):
            self.assertIn('no-store',self.client.get(url).get('Cache-Control',''))

    def test_selection_facts_are_used_consistently_in_application_ui(self):
        a=Application.objects.create(student=self.student,job=self.job,status='selected',selection_package=12,selection_title='Original role',selection_company='Original company',selected_at=timezone.now())
        self.job.title='Changed role';self.job.package=99;self.job.save()
        self.company.display_name='Changed company';self.company.save()
        self.client.force_login(self.student)
        response=self.client.get(reverse('applications'))
        self.assertContains(response,'Original role');self.assertContains(response,'Original company')
        self.assertNotContains(response,'Changed role');self.assertNotContains(response,'99.00 LPA')

    def test_resume_cleanup_failure_does_not_fail_committed_profile_update(self):
        from .models import PendingResumeDeletion
        with TemporaryDirectory() as directory,override_settings(MEDIA_ROOT=directory):
            self.student.resume.save('resume.pdf',SimpleUploadedFile('resume.pdf',b'%PDF-old'),save=True)
            old=self.student.resume.name
            self.client.force_login(self.student)
            payload={'display_name':self.student.display_name,'roll_no':'CS001','branch':'CSE','cgpa':'8.5','backlogs':0,'graduation_year':2027,'resume':SimpleUploadedFile('resume.pdf',b'%PDF-new',content_type='application/pdf')}
            storage=User._meta.get_field('resume').storage
            with patch.object(storage,'delete',side_effect=PermissionError('Simulated file lock')):
                with self.captureOnCommitCallbacks(execute=True): response=self.client.post(reverse('profile'),payload)
            self.assertEqual(response.status_code,302)
            self.student.refresh_from_db();self.assertNotEqual(old,self.student.resume.name)
            self.assertTrue(PendingResumeDeletion.objects.filter(name=old).exists())
            from .uploads import retry_resume_deletions
            retry_resume_deletions()
            self.assertFalse(storage.exists(old));self.assertFalse(PendingResumeDeletion.objects.exists())

    def test_resume_is_removed_if_profile_database_save_rolls_back(self):
        with TemporaryDirectory() as directory,override_settings(MEDIA_ROOT=directory):
            self.client.force_login(self.student)
            payload={'display_name':self.student.display_name,'roll_no':'CS001','branch':'CSE','cgpa':'8.5','backlogs':0,'graduation_year':2027,'resume':SimpleUploadedFile('resume.pdf',b'%PDF-new',content_type='application/pdf')}
            with patch('portal.views.activity',side_effect=RuntimeError('Simulated failed transaction')):
                with self.assertRaises(RuntimeError):self.client.post(reverse('profile'),payload)
            self.assertFalse(any(p.is_file() for p in Path(directory).rglob('*')))
            self.student.refresh_from_db();self.assertFalse(self.student.resume)

    def test_large_record_paths_return_not_found(self):
        self.client.force_login(self.admin)
        for pk in ('9'*100, '9223372036854775808', '0'):
            self.assertEqual(self.client.get(f'/jobs/{pk}/').status_code, 404)

    def test_created_superuser_is_an_approved_placement_officer(self):
        user = User.objects.create_superuser(username='root@example.com', email='root@example.com', password='NewCampus@2027!')
        self.assertEqual(user.role, 'admin')
        self.assertEqual(user.approval, 'approved')
        self.client.force_login(user)
        self.assertEqual(self.client.get(reverse('reports')).status_code, 200)

    def test_officer_profile_uses_personal_labels(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('profile'))
        self.assertContains(response, 'Full name')
        self.assertNotContains(response, 'Company name')

    def test_disabled_company_cannot_accept_applications(self):
        self.company.is_active = False; self.company.save()
        self.client.force_login(self.student)
        self.client.post(reverse('apply', args=[self.job.pk]))
        self.assertFalse(Application.objects.exists())
        self.assertNotContains(self.client.get(reverse('jobs')), 'Graduate Engineer')

    def test_dashboard_excludes_openings_already_applied_to(self):
        Application.objects.create(student=self.student, job=self.job)
        self.client.force_login(self.student)
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.context['stats'][0][1], 0)
        self.assertEqual(len(response.context['jobs']), 0)

    def test_unknown_role_is_denied_but_can_still_sign_out(self):
        self.student.role = 'unexpected'; self.student.save(update_fields=['role'])
        self.client.force_login(self.student)
        self.assertEqual(self.client.get(reverse('applications')).status_code, 403)
        self.assertRedirects(self.client.post(reverse('logout')), reverse('login'))
