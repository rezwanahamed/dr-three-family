# Development and production configuration

This Django project reads configuration directly from **`.env`**, located beside `manage.py`. The same filename is used for both local development and production; its values differ between installations.

`main_server/settings.py` loads this file with python-dotenv. Existing process environment variables take precedence over `.env` values.

## 1. Create the configuration file

Expected layout:

```text
project-root/
├── manage.py
├── .env
├── requirements.txt
└── main_server/
    ├── settings.py
    └── wsgi.py
```

If `.env` already exists, edit it and preserve your existing production secret key. Otherwise, create it using one of the examples below.

Use `KEY=value` assignments. Quote values containing spaces. Set `DJANGO_DEBUG=1` locally and `DJANGO_DEBUG=0` in production. Start from `.env.example` if needed.

## 2. Local development example

```dotenv
# .env — local development
DJANGO_SECRET_KEY='development-only-secret-do-not-use-in-production'
DJANGO_DEBUG=1
DJANGO_ALLOWED_HOSTS='localhost'
DJANGO_CSRF_TRUSTED_ORIGINS='http://localhost:8000,http://127.0.0.1:8000'

# Print reset emails in the terminal without sending real mail.
DJANGO_EMAIL_BACKEND='django.core.mail.backends.console.EmailBackend'
DEFAULT_FROM_EMAIL='Dr. Teeth Family <noreply@example.com>'

PASSWORD_RESET_TIMEOUT=300
# An empty value builds reset links from the incoming request.
PASSWORD_RESET_BASE_URL=''
```

Install dependencies and start Django from the project root:

```bash
python -m venv venv
source venv/bin/activate
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py check
python manage.py runserver
```

Use a Python version compatible with the pinned dependencies in `requirements.txt`.

Open `http://localhost:8000/dashboard/`. Supply an email address when creating your superuser: dashboard sign-in uses email and password.

The current local development database has this admin login:

- Email: `admin@gmail.com`
- Password: `123456`

These credentials are for local development only. They are stored as a Django user in `db.sqlite3`, not in `.env`. A fresh database needs its own account created with `createsuperuser`; uploading configuration alone does not create a user. Use a different, strong password for production.

To test password resets, submit an active account's registered email. The console backend prints the reset link in the terminal running Django. The password-reset timeout above is **300 seconds (5 minutes)**.

## 3. Production example

Generate a random secret locally or in your hosting terminal:

```bash
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

Put the result in `DJANGO_SECRET_KEY`. Keep it stable across deployments and application workers. If your production file already has a private random key, retain it.

```dotenv
# .env — production
DJANGO_SECRET_KEY='replace-with-your-generated-private-secret'
DJANGO_DEBUG=0
DJANGO_ALLOWED_HOSTS='clientdemo.softfluxit.com'
DJANGO_CSRF_TRUSTED_ORIGINS='https://clientdemo.softfluxit.com'

DJANGO_EMAIL_BACKEND='django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST='smtp.gmail.com'
EMAIL_PORT=587
EMAIL_HOST_USER='your-email@gmail.com'
EMAIL_HOST_PASSWORD='replace-with-your-smtp-app-password'
EMAIL_USE_TLS=true
EMAIL_USE_SSL=false
DEFAULT_FROM_EMAIL='Dr. Teeth Family <your-email@gmail.com>'

PASSWORD_RESET_TIMEOUT=300
PASSWORD_RESET_BASE_URL='https://clientdemo.softfluxit.com'
```

Use your actual SMTP account and the SMTP/app password provided for it. Set the sender address to one your provider permits. Django formats the display name for SMTP automatically.

## 4. Deploy on cPanel

1. Upload the project to your Python application's root directory.
2. Upload **`.env` separately**, beside `manage.py`. Git ignores this private file, so a Git deployment will not include it.
3. Select a Python runtime compatible with `requirements.txt` and activate the application's virtual environment using the command shown by your hosting panel.
4. From the application root, run:

   ```bash
   python -m pip install -r requirements.txt
   python manage.py migrate
   python manage.py collectstatic --noinput
   python manage.py check
   python manage.py check --deploy
   ```

   Review deployment-check findings for your hosting setup. Create the initial superuser with `python manage.py createsuperuser` if you do not already have one.

5. Configure the WSGI entry point to load `main_server.wsgi.application`. If your host uses a root-level `passenger_wsgi.py`, its application import can be:

   ```python
   from main_server.wsgi import application
   ```

   Keep any interpreter or path setup required by your host's generated Passenger file. The project root must be on Python's import path.

6. Configure the web server to serve `/static/` from `collected-static/` and uploaded `/media/` files from `media/`. Django's development server is not the production server.
7. Enable HTTPS for your domain, then restart the Python application using cPanel's restart control.
8. Check dashboard sign-in, form submissions, and a password reset for an existing account. Confirm that the email arrives and the link uses your production HTTPS domain.

Do not run `createsuperuser` or overwrite the database on every deployment. Back up the database and `media/` separately.

## 5. Configuration reference

| Setting | Format and purpose |
| --- | --- |
| `DJANGO_SECRET_KEY` | Private, stable random string used for signing. |
| `DJANGO_DEBUG` | `1` locally; `0` in production. |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated hostnames, without schemes or paths. |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | Comma-separated origins with schemes; include ports when applicable. |
| `DJANGO_EMAIL_BACKEND` | Console backend locally, SMTP backend for delivery. |
| `EMAIL_HOST` / `EMAIL_PORT` | SMTP hostname and numeric port. |
| `EMAIL_HOST_USER` / `EMAIL_HOST_PASSWORD` | SMTP credentials. |
| `EMAIL_USE_TLS` / `EMAIL_USE_SSL` | STARTTLS or implicit SSL; do not enable both. |
| `DEFAULT_FROM_EMAIL` | Sender name and email address. |
| `PASSWORD_RESET_TIMEOUT` | Lifetime in seconds; displayed as minutes in the reset form and email. |
| `PASSWORD_RESET_BASE_URL` | Optional fixed origin, such as `https://clientdemo.softfluxit.com`, without a path. |
| `DJANGO_DATABASE_PATH` | Optional SQLite file path; defaults to `db.sqlite3` in the project root. |

Multiple-domain example:

```dotenv
DJANGO_ALLOWED_HOSTS='example.com,www.example.com'
DJANGO_CSRF_TRUSTED_ORIGINS='https://example.com,https://www.example.com'
```

## 6. Troubleshooting

- **Settings missing:** Place `.env` beside `manage.py` and check that the application can read it.
- **`.env` format:** Use one `KEY=value` assignment per line and quote values containing spaces.
- **`DisallowedHost`:** Add the requested hostname to `DJANGO_ALLOWED_HOSTS` and restart.
- **CSRF verification failure:** Check that your browser's HTTPS origin is included in `DJANGO_CSRF_TRUSTED_ORIGINS`, restart, and reload the form. For proxy-related failures, check your hosting HTTPS/proxy configuration.
- **Emails appear only in logs:** Change the console backend to the SMTP backend.
- **SMTP delivery fails:** Check credentials, TLS/SSL settings, and whether the host permits outbound SMTP connections.
- **Old settings remain active:** Restart the cPanel Python application. Check whether existing process environment variables override your `.env` values.
- **Static files disappear with debug disabled:** Run `collectstatic` and check the web server's static-file mapping.

## 7. Keep private configuration private

`.env` contains credentials and is excluded by `.gitignore`. Keep it outside publicly served static/media directories and grant file-read access only to the application account as your host permits.

Use placeholders in shared examples, including `.env.example`; do not copy real passwords into documentation or commit them to Git. Keep separate local and production configurations so development does not send real email or use production data accidentally.

### Restart after uploading code to cPanel

The application reads content files with explicit UTF-8 encoding so it does not depend on the server's default locale. After uploading updated code, run this from the project root:

```bash
bash tools/restart_passenger.sh
```

The script locates the project directory, removes application `.pyc` files and empty `__pycache__` folders, then touches `tmp/restart.txt` to request a Passenger restart. It leaves virtual environments and database files untouched. Run it on the production server; running it locally does not restart the deployed application.

## Appointment booking

The themed appointment form submits to the existing Dentzo booking system through Django. See [appointment integration and deployment instructions](docs/appointment-booking.md), including remote hosting requirements and how uncertain booking responses are handled.
