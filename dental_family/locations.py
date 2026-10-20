"""Shared branch card rendering and weekly schedule fields."""
from html import escape
from urllib.parse import quote
from .content import safe_url

DAYS = ('Saturday', 'Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday')



def schedule_rows(record):
    """Combine adjacent days only when their published hours match."""
    groups = []
    for day in DAYS:
        key = day.lower()
        status = record.get(key + '_status', 'unconfirmed')
        opening, closing = record.get(key + '_open'), record.get(key + '_close')
        signature = (status, opening, closing) if status == 'open' and opening and closing else (status if status == 'closed' else 'unconfirmed', None, None)
        if groups and groups[-1][2] == signature:
            groups[-1][1] = day
        else:
            groups.append([day, day, signature])

    def clock(time):
        hour, minute = map(int, time.split(':'))
        return f'{hour % 12 or 12}:{minute:02d} {"AM" if hour < 12 else "PM"}'

    rows = []
    for first, last, (status, opening, closing) in groups:
        label = first if first == last else first + '–' + last
        hours = 'Closed' if status == 'closed' else f'{clock(opening)} – {clock(closing)}' if status == 'open' else 'Please call to confirm'
        if status == 'open' and closing <= opening:
            hours += ' (next day)'
        rows.append(f'<div class="location-hours-row location-hours-row--{status}"><dt>{label}</dt><dd>{escape(hours)}</dd></div>')
    return rows


def location_card(record, index):
    def value(key, default=''):
        return escape(str(record.get(key) or default), quote=True)
    photo = record.get('image') or '/static/dental_family/assets/images/clinic.jpg'
    if not safe_url(photo):
        photo = '/static/dental_family/assets/images/clinic.jpg'
    directions = record.get('directions_url') or 'https://www.google.com/maps/search/?api=1&query=' + quote(record.get('map_pin') or record.get('address', ''))
    appointment = record.get('booking_url') or '/appointment/'
    rows = schedule_rows(record)
    return f'''<article class="location-card location-card--photo"><div class="location-photo-wrap"><img class="location-clinic-photo" src="{escape(photo, quote=True)}" alt="{value('photo_alt', 'Clinic interior')}" loading="lazy" width="600" height="340"><span class="location-number">{index + 1:02d}</span></div>
<div class="location-card-content"><header class="location-card-heading"><div class="eyebrow">{value('area')}</div><h3>{value('title')}</h3></header>
<address class="location-full-address">{value('address')}</address>
<p class="location-phone">Clinic phone: <a href="tel:{value('phone')}">{value('phone')}</a></p>
<section class="location-hours-panel" aria-label="Weekly opening hours"><h4>Opening hours</h4><dl class="location-weekly-hours">{''.join(rows)}</dl></section>
{('<p class="location-hours-extra">' + value('hours') + '</p>') if record.get('hours') else ''}
<div class="location-links"><a class="button location-directions" href="{escape(directions if safe_url(directions) else '/contact/', quote=True)}" target="_blank" rel="noopener noreferrer">{value('directions_label', 'Get directions')} ↗</a><a class="button location-booking" href="{escape(appointment if safe_url(appointment) else '/appointment/', quote=True)}">{value('booking_label', 'Book appointment')} →</a></div></div></article>'''
