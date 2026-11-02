from django.http import HttpResponseForbidden
from django.urls import reverse
from django.utils.cache import patch_cache_control

class WorkspacePrivacyMiddleware:
    """Authenticated campus records must not be reused after logout or by a proxy."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and request.user.role not in {'admin', 'student', 'company'} and request.path_info != reverse('logout'):
            response = HttpResponseForbidden('This account has no valid workspace role.')
        else:
            response = self.get_response(request)
        if request.user.is_authenticated:
            patch_cache_control(response, private=True, no_store=True, no_cache=True, must_revalidate=True)
        return response
