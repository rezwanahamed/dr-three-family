# Services and treatment options

The Treatments dashboard has a Manage services section above the content library. The separate treatment-options column has been removed; treatment selections remain available in the content editor. These lists show names and management controls, without order numbers or drag handles.

Add service and Add treatment open name dialogs. Edit preserves the service identifier and updates treatment selections in saved content when an option is renamed. Names follow the dashboard's capitalization convention and are checked for duplicates within the relevant list.

Remove opens a confirmation dialog. Removing a service with linked content requires a destination service; its optional treatment selections are cleared. Removing an individual treatment option clears that optional selection on linked content, preserving the content itself. Cancel or Escape leaves the catalog unchanged.

Orders, catalog changes, linked content changes, and removal records persist in this browser's existing local draft storage. The content editor dropdowns use the managed catalog and its order. JSON exports include the effective services with one-based service order, ordered treatment options, and removed service identifiers. Changes do not automatically publish to public pages.

## Django integration

The Django-hosted dashboard now saves shared server drafts and publishes through **Publish changes**. The earlier local-only workflow described above applies to the standalone HTML preview. See [dashboard-integration.md](dashboard-integration.md) for the current Django workflow.

Treatment URLs are generated from the title using lowercase ASCII letters, numbers, and hyphens (for example, `Clear Aligners` → `/clear-aligners/`). Duplicate or reserved slugs receive `-2`, `-3`, etc. The server verifies uniqueness during publication. Saving a changed title regenerates the treatment URL; after publishing, previous URLs redirect permanently to the current treatment details page.

The public navigation groups actual treatment records by their selected service and links to their canonical detail URLs. Each service shows its newest three published treatments, based on server-recorded creation time. Edits keep the original creation time; older imported records use their existing catalog sequence when no creation date is available. Unpublished drafts do not appear.
