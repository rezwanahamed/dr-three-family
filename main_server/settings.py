"""Django settings for main_server, configured through environment variables."""

import os
from email.utils import formataddr
from pathlib import Path
from urllib.parse import urlsplit

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv


# Paths and environment
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env', override=False)


# Security and debugging
SECRET_KEY = os.environ.get(
    'DJANGO_SECRET_KEY',
    'local-preview-only-not-a-production-secret',
)
DEBUG = os.environ.get('DJANGO_DEBUG', '1') == '1'
ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get(
        'DJANGO_ALLOWED_HOSTS',
        'localhost,127.0.0.1,[::1],testserver',
    ).split(',')
    if host.strip()
]


# Applications
INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.staticfiles',
    'dental_family',
]


# Middleware (order matters)
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
]


# URL routing
ROOT_URLCONF = 'main_server.urls'
APPEND_SLASH = True


# Templates
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
            ],
        },
    },
]


# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.environ.get('DJANGO_DATABASE_PATH', BASE_DIR / 'db.sqlite3'),
    },
}


# Authentication
AUTHENTICATION_BACKENDS = [
    'dental_family.backends.EmailBackend',
]
LOGIN_URL = '/dashboard/login/'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/dashboard/login/'

# Password validation is currently disabled.
AUTH_PASSWORD_VALIDATORS = []


# Password reset
PASSWORD_RESET_TIMEOUT = int(os.environ.get('PASSWORD_RESET_TIMEOUT', '3600'))

# Optional canonical origin for emailed links, independent of request Host headers.
PASSWORD_RESET_BASE_URL = (
    os.environ.get('PASSWORD_RESET_BASE_URL', '').strip().rstrip('/')
)
if PASSWORD_RESET_BASE_URL:
    reset_origin = urlsplit(PASSWORD_RESET_BASE_URL)
    if (
        reset_origin.scheme not in {'http', 'https'}
        or not reset_origin.hostname
        or reset_origin.path
        or reset_origin.query
        or reset_origin.fragment
        or reset_origin.username
        or reset_origin.password
    ):
        raise ImproperlyConfigured(
            'PASSWORD_RESET_BASE_URL must be an HTTP(S) origin, '
            'e.g. https://clinic.example.com.'
        )


# Time zone
TIME_ZONE = 'Asia/Dhaka'
USE_TZ = True


# Static files
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'collected-static'


# Uploaded media
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'


# Email
EMAIL_BACKEND = os.environ.get(
    'DJANGO_EMAIL_BACKEND',
    'django.core.mail.backends.smtp.EmailBackend',
)
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'localhost')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'true').lower() in {'1', 'true', 'yes'}
EMAIL_USE_SSL = os.environ.get('EMAIL_USE_SSL', 'false').lower() in {'1', 'true', 'yes'}
EMAIL_TIMEOUT = 15
DEFAULT_FROM_EMAIL = os.environ.get(
    'DEFAULT_FROM_EMAIL',
    formataddr(('Dr. Teeth', 'noreply@drteethfamilydental.com')),
)
