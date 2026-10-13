"""Copy to production_env.py beside manage.py, then fill in your private values."""

DJANGO_SECRET_KEY = 'DJASHDASDHASHDSAdsfsdd'
DJANGO_DEBUG = False
DJANGO_ALLOWED_HOSTS = 'localhost'
DJANGO_CSRF_TRUSTED_ORIGINS = 'https://clientdemo.softfluxit.com'

EMAIL_HOST='smtp.gmail.com'
EMAIL_PORT='587'
EMAIL_HOST_USER='softfluxit@gmail.com'
EMAIL_HOST_PASSWORD='mqhttbrertuawvzy'
EMAIL_USE_TLS='true'
EMAIL_USE_SSL='false'
DEFAULT_FROM_EMAIL='Dr. Teeth Family <softfluxit@gmail.com>'
PASSWORD_RESET_TIMEOUT=300
# Optional fixed origin for emailed reset links:
PASSWORD_RESET_BASE_URL = 'https://clientdemo.softfluxit.com'
