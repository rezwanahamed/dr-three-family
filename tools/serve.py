#!/usr/bin/env python3
"""Preview standalone pages without Django, including route redirects and local assets."""
import argparse
import json
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
ROUTES = json.loads((ROOT / 'routes.json').read_text())
REDIRECTS = {'/price-guide': '/pricing-guide-2/', '/financing': '/financing-2/',
             '/oral-surgery': '/advanced_oral_surgery/', '/edit': '/',
             '/elementor-page-2017': '/', '/metform-form/contact-form-new': '/contact/'}


class Handler(SimpleHTTPRequestHandler):
    def translate_path(self, url):
        path = unquote(urlsplit(url).path)
        if path.startswith('/static/'):
            root, relative = ROOT / 'static', path.removeprefix('/static/')
        elif path in ['/robots.txt', '/sitemap.xml', '/icon.svg', '/favicon.ico']:
            root, relative = ROOT / 'static/dental_family', path.lstrip('/')
        else:
            root = ROOT / 'pages'
            relative = ROUTES.get(path, {}).get('html', path.lstrip('/'))
        resolved = (root / relative).resolve()
        if not resolved.is_relative_to(root.resolve()):
            return str(ROOT / 'pages/404.html')
        return str(resolved)

    def do_GET(self):
        path = urlsplit(self.path).path
        destination = REDIRECTS.get(path.rstrip('/'))
        if destination is None and path.startswith('/metform-form/'):
            destination = '/appointment/'
        if destination is None and path.startswith('/author/'):
            destination = '/blog/'
        if destination is None and not path.endswith('/') and path + '/' in ROUTES:
            destination = path + '/'
        if destination:
            self.send_response(301)
            self.send_header('Location', destination)
            self.end_headers()
            return
        return super().do_GET()

    def send_error(self, code, message=None, explain=None):
        if code == 404:
            content = (ROOT / 'pages/404.html').read_bytes()
            self.send_response(404)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        else:
            super().send_error(code, message, explain)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8000)
    args = parser.parse_args()
    print(f'Standalone website: http://127.0.0.1:{args.port}', flush=True)
    ThreadingHTTPServer(('127.0.0.1', args.port), Handler).serve_forever()
