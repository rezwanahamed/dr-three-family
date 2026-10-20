"""Build standalone price-guide previews with published-seed calculator data."""
import os
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));os.environ.setdefault('DJANGO_SETTINGS_MODULE','main_server.settings')
import django
django.setup()
from django.test import RequestFactory
from django.contrib.auth.models import AnonymousUser
from dental_family.content import seeds
from dental_family.public_content import managed_html
from dental_family.views import ROUTES
for route in ['/pricing-guide-2/','/a-little-clarity-on-costs/']:
 request=RequestFactory().get(route);request.user=AnonymousUser()
 html=managed_html(ROUTES['/pricing-guide-2/']['template'],request,route,seeds())
 path=ROOT/'pages'/route.strip('/')/'index.html';path.parent.mkdir(parents=True,exist_ok=True);path.write_text(html)
print('Built standalone price-guide pages with calculator.')
