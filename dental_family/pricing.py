"""Database catalog linkage and published calculator data."""
import re
from decimal import Decimal, InvalidOperation
from django.core.exceptions import ValidationError


def pricing_catalog(data, state=None):
    from .content import available_services, gallery_snapshot
    data = gallery_snapshot(data)
    state = state or {}
    records = {r['id']:r for r in data['records'] if r['section']=='treatments'}
    records.update({r['id']:r for r in state.get('drafts',[]) if r['section']=='treatments'})
    for deletion in state.get('deletions',[]):
        records.pop(deletion['id'],None)
    return [{**service, 'treatments':[{'id':r['id'],'title':r['title']} for r in records.values() if r.get('service')==service['id']]} for service in available_services(data,state)]


def validate_price_links(state, data):
    catalog = {service['id']:service for service in pricing_catalog(data,state)}
    for record in state.get('drafts',[]):
        if record['section']!='prices' or 'service_id' not in record:
            continue  # Existing unlinked fees remain editable during migration.
        service = catalog.get(record['service_id'])
        if service is None:
            raise ValidationError('Select an existing service for this price.')
        treatment = record.get('treatment_id','')
        if not isinstance(treatment,str) or (treatment and treatment not in {r['id'] for r in service['treatments']}):
            raise ValidationError('Select a treatment belonging to the chosen service.')
        record['category'] = service['name']


def price_bounds(record):
    kind = record.get('price_type')
    if kind=='custom':
        return None
    if kind in {'single','range'}:
        raw = (record.get('price_min'),record.get('price_max') if kind=='range' else record.get('price_min'))
    else:
        match = re.fullmatch(r'\s*([\d,]+(?:\.\d{1,2})?)(?:\s*[-–—]\s*([\d,]+(?:\.\d{1,2})?))?\s*(?:Tk|BDT|৳)\s*',record.get('price',''),re.I)
        if not match:
            return None
        raw = (match[1].replace(',',''),(match[2] or match[1]).replace(',',''))
    try:
        lo,hi = (Decimal(str(value)) for value in raw)
        if not lo.is_finite() or not hi.is_finite() or lo<0 or hi<lo:
            return None
        return int(lo*100),int(hi*100)
    except (InvalidOperation,ValueError,TypeError):
        return None


def resolve_service_id(record, data):
    services = {service['id']:service for service in data.get('services',[])}
    if record.get('service_id') in services:
        return record['service_id']
    by_name = {service['name'].casefold():service['id'] for service in services.values()}
    category = record.get('category','').casefold()
    identifier = by_name.get(category)
    if identifier:
        return identifier
    legacy = {'dental essentials':'general_dentistry','dental restorations':'general_dentistry'}
    identifier = legacy.get(category)
    return identifier if identifier in services else None


def calculator_data(data):
    services = {s['id']:{'id':s['id'],'name':s['name'],'prices':[]} for s in data.get('services',[])}
    by_name = {s['name'].casefold():s['id'] for s in data.get('services',[])}
    for record in sorted((r for r in data['records'] if r['section']=='prices'),key=lambda r:r.get('order',1)):
        service_id = resolve_service_id(record,data)
        if service_id not in services:
            service_id = by_name.get(record['category'].casefold(),'legacy:'+record['category'])
        services.setdefault(service_id,{'id':service_id,'name':record['category'],'prices':[]})
        bounds = price_bounds(record)
        services[service_id]['prices'].append({'id':record['id'],'title':record['title'],'treatment_id':record.get('treatment_id',''),'label':record['price'],'min':bounds[0] if bounds else None,'max':bounds[1] if bounds else None})
    return {'services':list(services.values())}
