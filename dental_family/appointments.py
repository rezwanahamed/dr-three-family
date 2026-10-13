"""Submit public appointments to the clinic's existing Laravel booking system."""
import json
from datetime import time
from http.cookiejar import CookieJar
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, build_opener, HTTPCookieProcessor, HTTPRedirectHandler

from bs4 import BeautifulSoup
from django import forms
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from django.views.decorators.http import require_http_methods

ORIGIN = 'https://drteethfamily.dentzobd.com'
FORM_URL = ORIGIN + '/appointment'
SUBMIT_URL = ORIGIN + '/save-appointment'
CHOICES = ('gender_id', 'chamber_address', 'doctor_name')


class BookingUnavailable(Exception):
    pass


class NoRedirects(HTTPRedirectHandler):
    # Never forward patient data or cookies to an unexpected redirect target.
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def remote_form():
    client = build_opener(HTTPCookieProcessor(CookieJar()), NoRedirects())
    with client.open(Request(FORM_URL, headers={'Accept': 'text/html'}), timeout=15) as response:
        html = response.read(1_000_001)
    if len(html) > 1_000_000:
        raise BookingUnavailable()
    soup = BeautifulSoup(html, 'html.parser')
    form = soup.select_one('form#appointmentForm')
    token = form.select_one('input[name="_token"]') if form else None
    if not token or not token.get('value'):
        raise BookingUnavailable()
    options = {}
    for name in CHOICES:
        select = form.find('select', attrs={'name': name})
        if select is None:
            raise BookingUnavailable()
        options[name] = [
            (item['value'], item.get_text(' ', strip=True))
            for item in select.find_all('option') if item.get('value')
        ]
    return client, token['value'], options


class AppointmentForm(forms.Form):
    en_name = forms.CharField(max_length=255)
    en_age = forms.IntegerField(min_value=0, max_value=130)
    en_number = forms.RegexField(r'^\+?[0-9]{7,14}$', max_length=14)
    email = forms.EmailField(max_length=254)
    gender_id = forms.ChoiceField(required=False)
    en_address = forms.CharField(required=False, max_length=2000)
    chamber_address = forms.ChoiceField(required=False)
    doctor_name = forms.ChoiceField(required=False)
    appointment_date = forms.DateField()
    appointment_time = forms.TimeField(input_formats=['%H:%M'])
    reason = forms.CharField(required=False, max_length=4000)

    def __init__(self, data=None, *, options):
        super().__init__(data)
        for name in CHOICES:
            self.fields[name].choices = [('', '')] + options[name]

    def clean_email(self):
        email = self.cleaned_data['email']
        if email.rsplit('@', 1)[-1].lower() != 'gmail.com':
            raise forms.ValidationError('Please enter a Gmail address, as required by the booking portal.')
        return email

    def clean_appointment_date(self):
        date = self.cleaned_data['appointment_date']
        if date < timezone.localdate():
            raise forms.ValidationError('Choose today or a future date.')
        return date

    def clean_appointment_time(self):
        value = self.cleaned_data['appointment_time']
        if not time(16) <= value <= time(22):
            raise forms.ValidationError('Choose a time between 4:00 PM and 10:00 PM.')
        return value

    def clean(self):
        data = super().clean()
        date, value = data.get('appointment_date'), data.get('appointment_time')
        now = timezone.localtime()
        if date == now.date() and value and value < now.time().replace(tzinfo=None):
            self.add_error('appointment_time', 'Choose a future appointment time.')
        return data


@never_cache
@ensure_csrf_cookie
@csrf_protect
@require_http_methods(['GET', 'POST'])
def appointment_booking(request):
    try:
        client, token, options = remote_form()
    except (BookingUnavailable, URLError, OSError, ValueError):
        return JsonResponse({'error': 'Online booking is temporarily unavailable. Please use the booking portal or call the clinic.'}, status=503)
    if request.method == 'GET':
        return JsonResponse({'options': options, 'today': timezone.localdate().isoformat()})
    form = AppointmentForm(request.POST, options=options)
    if not form.is_valid():
        return JsonResponse({'errors': dict(form.errors), 'error': 'Please check the highlighted fields.'}, status=422)
    payload = dict(form.cleaned_data)
    payload['appointment_date'] = payload['appointment_date'].isoformat()
    payload['appointment_time'] = payload['appointment_time'].strftime('%H:%M')
    payload['_token'] = token
    submission = Request(SUBMIT_URL, data=urlencode(payload).encode('utf-8'), headers={
        'Content-Type': 'application/x-www-form-urlencoded', 'Accept': 'application/json',
        'X-Requested-With': 'XMLHttpRequest', 'Referer': FORM_URL, 'Origin': ORIGIN,
    }, method='POST')
    try:
        with client.open(submission, timeout=25) as response:
            result = json.loads(response.read(100_001))
        if not isinstance(result, dict) or result.get('success') is not True:
            raise BookingUnavailable()
    except HTTPError as error:
        if error.code == 422:
            try:
                result = json.loads(error.read(100_001))
                errors = result.get('errors') if isinstance(result, dict) else None
                if isinstance(errors, dict):
                    safe_errors = {key: [str(item)[:500] for item in value[:5]] for key, value in errors.items() if key in form.fields and isinstance(value, list)}
                    return JsonResponse({'error': 'Please check your appointment details.', 'errors': safe_errors}, status=422)
            except (ValueError, OSError):
                pass
        return uncertain_booking()
    except (BookingUnavailable, URLError, OSError, ValueError):
        return uncertain_booking()
    return JsonResponse({'success': True, 'message': 'Your appointment request has been received. The clinic will confirm your visit.'})


def uncertain_booking():
    # Laravel saves the appointment before sending email, so errors may follow a save.
    return JsonResponse({'error': 'We could not confirm the booking result. Please contact the clinic before submitting again to avoid a duplicate appointment.', 'uncertain': True}, status=502)
