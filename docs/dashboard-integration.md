# Connected Django dashboard

The Django dashboard now reads and saves a shared workspace in the `WebsiteWorkspace` database model. It loads the existing exported website as its initial content. Existing browser-local drafts are imported on the first visit only when the server workspace is empty.

## Editorial workflow

1. Log in with an active staff account at `/dashboard/login/`.
2. Edit content and choose Save draft. Service/topic changes save automatically. The save status confirms when the database has received the draft.
3. Review changes in the dashboard, then choose Publish changes. Publication validates the complete workspace and commits it atomically.
4. Open the public website. Changes are applied to the existing branded HTML, CSS, and JavaScript.

Publication updates treatment/article details and summaries, thumbnails, page titles/descriptions, SEO tags and sitemap, listings, doctors, gallery images, clinic photos/captions, locations/maps/footer branches, FAQ topics/answers/order, and service navigation. New pages, treatment pages, articles, and FAQ topics receive public routes. Deleted public content returns the custom 404. Topic/service removal keeps the reassignment rules from the dashboard.

Drafts do not affect public pages until publication. The public site uses the last published snapshot; a database backup therefore includes both drafts and published content. JSON export remains available. Uploaded images remain under `MEDIA_ROOT/gallery`.

The server requires active staff access and CSRF tokens for mutation requests. Revision checks reject stale writes from another editing session rather than overwriting its work. The dashboard reports conflicts and failed saves; keep/export unsaved local edits before reloading to resolve a conflict. Rich text is sanitized on the server before it is rendered.

## Setup

Dependencies include Django, Pillow and Beautiful Soup:

```bash
cd frontend/django-compatiable
venv/bin/python -m pip install -r requirements.txt
venv/bin/python manage.py migrate
venv/bin/python manage.py runserver
```

The new migration has been applied to this workspace's database. No staff credentials or public content were changed by verification. The existing email-based staff login remains in use.

API endpoints:

- `GET /dashboard/content/`: published records, catalog data, shared drafts, and revision.
- `PUT /dashboard/content/`: save `{state, revision}` to the shared draft workspace.
- `POST /dashboard/publish/`: validate and publish `{state, revision}`.

Run `venv/bin/python manage.py test dental_family --noinput` for authentication, uploads, persistence, publication, routing, rich-text sanitization, SEO, content projection, and conflict checks.

The plain `pages/dashboard/index.html` export still supports offline local drafts. Django's generated dashboard template adds the server endpoints; `tools/build_dashboard.py` preserves this connection when regenerating it.

## Gallery sections

The gallery photo editor includes a required Section dropdown with Our space, Our team, and Our technology. The separate Gallery sections panel above the image library lists sections and photo counts. Its Add section button opens a dialog for creating custom sections. The image editor keeps only the selection dropdown; duplicate section names are blocked without regard to capitalization. Section selection is stored with the photo as `gallery_category`. Custom section names persist in server drafts and are included in JSON exports. After publication, the public gallery builds its filter buttons from the saved sections and filters photos using their selected section. Existing technology/team photos retain their categories.

Gallery section cards also provide Edit and Delete. Renaming updates the section on its photos without removing images. Delete opens a confirmation dialog; sections with photos require a destination section. Default sections can also be renamed or removed, and removed names stay removed after publication. The server rejects deleting a section while photos still reference it.

The public gallery always starts on All photos. Its remaining filter buttons come exclusively from the published backend gallery section list, including empty custom sections. All photos is a permanent UI filter, not an editable section. Legacy Our spaces/Our space names are normalized to Our space to prevent duplicate filters. The initial unpublished gallery also uses the backend seed data.
