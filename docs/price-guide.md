# Price guide dashboard

Open **Price guide** in the dashboard sidebar (`/dashboard/#prices`). The library starts with the 11 existing entries from the public price guide, organized into their original three categories.

Use **Add price** or **Edit** to set the treatment name, category, price or range, and numeric display order. The category field suggests existing categories and also accepts a new category. Prices are text, allowing values such as `500 Tk`, `7,000–10,000 Tk`, or `Contact for estimate`. Entries can be deleted after confirmation.

The table supports search, status filters, sorting, and pagination. Changes save as workspace drafts and activate the Publish changes indicator. Publish to update `/pricing-guide-2/`; the page retains its existing category cards, explanatory notice, payment link, and appointment section. Entries sort by display order; categories appear according to their first entry. Category and price text are escaped before public rendering.

Prices are stored as `prices` records in `WebsiteWorkspace`, alongside other content. The shared `price_guide_initialized` flag imports the original entries once into older workspaces and prevents deleted entries from reappearing. There are no model migrations for this feature.

`static/dental_family/js/price-data.js` contains the initial price entries for the plain HTML dashboard. `tools/build_dashboard.py` can rebuild that seed script from the exported price guide. Staff-only dashboard APIs, revision checks, and publishing controls apply to price changes as they do to the other dashboard content.

The canonical `/pricing-guide-2/` route renders the managed price guide directly, including for older workspaces where the guide was previously classified as a treatment and given a different slug. The `/price-guide/` alias redirects to this canonical page. This prevents an old treatment redirect from bypassing the integrated price guide.

`/a-little-clarity-on-costs/` also renders the full price guide with the same published entries. It uses the price guide template directly, including when older workspace data classified this URL as a treatment. The slashless URL redirects to the trailing-slash version.
