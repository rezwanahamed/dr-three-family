"""Local preview settings. Integrate dental_family into your own settings for production."""
import os
from pathlib import Path
from dotenv import load_dotenv
from email.utils import formataddr
from urllib.parse import urlsplit
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env', override=False)
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'local-preview-only-not-a-production-secret')
DEBUG = os.environ.get('DJANGO_DEBUG', '1') == '1'
ALLOWED_HOSTS = [host.strip() for host in os.environ.get('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1,[::1],testserver').split(',') if host.strip()]
INSTALLED_APPS = ['django.contrib.auth', 'django.contrib.contenttypes', 'django.contrib.sessions', 'django.contrib.staticfiles', 'dental_family']
MIDDLEWARE = ['django.middleware.security.SecurityMiddleware', 'django.contrib.sessions.middleware.SessionMiddleware', 'django.middleware.common.CommonMiddleware', 'django.middleware.csrf.CsrfViewMiddleware', 'django.contrib.auth.middleware.AuthenticationMiddleware']
DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': os.environ.get('DJANGO_DATABASE_PATH', BASE_DIR / 'db.sqlite3')}}
LOGIN_URL = '/dashboard/login/'
AUTHENTICATION_BACKENDS = ['dental_family.backends.EmailBackend']
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/dashboard/login/'
ROOT_URLCONF = 'demo.urls'
TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'DIRS': [BASE_DIR / 'templates'], 'APP_DIRS': True,
    'OPTIONS': {'context_processors': ['django.template.context_processors.request', 'django.contrib.auth.context_processors.auth']},
}]
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'collected-static'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
USE_TZ = True
TIME_ZONE = 'Asia/Dhaka'
APPEND_SLASH = True

EMAIL_BACKEND = os.environ.get('DJANGO_EMAIL_BACKEND', 'django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'localhost')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'true').lower() in {'1','true','yes'}
EMAIL_USE_SSL = os.environ.get('EMAIL_USE_SSL', 'false').lower() in {'1','true','yes'}
EMAIL_TIMEOUT = 15
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', formataddr(('Dr. Teeth','noreply@drteethfamilydental.com')))
PASSWORD_RESET_TIMEOUT = int(os.environ.get('PASSWORD_RESET_TIMEOUT', '3600'))
AUTH_PASSWORD_VALIDATORS = [
    # {'NAME':'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    # {'NAME':'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS':{'min_length':10}},
    # {'NAME':'django.contrib.auth.password_validation.CommonPasswordValidator'},
    # {'NAME':'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Optional canonical origin for emailed links, independent of request Host headers.
PASSWORD_RESET_BASE_URL = os.environ.get('PASSWORD_RESET_BASE_URL', '').strip().rstrip('/')
if PASSWORD_RESET_BASE_URL:
    reset_origin=urlsplit(PASSWORD_RESET_BASE_URL)
    if reset_origin.scheme not in {'http','https'} or not reset_origin.hostname or reset_origin.path or reset_origin.query or reset_origin.fragment or reset_origin.username or reset_origin.password:
        raise ImproperlyConfigured('PASSWORD_RESET_BASE_URL must be an HTTP(S) origin, e.g. https://clinic.example.com.')
