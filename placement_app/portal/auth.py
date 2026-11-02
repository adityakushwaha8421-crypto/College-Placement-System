from django.contrib.auth.backends import ModelBackend
from .models import User
class EmailBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        try:
            user = User.objects.get(email__iexact=(username or '').strip())
        except User.DoesNotExist:
            User().set_password(password)
            return None
        return user if user.check_password(password) and self.user_can_authenticate(user) else None
