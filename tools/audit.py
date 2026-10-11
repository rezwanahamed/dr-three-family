#!/usr/bin/env python3
"""Check every route, Django template, static reference, and retained legacy redirect."""
import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit, unquote
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'demo.settings')
import django
django.setup()
from django.test import Client, override_settings
from dental_family.views import not_found, server_error
from django.test import RequestFactory

routes = json.loads((ROOT / 'routes.json').read_text())
client = Client()
errors = []
checks = 0
for route, info in routes.items():
    response = client.get(route)
    if response.status_code != 200:
        errors.append(f'{route}: Django status {response.status_code}')
    standalone = (ROOT / 'pages' / info['html']).read_text()
    rendered = response.content.decode()
    for label, markup in [('HTML', standalone), ('Django', rendered)]:
        soup = BeautifulSoup(markup, 'html.parser')
        if not soup.title or not soup.find('main'):
            errors.append(f'{route}: missing title/main ({label})')
        if '/_next/' in markup or '__next_f' in markup or 'self.__next' in markup:
            errors.append(f'{route}: Next runtime leaked into {label}')
        if '{%' in markup:
            errors.append(f'{route}: unrendered Django tags ({label})')
        for node in soup.find_all(True):
            for attr in ['src', 'href']:
                value = node.get(attr, '')
                if value.startswith('/static/'):
                    asset = ROOT / unquote(urlsplit(value).path).lstrip('/')
                    checks += 1
                    if not asset.is_file():
                        errors.append(f'{route}: missing asset {value}')
                elif attr == 'href' and value.startswith('/') and not value.startswith('//'):
                    target = urlsplit(value).path
                    if target not in routes and target not in ['/icon.svg', '/favicon.ico']:
                        errors.append(f'{route}: missing internal route {target}')
        # The original DOM, including CSS classes, should match the Django output.
    static_main = BeautifulSoup(standalone, 'html.parser').find('main')
    django_main = BeautifulSoup(rendered, 'html.parser').find('main')
    if str(static_main) != str(django_main):
        errors.append(f'{route}: standalone and Django main markup differ')

for source, target in [('/price-guide', '/pricing-guide-2/'), ('/financing', '/financing-2/'),
                       ('/oral-surgery', '/advanced_oral_surgery/'),
                       ('/metform-form/contact-form-new', '/contact/'),
                       ('/metform-form/anything', '/appointment/'), ('/author/example', '/blog/')]:
    response = client.get(source)
    if response.status_code != 301 or response['Location'] != target:
        errors.append(f'Legacy redirect failed: {source}')
with override_settings(DEBUG=False):
    response = client.get('/page-that-does-not-exist/')
    if response.status_code != 404 or b'missing-title' not in response.content:
        errors.append('Custom 404 failed')
with override_settings(DEBUG=True):
    for missing in ['/s', '/s/', '/missing/nested/page/']:
        response = client.get(missing)
        if response.status_code != 404 or b'missing-title' not in response.content:
            errors.append(f'Custom development 404 failed: {missing}')
    response = client.get('/services')
    if response.status_code != 301 or response['Location'] != '/services/':
        errors.append('Slashless page redirect failed')
if server_error(RequestFactory().get('/')).status_code != 500:
    errors.append('Custom 500 failed')

for stylesheet in (ROOT / 'static').rglob('*.css'):
    for match in re.findall(r'url\(([^)]+)\)', stylesheet.read_text()):
        value = match.strip(' \"\'')
        if value.startswith(('data:', 'https:', 'http:', '#')):
            continue
        value = unquote(urlsplit(value).path)
        asset = ROOT / value.lstrip('/') if value.startswith('/') else stylesheet.parent / value
        checks += 1
        if not asset.is_file():
            errors.append(f'{stylesheet.name}: missing CSS asset {value}')

report = {'routes': len(routes), 'asset_references_checked': checks, 'errors': sorted(set(errors))}
(ROOT / 'validation').mkdir(exist_ok=True)
(ROOT / 'validation/routes.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
sys.exit(bool(errors))
