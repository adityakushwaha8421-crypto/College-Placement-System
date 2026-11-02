from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.core.exceptions import ValidationError
from django.utils import timezone
from urllib.parse import urlsplit
from django.core.validators import URLValidator
from .models import User, Job, Interview, BRANCHES

class LoginForm(AuthenticationForm):
    username = forms.CharField(label='Email address', widget=forms.TextInput(attrs={'autofocus': True, 'placeholder': 'you@college.edu', 'autocomplete': 'username'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'autocomplete': 'current-password', 'placeholder': 'Enter your password'}))

class RegistrationForm(UserCreationForm):
    role = forms.ChoiceField(choices=[('student', 'Student'), ('company', 'Recruiter')])
    class Meta:
        model = User
        fields = ['role', 'display_name', 'email', 'roll_no', 'branch', 'cgpa', 'graduation_year', 'website']
        labels = {'display_name': 'Full name / company name', 'roll_no': 'Student roll number', 'website': 'Company website'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        role = self.data.get('role') if self.is_bound else None
        # Ignore values from the other role before individual field validation.
        ignored = ('roll_no', 'branch', 'cgpa', 'graduation_year') if role == 'company' else ('website',) if role == 'student' else ()
        for name in ignored:
            self.fields[name].disabled = True
        for name in ('cgpa', 'graduation_year'):
            self.fields[name].required = False

    def clean_email(self):
        email = self.cleaned_data['email'].lower().strip()
        if User.objects.filter(email__iexact=email).exists(): raise ValidationError('An account already uses this email.')
        return email

    def clean(self):
        data = super().clean()
        if data.get('role') == 'student':
            for field in ('roll_no', 'branch', 'cgpa', 'graduation_year'):
                if data.get(field) in (None, ''): self.add_error(field, 'Required for student registration.')
        elif data.get('role') == 'company':
            data['roll_no'] = None
            data['branch'] = ''
            data['cgpa'] = 0
            data['graduation_year'] = 2027
        if data.get('role') == 'student':
            data['website'] = ''
        return data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data['email'].lower()
        user.email = user.username
        user.approval = 'pending'
        if commit: user.save()
        return user

class StudentProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['display_name', 'roll_no', 'branch', 'cgpa', 'backlogs', 'graduation_year', 'phone', 'bio', 'resume']
        widgets = {'bio': forms.Textarea(attrs={'rows': 3}), 'resume': forms.FileInput(attrs={'accept': 'application/pdf'})}
        help_texts = {'resume': 'PDF only, maximum 5 MB. Visible only to placement officers and recruiters you apply to.'}

    def clean_resume(self):
        f = self.cleaned_data.get('resume')
        if f and hasattr(f, 'content_type'):
            if f.size > 5 * 1024 * 1024: raise ValidationError('Resume must be 5 MB or smaller.')
            signature = f.read(5)
            f.seek(0)
            if signature != b'%PDF-': raise ValidationError('Upload a valid PDF document.')
        return f

    def clean(self):
        data = super().clean()
        for field in ('branch', 'roll_no'):
            if not data.get(field): self.add_error(field, 'This field is required.')
        return data

class CompanyProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['display_name', 'website', 'phone', 'bio']
        widgets = {'bio': forms.Textarea(attrs={'rows': 5})}
        labels = {'display_name': 'Company name', 'bio': 'About the company'}

class JobForm(forms.ModelForm):
    branches = forms.MultipleChoiceField(choices=BRANCHES, widget=forms.CheckboxSelectMultiple)
    class Meta:
        model = Job
        fields = ['title', 'location', 'job_type', 'package', 'min_cgpa', 'max_backlogs', 'branches', 'deadline', 'description']
        widgets = {'deadline': forms.DateInput(attrs={'type': 'date'}), 'description': forms.Textarea(attrs={'rows': 6})}
        help_texts = {'package': 'Annual cost to company, in lakh rupees.', 'description': 'Describe responsibilities, skills, hiring stages, and benefits.'}

    def clean_deadline(self):
        value = self.cleaned_data['deadline']
        if value < timezone.localdate(): raise ValidationError('Choose today or a future deadline.')
        return value

class InterviewForm(forms.ModelForm):
    class Meta:
        model = Interview
        fields = ['starts_at', 'duration', 'mode', 'venue', 'notes']
        widgets = {'starts_at': forms.DateTimeInput(format='%Y-%m-%dT%H:%M', attrs={'type': 'datetime-local'}), 'notes': forms.Textarea(attrs={'rows': 3})}
        help_texts = {'starts_at': 'India Standard Time (IST).', 'duration': 'Minutes, from 15 to 240.'}

    def clean_starts_at(self):
        value = self.cleaned_data['starts_at']
        if value <= timezone.now(): raise ValidationError('Schedule interviews in the future.')
        return value

    def clean(self):
        data = super().clean()
        if data.get('mode') == 'Online' and data.get('venue'):
            try:
                value = data['venue']
                URLValidator(schemes=['http', 'https'])(value)
                url = urlsplit(value)
                # Accessing port also validates invalid/out-of-range numeric ports.
                url.port
                if url.username is not None or url.password is not None:
                    raise ValueError('Meeting links cannot contain credentials.')
            except (ValidationError, ValueError):
                self.add_error('venue', 'Enter a valid public http:// or https:// meeting URL without credentials.')
        return data


class OfficerProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['display_name', 'phone', 'bio']
        labels = {'display_name': 'Full name', 'bio': 'About you'}
        widgets = {'bio': forms.Textarea(attrs={'rows': 4})}
