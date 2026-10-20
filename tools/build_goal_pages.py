"""Build the standalone homepage goal section and its results pages."""
import os
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
os.environ.setdefault('DJANGO_SETTINGS_MODULE','main_server.settings')
import django
django.setup()
import json
from django.test import RequestFactory
from django.contrib.auth.models import AnonymousUser
from django.template.loader import render_to_string
from dental_family.content import seeds
from dental_family.improvements import goal_url,treatments_for_goal
from dental_family.public_content import treatment_navigation_html
catalog=json.loads((ROOT/'static/dental_family/improvement-catalog.json').read_text())
data=seeds();data['improvement_options']=catalog['options']
for record in data['records']:
 if record['section']=='treatments':record['improvement_options']=catalog['selections'].get(record['id'],[])
goals=[{**option,'url':goal_url(option)} for option in catalog['options']]
block=render_to_string('dental_family/includes/treatment_goals.html',{'goals':goals,'homepage':True})
for name in ['pages/index.html','templates/dental_family/pages/index.html']:
 p=ROOT/name;text=p.read_text()
 marker='<section aria-labelledby="smile-comparison-title"'
 if 'id="smile-goals"' in text:
  start=text.rfind('<section',0,text.index('id="smile-goals"'))
  end=text.index('</section>',start)+len('</section>');text=text[:start]+text[end:]
 assert marker in text
 end=text.index('</section>',text.index(marker))+len('</section>')
 p.write_text(text[:end]+block+text[end:])
services={s['id']:s['name'] for s in data['services']}
for option in catalog['options']:
 route=goal_url(option);request=RequestFactory().get(route);request.user=AnonymousUser()
 records=[{**r,'service_name':services.get(r.get('service'),'Dental care')} for r in treatments_for_goal(option,data)]
 html=render_to_string('dental_family/goal_treatments.html',{'goal':option,'treatments':records},request=request)
 html=treatment_navigation_html(html,data)
 path=ROOT/'pages'/route.strip('/')/'index.html';path.parent.mkdir(parents=True,exist_ok=True);path.write_text(html)
print('Built homepage goal navigation and',len(goals),'standalone goal-list pages.')
