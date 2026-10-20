from bs4 import BeautifulSoup
from django.test import SimpleTestCase
from .locations import schedule_rows


class LocationScheduleTests(SimpleTestCase):
    def rows(self, record):
        return BeautifulSoup(''.join(schedule_rows(record)), 'html.parser').select('.location-hours-row')

    def test_matching_days_become_a_range_with_separate_closed_day(self):
        record = {'friday_status': 'closed'}
        for day in ('saturday', 'sunday', 'monday', 'tuesday', 'wednesday', 'thursday'):
            record.update({day+'_status': 'open', day+'_open': '10:00', day+'_close': '20:00'})
        rows = self.rows(record)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0].dt.text, 'Saturday–Thursday')
        self.assertEqual(rows[0].dd.text, '10:00 AM – 8:00 PM')
        self.assertEqual(rows[1].dt.text, 'Friday')
        self.assertEqual(rows[1].dd.text, 'Closed')

    def test_unconfirmed_week_is_one_range(self):
        rows = self.rows({})
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].dt.text, 'Saturday–Friday')
        self.assertEqual(rows[0].dd.text, 'Please call to confirm')

    def test_different_hours_and_overnight_are_preserved(self):
        rows = self.rows({'saturday_status': 'open', 'saturday_open': '20:00', 'saturday_close': '02:00', 'sunday_status': 'open', 'sunday_open': '10:00', 'sunday_close': '18:00'})
        self.assertEqual(len(rows), 3)
        self.assertIn('(next day)', rows[0].dd.text)
        self.assertEqual(rows[1].dt.text, 'Sunday')
