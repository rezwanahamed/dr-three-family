"""Render managed content using the website's existing markup, CSS and animations."""
from copy import deepcopy
from html import escape
from urllib.parse import quote
import re
from bs4 import BeautifulSoup
from django.template.loader import render_to_string
from .content import clean_html, safe_url, gallery_snapshot, payment_lines


def text(node, value):
    if node is not None:
        node.clear()
        node.append(str(value or ''))


def image(node, record):
    if node and record.get('image') and safe_url(record['image']):
        node['src'] = record['image'].replace('/assets/images/theme/aligners.png', '/assets/images/theme/aligners-purple.png')
        node['alt'] = record.get('image_alt') or record.get('alt') or record['title']
        node.attrs.pop('srcset', None)


def fragment(html):
    return BeautifulSoup(html, 'html.parser')


def replace_children(container, nodes):
    if container is not None:
        container.clear()
        for node in nodes:
            container.append(node)


def managed_html(template, request, route, data, is_new=False, filter_services=None):
    soup = BeautifulSoup(render_to_string(template, request=request), 'html.parser')
    data = gallery_snapshot(data)
    records = data['records']
    aliases = {url:r['url'] for r in records if r['section']=='treatments' for url in r.get('url_aliases',[])}
    for link in soup.select('a[href]'):
        if link['href'] in aliases:
            link['href'] = aliases[link['href']]
    record = next((r for r in records if r['section'] in {'pages','articles','treatments'} and r['url'] == route), None)
    if record and (record.get('_edited') or is_new):
        text(soup.select_one('main h1'), record['title'])
        text(soup.select_one('.page-intro-content > p'), record.get('short_details') or record.get('description'))
        text(soup.select_one('title'), record.get('seo_title') or record['title'] + ' | Dr. Teeth Family Dental')
        for name, value in [('description',record.get('meta_description') or record.get('short_details') or record.get('description','')),('keywords',record.get('keywords','')),('robots',record.get('robots','index,follow'))]:
            node = soup.select_one(f'meta[name="{name}"]')
            if not node:
                node = soup.new_tag('meta', attrs={'name': name})
                soup.head.append(node)
            node['content'] = value
        for key, value in [('og:title',record.get('og_title') or record.get('seo_title') or record['title']),('og:description',record.get('og_description') or record.get('meta_description') or record.get('short_details','')),('og:image',record.get('image',''))]:
            node = soup.select_one(f'meta[property="{key}"]') or soup.new_tag('meta', attrs={'property':key})
            node['content'] = request.build_absolute_uri(value) if key=='og:image' and value else value
            if not node.parent:
                soup.head.append(node)
        canonical = soup.select_one('link[rel="canonical"]') or soup.new_tag('link', rel='canonical')
        canonical['href'] = record.get('canonical_url') or request.build_absolute_uri(route)
        if not canonical.parent:
            soup.head.append(canonical)
        if record['section'] in {'treatments','articles'}:
            prose = soup.select_one('main .prose')
            if prose:
                replace_children(prose, list(fragment(clean_html(record.get('details') or '<p>'+escape(record.get('description',''))+'</p>')).contents))
        elif is_new:
            body = soup.select_one('main .page-body')
            cta = body.select_one('.page-cta') if body else None
            if body:
                replace_children(body, list(fragment('<div class="prose"><p>'+escape(record.get('description',''))+'</p></div>').contents))
                if cta:
                    body.append(cta)

    if record and record['section']=='treatments':
        for previous in soup.select('[data-treatment-comparison]'):
            previous.decompose()
        if all(record.get(key) and safe_url(record[key]) for key in ('before_image','after_image')):
            comparison = fragment(render_to_string('dental_family/treatment_comparison.html', {'treatment': record}))
            body = soup.select_one('main .page-body')
            related = soup.select_one('main .related-section')
            if related:
                related.insert_before(comparison)
            elif body:
                cta = body.select_one('.page-cta')
                if cta:
                    cta.insert_before(comparison)
                else:
                    body.append(comparison)

    for hero in soup.select('main .article-hero'):
        hero.decompose()

    def group(section):
        return sorted([r for r in records if r['section']==section], key=lambda r:int(r.get('order') or 1))

    # Images retain the same gallery/clinic/doctor wrappers and JavaScript hooks.
    grid = soup.select_one('main .gallery-grid')
    if grid:
        originals = grid.select('button')
        nodes = []
        for i, r in enumerate(group('gallery')):
            source_index = int(r['id'].split('-')[-1]) if r['id'].startswith('photo-') else i
            card = deepcopy(originals[min(source_index,len(originals)-1)]) if originals else fragment('<button><div><img/></div><span></span></button>').button
            image(card.img, r)
            card['aria-label'] = 'Enlarge: '+r['title']
            category = r.get('gallery_category') or card.get('data-category','Our space')
            card['data-category'] = 'Our space' if category=='Our spaces' else category
            card['class'] = ['gallery-team-card'] if card['data-category']=='Our team' or '/doctors/' in r.get('image','') else []
            label = card.select_one(':scope > span')
            text(label, r['title'])
            nodes.append(card)
        replace_children(grid, nodes)
        categories=data['gallery_sections']
        filters=soup.select_one('.filter-row')
        replace_children(filters,[fragment('<button aria-pressed="'+('true' if index==0 else 'false')+'">'+('<span class="filter-active"></span>' if index==0 else '')+'<span class="filter-label">'+escape(name)+'</span></button>').button for index,name in enumerate(['All photos']+categories)])
    clinic = soup.select_one('main .about-page--photos')
    if clinic:
        base = clinic.select_one('figure')
        nodes=[]
        for i,r in enumerate(group('clinic')):
            card=deepcopy(base)
            image(card.img,r)
            text(card.select_one('h3'),r['title'])
            text(card.select_one('p'),r.get('description'))
            text(card.select_one('figcaption > span'),str(i+1).zfill(2))
            nodes.append(card)
        replace_children(clinic,nodes)
    directory=soup.select_one('main .doctor-directory')
    if directory:
        base=directory.select_one('.doctor-profile')
        nodes=[]
        for r in group('doctors'):
            card=deepcopy(base)
            text(card.select_one('h2'),r['title'])
            text(card.select_one('.doctor-biography .eyebrow'),r.get('specialty'))
            text(card.select_one('.doctor-portrait--specialty'),r.get('specialty'))
            image(card.img,r)
            if not r.get('image') and card.img:
                card.img.decompose()
            entries='\n'.join(r.get(key,'') for key in ['qualifications','training','position']).splitlines()
            replace_children(card.ul,[fragment('<li>'+escape(line)+'</li>').li for line in entries if line.strip()])
            text(card.select_one('.registration'),'BM&DC '+r['registration'] if r.get('registration') else '')
            nodes.append(card)
        replace_children(directory,nodes)
    for selector in ['.doctor-nav--list','.doctors-grid']:
        container=soup.select_one(selector)
        if not container:
            continue
        cards=container.select(':scope > li, :scope > article, :scope > a')
        if not cards:
            continue
        nodes=[]
        for i,r in enumerate(group('doctors')[:3]):
            card=deepcopy(cards[min(i,len(cards)-1)])
            image(card.select_one('img'),r)
            text(card.select_one('strong,h3'),r['title'])
            text(card.select_one('.doctor-nav--role'),r.get('specialty'))
            text(card.select_one('.doctor-nav--registration'),'BM&DC '+r.get('registration',''))
            text(card.select_one('.doctor-info p'),r.get('specialty'))
            text(card.select_one('.doctor-portrait--specialty'),r.get('specialty'))
            nodes.append(card)
        replace_children(container,nodes)
    homepage_locations = sorted(
        [r for r in group('locations') if r.get('show_on_homepage', True)],
        key=lambda r: (int(r.get('homepage_order') or r.get('order') or 1), not bool(r.get('homepage_order'))),
    )[:2]
    if route == '/':
        hero_location = soup.select_one('.hero--location')
        if hero_location:
            if not homepage_locations:
                hero_location.decompose()
            else:
                label = hero_location.select_one('span')
                text(label, 'YOUR LOCAL DENTAL FAMILY')
                link = hero_location.select_one('a')
                if link:
                    text(link, ' · '.join(r['title'].removesuffix(' branch') for r in homepage_locations) + ' ↗')
                    link['href'] = '#locations'
    for container in soup.select('.locations-grid'):
        from .locations import location_card
        replace_children(container, [fragment(location_card(r, i)).article for i, r in enumerate(homepage_locations if route == '/' else group('locations'))])
        if route == '/':
            section = container.find_parent('section')
            if section:
                section['id'] = 'locations'
                if not homepage_locations:
                    section.decompose()
    branches=soup.select('.footer--branch')
    if branches:
        parent=branches[0].parent
        for i,r in enumerate(group('locations')):
            card=deepcopy(branches[0])
            text(card.select_one('h2'),r['title'])
            text(card.select_one('address'),r.get('address'))
            text(card.select_one('.footer--area'),r.get('area'))
            text(card.select_one('.footer--branchNumber'),str(i+1).zfill(2))
            link=card.select_one('a')
            if link:
                link['href']='https://www.google.com/maps/search/?api=1&query='+quote(r.get('map_pin') or r.get('address',''))
            parent.insert(parent.contents.index(branches[0]),card)
        for card in branches:
            card.decompose()
    topics=data['topics']
    if route=='/faq/':
        container=soup.select_one('.topic-grid')
        base=container.select_one('.topic-card') if container else None
        if base:
            nodes=[]
            for topic in topics:
                card=deepcopy(base)
                card['href']=topic['url']
                text(card.h3,topic['title'])
                count=sum(r['section']=='faqs' and r.get('topic')==topic['id'] for r in records)
                text(card.p,f'{count} questions answered by our team.')
                nodes.append(card)
            replace_children(container,nodes)
    topic=next((topic for topic in topics if topic['url']==route),None)
    if topic:
        text(soup.select_one('title'),topic['title']+' FAQs | Dr. Teeth Family Dental')
        text(soup.select_one('main h1'),topic['title']+': your questions.')
        text(soup.select_one('.page-intro-content > p'),'Helpful answers about '+topic['title'].lower()+', from your dental team.')
        container=soup.select_one('.topic-faqs')
        nodes=[]
        for i,r in enumerate([r for r in group('faqs') if r.get('topic')==topic['id']]):
            identifier='faq-'+str(i)
            answer=''.join('<p>'+escape(line)+'</p>' for line in r.get('description','').splitlines() if line.strip())
            nodes.append(fragment(f'<div class="accordion-item"><h3><button type="button" id="{identifier}-trigger" aria-expanded="false" aria-controls="{identifier}-panel">{escape(r["title"])}<span class="accordion-plus" aria-hidden="true">+</span></button></h3><div class="accordion-panel" id="{identifier}-panel" role="region" aria-labelledby="{identifier}-trigger" aria-hidden="true" inert style="height:0;opacity:0"><div>{answer}</div></div></div>').div)
        replace_children(container,nodes)
    # Update listing cards in place and add new items with the established card styles.
    for selector,section in [('.treatment-card--card','treatments'),('.blog-card','articles')]:
        cards=soup.select('main '+selector)
        if not cards:
            continue
        if route=='/' and section=='treatments':
            container=cards[0].parent
            originals={card.get('href'):deepcopy(card) for card in cards}
            selected=sorted((r for r in records if r['section']=='treatments' and r.get('show_on_homepage')),key=lambda r:r.get('homepage_order',0))[:3]
            nodes=[]
            for index,r in enumerate(selected,1):
                card=deepcopy(originals.get(r['url'],cards[0]));card['href']=r['url']
                text(card.select_one('h2,h3'),r['title']);text(card.select_one('p'),r.get('short_details') or r.get('description'));image(card.select_one('img'),r)
                text(card.select_one('.treatment-card--number'),str(index).zfill(2))
                nodes.append(card)
            replace_children(container,nodes)
            continue
        base=deepcopy(cards[0]);containers=[];shown=set()
        for card in cards:
            r=next((r for r in records if r['section']==section and r['url']==card.get('href')),None)
            if not r:
                card.decompose()
                continue
            shown.add(r['id']);containers.append(card.parent)
            if section=='treatments':
                card['data-service']=r.get('service','')
                service_name=next((service['name'] for service in data['services'] if service['id']==r.get('service')),'')
                card['data-search']=' '.join([r['title'],r.get('short_details') or r.get('description') or '',service_name])
            if r.get('_edited'):
                text(card.select_one('h2,h3'),r['title']);text(card.select_one('p'),r.get('short_details') or r.get('description'));image(card.select_one('img'),r)
        if route in {'/services/','/blog/'}:
            container=containers[0] if containers else soup.select_one('.services-grid,.blog-grid')
            if container:
                for r in records:
                    if r['section']!=section or r['id'] in shown:
                        continue
                    card=deepcopy(base);card['href']=r['url'];text(card.select_one('h2,h3'),r['title']);text(card.select_one('p'),r.get('short_details') or r.get('description'));image(card.select_one('img'),r)
                    if section=='treatments':
                        card['data-service']=r.get('service','')
                        service_name=next((service['name'] for service in data['services'] if service['id']==r.get('service')),'')
                        card['data-search']=' '.join([r['title'],r.get('short_details') or r.get('description') or '',service_name])
                    container.append(card)
    service_filter=soup.select_one('[data-treatment-service]')
    if service_filter:
        services = data['services'] if filter_services is None else filter_services
        replace_children(service_filter,[fragment('<option value="">All services</option>').option]+[fragment('<option value="'+escape(service['id'])+'">'+escape(service['name'])+'</option>').option for service in services])
    payment_grid=soup.select_one('main .payment-grid')
    if payment_grid:
        nodes=[]
        for payment in group('payments'):
            if not payment.get('enabled',True):
                continue
            card=fragment('<article class="payment-card"><div class="eyebrow">'+escape(payment['payment_label'])+'</div><h2>'+escape(payment['title'])+'</h2>'+''.join('<p>'+escape(line)+'</p>' for line in payment_lines(payment))+'</article>').article
            nodes.append(card)
        replace_children(payment_grid,nodes)
    price_grid=soup.select_one('main .prices-grid')
    if price_grid:
        categories={}
        for price in group('prices'):
            categories.setdefault(price['category'],[]).append(price)
        nodes=[]
        for category in data.get('price_services',list(categories)):
            items=categories.get(category,[])
            if not items:
                continue
            card=fragment('<section class="price-card"><h2>'+escape(category)+'</h2><dl>'+''.join('<div><dt>'+escape(item['title'])+'</dt><dd>'+escape(item['price'])+'</dd></div>' for item in items)+'</dl></section>').section
            nodes.append(card)
        replace_children(price_grid,nodes)
    treatment_navigation(soup,data)
    contact_details(soup,data)
    return str(soup)


def treatment_navigation(soup,data):
    """List the newest three published treatment records for each service."""
    data=gallery_snapshot(data)
    records=data['records']
    nav=soup.select_one('.doctor-nav--serviceGrid')
    if not nav:
        return
    cards=nav.select(':scope > li')
    base=cards[0] if cards else None
    nodes=[]
    for i,service in enumerate(data['services'][:6]):
        if not base:
            break
        card=deepcopy(base)
        text(card.select_one('.doctor-nav--serviceNumber'),str(i+1).zfill(2))
        link=card.select_one('.doctor-nav--serviceTitle')
        text(link,service['name'])
        items=[(index,r) for index,r in enumerate(records) if r['section']=='treatments' and r.get('service')==service['id']]
        items.sort(key=lambda pair:(pair[1].get('created_at',''),pair[0]),reverse=True)
        latest=[r for _,r in items[:3]]
        link['href']='/services/'
        replace_children(card.select_one('.doctor-nav--treatmentList'),[fragment('<li><a href="'+escape(r['url'])+'">'+escape(r['title'])+'</a></li>').li for r in latest])
        nodes.append(card)
    replace_children(nav,nodes)


def treatment_navigation_html(html,data):
    soup=BeautifulSoup(html,'html.parser')
    treatment_navigation(soup,data)
    contact_details(soup,data)
    return str(soup)


def contact_details(soup,data):
    """Apply shared contact details while keeping branch-specific phone numbers."""
    details=gallery_snapshot(data)['contact_details']
    phone=details['phone']
    digits=re.sub(r'\D','',phone)
    email=details['email']
    for link in list(soup.select('a[href]')):
        href=link['href']
        if href.startswith('tel:') and re.sub(r'\D','',href)== '8801999961517':
            link['href']='tel:+'+digits
            for value in list(link.find_all(string=True)):
                if re.sub(r'\D','',str(value))=='8801999961517' or '+880 1999-961517' in str(value):
                    value.replace_with(str(value).replace('+880 1999-961517',phone).replace('+8801999961517',phone))
        elif href.startswith('mailto:info@drteethfamilydental.com'):
            link['href']='mailto:'+email
            for value in list(link.find_all(string=True)):
                if 'info@drteethfamilydental.com' in str(value):
                    value.replace_with(str(value).replace('info@drteethfamilydental.com',email))
        elif href.startswith('https://wa.me/'):
            if details['whatsapp']:
                link['href']='https://wa.me/'+re.sub(r'\D','',details['whatsapp'])
            else:
                link.decompose()
        elif href.startswith(('https://www.facebook.com/dr.teethfamily2','https://www.instagram.com/dr_teeth_family')):
            name='facebook' if 'facebook.com' in href else 'instagram'
            if details[name]:
                link['href']=details[name]
            else:
                link.decompose()
    for form in soup.select('[data-contact-form]'):
        form['data-contact-email']=email
    if details['opening_hours']:
        for note in soup.select('.hours-note'):
            text(note,details['opening_hours'])
