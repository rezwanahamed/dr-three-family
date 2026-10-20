"""Shared published appointment window for public pages and booking validation."""
import re
from datetime import datetime
from django.core.exceptions import ValidationError

DEFAULT_HOURS = {'start': '16:00', 'end': '22:00'}


def validate_hours(settings):
    start = settings.get('appointment_start', DEFAULT_HOURS['start'])
    end = settings.get('appointment_end', DEFAULT_HOURS['end'])
    if any(not isinstance(t, str) or not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d', t) for t in (start, end)) or start >= end:
        raise ValidationError('Appointment closing time must be after opening time. Use valid same-day times.')


def hours_for(data):
    settings = data.get('settings', {})
    start, end = settings.get('appointment_start', '16:00'), settings.get('appointment_end', '22:00')
    def label(value):
        return datetime.strptime(value, '%H:%M').strftime('%I:%M %p').lstrip('0')
    return {'start': start, 'end': end, 'label': label(start) + ' – ' + label(end), 'timezone': 'Asia/Dhaka'}


def published_data():
    from .models import WebsiteWorkspace
    workspace = WebsiteWorkspace.objects.filter(pk=1).first()
    return workspace.published if workspace and workspace.published else {}


def effective_slots(record, hours):
    slots = []
    for slot in record.get('availability', []):
        start, end = max(slot['start'], hours['start']), min(slot['end'], hours['end'])
        if start < end:
            slots.append({'day': slot['day'], 'start': start, 'end': end})
    return slots


def doctor_schedules(data, options):
    # Match portal choices by name rather than assuming portal IDs equal dashboard IDs.
    def normalize(value):
        return re.sub(r'[^a-z0-9]', '', value.lower())
    records = {normalize(r['title']): r for r in data.get('records', []) if r['section'] == 'doctors'}
    hours = hours_for(data)
    result = {}
    for value, name in options['doctor_name']:
        record = records.get(normalize(name))
        if record and record.get('availability'):
            result[value] = effective_slots(record, hours)
    return result
