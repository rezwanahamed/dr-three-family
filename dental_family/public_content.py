"""Render managed content using the website's existing markup, CSS and animations."""
from copy import deepcopy
from html import escape
from urllib.parse import quote
from bs4 import BeautifulSoup
from django.template.loader import render_to_string
from .content import clean_html, safe_url, gallery_snapshot


def text(node, value):
    if node is not None:
        node.clear()
        node.append(str(value or ''))


def image(node, record):
    if node and record.get('image') and safe_url(record['image']):
        node['src'] = record['image']
        node['alt'] = record.get('image_alt') or record.get('alt') or record['title']
        node.attrs.pop('srcset', None)


def fragment(html):
    return BeautifulSoup(html, 'html.parser')


def replace_children(container, nodes):
    if container is not None:
        container.clear()
        for node in nodes:
            container.append(node)


def managed_html(template, request, route, data, is_new=False):
    soup = BeautifulSoup(render_to_string(template, request=request), 'html.parser')
    data = gallery_snapshot(data)
    records = data['records']
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
                if record['section']=='articles' and record.get('image'):
                    hero = fragment('<div class="article-hero"><img loading="lazy" alt="" /></div>').div
                    image(hero.img, record)
                    prose.insert(0, hero)
        elif is_new:
            body = soup.select_one('main .page-body')
            cta = body.select_one('.page-cta') if body else None
            if body:
                replace_children(body, list(fragment('<div class="prose"><p>'+escape(record.get('description',''))+'</p></div>').contents))
                if cta:
                    body.append(cta)

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
    for container in soup.select('.locations-grid'):
        base=container.select_one('.location-card')
        if not base:
            continue
        nodes=[]
        for i,r in enumerate(group('locations')):
            card=deepcopy(base)
            text(card.select_one('h3,h2'),r['title'])
            text(card.select_one('.eyebrow'),r.get('area'))
            text(card.select_one('.location-number'),str(i+1).zfill(2))
            text(card.select_one('p'),r.get('address'))
            query=quote(r.get('map_pin') or r.get('address',''))
            for link in card.select('a'):
                link['href']='tel:'+r.get('phone','') if link.get('href','').startswith('tel:') else 'https://www.google.com/maps/search/?api=1&query='+query
            iframe=card.select_one('iframe')
            if iframe:
                iframe['src']='https://www.google.com/maps?q='+query+'&z=17&t=m&iwloc=A&output=embed'
                iframe['title']='Google Maps — '+r['title']
            if r.get('hours'):
                card.append(fragment('<p class="hours-note">'+escape(r['hours'])+'</p>').p)
            nodes.append(card)
        replace_children(container,nodes)
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
        base=deepcopy(cards[0]);containers=[];shown=set()
        for card in cards:
            r=next((r for r in records if r['section']==section and r['url']==card.get('href')),None)
            if not r:
                card.decompose()
                continue
            shown.add(r['id']);containers.append(card.parent)
            if r.get('_edited'):
                text(card.select_one('h2,h3'),r['title']);text(card.select_one('p'),r.get('short_details') or r.get('description'));image(card.select_one('img'),r)
        if route in {'/services/','/blog/'}:
            container=containers[0] if containers else soup.select_one('.services-grid,.blog-grid')
            if container:
                for r in records:
                    if r['section']!=section or r['id'] in shown:
                        continue
                    card=deepcopy(base);card['href']=r['url'];text(card.select_one('h2,h3'),r['title']);text(card.select_one('p'),r.get('short_details') or r.get('description'));image(card.select_one('img'),r);container.append(card)
    nav=soup.select_one('.doctor-nav--serviceGrid')
    if nav:
        cards=nav.select(':scope > li');base=cards[0] if cards else None
        nodes=[]
        for i,service in enumerate(data['services']):
            if not base:
                break
            card=deepcopy(base);text(card.select_one('.doctor-nav--serviceNumber'),str(i+1).zfill(2));link=card.select_one('.doctor-nav--serviceTitle');text(link,service['name']);link['href']=next((r['url'] for r in records if r['section']=='treatments' and (r.get('service')==service['id'] or r['url']==f'/{service["id"]}/')),'/services/')
            replace_children(card.select_one('.doctor-nav--treatmentList'),[fragment('<li><a href="'+escape(link['href'])+'">'+escape(name)+'</a></li>').li for name in service['treatments'][:3]])
            nodes.append(card)
        replace_children(nav,nodes)
    return str(soup)
