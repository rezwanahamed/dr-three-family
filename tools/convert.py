#!/usr/bin/env python3
"""Convert an isolated Next static export into framework-free pages and Django templates."""
import argparse
import json
import re
import shutil
import subprocess
from pathlib import Path
from bs4 import BeautifulSoup, Comment

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / 'static/dental_family'
PREFIX = '/static/dental_family/'


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')


def django_static(markup):
    return re.sub(r'(["\'])/static/dental_family/([^"\']+)(["\'])',
                  lambda m: m[1] + "{% static 'dental_family/" + m[2] + "' %}" + m[3], markup)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('export', type=Path)
    parser.add_argument('--source', type=Path, default=ROOT.parent / 'main_website/dental_family')
    args = parser.parse_args()
    export = args.export.resolve()
    if not (export / 'index.html').exists():
        parser.error('The export must contain index.html')

    shutil.copytree(export / 'assets', STATIC / 'assets', dirs_exist_ok=True)
    shutil.copytree(export / '_next/static/media', STATIC / 'fonts', dirs_exist_ok=True)
    for name in ['icon.svg', 'favicon.ico', 'robots.txt', 'sitemap.xml']:
        if (export / name).exists():
            shutil.copy2(export / name, STATIC / name)

    # Keep exact compiled selectors/cascade while giving modules readable names.
    css_files = sorted((export / '_next/static/css').glob('*.css'))
    class_map = {}
    for file in css_files:
        for name in re.findall(r'\.([a-z][\w-]*__[\w-]+)', file.read_text()):
            match = re.match(r'([a-z][\w-]*?)_([a-zA-Z]\w*?)__[\w-]+$', name)
            if match:
                class_map[name] = f'{match[1]}--{match[2]}'
    def classes(text):
        return re.sub(r'(?<![\w-])([a-z][\w-]*__[\w-]+)(?![\w-])',
                      lambda m: class_map.get(m[1], m[1]), text)
    css_map = {}
    for file in css_files:
        text = file.read_text()
        label = ('site' if '--paper:' in text else
                 'components' if '.hero_' in text else
                 'maps' if '.branch-map_' in text else
                 'recovery' if '.recovery-screen_' in text else 'not-found')
        name = f'{label}.css'
        if name in css_map.values():
            name = f'{label}-{file.stem}.css'
        css_map[file.name] = name
        text = classes(text)
        text = text.replace('/_next/static/media/', '../fonts/').replace('../media/', '../fonts/')
        text = text.replace('/assets/', PREFIX + 'assets/')
        write(STATIC / 'css' / name, '/* Original production CSS, with readable module selectors. */\n' + text + '\n')
    source_css = (args.source / 'app/globals.css').read_text()
    palette = re.search(r':root\s*\{.*?\}', source_css, re.S).group()
    theme_path = STATIC / 'css/theme.css'
    # Retain the independently tuned console palette when refreshing public styles.
    dashboard_marker = '/* Website dashboard palette.'
    dashboard_palette = ''
    if theme_path.exists() and dashboard_marker in theme_path.read_text():
        dashboard_palette = '\n' + dashboard_marker + theme_path.read_text().split(dashboard_marker, 1)[1]
    write(theme_path, '/* Edit the shared brand palette here. */\n' + palette + '\n' + dashboard_palette)
    write(ROOT / 'tools/class-map.json', json.dumps(class_map, indent=2) + '\n')

    routes = {}
    documents = {}
    html_paths = sorted(export.rglob('*.html'))
    for file in html_paths:
        relative = file.relative_to(export)
        if relative.parts[0] in ('_next', '_not-found', '404'):
            continue
        if str(relative) == '404.html' or relative.parts[0] == 'migration-error':
            path = '500.html' if relative.parts[0] == 'migration-error' else '404.html'
            route = None
        elif relative.name == 'index.html':
            route = '/' if relative.parent == Path('.') else '/' + relative.parent.as_posix() + '/'
            path = relative.as_posix()
        else:
            # Next also writes duplicate 404/index.html; use only the standalone 404.
            if relative.parts[0] == '404':
                continue
            route = '/' + relative.with_suffix('').as_posix() + '/'
            path = relative.with_suffix('').as_posix() + '/index.html'
        soup = BeautifulSoup(file.read_text(), 'html.parser')
        for node in soup.select('script, link[rel="modulepreload"], link[as="script"]'):
            node.decompose()
        for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
            comment.extract()
        # React's empty suspense marker is not website content.
        for node in list(soup.body.find_all('div', recursive=False)):
            if node.get('hidden') is not None and not node.contents:
                node.decompose()
        for node in soup.find_all(True):
            if node.has_attr('class'):
                node['class'] = [class_map.get(name, name) for name in node['class']]
            for attr in list(node.attrs):
                if attr.startswith('data-next') or attr in ('data-nimg', 'fetchpriority'):
                    del node[attr]
            for attr in ['href', 'src']:
                value = node.get(attr)
                if not value:
                    continue
                if value.startswith('/_next/static/css/'):
                    node[attr] = PREFIX + 'css/' + css_map[Path(value).name]
                elif value.startswith('/_next/static/media/'):
                    node[attr] = PREFIX + 'fonts/' + Path(value).name
                elif value.startswith('/assets/'):
                    node[attr] = PREFIX + value.lstrip('/')
                elif value in ['/icon.svg', '/favicon.ico']:
                    node[attr] = PREFIX + value.lstrip('/')
                elif attr == 'href' and value.startswith('/') and not value.startswith('//') and not Path(value).suffix:
                    node[attr] = value.rstrip('/') + '/'
            if node.has_attr('srcset'):
                node['srcset'] = node['srcset'].replace('/assets/', PREFIX + 'assets/')
        for name in ['theme.css', 'interactions.css']:
            link = soup.new_tag('link', rel='stylesheet', href=PREFIX + 'css/' + name)
            soup.head.append(link)
        script = soup.new_tag('script', src=PREFIX + 'js/site.js', defer='')
        soup.body.append(script)
        if not soup.body.get('id'):
            soup.body['id'] = 'top'
        for root in soup.select('.smile-comparison--comparison'):
            root['data-comparison'] = ''
        for image in soup.select('.lightbox-image'):
            image['style'] = 'opacity:1'
        for card in soup.select('.gallery-grid > button'):
            text = card.find('span', recursive=False).get_text(strip=True).rstrip('↗')
            card['data-category'] = 'Our team' if 'gallery-team-card' in card.get('class', []) else text
            card['style'] = 'opacity:1;transform:none'
        for form in soup.select('form.contact-form--form'):
            form['data-contact-form'] = ''
            status = soup.new_tag('div', attrs={'class': 'contact-form--status', 'data-form-status': '', 'role': 'status', 'hidden': ''})
            status.append(BeautifulSoup('<strong>Your email draft is ready to open.</strong><p>Send it from your email app to complete your inquiry. If it didn’t open, email <a href="mailto:info@drteethfamilydental.com">info@drteethfamilydental.com</a>. Nothing has been sent by this website.</p>', 'html.parser'))
            form.append(status)
        for button in soup.select('.recovery-screen--primary'):
            if button.name == 'button':
                button['data-retry'] = ''
        if route:
            routes[route] = {'template': 'dental_family/pages/' + path,
                             'html': path, 'title': soup.title.get_text() if soup.title else ''}
        documents[path] = soup

    home = documents['index.html']
    # All ordinary pages share exactly the same server-rendered header/footer.
    header_nodes = []
    for node in home.body.children:
        if getattr(node, 'name', None) == 'main':
            break
        if getattr(node, 'name', None):
            header_nodes.append(str(node))
    write(ROOT / 'templates/dental_family/includes/header.html', '{% load static %}\n' + django_static(''.join(header_nodes)))
    write(ROOT / 'templates/dental_family/includes/footer.html', '{% load static %}\n' + django_static(str(home.body.footer)))
    html_class = ' '.join(home.html.get('class', []))
    base = '''{% load static %}
<!DOCTYPE html>
<html lang="en" data-scroll-behavior="smooth" class="HTML_CLASS">
<head>{% block head %}{% endblock %}</head>
<body id="top">
{% block site_header %}{% include 'dental_family/includes/header.html' %}{% endblock %}
{% block content %}{% endblock %}
{% block site_footer %}{% include 'dental_family/includes/footer.html' %}{% endblock %}
<script src="{% static 'dental_family/js/site.js' %}" defer></script>
</body>
</html>
'''.replace('HTML_CLASS', html_class)
    write(ROOT / 'templates/dental_family/base.html', base)
    for path, soup in documents.items():
        write(ROOT / 'pages' / path, str(soup) + '\n')
        head = django_static(''.join(str(node) for node in soup.head.contents))
        main = soup.find('main')
        content = str(main)
        template = "{% extends 'dental_family/base.html' %}\n{% load static %}\n{% block head %}" + head + '{% endblock %}\n'
        if not soup.find('header', class_='site-header'):
            template += '{% block site_header %}{% endblock %}\n{% block site_footer %}{% endblock %}\n'
            content = ''.join(str(node) for node in soup.body.contents if getattr(node, 'name', None) != 'script')
        template += '{% block content %}' + django_static(content) + '{% endblock %}\n'
        write(ROOT / 'templates/dental_family/pages' / path, template)

    write(ROOT / 'routes.json', json.dumps(routes, indent=2, ensure_ascii=False) + '\n')
    if (args.source / 'node_modules/postcss').exists():
        subprocess.run(['node', str(ROOT / 'tools/format-css.cjs'), str(args.source.resolve())], check=True)
    print(f'Converted {len(routes)} website routes, plus 404 and 500 pages. Runtime: plain HTML/CSS/JS.')


if __name__ == '__main__':
    main()
