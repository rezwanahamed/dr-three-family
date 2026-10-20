import json
from copy import deepcopy
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from bs4 import BeautifulSoup
from .booking_hours import hours_for, effective_slots
from .content import seeds, validate_state
from .models import WebsiteWorkspace
from .test_appointments import OPTIONS, payload


class BookingHoursTests(TestCase):
    def setUp(self):
        self.data = seeds()
        self.data['settings'] = {'appointment_start':'10:00','appointment_end':'18:00'}
        WebsiteWorkspace.objects.create(pk=1, published=self.data)

    @patch('dental_family.appointments.remote_form')
    def test_api_exposes_and_enforces_published_hours(self, remote):
        from unittest.mock import MagicMock
        upstream = MagicMock()
        remote.return_value = (upstream, 'token', OPTIONS)
        response = self.client.get('/api/appointment/')
        self.assertEqual(response.json()['hours']['start'], '10:00')
        self.assertEqual(response.json()['hours']['label'], '10:00 AM – 6:00 PM')
        response = self.client.post('/api/appointment/', {**payload(), 'appointment_time':'19:00'})
        self.assertEqual(response.status_code, 422)
        self.assertIn('appointment_time', response.json()['errors'])
        upstream.open.assert_not_called()

    def test_visible_hours_and_form_constraints_are_consistent(self):
        for route in ['/', '/appointment/', '/our-doctors/', '/contact/', '/about-us/']:
            response = self.client.get(route)
            soup = BeautifulSoup(response.content, 'html.parser')
            notes = soup.select('.booking-hours-note')
            self.assertTrue(notes, route)
            self.assertTrue(all('10:00 AM – 6:00 PM' in n.text for n in notes), route)
        soup = BeautifulSoup(self.client.get('/appointment/').content, 'html.parser')
        field = soup.select_one('[name="appointment_time"]')
        self.assertEqual((field['min'], field['max']), ('10:00','18:00'))
        self.assertEqual(soup.select_one('.appointment-hours strong').text, '10:00 AM – 6:00 PM')
        self.assertNotIn('4:00 PM — 10:00 PM', str(soup))

    def test_invalid_ranges_are_rejected(self):
        for start, end in [('18:00','10:00'), ('12:00','12:00'), ('bad','18:00')]:
            with self.assertRaises(ValidationError):
                validate_state({'settings':{'appointment_start':start,'appointment_end':end}})

    def test_doctor_hours_are_clipped_to_website_window(self):
        record = {'availability':[{'day':'monday','start':'08:00','end':'12:00'}, {'day':'monday','start':'16:00','end':'20:00'}]}
        self.assertEqual(effective_slots(record, hours_for(self.data)), [
            {'day':'monday','start':'10:00','end':'12:00'}, {'day':'monday','start':'16:00','end':'18:00'}])

    def test_saved_draft_does_not_change_live_hours_until_publish(self):
        staff = get_user_model().objects.create_user(username='editor',password='test',is_staff=True)
        self.client.force_login(staff)
        base = self.client.get('/dashboard/content/').json()
        state = {'drafts':[], 'settings':{'appointment_start':'11:00','appointment_end':'19:00'}}
        response = self.client.put('/dashboard/content/', json.dumps({'revision':base['revision'],'state':state}), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertContains(self.client.get('/appointment/'), '10:00 AM – 6:00 PM')
        response = self.client.post('/dashboard/publish/', json.dumps({'revision':response.json()['revision'],'state':state}), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertContains(self.client.get('/appointment/'), '11:00 AM – 7:00 PM')
        self.assertEqual(self.client.get('/dashboard/content/').json()['published_settings']['appointment_start'], '11:00')

    @patch('dental_family.appointments.remote_form')
    def test_doctor_split_sessions_are_enforced(self, remote):
        from unittest.mock import MagicMock
        from datetime import date
        doctor = next(r for r in self.data['records'] if r['section']=='doctors')
        tomorrow = date.fromisoformat(payload()['appointment_date'])
        doctor['availability'] = [{'day':tomorrow.strftime('%A').lower(),'start':'10:00','end':'12:00'}, {'day':tomorrow.strftime('%A').lower(),'start':'16:00','end':'18:00'}]
        workspace = WebsiteWorkspace.objects.get(pk=1);workspace.published=self.data;workspace.save()
        options = deepcopy(OPTIONS);options['doctor_name']=[('portal-doctor',doctor['title'])]
        upstream=MagicMock();remote.return_value=(upstream,'token',options)
        response=self.client.post('/api/appointment/', {**payload(),'doctor_name':'portal-doctor','appointment_time':'14:00'})
        self.assertEqual(response.status_code,422)
        self.assertIn('doctor',response.json()['errors']['appointment_time'][0])
        upstream.open.assert_not_called()
