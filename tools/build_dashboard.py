#!/usr/bin/env python3
"""Refresh dashboard content from the exported website (no invented clinic data)."""
import json
from pathlib import Path
from bs4 import BeautifulSoup
ROOT = Path(__file__).resolve().parents[1]
from build_faq import build as build_faq
build_faq()
records=[]
routes=json.loads((ROOT/'routes.json').read_text())
for route, info in routes.items():
    soup=BeautifulSoup((ROOT/'pages'/info['html']).read_text(),'html.parser')
    main=soup.select_one('main') or soup
    heading=main.select_one('h1')
    title=heading.get_text(' ',strip=True) if heading else info['title'].split('|')[0].strip()
    image=main.select_one('img')
    description=main.select_one('p')
    kind='pages'
    if route not in ['/', '/about-us/','/appointment/','/blog/','/contact/','/faq/','/gallery/','/google-reviews/','/our-doctors/','/privacy-policy/','/services/']:
        kind='pages' if route.startswith('/faqs') else 'articles' if route.startswith(('/11-','/6-','/9-','/how-','/what-','/root-canal-treatment-for-','/faqs','/category/')) else 'treatments'
    records.append(dict(id=route, title=title, section=kind, description=description.get_text(' ',strip=True) if description else '', url=route, image=image.get('src','') if image else '', status='Website snapshot'))
soup=BeautifulSoup((ROOT/'pages/gallery/index.html').read_text(),'html.parser')
for i,img in enumerate(soup.select('.gallery-grid button img')):
    records.append(dict(id=f'photo-{i}',title=img.get('alt','Clinic photo'),section='gallery',description=img.get('alt',''),url='/gallery/',image=img['src'],gallery_category=('Our space' if img.find_parent('button').get('data-category')=='Our spaces' else img.find_parent('button').get('data-category','Our space')),alt=img.get('alt',''),order=i+1,status='Website snapshot'))
soup=BeautifulSoup((ROOT/'pages/our-doctors/index.html').read_text(),'html.parser')
for i,card in enumerate(soup.select('main article')):
    heading=card.select_one('h2,h3')
    img=card.select_one('img')
    if heading:
        records.append(dict(id=f'doctor-{i}',title=heading.get_text(' ',strip=True),section='doctors',description='',url='/our-doctors/',image=img['src'] if img else '',order=i+1,status='Website snapshot'))
        details = [item.get_text(' ', strip=True) for item in card.select('.doctor-biography li')]
        specialty = card.select_one('.doctor-biography .eyebrow')
        registration = card.select_one('.registration')
        appointment = card.select_one('.doctor-biography a.button')
        records[-1].update(
            specialty=specialty.get_text(' ', strip=True) if specialty else '',
            qualifications='\n'.join(line for line in details if not line.startswith(('Advanced training', 'Senior Lecturer'))),
            training='\n'.join(line for line in details if line.startswith('Advanced training')),
            position='\n'.join(line for line in details if line.startswith('Senior Lecturer')),
            registration=registration.get_text(' ', strip=True).removeprefix('BM&DC ').strip() if registration else '',
            appointment_url=appointment.get('href', '') if appointment else '',
        )
soup=BeautifulSoup((ROOT/'pages/about-us/index.html').read_text(),'html.parser')
for card in soup.select('main figure'):
    heading=card.select_one('figcaption h3')
    image=card.select_one('img')
    description=card.select_one('figcaption p')
    if heading and image:
        order=sum(r['section']=='clinic' for r in records)+1
        records.append(dict(id=f'clinic-photo-{order}', section='clinic', title=heading.get_text(' ',strip=True), description=description.get_text(' ',strip=True) if description else '', image=image['src'], alt=image.get('alt',''), order=order, url='/about-us/', status='Website snapshot'))
homepage=BeautifulSoup((ROOT/'pages/index.html').read_text(),'html.parser')
homepage_urls=[card.get('href') for card in homepage.select('main .treatment-card--card')][:6]
for record in records:
    if record['section']=='treatments':
        record['show_on_homepage']=record['url'] in homepage_urls
        record['homepage_order']=homepage_urls.index(record['url'])+1 if record['url'] in homepage_urls else 0
(ROOT/'static/dental_family/dashboard-content.json').write_text(json.dumps(records,indent=2)+'\n')
source=(ROOT/'pages/dashboard/index.html').read_text().replace('<body ', '<body data-server-url="/dashboard/content/" data-publish-url="/dashboard/publish/" ', 1)
import re
source=re.sub(r'(["\'])/static/dental_family/([^"\']+)(["\'])',lambda m:m[1]+"{% static 'dental_family/"+m[2]+"' %}"+m[3],source)
(ROOT/'templates/dental_family/dashboard/index.html').write_text('{% load static %}\n'+source)
print(f'Dashboard snapshot: {len(records)} entries')
