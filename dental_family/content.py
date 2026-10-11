"""Dashboard persistence, validation, and public content projection."""
import json
import re
from pathlib import Path
from urllib.parse import urlsplit
from bs4 import BeautifulSoup
from django.core.exceptions import ValidationError

ROOT = Path(__file__).resolve().parents[1]
SECTIONS = {'pages', 'treatments', 'articles', 'gallery', 'clinic', 'doctors', 'locations', 'faqs'}


def script_data(name, variable):
    text = (ROOT / 'static/dental_family/js' / name).read_text()
    return json.JSONDecoder().raw_decode(text.split('window.' + variable + ' =', 1)[1].strip())[0] if 'window.' + variable + ' =' in text else json.JSONDecoder().raw_decode(text.split('window.' + variable + '=', 1)[1].strip())[0]


def seeds():
    records = json.loads((ROOT / 'static/dental_family/dashboard-content.json').read_text())
    return {'records': records + script_data('location-data.js', 'DashboardLocations') + script_data('faq-data.js', 'DashboardFAQs'), 'topics': script_data('faq-data.js', 'DashboardFAQTopics'), 'services': script_data('service-catalog.js', 'DashboardServices'), 'gallery_sections': ['Our space','Our team','Our technology']}


def gallery_name(value):
    name = ' '.join(str(value).split())
    return 'Our space' if name.casefold() in {'our space','our spaces'} else name


def gallery_names(values):
    names = {}
    for value in values:
        name = gallery_name(value)
        if name and name.casefold() != 'all photos':
            names.setdefault(name.casefold(), name)
    return list(names.values())


def gallery_snapshot(data):
    from copy import deepcopy
    result = deepcopy(data)
    result['gallery_sections'] = gallery_names(data.get('gallery_sections', ['Our space','Our team','Our technology']))
    original = {r['id']:r.get('gallery_category') for r in seeds()['records'] if r['section']=='gallery'}
    for record in result['records']:
        if record['section']=='gallery':
            record['gallery_category'] = gallery_name(record.get('gallery_category') or original.get(record['id']) or 'Our space')
    return result


def safe_url(value, local=False):
    if not isinstance(value, str) or re.search(r'[\x00-\x20\\]', value):
        return False
    if value.startswith('/') and not value.startswith('//'):
        return True
    return not local and urlsplit(value).scheme.lower() in {'http', 'https', 'mailto', 'tel'}


def clean_html(value):
    soup = BeautifulSoup(str(value), 'html.parser')
    allowed = {'p','br','b','strong','i','em','u','s','strike','h1','h2','h3','h4','h5','h6','ul','ol','li','blockquote','div','pre','code','hr','a'}
    for tag in list(soup.find_all(True)):
        if tag.name is None:
            continue
        if tag.name in {'script','style','iframe','object','svg'}:
            tag.decompose()
        elif tag.name not in allowed:
            tag.unwrap()
        else:
            href = tag.get('href', '')
            tag.attrs = {'href': href, 'rel': 'noopener noreferrer'} if tag.name == 'a' and safe_url(href) else {}
    return str(soup)


def validate_state(data):
    if not isinstance(data, dict):
        raise ValidationError('Invalid workspace.')
    for name in ['drafts','deletions','activity','services','faqTopics','deletedFAQTopics','deletedServices','faqTopicOrder','serviceOrder','galleryCategories','deletedGalleryCategories']:
        if name in data and (not isinstance(data[name], list) or len(data[name]) > 2000):
            raise ValidationError(f'Invalid {name}.')
    for name in ['settings','serviceEdits','treatmentOptions','optionOrder']:
        if name in data and not isinstance(data[name], dict):
            raise ValidationError(f'Invalid {name}.')
    for name in ['deletedServices','faqTopicOrder','serviceOrder','galleryCategories','deletedGalleryCategories']:
        if not all(isinstance(value,str) for value in data.get(name,[])):
            raise ValidationError(f'Invalid {name}.')
    for name in ['optionOrder','treatmentOptions']:
        if not all(isinstance(values,list) and all(isinstance(value,str) for value in values) for values in data.get(name,{}).values()):
            raise ValidationError(f'Invalid {name}.')
    for name in data.get('galleryCategories', []):
        if not name.strip() or len(name)>100 or name.casefold()=='all photos':
            raise ValidationError('Invalid gallery section name.')
    for record in data.get('drafts', []):
        if not isinstance(record, dict) or record.get('section') not in SECTIONS or not isinstance(record.get('id'), str) or not record['id']:
            raise ValidationError('Invalid content record.')
        if not isinstance(record.get('title'), str) or not record['title'].strip() or len(record['title']) > 500:
            raise ValidationError('A content title is required (maximum 500 characters).')
        if not safe_url(record.get('url'), local=True) or not re.fullmatch(r'/[\w/.-]*/?', record['url']):
            raise ValidationError('Use a valid local content URL.')
        if record['url'].split('/')[1] in {'dashboard','static','media'}:
            raise ValidationError('This URL is reserved.')
        for key in ['image','canonical_url']:
            if record.get(key) and (not safe_url(record[key]) or (not record[key].startswith('/') and urlsplit(record[key]).scheme not in {'http','https'})):
                raise ValidationError(f'Invalid {key}.')
        if record.get('details'):
            record['details'] = clean_html(record['details'])
        for key, value in record.items():
            if key in {'gallery_category','description','short_details','topic','service','image','alt','address','phone','hours','map_pin','qualifications','training','position','registration','specialty','robots','seo_title','meta_description','keywords','og_title','og_description'} and not isinstance(value,str):
                raise ValidationError(f'Invalid {key}.')
            if isinstance(value, str) and len(value) > 100000:
                raise ValidationError(f'{key} is too long.')
    for deletion in data.get('deletions', []):
        if not isinstance(deletion, dict) or not isinstance(deletion.get('id'), str):
            raise ValidationError('Invalid deletion.')
    for topic in data.get('faqTopics', []):
        if not isinstance(topic, dict) or not topic.get('id') or not topic.get('title') or not safe_url(topic.get('url'), local=True):
            raise ValidationError('Invalid FAQ topic.')
    for service in data.get('services', []) + list(data.get('serviceEdits', {}).values()):
        if not isinstance(service, dict) or not service.get('id') or not isinstance(service.get('name'), str) or not service['name'].strip() or not isinstance(service.get('treatments'), list) or not all(isinstance(name, str) for name in service['treatments']):
            raise ValidationError('Invalid service.')
    return data


def ordered(items, ids, key):
    positions = {value: index for index, value in enumerate(ids)}
    return sorted(items, key=lambda item: positions.get(key(item), len(ids)))


def snapshot(published, state):
    base = published or seeds()
    by_id = {record['id']: record for record in base['records']}
    for record in state.get('drafts', []):
        by_id[record['id']] = {**record, 'status': 'Website snapshot', '_edited': True}
    for deletion in state.get('deletions', []):
        by_id.pop(deletion['id'], None)
    topics = {topic['id']: topic for topic in base['topics']}
    topics.update({topic['id']: topic for topic in state.get('faqTopics', [])})
    for topic in state.get('deletedFAQTopics', []):
        topics.pop(topic['id'], None)
    services = {service['id']: service for service in base['services']}
    services.update({service['id']: service for service in state.get('services', [])})
    services.update(state.get('serviceEdits', {}))
    for service_id in state.get('deletedServices', []):
        services.pop(service_id, None)
    for service_id, service in services.items():
        options = list(dict.fromkeys(service['treatments'] + state.get('treatmentOptions', {}).get(service_id, [])))
        service['treatments'] = ordered(options, state.get('optionOrder', {}).get(service_id, []), lambda value: value)
    result = {'records': list(by_id.values()), 'topics': ordered(list(topics.values()), state.get('faqTopicOrder', []), lambda item: item['id']), 'services': ordered(list(services.values()), state.get('serviceOrder', []), lambda item: item['id']), 'settings': state.get('settings', base.get('settings', {}))}
    topic_routes = {}
    for topic in result['topics']:
        if not re.fullmatch(r'/[\w.-]+/',topic['url']) or topic['url'].split('/')[1] in {'dashboard','static','media'}:
            raise ValidationError('Invalid FAQ URL.')
        if topic['url'] in topic_routes:
            raise ValidationError('Two FAQ topics cannot share a URL.')
        topic_routes[topic['url']] = topic['id']
    categories = gallery_names(base.get('gallery_sections',['Our space','Our team','Our technology']) + state.get('galleryCategories',[]))
    deleted_categories = gallery_names(state.get('deletedGalleryCategories',[]))
    categories = [name for name in categories if name not in deleted_categories]
    seed_categories = {r['id']:r.get('gallery_category') for r in seeds()['records'] if r['section']=='gallery'}
    for record in result['records']:
        if record['section']=='gallery':
            record['gallery_category'] = gallery_name(record.get('gallery_category') or seed_categories.get(record['id']) or 'Our space')
            if not isinstance(record['gallery_category'],str) or not record['gallery_category'].strip() or len(record['gallery_category'])>100 or record['gallery_category'].casefold()=='all photos':
                raise ValidationError('Invalid gallery section.')
            if record['gallery_category'] in deleted_categories:
                raise ValidationError('Move photos before deleting their gallery section.')
            if record['gallery_category'] not in categories:
                categories.append(record['gallery_category'])
    result['gallery_sections'] = categories
    routes = {}
    for record in result['records']:
        if record['section'] in {'pages','articles','treatments'}:
            if record['url'] in routes and routes[record['url']] != record['id']:
                raise ValidationError('Two content items cannot use the same URL.')
            routes[record['url']] = record['id']
        if record['section'] == 'faqs' and record.get('topic') not in topics:
            raise ValidationError('Move FAQ questions before removing their topic.')
    return result
