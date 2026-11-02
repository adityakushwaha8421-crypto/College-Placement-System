from uuid import uuid4
from django.contrib.auth.models import AbstractUser, UserManager
from django.core.validators import MinValueValidator, MaxValueValidator, FileExtensionValidator
from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone

BRANCHES = [('CSE', 'Computer Science'), ('IT', 'Information Technology'), ('ECE', 'Electronics'), ('EE', 'Electrical'), ('ME', 'Mechanical'), ('CE', 'Civil')]

def resume_path(instance, filename):
    return f'resumes/{instance.pk}/{uuid4().hex}.pdf'

class PlacementUserManager(UserManager):
    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault('role', 'admin')
        extra_fields.setdefault('approval', 'approved')
        return super().create_superuser(username, email, password, **extra_fields)


class User(AbstractUser):
    ROLE = [('admin', 'Placement officer'), ('student', 'Student'), ('company', 'Recruiter')]
    APPROVAL = [('pending', 'Pending review'), ('approved', 'Approved'), ('rejected', 'Not approved')]
    username = models.CharField(max_length=254, unique=True)
    email = models.EmailField(unique=True)
    objects = PlacementUserManager()
    role = models.CharField(max_length=12, choices=ROLE, default='student')
    display_name = models.CharField(max_length=100)
    approval = models.CharField(max_length=12, choices=APPROVAL, default='pending')
    roll_no = models.CharField(max_length=25, unique=True, null=True, blank=True)
    branch = models.CharField(max_length=5, choices=BRANCHES, blank=True)
    cgpa = models.DecimalField(max_digits=4, decimal_places=2, default=0, validators=[MinValueValidator(0), MaxValueValidator(10)])
    backlogs = models.PositiveSmallIntegerField(default=0, validators=[MaxValueValidator(50)])
    graduation_year = models.PositiveSmallIntegerField(default=2027, validators=[MinValueValidator(2000), MaxValueValidator(2100)])
    phone = models.CharField(max_length=20, blank=True)
    website = models.URLField(blank=True)
    bio = models.TextField(max_length=1500, blank=True)
    resume = models.FileField(upload_to=resume_path, blank=True, validators=[FileExtensionValidator(['pdf'])])

    class Meta:
        constraints = [models.UniqueConstraint(Lower('email'), name='unique_login_email_case_insensitive')]

    def __str__(self):
        return self.display_name or self.username

    @property
    def initials(self):
        return ''.join(n[0] for n in str(self).split()[:2]).upper() or 'U'

class Job(models.Model):
    STATUSES = [('pending', 'Awaiting approval'), ('open', 'Open'), ('closed', 'Closed')]
    company = models.ForeignKey(User, on_delete=models.PROTECT, related_name='jobs')
    title = models.CharField(max_length=150)
    location = models.CharField(max_length=100)
    job_type = models.CharField(max_length=20, choices=[('Full-time', 'Full-time'), ('Internship', 'Internship')], default='Full-time')
    package = models.DecimalField('CTC (LPA)', max_digits=6, decimal_places=2, validators=[MinValueValidator(0.01), MaxValueValidator(999)])
    min_cgpa = models.DecimalField('Minimum CGPA', max_digits=4, decimal_places=2, default=6, validators=[MinValueValidator(0), MaxValueValidator(10)])
    max_backlogs = models.PositiveSmallIntegerField(default=0, validators=[MaxValueValidator(50)])
    branches = models.JSONField(default=list)
    deadline = models.DateField()
    description = models.TextField(max_length=6000)
    status = models.CharField(max_length=10, choices=STATUSES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-pk']

    def __str__(self):
        return self.title

    @property
    def accepting(self):
        return self.status == 'open' and self.company.is_active and self.company.approval == 'approved' and self.deadline >= timezone.localdate()

    def eligibility_reasons(self, student):
        reasons = []
        if not student.is_active or student.approval != 'approved': reasons.append('Your student profile needs approval.')
        if not self.accepting: reasons.append('This opening is not accepting applications.')
        if student.branch not in self.branches: reasons.append('Your branch does not match this opening.')
        if student.cgpa < self.min_cgpa: reasons.append(f'Minimum CGPA is {self.min_cgpa}.')
        if student.backlogs > self.max_backlogs: reasons.append(f'At most {self.max_backlogs} active backlogs allowed.')
        return reasons

class Application(models.Model):
    STATUSES = [('applied', 'Applied'), ('shortlisted', 'Shortlisted'), ('selected', 'Selected'), ('rejected', 'Rejected'), ('withdrawn', 'Withdrawn')]
    student = models.ForeignKey(User, on_delete=models.PROTECT, related_name='applications')
    job = models.ForeignKey(Job, on_delete=models.PROTECT, related_name='applications')
    status = models.CharField(max_length=15, choices=STATUSES, default='applied')
    cover_note = models.TextField(max_length=1500, blank=True)
    selection_package = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    selection_title = models.CharField(max_length=150, blank=True)
    selection_company = models.CharField(max_length=100, blank=True)
    selected_at = models.DateTimeField(null=True, blank=True)
    applied_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-applied_at', '-pk']
        constraints = [models.UniqueConstraint(fields=['student', 'job'], name='one_application_per_student_job')]

    @property
    def display_title(self):
        return self.selection_title if self.status == 'selected' else self.job.title

    @property
    def display_company(self):
        return self.selection_company if self.status == 'selected' else self.job.company.display_name

    @property
    def display_package(self):
        return self.selection_package if self.status == 'selected' else self.job.package

    @property
    def can_withdraw(self):
        return self.status in ('applied', 'shortlisted')

class Interview(models.Model):
    application = models.OneToOneField(Application, on_delete=models.CASCADE, related_name='interview')
    starts_at = models.DateTimeField()
    duration = models.PositiveSmallIntegerField(default=45, validators=[MinValueValidator(15), MaxValueValidator(240)])
    mode = models.CharField(max_length=10, choices=[('Online', 'Online'), ('On campus', 'On campus')])
    venue = models.CharField('Venue or meeting URL', max_length=300)
    notes = models.TextField(max_length=1500, blank=True)

    class Meta:
        ordering = ['starts_at']

class Activity(models.Model):
    actor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    application = models.ForeignKey(Application, on_delete=models.SET_NULL, null=True, blank=True)
    message = models.CharField(max_length=250)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-pk']


class PendingResumeDeletion(models.Model):
    """Keep ownership of superseded uploads until storage confirms deletion."""
    name = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    attempts = models.PositiveIntegerField(default=0)
    last_error = models.TextField(blank=True)
