"""Reusable treatment-goal cards selected by editors."""
from django.core.exceptions import ValidationError
from .content import safe_url
from urllib.parse import urlsplit


def validate_options(options):
    if not isinstance(options, list) or len(options) > 100:
        raise ValidationError('Use at most 100 improvement options.')
    ids = set()
    for option in options:
        if not isinstance(option, dict):
            raise ValidationError('Invalid improvement option.')
        for field, limit in [('id',150),('title',150),('image',2000),('treatment_id',200)]:
            value = option.get(field)
            if not isinstance(value,str) or not value.strip() or len(value)>limit:
                raise ValidationError('Each improvement option needs a title, image, and destination treatment.')
        if option['id'] in ids:
            raise ValidationError('Improvement option IDs must be unique.')
        ids.add(option['id'])
        image = option['image']
        if not safe_url(image) or (not image.startswith('/') and urlsplit(image).scheme not in {'http','https'}):
            raise ValidationError('Use a local or HTTP(S) option image URL.')


def goal_library(data):
    if 'improvement_options' in data:
        return data['improvement_options']
    import json
    from django.conf import settings
    return json.loads((settings.BASE_DIR / 'static/dental_family/improvement-catalog.json').read_text())['options']


def goal_url(option):
    from django.utils.text import slugify
    return '/smile-goals/' + slugify(option['id']) + '/'


def treatments_for_goal(option, data):
    records = [record for record in data['records'] if record['section']=='treatments' and (
        option['id'] in (record.get('improvement_options') or []) or record['id']==option['treatment_id'])]
    return sorted(records, key=lambda record:(record['id']!=option['treatment_id'],record['title'].casefold()))


def goal_treatments_page(request, slug):
    from django.http import Http404, HttpResponse
    from django.template.loader import render_to_string
    from django.utils.text import slugify
    from .models import WebsiteWorkspace
    from .content import seeds
    from .public_content import treatment_navigation_html
    workspace = WebsiteWorkspace.objects.filter(pk=1).first()
    data = workspace.published if workspace and workspace.published else seeds()
    option = next((item for item in goal_library(data) if slugify(item['id'])==slug),None)
    if option is None:
        raise Http404('Smile goal not found')
    services = {service['id']:service['name'] for service in data.get('services',[])}
    records = [{**record, 'service_name':services.get(record.get('service'),'Dental care')} for record in treatments_for_goal(option,data)]
    html = render_to_string('dental_family/goal_treatments.html', {'goal':option,'treatments':records}, request=request)
    return HttpResponse(treatment_navigation_html(html,data))
