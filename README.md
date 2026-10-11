# Dr. Teeth — Django-ready website

The website is converted into plain HTML, CSS, and browser JavaScript. The delivered
pages do **not** load React, Next.js, Framer Motion, or a Tailwind runtime. Django
renders the same HTML through reusable templates.

## Preview with Django

Run from this directory:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py check
python manage.py runserver
```

Open `http://127.0.0.1:8000/`. Database migrations are unnecessary for this frontend.

## Preview without Django

```bash
python3 tools/serve.py --port 8000
```

The standalone preview serves `pages/` and maps `/static/` to the supplied assets.
Use an HTTP server rather than opening HTML with `file://`, because links and assets
use paths from the website root.

## Files

- `pages/`: 42 standalone HTML routes, plus `404.html` and `500.html`.
- `templates/dental_family/`: Django templates for all pages.
- `templates/dental_family/base.html`: shared document structure.
- `templates/dental_family/includes/`: shared navigation and footer.
- `static/dental_family/css/theme.css`: centrally editable brand palette.
- `static/dental_family/css/site.css`: original compiled global/Tailwind CSS and fonts.
- `static/dental_family/css/components.css`: original component styles with readable selectors.
- `static/dental_family/css/maps.css`, `not-found.css`, `recovery.css`: remaining page styles.
- `static/dental_family/css/interactions.css`: hover/tap and interaction styling.
- `static/dental_family/js/site.js`: all interactive behavior, without framework dependencies.
- `static/dental_family/assets/`: original photographs, logos, fonts, and other assets.
- `static/dental_family/fonts/`: compiled local font files used by the original layout.
- `routes.json`: route-to-template mapping and page titles.
- `dental_family/`: Django views, URLs, and legacy redirects.
- `demo/`: local Django preview project.
- `validation/`: route/asset audit, browser results, and comparison screenshots.

CSS selector names are readable, for example `.hero--scene` and
`.doctor-nav--dropdown`, while retaining the original cascade and dimensions.
The `__variable_*` font classes preserve the original locally hosted typefaces.

## Integrate into your Django project

1. Copy `dental_family/`, `templates/`, `static/`, and `routes.json` together into a
   directory on your project's Python path. The adapter locates the manifest and
   metadata files relative to its package. Alternatively, adjust `ROOT` in
   `dental_family/views.py` to your chosen project directory.
2. Add `dental_family` and `django.contrib.staticfiles` to `INSTALLED_APPS`.
3. Add the supplied `templates/` directory to `TEMPLATES[0]['DIRS']`.
4. Add the supplied `static/` directory to `STATICFILES_DIRS`.
5. Include the website URLs at the root:

   ```python
   from django.urls import include, path

   urlpatterns = [path('', include('dental_family.urls'))]
   handler404 = 'dental_family.views.not_found'
   handler500 = 'dental_family.views.server_error'
   ```

6. Set `STATIC_URL = '/static/'`, set a separate `STATIC_ROOT`, and run
   `python manage.py collectstatic` for deployment. Serve collected static files
   using your web server or your project's static-file middleware.
7. Use your existing production settings, secret key, hosts, and security settings;
   `demo/settings.py` is for local preview.

URLs use trailing slashes; Django's `CommonMiddleware` supports the previous URLs
without them. Legacy treatment, payment, author, and form URLs retain their 301
redirects. Existing external booking links and Google Maps embeds are preserved.
Unmatched website URLs display the custom 404 with HTTP status 404, including
when `DEBUG=True`. Include any other application URL patterns before this website
include, because its final pattern handles unmatched website paths.

## Edit the website

Change `static/dental_family/css/theme.css` to update the brand scheme centrally.
Edit page content in `templates/dental_family/pages/`; edit the shared navigation
and footer once in `includes/`. The standalone HTML copies are independent preview
artifacts, so update them too if maintaining both versions after migration.

The delivered contact form preserves the original email composer: it validates
fields and opens a `mailto:` draft. It does not save submissions. To replace it
with a Django form, supply your form view/action and CSRF token, and remove the
`data-contact-form` hook so the email-composer JavaScript does not intercept it.

## Validate or refresh the migration

The conversion tools are optional development utilities, not runtime dependencies:

```bash
pip install -r tools/requirements.txt
python tools/audit.py
```

`tools/audit.py` renders every Django page, checks local assets/internal links,
compares standalone and Django content, and checks legacy redirects and errors.

`tools/browser_check.py` compares desktop/mobile screenshots and exercises the
interactive controls. Start the original export at port 8011, the Django preview
at 8012, and the standalone preview at 8013 before running it. Pass `--browser`
to use a different installed Chromium executable.

To regenerate from the Next source while it is still available:

```bash
python tools/build_export.py --source ../main_website/dental_family
```

This builds a temporary copy, injects animation markers, and exports all routes.
It does not modify the original website. It requires the original Node dependencies
only during regeneration and overwrites generated HTML/templates and compiled CSS.
Your standalone/Django production website does not require Node or Next.js.

The JavaScript reproduces viewport reveals, hero parallax, counters, menu animation,
accordion height changes, gallery filters/lightbox, testimonial transitions/autoplay,
image comparison, contact-form validation, and reading progress. It respects reduced
motion, keyboard navigation, focus handling, and the desktop/mobile breakpoints.
Viewport/counter transitions and springs are implemented with Web Animations and
`requestAnimationFrame`; their timing is matched closely, rather than retaining
Framer Motion as a runtime dependency.

### Website dashboard preview

Open `/dashboard/` for the Cloudflare-inspired website console (HTML, CSS, JavaScript). It contains a website overview, searchable pages, treatments, doctors, gallery, articles, activity, and workspace settings. It shares the brand variables in `static/dental_family/css/theme.css`.

The console is a UI preview: edits are browser-local drafts, exportable as JSON. It has no authentication, database writes, live analytics, or publication API. Connect staff authentication and Django models before using it as a production CMS. No patient records are included.

After regenerating the website export, run `python tools/build_dashboard.py` (requires Beautiful Soup) to refresh the content snapshot and Django dashboard template. The editable dashboard source is `pages/dashboard/index.html`, with `static/dental_family/css/dashboard.css` and `static/dental_family/js/dashboard.js`. The Django template uses the static tag so it supports configured static hosting.

Dashboard refinements include global content search (`Ctrl/Cmd+K`, arrow keys and Enter), title sorting, a dedicated local-drafts view, quick edits from the overview, and a side-panel editor with unsaved-change protection. Mobile content lists become compact cards; navigation has a dismissible backdrop. Filters remain selected after saving a draft. Run `python tools/dashboard_check.py` with the local Django preview on port 8012 for browser regression checks (requires Playwright and Chrome).

Dashboard motion uses native Web Animations and CSS: short page and list entrances, press/hover feedback, animated editor/search/account dialogs with exit transitions, and mobile navigation transitions. Animation cancellation handles rapid repeated actions; final opacity always comes from the normal styles. `prefers-reduced-motion` disables motion, including when the preference changes while the dashboard is open. Run `python tools/dashboard_motion_check.py` to verify animation completion and reduced-motion behavior against the preview on port 8012.

The **Our clinic** dashboard section (`/dashboard/#clinic`) manages the About Us introduction and its featured photo collection. Existing photos, captions and alt text come from the exported `/about-us/` page. Photo drafts include editable title, caption, image URL, accessible alt text and display order; new photos receive the next available order. As with other dashboard content, these are browser-local drafts and do not publish to the public page.

The dashboard has a unified visual system in `dashboard.css`: an inset plum navigation rail, lavender canvas, consistent cards and controls, responsive content layouts, and matching editor/search dialogs. Its palette uses the dashboard variables in `theme.css`. This redesign changes presentation only; existing browser-local drafts, content data, and editing behavior remain unchanged.

Dashboard navigation and action icons use locally bundled Phosphor regular SVGs. The bundle loads before `dashboard.js`; its source revision and MIT license are recorded under `static/dental_family/assets/icons/phosphor/`. Native selects share a Phosphor caret with 44px of right padding and a 14px inset, preserving keyboard and mobile selection. No icon CDN or framework runtime is required.

Our clinic photos use a table with uniform thumbnails. Drag the Phosphor grip handle to reorder rows, or focus a handle and press Up/Down. The complete order is saved as local drafts and included in JSON exports. Reordering is enabled only with an empty search, All content, and Default order, avoiding partial-list changes. Mobile keeps the table with horizontal scrolling. Caption/image edits preserve the saved order.

The Gallery dashboard uses the same uniform photo table and drag/keyboard ordering as Our clinic. Gallery drafts include image, caption, accessible alt text, and display order. Ordering is stored independently for each collection; older gallery drafts receive their original snapshot order automatically. Existing search/filter safeguards and mobile horizontal scrolling apply to both tables.
