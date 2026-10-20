"""Dashboard persistence, validation, and public content projection."""
import json
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urlsplit

from bs4 import BeautifulSoup
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator, validate_email
from django.utils import timezone
from django.utils.text import slugify

ROOT = Path(__file__).resolve().parents[1]
LEGACY_TREATMENT_SERVICES = {
    '/advanced_oral_surgery/':'advanced_oral_surgery', '/clear_aligner/':'clear_aligner',
    '/cosmetic_dentistry/':'cosmetic_dentistry', '/cosmetic-bonding/':'cosmetic_dentistry',
    '/gum-reshaping/':'cosmetic_dentistry', '/teeth-whitening/':'cosmetic_dentistry', '/veneers/':'cosmetic_dentistry',
    '/general_dentistry/':'general_dentistry', '/fillings/':'general_dentistry',
    '/regular-dental-checkup/':'general_dentistry', '/restorative_dentistry/':'general_dentistry',
    '/root-canals/':'root-canals', '/emergency_dental_care/':'emergency_dental_care',
}
SECTIONS = {'pages', 'treatments', 'articles', 'gallery', 'clinic', 'doctors', 'locations', 'faqs', 'prices', 'payments'}


def script_data(name, variable):
    text = (ROOT / 'static/dental_family/js' / name).read_text(encoding='utf-8')
    return json.JSONDecoder().raw_decode(text.split('window.' + variable + ' =', 1)[1].strip())[0] if 'window.' + variable + ' =' in text else json.JSONDecoder().raw_decode(text.split('window.' + variable + '=', 1)[1].strip())[0]


def seeds():
    records = json.loads((ROOT / 'static/dental_family/dashboard-content.json').read_text(encoding='utf-8'))
    return {'records': records + script_data('payment-data.js','DashboardPayments') + script_data('price-data.js', 'DashboardPrices') + script_data('location-data.js', 'DashboardLocations') + script_data('faq-data.js', 'DashboardFAQs'), 'topics': script_data('faq-data.js', 'DashboardFAQTopics'), 'services': script_data('service-catalog.js', 'DashboardServices'), 'gallery_sections': ['Our space','Our team','Our technology'], 'price_guide_initialized':True, 'payments_initialized':True, 'contact_details':script_data('contact-data.js','DashboardContactDetails')}


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
    if not data.get('price_guide_initialized'):
        existing = {r['id'] for r in result['records']}
        result['records'].extend(r for r in script_data('price-data.js','DashboardPrices') if r['id'] not in existing)
    if not data.get('payments_initialized'):
        existing={r['id'] for r in result['records']}
        result['records'].extend(r for r in script_data('payment-data.js','DashboardPayments') if r['id'] not in existing)
    result['payments_initialized']=True
    result.setdefault('contact_details',script_data('contact-data.js','DashboardContactDetails'))
    result['price_guide_initialized'] = True
    result.setdefault('price_services', list(dict.fromkeys(r['category'] for r in result['records'] if r['section']=='prices')))
    for record in result['records']:
        if record['id'] in {'/pricing-guide-2/','/financing-2/'} and record['section']=='treatments':
            record['section']='pages'
    result['gallery_sections'] = gallery_names(data.get('gallery_sections', ['Our space','Our team','Our technology']))
    homepage_defaults = {r['id']:r for r in seeds()['records'] if r['section']=='treatments'}
    for record in result['records']:
        if record['section']=='treatments':
            default = homepage_defaults.get(record['id'], {})
            record.setdefault('service', LEGACY_TREATMENT_SERVICES.get(record['id'],''))
            record.setdefault('show_on_homepage', default.get('show_on_homepage', False))
            record.setdefault('homepage_order', default.get('homepage_order', 0))
    featured = sorted((r for r in result['records'] if r['section']=='treatments' and r.get('show_on_homepage')), key=lambda r:r.get('homepage_order', 0))
    for record in featured[3:]:
        record['show_on_homepage'] = False
        record['homepage_order'] = 0
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


def validate_contact_details(details):
    fields={'phone','email','whatsapp','facebook','instagram','opening_hours'}
    if not isinstance(details,dict) or set(details)!=fields:
        raise ValidationError('Enter valid contact details.')
    for name,value in details.items():
        if not isinstance(value,str) or len(value)>500:
            raise ValidationError('Contact fields must contain valid text.')
        details[name]=value.strip()
    validate_email(details['email'])
    for name in ['phone','whatsapp']:
        value=details[name]
        if name=='whatsapp' and not value:
            continue
        if not re.fullmatch(r'[+0-9 ()-]+',value) or not 7<=len(re.sub(r'\D','',value))<=15:
            raise ValidationError('Enter a valid phone number including its country code.')
    for name in ['facebook','instagram']:
        if details[name]:
            URLValidator(schemes=['http','https'])(details[name])
    return details


def payment_lines(record):
    lines=[]
    if record.get('payment_type')=='mobile':
        lines.append(record.get('mobile_number',''))
    elif record.get('payment_type')=='bank':
        lines.extend([record.get('account_name',''), 'Account: '+record.get('account_number','')])
        if record.get('branch'):
            lines.append(record['branch'])
        if record.get('routing'):
            lines.append('Routing: '+record['routing'])
    lines.extend(record.get('notes','').splitlines())
    return [line for line in lines if line.strip()]


def validate_state(data, *, draft=False):
    if not isinstance(data, dict):
        raise ValidationError('Invalid workspace.')
    if 'improvementOptions' in data:
        from .improvements import validate_options
        validate_options(data['improvementOptions'])
    if 'contactDetails' in data:
        validate_contact_details(data['contactDetails'])
    for name in ['drafts','deletions','activity','services','faqTopics','deletedFAQTopics','deletedServices','faqTopicOrder','serviceOrder','galleryCategories','deletedGalleryCategories']:
        if name in data and (not isinstance(data[name], list) or len(data[name]) > 2000):
            raise ValidationError(f'Invalid {name}.')
    if 'homepageTreatmentOrder' in data:
        ids = data['homepageTreatmentOrder']
        if not isinstance(ids, list) or len(ids)>3 or not all(isinstance(value,str) for value in ids) or len(set(ids))!=len(ids):
            raise ValidationError('Select up to three unique homepage treatments.')
    if 'priceServices' in data:
        names=data['priceServices']
        if not isinstance(names,list) or len(names)>200 or any(not isinstance(name,str) or not name.strip() or len(name)>120 for name in names):
            raise ValidationError('Enter valid price guide service names.')
        names=[' '.join(name.split()) for name in names]
        if len({name.casefold() for name in names})!=len(names):
            raise ValidationError('Price guide service names must be unique.')
        data['priceServices']=names
    for name in ['settings','serviceEdits','treatmentOptions','optionOrder']:
        if name in data and not isinstance(data[name], dict):
            raise ValidationError(f'Invalid {name}.')
    from .booking_hours import validate_hours
    validate_hours(data.get('settings', {}))
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
        for key in ['image','before_image','after_image','canonical_url']:
            if record.get(key) and (not safe_url(record[key]) or (not record[key].startswith('/') and urlsplit(record[key]).scheme not in {'http','https'})):
                raise ValidationError(f'Invalid {key}.')
        if record['section']=='payments':
            kind=record.get('payment_type')
            if not isinstance(kind,str) or kind not in {'mobile','bank','cash','card','other'}:
                raise ValidationError('Choose a valid payment method.')
            for field in ['payment_label','mobile_number','account_name','account_number','branch','routing','notes']:
                value=record.get(field,'')
                if not isinstance(value,str) or len(value)>(2000 if field=='notes' else 150):
                    raise ValidationError('Enter valid payment details.')
                record[field]=value.strip()
            if not record['payment_label']:
                raise ValidationError('A payment label is required.')
            if kind=='mobile' and (not re.fullmatch(r'[+0-9 ()-]+',record['mobile_number']) or not 7<=len(re.sub(r'\D','',record['mobile_number']))<=15):
                raise ValidationError('Enter a valid mobile wallet number.')
            if kind=='bank' and (not record['account_name'] or not re.fullmatch(r'[0-9 -]+',record['account_number'])):
                raise ValidationError('Enter the bank account name and account number.')
            if kind=='bank' and record['routing'] and not record['routing'].isdigit():
                raise ValidationError('Routing numbers must contain digits only.')
            if type(record.get('order')) is not int or not 1<=record['order']<=10000 or type(record.get('enabled')) is not bool:
                raise ValidationError('Enter a valid payment order and visibility.')
            if record['url']!='/financing-2/':
                raise ValidationError('Use the payment options page URL.')
            record['description']='\n'.join(payment_lines(record))
        if record['section']=='prices':
            if 'price_type' in record:
                kind=record['price_type']
                if not isinstance(kind,str) or kind not in {'single','range','custom'}:
                    raise ValidationError('Choose a valid price type.')
                if kind!='custom':
                    amounts=[]
                    for field in ['price_min']+(['price_max'] if kind=='range' else []):
                        try:
                            value=Decimal(str(record.get(field,'')))
                            if not value.is_finite() or not 0<=value<=1000000000 or value.quantize(Decimal('.01'))!=value:
                                raise InvalidOperation
                        except (InvalidOperation,ValueError):
                            raise ValidationError('Enter valid prices with up to two decimal places.')
                        record[field]=str(value)
                        amounts.append(value)
                    if kind=='range' and amounts[1]<=amounts[0]:
                        raise ValidationError('The maximum price must be greater than the minimum price.')
                    if kind=='single':
                        record.pop('price_max',None)
                    record['price']='–'.join(format(value,',.2f').rstrip('0').rstrip('.') for value in amounts)+' Tk'
                    record['description']=record['price']
                else:
                    record.pop('price_min',None)
                    record.pop('price_max',None)
            for field in ['category','price']:
                if not isinstance(record.get(field),str) or not record[field].strip() or len(record[field])>120:
                    raise ValidationError(f'A valid {"service" if field=="category" else field} is required for price entries.')
                record[field]=record[field].strip()
            if type(record.get('order')) is not int or not 1<=record['order']<=10000:
                raise ValidationError('Price display order must be an integer from 1 to 10000.')
            if record['url']!='/pricing-guide-2/':
                raise ValidationError('Price entries must use the price guide URL.')
        if record['section'] == 'locations':
            if 'show_on_homepage' in record and type(record['show_on_homepage']) is not bool:
                raise ValidationError('Invalid homepage branch visibility.')
            if 'homepage_order' in record and (type(record['homepage_order']) is not int or not 1 <= record['homepage_order'] <= 10000):
                raise ValidationError('Homepage branch order must be an integer from 1 to 10000.')
            for field in ('photo_alt', 'directions_label', 'booking_label', 'directions_url', 'booking_url'):
                if field in record and (not isinstance(record[field], str) or len(record[field]) > 1000):
                    raise ValidationError(f'Invalid {field}.')
            for field in ('directions_url', 'booking_url'):
                if record.get(field) and (not safe_url(record[field]) or (not record[field].startswith('/') and urlsplit(record[field]).scheme not in {'http', 'https'})):
                    raise ValidationError('Use a local path or an HTTP(S) button link.')
            for day in ('saturday', 'sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday'):
                status = record.get(day + '_status', 'unconfirmed')
                if status not in ('open', 'closed', 'unconfirmed'):
                    raise ValidationError('Invalid opening day status.')
                for suffix in ('_open', '_close'):
                    value = record.get(day + suffix, '')
                    if not isinstance(value, str) or (value and not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d', value)):
                        raise ValidationError('Enter valid opening and closing times.')
                    if status == 'open' and not value:
                        raise ValidationError('Open days need opening and closing times.')
        if record['section'] == 'treatments' and 'improvement_options' in record:
            values = record['improvement_options']
            if not isinstance(values,list) or len(values)>100 or any(not isinstance(value,str) for value in values) or len(set(values))!=len(values):
                raise ValidationError('Select valid improvement options.')
        if record['section'] == 'doctors':
            from .doctors import validate_availability
            validate_availability(record.get('availability', []), draft=draft)
            if not isinstance(record.get('biography', ''), str):
                raise ValidationError('Biography must be text.')
        if record.get('details'):
            record['details'] = clean_html(record['details'])
        for key, value in record.items():
            if key in {'gallery_category','description','short_details','topic','service','image','before_image','after_image','alt','address','phone','hours','map_pin','qualifications','training','position','registration','specialty','robots','seo_title','meta_description','keywords','og_title','og_description'} and not isinstance(value,str):
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


def treatment_slug(title):
    title = title.replace('’', "'").replace("'", '').replace('&', ' and ')
    return slugify(title)[:100].rstrip('-') or 'treatment'


def assign_treatment_urls(records, original, drafts, topics):
    """Generate canonical treatment URLs and retain previous URLs as redirects."""
    edited = {r['id'] for r in drafts if r['section']=='treatments'}
    old = {r['id']:r for r in original}
    exported = json.loads((ROOT / 'routes.json').read_text(encoding='utf-8'))
    original_urls = {r['url'] for r in original if r['section']=='treatments'}
    used = {'/dashboard/', '/static/', '/media/'} | (set(exported)-original_urls)
    used.update(t['url'] for t in topics)
    used.update(r['url'] for r in records if r['id'] not in edited)
    for r in records:
        used.update(old.get(r['id'],{}).get('url_aliases',[]))
    for r in records:
        if r['id'] not in edited:
            continue
        previous = old.get(r['id'], {})
        own_aliases = set(previous.get('url_aliases', []))
        base = treatment_slug(r['title'])
        slug = base
        suffix = 2
        while '/' + slug + '/' in used-own_aliases:
            slug = f'{base}-{suffix}'
            suffix += 1
        r['slug'] = slug
        r['url'] = '/' + slug + '/'
        aliases = own_aliases | ({previous['url']} if previous.get('url') else set())
        r['url_aliases'] = sorted(aliases-{r['url']})
        used.add(r['url'])
        used.update(r['url_aliases'])


def available_services(published, state):
    """Current dashboard catalog, including saved service edits and removals."""
    base = published or seeds()
    services = {service['id']: service for service in base['services']}
    services.update({service['id']: service for service in state.get('services', [])})
    services.update(state.get('serviceEdits', {}))
    for identifier in state.get('deletedServices', []):
        services.pop(identifier, None)
    return ordered(list(services.values()), state.get('serviceOrder', []), lambda item: item['id'])


def snapshot(published, state):
    base = gallery_snapshot(published or seeds())
    by_id = {record['id']: record for record in base['records']}
    for record in state.get('drafts', []):
        by_id[record['id']] = {**by_id.get(record['id'], {}), **record, 'status': 'Website snapshot', '_edited': True}
        if record['section']=='prices':
            saved=by_id[record['id']]
            if 'price_type' not in record:
                for field in ['price_type','price_min','price_max']:
                    saved.pop(field,None)
            elif record['price_type']!='range':
                saved.pop('price_max',None)
                if record['price_type']=='custom':
                    saved.pop('price_min',None)
        if record['section']=='treatments':
            previous = next((r for r in base['records'] if r['id']==record['id']),None)
            by_id[record['id']]['created_at'] = previous.get('created_at','') if previous else timezone.now().isoformat()
    for deletion in state.get('deletions', []):
        by_id.pop(deletion['id'], None)
    # Treat requested branch positions as moves, so editing one branch cannot
    # leave it tied with another branch at the same position.
    branches = [r for r in by_id.values() if r['section'] == 'locations']
    for field in ('order', 'homepage_order'):
        arranged = sorted(branches, key=lambda r: (int(r.get(field) or r.get('order') or 1), not bool(r.get(field))))
        for edit in state.get('drafts', []):
            if edit['section'] != 'locations' or field not in edit:
                continue
            record = by_id.get(edit['id'])
            if record is None:
                continue
            arranged = [r for r in arranged if r['id'] != edit['id']]
            arranged.insert(min(int(edit[field]) - 1, len(arranged)), record)
        for position, record in enumerate(arranged, 1):
            record[field] = position
    selected = state.get('homepageTreatmentOrder', [r['id'] for r in sorted(by_id.values(), key=lambda r:r.get('homepage_order',0)) if r['section']=='treatments' and r.get('show_on_homepage')])
    selected = [identifier for identifier in selected if identifier not in {d['id'] for d in state.get('deletions', [])}]
    if len(selected)>3 or any(identifier not in by_id or by_id[identifier]['section']!='treatments' for identifier in selected):
        raise ValidationError('Select up to three existing treatments for the homepage.')
    for record in by_id.values():
        if record['section']=='treatments':
            record['show_on_homepage'] = record['id'] in selected
            record['homepage_order'] = selected.index(record['id'])+1 if record['id'] in selected else 0
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
    assign_treatment_urls(list(by_id.values()), base['records'], state.get('drafts',[]), list(topics.values()))
    result = {'payments_initialized':True, 'price_guide_initialized':True, 'records': list(by_id.values()), 'topics': ordered(list(topics.values()), state.get('faqTopicOrder', []), lambda item: item['id']), 'services': ordered(list(services.values()), state.get('serviceOrder', []), lambda item: item['id']), 'settings': state.get('settings', base.get('settings', {}))}
    result['improvement_options'] = state.get('improvementOptions', base.get('improvement_options', []))
    available_goals = {item['id'] for item in result['improvement_options']}
    for record in result['records']:
        if record['section']=='treatments' and 'improvement_options' in record:
            record['improvement_options'] = [value for value in record['improvement_options'] if value in available_goals]
    result['contact_details']=state.get('contactDetails',base.get('contact_details',script_data('contact-data.js','DashboardContactDetails')))
    price_services = list(state.get('priceServices',base.get('price_services',[])))
    for record in result['records']:
        if record['section']=='prices' and record['category'] not in price_services:
            if 'priceServices' in state:
                raise ValidationError('Move price entries to another service before deleting their service.')
            price_services.append(record['category'])
    result['price_services'] = price_services
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
