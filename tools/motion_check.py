#!/usr/bin/env python3
"""Check animation behavior with reduced motion disabled."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
(ROOT / 'validation').mkdir(parents=True, exist_ok=True)
report = []
with sync_playwright() as p:
    browser = p.chromium.launch(executable_path='/usr/bin/google-chrome', headless=True, args=['--no-sandbox'])
    page = browser.new_page(viewport={'width':1440,'height':1000}, reduced_motion='no-preference')
    page.route('**/*', lambda route: route.continue_() if route.request.url.startswith('http://127.0.0.1:8013') or route.request.url.startswith('data:') else route.abort())
    page.goto('http://127.0.0.1:8013/',wait_until='networkidle')
    page.locator('.hero--scene').hover(position={'x':100,'y':100})
    page.wait_for_timeout(600)
    transform=page.locator('.hero--imageLayer').evaluate('el=>getComputedStyle(el).transform')
    assert transform!='none'
    report.append('Hero spring parallax responds to pointer')
    card=page.locator('[data-lift]').first
    card.hover()
    page.wait_for_timeout(300)
    assert '-4' in card.evaluate('el=>getComputedStyle(el).transform')
    report.append('Motion links lift on hover')
    page.locator('.clinic-stats--banner').scroll_into_view_if_needed()
    page.wait_for_timeout(2300)
    assert page.locator('.clinic-stats--animatedNumber').all_text_contents()==['10','25','8','15K']
    report.append('Animated counters reach original final values')
    carousel=page.locator('[aria-roledescription=carousel]')
    carousel.scroll_into_view_if_needed()
    page.mouse.move(0,0)
    page.wait_for_timeout(6300)
    assert page.locator('[aria-label^="Show review 2 "]').get_attribute('aria-current')=='true'
    report.append('Testimonials automatically advance after six seconds')
    carousel.hover()
    page.wait_for_timeout(6300)
    assert page.locator('[aria-label^="Show review 2 "]').get_attribute('aria-current')=='true'
    report.append('Testimonial autoplay pauses while hovered')
    browser.close()
(ROOT/'validation/motion.json').write_text(json.dumps({'checks':report,'errors':[]},indent=2)+'\n')
print(json.dumps(report,indent=2))
