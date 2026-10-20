/* Isolated doctor-editor regression check; no real workspace is modified.
 * Run with: NODE_PATH=<directory containing playwright> node tools/doctor_save_check.cjs
 */
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
(async () => {
  const browser = await chromium.launch({ executablePath: '/usr/bin/google-chrome', headless: true, args: ['--no-sandbox'] });
  try {
    const page = await browser.newPage({ reducedMotion: 'reduce' });
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    let state = {}, revision = 0;
    await page.route('**/*', async route => {
      const url = new URL(route.request().url());
      if (url.pathname === '/dashboard/content/') {
        if (route.request().method() === 'PUT') {
          const payload = route.request().postDataJSON();
          assert.equal(payload.revision, revision);
          state = payload.state;
          if(state.drafts.length)assert(Array.isArray(state.drafts[0].availability));
          revision++;
          return route.fulfill({ json: { revision } });
        }
        return route.fulfill({ json: { records: JSON.parse(fs.readFileSync(path.join(root, 'static/dental_family/dashboard-content.json'))), state, revision, topics: [], services: [], gallery_sections: [], published_settings: {} } });
      }
      if (url.pathname === '/dashboard/') {
        const html = fs.readFileSync(path.join(root, 'pages/dashboard/index.html'), 'utf8').replace('<body ', '<body data-server-url="/dashboard/content/" ');
        return route.fulfill({ contentType: 'text/html', body: html });
      }
      const file = path.join(root, url.pathname.startsWith('/static/') ? 'collected-static/' + url.pathname.slice(8) : url.pathname);
      if (fs.existsSync(file) && fs.statSync(file).isFile()) return route.fulfill({ path: file });
      return route.abort();
    });
    await page.goto('http://localhost/dashboard/#overview');
    await page.locator('[name="appointment_start"]').fill('10:00');
    await page.locator('[name="appointment_end"]').fill('18:00');
    await page.getByRole('button', {name:'Save appointment hours',exact:true}).click();
    await page.waitForFunction(() => document.querySelector('#server-save-status').textContent === 'Draft saved to server');
    assert.equal(state.settings.appointment_start, '10:00');
    assert.equal(state.settings.appointment_end, '18:00');
    assert(await page.locator('#publish-changes').evaluate(e=>e.classList.contains('has-drafts')));
    await page.locator('[data-nav="doctors"]').click();
    await page.locator('button.edit').first().click();
    await page.locator('[name="biography"]').fill('Saved doctor biography');
    for (const [start, end] of [['09:00', '12:00'], ['16:00', '20:00']]) {
      await page.locator('#doctor-add-time').click();
      const row = page.locator('.doctor-time-row').last();
      await row.locator('select').selectOption('monday');
      await row.locator('[data-start]').fill(start);
      await row.locator('[data-end]').fill(end);
    }
    await page.getByRole('button', { name: 'Save draft', exact: true }).click();
    await page.waitForFunction(() => document.querySelector('#server-save-status').textContent === 'Draft saved to server');
    assert.equal(state.drafts[0].biography, 'Saved doctor biography');
    assert.equal(state.drafts[0].availability.length, 2);
    await page.reload();
    await page.locator('button.edit').first().click();
    assert.equal(await page.locator('[name="biography"]').inputValue(), 'Saved doctor biography');
    assert.equal(await page.locator('.doctor-time-row').count(), 2);
    assert.equal(await page.locator('[data-start]').last().inputValue(), '16:00');
    assert.equal(state.settings.appointment_start, '10:00');
    assert.deepEqual(errors, []);
    console.log('PASS: collected dashboard assets save biography and split-day hours to the server and restore them after reload.');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
