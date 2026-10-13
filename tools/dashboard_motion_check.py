#!/usr/bin/env python3
"""Check motion completion, rapid interactions, and reduced-motion support."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
ROOT=Path(__file__).resolve().parents[1]
(ROOT / 'validation').mkdir(parents=True, exist_ok=True)
report=[]
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path='/usr/bin/google-chrome',headless=True,args=['--no-sandbox'])
    for preference in ['no-preference','reduce']:
        page=browser.new_page(viewport={'width':1440,'height':1000},reduced_motion=preference)
        errors=[]
        page.on('pageerror',lambda error:errors.append(str(error)))
        page.goto('http://127.0.0.1:8012/dashboard/',wait_until='networkidle')
        expect(page.get_by_role('heading',name='Manage your website')).to_be_visible()
        page.wait_for_timeout(450)
        page.evaluate("document.querySelector('#add').click()")
        animations=page.locator('#editor').evaluate('el=>el.getAnimations().length')
        assert (animations>0) if preference=='no-preference' else animations==0
        page.wait_for_timeout(350)
        assert page.locator('#editor').evaluate('el=>getComputedStyle(el).opacity')=='1'
        # Reopening while a close animation runs must cancel the close safely.
        page.evaluate("document.querySelector('#cancel-editor').click(); document.querySelector('#add').click()")
        page.wait_for_timeout(350)
        expect(page.locator('#editor')).to_be_visible()
        assert page.locator('#editor').evaluate('el=>getComputedStyle(el).opacity')=='1'
        page.locator('#cancel-editor').click()
        expect(page.locator('#editor')).to_be_hidden()
        page.keyboard.press('Control+k')
        expect(page.locator('#search-dialog')).to_be_visible()
        page.keyboard.press('Escape')
        expect(page.locator('#search-dialog')).to_be_hidden()
        page.locator('[data-nav="treatments"]').click()
        page.locator('#sort-content').select_option('az')
        page.locator('#sort-content').select_option('za')
        page.wait_for_timeout(450)
        assert page.locator('#view').evaluate('el=>getComputedStyle(el).opacity')=='1'
        assert page.locator('tbody tr').first.evaluate('el=>getComputedStyle(el).opacity')=='1'
        page.set_viewport_size({'width':390,'height':844})
        page.evaluate("document.querySelector('#menu').click(); document.querySelector('#menu').click(); document.querySelector('#menu').click()")
        page.wait_for_timeout(350)
        expect(page.locator('#menu')).to_have_attribute('aria-expanded','true')
        expect(page.locator('#nav-backdrop')).to_be_visible()
        page.locator('[data-nav="gallery"]').click()
        page.wait_for_timeout(450)
        expect(page.locator('#nav-backdrop')).to_be_hidden()
        assert page.locator('.media-card').first.evaluate('el=>getComputedStyle(el).opacity')=='1'
        if preference=='reduce':assert page.evaluate('document.getAnimations().length')==0
        assert not errors,errors
        report.append({'motion':preference,'dialog_entry_animated':animations>0,'rapid_reopen':'passed','navigation':'passed','final_opacity':1,'errors':errors})
        page.close()
    browser.close()
(ROOT/'validation/dashboard-motion.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
