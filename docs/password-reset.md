# Email password reset

The login page's **Forgot password?** link opens `/dashboard/forgot-password/`.

1. Enter a registered email address.
2. Open the reset link from the email.
3. Enter and confirm a new password.
4. Return to sign-in and use the new password.

Active registered accounts with usable passwords can reset their passwords, including nonstaff users. Dashboard access still requires staff status. Unknown or inactive addresses receive the same confirmation page, with no email sent. Reset links expire after one hour by default and become invalid after use. Django validates password strength and CSRF tokens.

## Configure email

A local `.env` and a shareable `.env.example` are included in the project root. Django loads `.env` automatically, while existing process environment variables take precedence. `.env` files are ignored by Git.

Fill in `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, and `DEFAULT_FROM_EMAIL` using your email provider's SMTP settings. Use its SMTP or app password if required. Keep `DJANGO_EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend` for actual delivery. Configure the sender as an address your provider permits.

Use `EMAIL_USE_TLS=true` and `EMAIL_USE_SSL=false` for STARTTLS, normally port 587. For implicit TLS, normally port 465, use `EMAIL_USE_TLS=false` and `EMAIL_USE_SSL=true`. Do not enable both.

Add your deployed hostname to `DJANGO_ALLOWED_HOSTS` and serve the site over HTTPS so emailed links use the correct public address and scheme. `PASSWORD_RESET_TIMEOUT` is in seconds; its default is 3600. Keep a stable production `DJANGO_SECRET_KEY` in your environment so reset links remain valid across workers and restarts.

Restart Django after changing the environment file. Install dependencies with `pip install -r requirements.txt` if deploying to another environment.

For local testing without sending emails, set `DJANGO_EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend`. Django then prints reset emails to the server terminal. Restore the SMTP backend for delivery. Delivery failures show a retry message without exposing SMTP credentials.

SMTP delivery cannot work until real provider settings are supplied. Automated tests use Django's in-memory email backend and do not send external emails.
