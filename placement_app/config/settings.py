from pathlib import Path
import os
from django.core.management.utils import get_random_secret_key
BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_FILE = BASE_DIR / '.local-secret'
if not SECRET_FILE.exists():
    try:
        with open(SECRET_FILE, 'x', opener=lambda p, flags: os.open(p, flags, 0o600)) as f:
            f.write(get_random_secret_key())
    except FileExistsError:
        pass
SECRET_KEY = os.environ.get('PLACEMENT_SECRET_KEY') or SECRET_FILE.read_text().strip()
DEBUG = os.environ.get('PLACEMENT_DEBUG', '1') == '1'
ALLOWED_HOSTS = ['localhost', '127.0.0.1', '[::1]', 'testserver']
ALLOWED_HOSTS += [h for h in os.environ.get('PLACEMENT_ALLOWED_HOSTS', '').split(',') if h]
_render_host = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
if _render_host:
    ALLOWED_HOSTS.append(_render_host)
CSRF_TRUSTED_ORIGINS = ['https://' + h for h in ALLOWED_HOSTS if h not in ('localhost', '127.0.0.1', '[::1]', 'testserver')]
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
INSTALLED_APPS = ['django.contrib.auth', 'django.contrib.contenttypes', 'django.contrib.sessions', 'django.contrib.messages', 'django.contrib.staticfiles', 'portal']
MIDDLEWARE = ['django.middleware.security.SecurityMiddleware', 'whitenoise.middleware.WhiteNoiseMiddleware', 'django.contrib.sessions.middleware.SessionMiddleware', 'django.middleware.common.CommonMiddleware', 'django.middleware.csrf.CsrfViewMiddleware', 'django.contrib.auth.middleware.AuthenticationMiddleware', 'portal.middleware.WorkspacePrivacyMiddleware', 'django.contrib.messages.middleware.MessageMiddleware', 'django.middleware.clickjacking.XFrameOptionsMiddleware']
ROOT_URLCONF = 'config.urls'
TEMPLATES = [{'BACKEND': 'django.template.backends.django.DjangoTemplates', 'DIRS': [BASE_DIR / 'templates'], 'APP_DIRS': True, 'OPTIONS': {'context_processors': ['django.template.context_processors.request', 'django.contrib.auth.context_processors.auth', 'django.contrib.messages.context_processors.messages']}}]
WSGI_APPLICATION = 'config.wsgi.application'
DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': os.environ.get('PLACEMENT_DB_PATH', str(BASE_DIR / 'db.sqlite3')), 'OPTIONS': {'timeout': 20, 'transaction_mode': 'IMMEDIATE'}}}
AUTH_USER_MODEL = 'portal.User'
AUTH_PASSWORD_VALIDATORS = [{'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'}, {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'}, {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'}, {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'}]
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True
STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
STORAGES = {'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'}, 'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedStaticFilesStorage'}}
MEDIA_ROOT = Path(os.environ.get('PLACEMENT_UPLOAD_DIR', str(BASE_DIR / 'private_uploads')))
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'dashboard'
LOGOUT_REDIRECT_URL = 'login'
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE = 'Lax'
X_FRAME_OPTIONS = 'DENY'
SECURE_CONTENT_TYPE_NOSNIFF = True
DATA_UPLOAD_MAX_MEMORY_SIZE = 6 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024
AUTHENTICATION_BACKENDS = ['portal.auth.EmailBackend']
