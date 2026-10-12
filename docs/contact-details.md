# Contact details

Open **Contact details** in the dashboard sidebar (`/dashboard/#contact`). Edit the shared phone number, contact email, WhatsApp number, Facebook/Instagram links, and opening-hours or visit note. Include the country code in phone numbers.

**Save contact details** stores a shared workspace draft. **Publish changes** applies it to the public website. Changes update the contact page, shared phone/email links, footer links, WhatsApp, social links, and location visit notes. The contact form prepares its email draft for the published contact email; it does not send email automatically. This contact email is independent of SMTP settings and login emails.

Optional blank WhatsApp or social fields hide their public links. A blank visit note keeps the page's original note. Branch addresses, maps, and individual branch phone numbers are edited in **Locations**; numbers different from the original shared clinic number remain branch-specific.

Published details live under `contact_details` in `WebsiteWorkspace.published`; draft details use `contactDetails` in the workspace state. Older workspaces inherit the existing website contact details. Email, telephone, and social URLs are validated by the backend. Staff access, CSRF validation, and revision checks apply to these updates.

`static/dental_family/js/contact-data.js` provides initial values for the plain HTML dashboard. No database migration is required.
