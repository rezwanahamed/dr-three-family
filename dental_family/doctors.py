"""Doctor profile routing and weekly consulting hours."""
import re
from django.core.exceptions import ValidationError
from django.http import Http404
from django.shortcuts import render
from django.utils.text import slugify

DAYS = ('saturday', 'sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday')


def profile_url(record):
    return '/our-doctors/' + slugify(record['id']) + '/'


def validate_availability(value):
    if not isinstance(value, list) or len(value) > 100:
        raise ValidationError('Availability must contain at most 100 time ranges.')
    by_day = {}
    for slot in value:
        if not isinstance(slot, dict) or slot.get('day') not in DAYS:
            raise ValidationError('Choose a valid availability day.')
        for key in ('start', 'end'):
            if not isinstance(slot.get(key), str) or not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d', slot[key]):
                raise ValidationError('Enter valid availability times.')
        if slot['start'] >= slot['end']:
            raise ValidationError('Availability end time must be after its start time.')
        by_day.setdefault(slot['day'], []).append((slot['start'], slot['end']))
    for ranges in by_day.values():
        ranges.sort()
        if any(a[1] > b[0] for a, b in zip(ranges, ranges[1:])):
            raise ValidationError('Availability ranges on the same day must not overlap.')



def upcoming_availability(record, now=None, hours=None):
    from datetime import timedelta, datetime
    from zoneinfo import ZoneInfo
    from django.utils import timezone
    now = (now or timezone.now()).astimezone(ZoneInfo('Asia/Dhaka'))
    from .booking_hours import effective_slots
    availability = effective_slots(record, hours) if hours else record.get('availability', [])
    result = []
    for offset in range(7):
        date = now.date() + timedelta(days=offset)
        slots = []
        for slot in sorted(availability, key=lambda s: s['start']):
            if slot['day'] != date.strftime('%A').lower():
                continue
            if offset == 0 and slot['end'] <= now.strftime('%H:%M'):
                continue
            def label(value):
                return datetime.strptime(value, '%H:%M').strftime('%I:%M %p').lstrip('0')
            slots.append({'start': label(slot['start']), 'end': label(slot['end'])})
        if slots:
            result.append({'date': date, 'slots': slots})
    return result


def doctor_profile(request, slug):
    from .content import seeds
    from .models import WebsiteWorkspace
    workspace = WebsiteWorkspace.objects.filter(pk=1).first()
    data = workspace.published if workspace and workspace.published else seeds()
    doctor = next((r for r in data['records'] if r['section'] == 'doctors' and slugify(r['id']) == slug), None)
    if doctor is None:
        raise Http404('Doctor not found')
    from .booking_hours import hours_for, effective_slots
    hours = hours_for(data)
    availability = effective_slots(doctor, hours)
    schedule = []
    for day in DAYS:
        slots = sorted((s for s in availability if s['day'] == day), key=lambda s:s['start'])
        if slots:
            schedule.append({'day': day.title(), 'slots': slots})
    return render(request, 'dental_family/doctor_detail.html', {
        'doctor': doctor, 'schedule': schedule, 'booking_hours': hours,
        'credentials': '\n'.join(doctor.get(k, '') for k in ('qualifications', 'training', 'position')).splitlines(),
    })
