#!/usr/bin/env python3
"""Browser QA against a served original export and the Django/standalone migration."""
import argparse
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--original', default='http://127.0.0.1:8011')
parser.add_argument('--converted', default='http://127.0.0.1:8013')
parser.add_argument('--django', default='http://127.0.0.1:8012')
parser.add_argument('--browser', default='/usr/bin/google-chrome')
args = parser.parse_args()
report = {'route_checks': [], 'screenshots': [], 'interactions': [], 'errors': []}
shots = ROOT / 'validation/screenshots'
shots.mkdir(parents=True, exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=args.browser, headless=True, args=['--no-sandbox'])
    page = browser.new_page(viewport={'width': 1440, 'height': 1000}, reduced_motion='reduce')
    allowed = [args.original, args.converted, args.django]
    page.route('**/*', lambda route: route.continue_() if any(route.request.url.startswith(host) for host in allowed) or route.request.url.startswith('data:') else route.abort())
    page.on('pageerror', lambda error: report['errors'].append(str(error)))

    def load(base, path='/'):
        response = page.goto(base + path, wait_until='networkidle')
        page.evaluate("""async () => {
          await document.fonts.ready;
          document.querySelectorAll('img').forEach(img => img.loading='eager');
          await Promise.all([...document.images].map(img => img.decode().catch(()=>{})));
        }""")
        return response

    for route in json.loads((ROOT / 'routes.json').read_text()):
        response = load(args.converted, route)
        data = page.evaluate("""() => ({overflow:document.documentElement.scrollWidth>innerWidth,
          broken:[...document.images].filter(img=>!img.complete||!img.naturalWidth).map(img=>img.src)})""")
        report['route_checks'].append({'route': route, 'status': response.status, **data})
        if response.status != 200 or data['overflow'] or data['broken']:
            report['errors'].append(f'Route failed: {route}: {data}')

    for width, height, routes in [(1440,1000,['/','/about-us/','/services/','/gallery/','/contact/','/google-reviews/','/faq/','/404.html']),
                                 (390,844,['/','/gallery/','/contact/'])]:
        page.set_viewport_size({'width':width,'height':height})
        for route in routes:
            name = ('home' if route=='/' else route.strip('/').replace('/','-').replace('.html',''))+f'-{width}'
            sizes = {}
            for label, base in [('original',args.original),('converted',args.converted)]:
                load(base,route)
                sizes[label] = page.evaluate('({width:document.documentElement.scrollWidth,height:document.documentElement.scrollHeight})')
                page.screenshot(path=str(shots/f'{name}-{label}.png'),full_page=True,animations='disabled')
            report['screenshots'].append({'name':name,'sizes':sizes})

    page.set_viewport_size({'width':1440,'height':1000})
    load(args.converted)
    page.locator('.doctor-nav--treatmentsItem > a').hover()
    assert page.locator('.doctor-nav--treatmentsDropdown').is_visible()
    assert page.locator('.doctor-nav--serviceCategory').count()==6
    assert all(page.locator('.doctor-nav--treatmentList').nth(i).locator('li').count()<=3 for i in range(6))
    page.keyboard.press('Escape')
    assert not page.locator('.doctor-nav--treatmentsDropdown').is_visible()
    page.locator('.doctor-nav--doctorsItem > a').hover()
    assert page.locator('.doctor-nav--doctor').count()==3
    assert page.locator('.doctor-nav--doctorsDropdown').is_visible()
    page.keyboard.press('Escape')
    report['interactions'].append('Desktop dropdowns, limits, and Escape')

    slider = page.locator('[data-comparison] input')
    slider.scroll_into_view_if_needed()
    slider.fill('75')
    assert '25%' in page.locator('.smile-comparison--before').get_attribute('style')
    slider.press('ArrowRight')
    assert slider.input_value()=='76'
    report['interactions'].append('Comparison drag/range value and keyboard')

    button = page.locator('.accordion-item h3 button').first
    initially_open = button.get_attribute('aria-expanded') == 'true'
    button.click()
    assert button.get_attribute('aria-expanded')==str(not initially_open).lower()
    panel = page.locator('#'+button.get_attribute('aria-controls').replace(':','\\:'))
    assert panel.get_attribute('aria-hidden')==str(initially_open).lower()
    button.click()
    assert button.get_attribute('aria-expanded')==str(initially_open).lower()
    report['interactions'].append('Accordion expand/collapse and ARIA')

    track = page.locator('.google-style-reviews--track')
    assert track.locator('.google-style-review').count() == 6
    page.locator('[data-review-next]').click()
    page.wait_for_function("document.querySelector('.google-style-reviews--track').scrollLeft > 0")
    page.locator('[data-review-previous]').click()
    page.wait_for_function("document.querySelector('.google-style-reviews--track').scrollLeft < 2")
    report['interactions'].append('Review cards next/previous and scroll position')

    load(args.converted,'/gallery/')
    total=page.locator('.gallery-grid > button').count()
    page.get_by_role('button',name='Our team',exact=True).click()
    visible=page.locator('.gallery-grid > button:visible').count()
    assert 0<visible<total
    page.locator('.gallery-grid > button:visible').first.click()
    assert page.locator('dialog').is_visible()
    assert page.locator('.lightbox-image').evaluate("el => getComputedStyle(el).opacity") == '1'
    first=page.locator('.lightbox-image img').get_attribute('src')
    page.keyboard.press('ArrowRight')
    assert page.locator('.lightbox-image img').get_attribute('src')!=first
    assert page.locator('.lightbox-image').evaluate("el => getComputedStyle(el).opacity") == '1'
    page.keyboard.press('Escape')
    assert not page.locator('dialog').is_visible()
    page.get_by_role('button',name='All photos',exact=True).click()
    assert page.locator('.gallery-grid > button:visible').count()==total
    report['interactions'].append('Gallery filters, lightbox, next, Escape, focus restoration')

    load(args.converted,'/contact/')
    page.get_by_role('button',name='Prepare my email').click()
    assert page.locator('[aria-invalid=true]').count()==3
    page.locator('textarea').fill('A question about booking.')
    assert page.locator('.contact-form--messageMeta > span').inner_text().startswith('25/')
    assert page.locator('textarea').get_attribute('aria-invalid')=='false'
    report['interactions'].append('Contact form errors, correction, character counter')

    page.set_viewport_size({'width':390,'height':844})
    load(args.converted)
    page.get_by_role('button',name='Open navigation').click()
    assert page.locator('#main-nav').is_visible()
    assert not page.locator('.doctor-nav--treatmentsDropdown').is_visible()
    page.get_by_role('button',name='Close navigation').click()
    assert not page.locator('#main-nav').is_visible()
    report['interactions'].append('Mobile menu, desktop-only panels')

    page.set_viewport_size({'width':1440,'height':1000})
    load(args.django)
    page.screenshot(path=str(shots/'home-1440-django.png'),full_page=True,animations='disabled')
    browser.close()

(ROOT/'validation/browser.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'routes':len(report['route_checks']),'screenshot_pairs':len(report['screenshots']),'interactions':report['interactions'],'errors':report['errors']},indent=2))
if report['errors']:
    raise SystemExit(1)
