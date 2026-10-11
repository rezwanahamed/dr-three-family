# Services and treatment options

The Treatments dashboard has a Manage services section above the content library. The separate treatment-options column has been removed; treatment selections remain available in the content editor. These lists show names and management controls, without order numbers or drag handles.

Add service and Add treatment open name dialogs. Edit preserves the service identifier and updates treatment selections in saved content when an option is renamed. Names follow the dashboard's capitalization convention and are checked for duplicates within the relevant list.

Remove opens a confirmation dialog. Removing a service with linked content requires a destination service; its optional treatment selections are cleared. Removing an individual treatment option clears that optional selection on linked content, preserving the content itself. Cancel or Escape leaves the catalog unchanged.

Orders, catalog changes, linked content changes, and removal records persist in this browser's existing local draft storage. The content editor dropdowns use the managed catalog and its order. JSON exports include the effective services with one-based service order, ordered treatment options, and removed service identifiers. Changes do not automatically publish to public pages.
