from django.urls import path, register_converter
from . import views
from django.contrib.auth.views import PasswordChangeView, PasswordChangeDoneView
from django.urls import reverse_lazy
class RecordIDConverter:
    regex = r'[1-9][0-9]{0,18}'
    def to_python(self, value):
        value = int(value)
        if value > 9223372036854775807: raise ValueError('Record ID exceeds database range.')
        return value
    def to_url(self, value):
        return str(self.to_python(str(value)))

register_converter(RecordIDConverter, 'record_id')
urlpatterns = [
 path('', views.dashboard, name='dashboard'),
 path('login/', views.SignIn.as_view(), name='login'),
 path('logout/', views.SignOut.as_view(), name='logout'),
 path('register/', views.register, name='register'),
 path('jobs/', views.jobs, name='jobs'),
 path('jobs/new/', views.job_form, name='job_create'),
 path('jobs/<record_id:pk>/', views.job_detail, name='job_detail'),
 path('jobs/<record_id:pk>/edit/', views.job_form, name='job_edit'),
 path('jobs/<record_id:pk>/state/', views.job_state, name='job_state'),
 path('jobs/<record_id:pk>/apply/', views.apply, name='apply'),
 path('applications/', views.applications, name='applications'),
 path('applications/<record_id:pk>/state/', views.application_state, name='application_state'),
 path('applications/<record_id:pk>/schedule/', views.schedule_interview, name='schedule_interview'),
 path('applications/<record_id:pk>/confirmation/', views.selection_record, name='selection_record'),
 path('interviews/', views.interviews, name='interviews'),
 path('people/<str:kind>/', views.people, name='people'),
 path('people/<record_id:pk>/approval/', views.approve_user, name='approve_user'),
 path('profile/', views.profile, name='profile'),
 path('password/', PasswordChangeView.as_view(template_name='registration/password_change.html', success_url=reverse_lazy('password_done')), name='password_change'),
 path('password/done/', PasswordChangeDoneView.as_view(template_name='registration/password_done.html'), name='password_done'),
 path('resumes/<record_id:pk>/', views.resume, name='resume'),
 path('reports/', views.reports, name='reports'),
]
