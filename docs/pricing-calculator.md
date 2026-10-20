# Database-linked pricing and public calculator

The dashboard price editor selects from the current service catalog and treatment records returned by the shared database workspace. Service selection comes first. The treatment dropdown is restricted to the selected service; its empty choice creates a service-level price. Services with no treatment records can still be priced.

New price records store `service_id` and optional `treatment_id` alongside existing amount/range/custom-text fields. The backend checks catalog membership, including pending service and treatment edits. Existing unlinked fees remain available; the editor offers their original labels when updating them. Price-service creation is now managed through the main Treatments service catalog.

The calculator on `/a-little-clarity-on-costs/` and its legacy price-guide route uses published prices only. Draft fees do not appear. Numeric prices are supplied in integer minor units (1/100 Tk) to avoid rounding errors; fixed and range totals multiply by quantity. Custom-text/quote-only prices remain visible and are explicitly excluded from the known subtotal, never treated as free. No new fees are invented.

The database remains the source of truth at request time. Legacy Dental essentials and Dental restorations fees are associated with the existing general-dentistry service for selection; unmatched legacy groups stay visible so existing prices are not lost.

Frontend: `static/dental_family/js/pricing-calculator.js` and the calculator block in `theme.css`. Backend: `dental_family/pricing.py`. To rebuild standalone previews, run `venv/bin/python tools/build_pricing_page.py`. Refresh collected assets with `venv/bin/python manage.py collectstatic --noinput`.
