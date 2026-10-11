import json
from pathlib import Path
from django.http import FileResponse, Http404
from django.shortcuts import render, redirect

ROOT = Path(__file__).resolve().parent.parent
ROUTES = json.loads((ROOT / 'routes.json').read_text(encoding='utf-8'))


def page(request, route='/'):
    info = ROUTES.get(route)
    if info is None:
        raise Http404('Page not found')
    return render(request, info['template'])


def legacy_redirect(request, destination, **kwargs):
    return redirect(destination, permanent=True)


def metadata_file(request, filename):
    types = {'robots.txt': 'text/plain', 'sitemap.xml': 'application/xml',
             'icon.svg': 'image/svg+xml', 'favicon.ico': 'image/x-icon'}
    if filename not in types:
        raise Http404
    return FileResponse((ROOT / 'static/dental_family' / filename).open('rb'), content_type=types[filename])


def not_found(request, exception=None):
    return render(request, 'dental_family/pages/404.html', status=404)


def missing_page(request, unmatched_path=''):
    # The fallback also matches slashless URLs, so preserve their canonical redirect.
    canonical = '/' + unmatched_path.rstrip('/') + '/'
    if not request.path.endswith('/') and canonical in ROUTES:
        return redirect(canonical, permanent=True)
    return not_found(request)


def server_error(request):
    return render(request, 'dental_family/pages/500.html', status=500)


def dashboard(request):
    """Public local UI preview; no patient data or publishing operations."""
    return render(request, 'dental_family/dashboard/index.html')
