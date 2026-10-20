import json
from copy import deepcopy
from bs4 import BeautifulSoup
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from .content import seeds
from .doctors import profile_url, validate_availability
from .models import WebsiteWorkspace


class DoctorProfileTests(TestCase):
    def test_listings_have_profile_and_booking_links(self):
        for route, selector in [('/', '.doctors-grid > article'), ('/our-doctors/', '.doctor-directory > article')]:
            soup = BeautifulSoup(self.client.get(route).content, 'html.parser')
            cards = soup.select(selector)
            self.assertTrue(cards)
            for card in cards:
                self.assertEqual(card.select_one('.doctor-book-link')['href'], '/appointment/')
                response = self.client.get(card.select_one('.doctor-profile-link')['href'])
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, card.select_one('h2,h3').get_text())
        self.assertEqual(self.client.get('/our-doctors/unknown-doctor/').status_code, 404)

    def test_publish_biography_and_split_day_availability(self):
        staff = get_user_model().objects.create_user(username='editor', password='test', is_staff=True)
        self.client.force_login(staff)
        base = self.client.get('/dashboard/content/').json()
        doctor = deepcopy(next(r for r in base['records'] if r['section']=='doctors'))
        doctor.update(biography='Personal approach to care.\nA second paragraph.', availability=[
            {'day':'monday','start':'09:00','end':'12:00'},
            {'day':'monday','start':'16:00','end':'20:00'},
        ])
        state = {'drafts':[doctor], 'deletions':[], 'activity':[], 'settings':{'appointment_start':'08:00','appointment_end':'22:00'}}
        response = self.client.post('/dashboard/publish/', json.dumps({'revision':base['revision'],'state':state}), content_type='application/json')
        self.assertEqual(response.status_code, 200, response.content)
        response = self.client.get(profile_url(doctor))
        for value in ['Personal approach to care.', 'Monday', '09:00', '12:00', '16:00', '20:00']:
            self.assertContains(response, value)
        self.assertEqual(next(r for r in WebsiteWorkspace.objects.get(pk=1).published['records'] if r['id']==doctor['id'])['availability'], doctor['availability'])

    def test_dashboard_fields_and_invalid_schedule_rejected(self):
        staff = get_user_model().objects.create_user(username='scheduler', password='test', is_staff=True)
        self.client.force_login(staff)
        response = self.client.get('/dashboard/')
        self.assertContains(response, 'name="biography"')
        self.assertContains(response, 'id="doctor-add-time"')
        base = self.client.get('/dashboard/content/').json()
        doctor = deepcopy(next(r for r in base['records'] if r['section']=='doctors'))
        doctor['availability'] = [{'day':'monday','start':'16:00','end':'09:00'}]
        response = self.client.post('/dashboard/publish/', json.dumps({
            'revision':base['revision'], 'state':{'drafts':[doctor],'deletions':[],'activity':[]}
        }), content_type='application/json')
        self.assertEqual(response.status_code, 400)

    def test_schedule_validation(self):
        for slots in [None, [{'day':'bad','start':'09:00','end':'10:00'}],
                      [{'day':'monday','start':'12:00','end':'09:00'}],
                      [{'day':'monday','start':'09:00','end':'12:00'}, {'day':'monday','start':'11:00','end':'13:00'}]]:
            with self.assertRaises(ValidationError):
                validate_availability(slots)
        validate_availability([{'day':'monday','start':'09:00','end':'12:00'}, {'day':'monday','start':'12:00','end':'13:00'}])

    def test_biography_is_escaped(self):
        data = seeds()
        doctor = next(r for r in data['records'] if r['section']=='doctors')
        doctor['biography'] = '<script>alert(1)</script>'
        WebsiteWorkspace.objects.create(pk=1, published=data)
        response = self.client.get(profile_url(doctor))
        self.assertContains(response, '&lt;script&gt;')
        self.assertNotContains(response, '<script>alert(1)</script>')

    def test_directory_shows_upcoming_dates_and_split_sessions(self):
        from datetime import datetime, timezone
        from unittest.mock import patch
        data = seeds()
        data['settings'] = {'appointment_start':'08:00','appointment_end':'22:00'}
        doctor = next(r for r in data['records'] if r['section']=='doctors')
        doctor['availability'] = [
            {'day':'monday','start':'09:00','end':'12:00'},
            {'day':'monday','start':'16:00','end':'20:00'},
        ]
        WebsiteWorkspace.objects.create(pk=1, published=data)
        with patch('django.utils.timezone.now', return_value=datetime(2026, 10, 19, 2, tzinfo=timezone.utc)):
            response = self.client.get('/our-doctors/')
        soup = BeautifulSoup(response.content, 'html.parser')
        panel = soup.select_one('.doctor-list-availability')
        self.assertEqual(panel.select_one('time')['datetime'], '2026-10-19')
        self.assertIn('9:00 AM – 12:00 PM', panel.text)
        self.assertIn('4:00 PM – 8:00 PM', panel.text)
        self.assertIn('Bangladesh time', panel.text)

    def test_upcoming_dates_use_bangladesh_time_and_omit_ended_sessions(self):
        from datetime import datetime, timezone
        from .doctors import upcoming_availability
        record = {'availability': [
            {'day':'monday','start':'09:00','end':'12:00'},
            {'day':'monday','start':'16:00','end':'20:00'},
        ]}
        dates = upcoming_availability(record, datetime(2026, 10, 19, 8, tzinfo=timezone.utc))
        self.assertEqual(len(dates), 1)
        self.assertEqual(dates[0]['slots'], [{'start':'4:00 PM','end':'8:00 PM'}])
        self.assertEqual(upcoming_availability(record, datetime(2026, 10, 19, 15, tzinfo=timezone.utc)), [])
