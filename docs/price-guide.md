# Price guide dashboard

Open **Price guide** in the dashboard sidebar (`/dashboard/#prices`). The library starts with the 11 existing entries from the public price guide, organized into their original three services.

Use **Add price** or **Edit** to set the treatment name, service, price or range, and numeric display order. Choose a service from the dropdown. Use the separate Manage services panel to add, edit, or delete services. Choose Single price or Price range and enter amounts in Tk. Range mode requires a minimum and a greater maximum. The preview formats values such as `1,000–1,500 Tk`. Custom text remains available for notes such as `Contact for estimate`. Existing price strings load into the appropriate mode automatically. Entries can be deleted after confirmation.

The table supports search, status filters, sorting, and pagination. Changes save as workspace drafts and activate the Publish changes indicator. Publish to update `/pricing-guide-2/`; the page retains its existing service cards, explanatory notice, payment link, and appointment section. Entries sort by display order within their service. Drag service handles in Manage services to arrange the public cards; keyboard up/down arrows also work. Service and price text are escaped before public rendering.

Prices are stored as `prices` records in `WebsiteWorkspace`, alongside other content. The shared `price_guide_initialized` flag imports the original entries once into older workspaces and prevents deleted entries from reappearing. There are no model migrations for this feature.

`static/dental_family/js/price-data.js` contains the initial price entries for the plain HTML dashboard. `tools/build_dashboard.py` can rebuild that seed script from the exported price guide. Staff-only dashboard APIs, revision checks, and publishing controls apply to price changes as they do to the other dashboard content.

The canonical `/pricing-guide-2/` route renders the managed price guide directly, including for older workspaces where the guide was previously classified as a treatment and given a different slug. The `/price-guide/` alias redirects to this canonical page. This prevents an old treatment redirect from bypassing the integrated price guide.

`/a-little-clarity-on-costs/` also renders the full price guide with the same published entries. It uses the price guide template directly, including when older workspace data classified this URL as a treatment. The slashless URL redirects to the trailing-slash version.

Services have an independent ordered list stored as `price_services` in published content and `priceServices` in drafts. Renaming a service updates its price entries. Deleting a service with entries requires reassigning those entries to another service; deleting an empty service only requires confirmation. Empty services stay available in the dashboard but do not render an empty public price card. Internal price records keep the legacy `category` field for compatibility. Service changes and order only affect the public guide after publishing.
