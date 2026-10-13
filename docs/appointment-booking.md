# Appointment booking integration

The Django `/appointment/` page keeps the website theme and submits through `/api/appointment/` to the existing Dentzo Laravel application. Appointment and patient records are stored by Laravel, not in the Django content database.

## Request flow

1. The browser requests `GET /api/appointment/`. Django reads `https://drteethfamily.dentzobd.com/appointment` to obtain current gender, doctor, and branch options. The browser also receives its Django CSRF cookie.
2. The visitor completes the themed form. Required fields are patient name, age, phone, Gmail address, appointment date, and time. Gender, address, branch, doctor, and reason are optional. Times are 4 PM–10 PM in Bangladesh time; past dates/times are rejected.
3. The browser posts to Django with its CSRF token. Django creates a new isolated Laravel cookie session, reads a fresh Laravel `_token`, validates the submitted choices, and posts the expected form fields to `https://drteethfamily.dentzobd.com/save-appointment` using that same session.
4. Success is displayed only when Laravel returns JSON with `success: true`. Laravel validation errors appear next to the fields. No patient details are persisted by this integration in Django, browser storage, or application logs.

The supplied `routes/api.php` contains no public appointment API. The supplied `routes/web.php` defines the public GET form and POST submission routes, handled by `FrontviewController`; the admin appointment handler is not used. No static CSRF token, shared user session, CORS exemption, or Laravel CSRF exemption is needed.

## Deployment

Upload the changed Django application code and templates, then run:

```bash
python manage.py collectstatic --noinput
python manage.py check
bash tools/restart_passenger.sh
```

There are no new database migrations or dependencies. The Django server must have outbound HTTPS access to the Dentzo domain. The remote booking form must expose `form#appointmentForm`, a hidden `_token`, and the `gender_id`, `chamber_address`, and `doctor_name` selects as in the supplied Blade template.

The live portal returned a browser-verification page during inspection. If that also happens from the deployed Django server, the form displays an unavailable message and a direct portal link. The Dentzo hosting administrator will need to permit the Django server's requests to these two booking routes through the hosting bot-verification layer, or provide an authenticated server API. Keep Laravel CSRF protection enabled. Do not disable TLS certificate verification.

## Delivery and duplicate handling

The supplied PHP controller creates the appointment before it sends patient/admin email. A timeout or SMTP error can therefore occur after a booking has been saved. The Django integration never automatically retries submissions. For uncertain results, it disables further submission on the current form and asks the visitor to contact the clinic before retrying. This is not a cross-session idempotency guarantee; Laravel would need an idempotency key for that.

For an existing patient phone number, the supplied PHP code reuses the existing patient record and email; it does not update those details from the new form. Appointment status begins as `pending`, so the UI describes success as a received request, not a confirmed visit.

## Verification

```bash
python manage.py test dental_family.test_appointments dental_family.test_content
```

Tests mock the remote service and never create real appointments or send email. They cover dynamic choices, CSRF, payload mapping, validation, upstream failures, and rendering with published content. A real booking was not submitted during implementation.
