import json
from datetime import timedelta
from io import BytesIO
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs

from django.test import Client, SimpleTestCase, TestCase, override_settings
from django.utils import timezone
from .appointments import AppointmentForm, BookingUnavailable, FORM_URL, SUBMIT_URL, remote_form

OPTIONS = {'gender_id': [('2', 'Male'), ('3', 'Female')], 'doctor_name': [('Doctor A', 'Doctor A')], 'chamber_address': [('Branch A', 'Branch A')]}


def payload():
    return {'en_name': 'Test Patient', 'en_age': '30', 'en_number': '01700000000', 'email': 'patient@gmail.com', 'gender_id': '2', 'en_address': 'Test address', 'doctor_name': 'Doctor A', 'chamber_address': 'Branch A', 'appointment_date': (timezone.localdate() + timedelta(days=1)).isoformat(), 'appointment_time': '17:30', 'reason': 'Checkup'}


class AppointmentFormTests(SimpleTestCase):
    def test_valid_and_invalid_fields(self):
        self.assertTrue(AppointmentForm(payload(), options=OPTIONS).is_valid())
        for key, value in [('en_age', '-1'), ('en_number', 'not-a-phone'), ('email', 'person@example.com'), ('doctor_name', 'Unknown'), ('gender_id', '999'), ('appointment_time', '12:00'), ('appointment_date', '2000-01-01')]:
            with self.subTest(field=key):
                form = AppointmentForm({**payload(), key: value}, options=OPTIONS)
                self.assertFalse(form.is_valid())
                self.assertIn(key, form.errors)

    @patch('dental_family.appointments.build_opener')
    def test_remote_token_and_live_choices(self, opener):
        html = '<form id="appointmentForm"><input name="_token" value="fresh-token">'
        for name in OPTIONS:
            html += f'<select name="{name}"><option value="">Choose</option><option value="x">Live option</option></select>'
        html += '</form>'
        opener.return_value.open.return_value.__enter__.return_value.read.return_value = html.encode()
        client, token, options = remote_form()
        self.assertEqual(token, 'fresh-token')
        self.assertEqual(options['doctor_name'], [('x', 'Live option')])
        self.assertIs(client, opener.return_value)
        opener.return_value.open.return_value.__enter__.return_value.read.return_value = b'<html>Verify your browser</html>'
        with self.assertRaises(BookingUnavailable):
            remote_form()


class AppointmentEndpointTests(TestCase):
    def setUp(self):
        self.remote = patch('dental_family.appointments.remote_form').start()
        self.addCleanup(patch.stopall)
        self.upstream = MagicMock()
        self.remote.return_value = (self.upstream, 'fresh-token', OPTIONS)
        self.upstream.open.return_value.__enter__.return_value.read.return_value = b'{"success": true}'

    def test_choices_set_csrf_cookie_and_never_expose_remote_token(self):
        response = self.client.get('/api/appointment/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('csrftoken', response.cookies)
        self.assertNotContains(response, 'fresh-token')
        self.assertIn('no-store', response.headers['Cache-Control'])

    def test_booking_uses_verified_token_and_expected_endpoint(self):
        response = self.client.post('/api/appointment/', payload())
        self.assertTrue(response.json()['success'])
        request = self.upstream.open.call_args.args[0]
        self.assertEqual(request.full_url, SUBMIT_URL)
        data = parse_qs(request.data.decode())
        self.assertEqual(data['_token'], ['fresh-token'])
        self.assertEqual(data['en_number'], ['01700000000'])
        self.assertEqual(data['appointment_time'], ['17:30'])
        self.upstream.open.assert_called_once()

    def test_csrf_required(self):
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(client.post('/api/appointment/', payload()).status_code, 403)
        self.remote.assert_not_called()
        client.get('/api/appointment/')
        response = client.post('/api/appointment/', payload(), HTTP_X_CSRFTOKEN=client.cookies['csrftoken'].value)
        self.assertEqual(response.status_code, 200)

    def test_invalid_data_never_submitted(self):
        response = self.client.post('/api/appointment/', {**payload(), 'en_name': ''})
        self.assertEqual(response.status_code, 422)
        self.upstream.open.assert_not_called()

    def test_unavailable_form_does_not_submit(self):
        self.remote.side_effect = BookingUnavailable()
        self.assertEqual(self.client.post('/api/appointment/', payload()).status_code, 503)
        self.upstream.open.assert_not_called()

    def test_uncertain_response_is_not_success_or_retried(self):
        for failure in [TimeoutError(), URLError('offline'), HTTPError(SUBMIT_URL, 500, 'error', {}, BytesIO(b'private details'))]:
            with self.subTest(failure=type(failure).__name__):
                self.upstream.open.reset_mock()
                self.upstream.open.side_effect = failure
                response = self.client.post('/api/appointment/', payload())
                self.assertEqual(response.status_code, 502)
                self.assertTrue(response.json()['uncertain'])
                self.assertNotIn('private details', response.content.decode())
                self.upstream.open.assert_called_once()

    def test_remote_validation_and_unexpected_html(self):
        self.upstream.open.side_effect = HTTPError(SUBMIT_URL, 422, 'invalid', {}, BytesIO(json.dumps({'errors': {'en_number': ['Invalid phone']}}).encode()))
        response = self.client.post('/api/appointment/', payload())
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()['errors']['en_number'], ['Invalid phone'])
        self.upstream.open.side_effect = None
        self.upstream.open.return_value.__enter__.return_value.read.return_value = b'<html>Server error</html>'
        self.assertTrue(self.client.post('/api/appointment/', payload()).json()['uncertain'])

    def test_appointment_page_retains_theme_and_form(self):
        from .models import WebsiteWorkspace
        from .content import seeds
        WebsiteWorkspace.objects.create(pk=1, published=seeds())
        response = self.client.get('/appointment/')
        self.assertContains(response, 'id="appointment-form"')
        self.assertContains(response, 'appointment.css')
        self.assertContains(response, 'booking-aside')
        self.assertNotContains(response, 'PyIs48dn')
