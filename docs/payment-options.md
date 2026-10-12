# Payment options dashboard

Open **Payment options** in the dashboard sidebar (`/dashboard/#payments`). The library starts with the existing bKash, Nagad, and BRAC Bank entries from the website.

Use **Add payment option** in the library or page header. Enter the provider/method name, method type, display label, and display order. Mobile wallet methods require a wallet number. Bank transfer methods require the account name and number, with optional branch and routing number. Cash, card, and other methods accept additional text. Account and routing values remain strings to preserve leading zeros.

Use **Show on the website** to make an option visible or hide it without deleting it. Delete requires confirmation. The table supports search, status filters, sorting, and pagination.

Changes save as shared workspace drafts. **Publish changes** updates `/financing-2/` and `/simple-ways-to-pay/` using the existing payment-card design. Only visible methods render, in display order. The existing confirmation notice and clinic contact links remain on the page. This feature displays payment information; it does not process payments or create financing arrangements.

Payment records use the `payments` section of `WebsiteWorkspace`. The `payments_initialized` flag imports existing entries once into older workspaces and prevents deleted options from reappearing. `static/dental_family/js/payment-data.js` provides the initial records for the plain HTML dashboard. No migration is required.

Staff access, CSRF validation, revision checks, and backend field validation apply to payment updates. Payment text is escaped before public rendering. Automated and browser tests use isolated data and do not change live bank or wallet details.
