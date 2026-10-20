# Curated improvement goals

The catalog is based on the six published service categories and thirteen treatment detail pages in the website workspace. Stable treatment IDs are used so cards follow the current published URLs if slugs change.

| Goal | Destination treatment |
| --- | --- |
| Improve my smile | Cosmetic Dentistry |
| Straighten my teeth | Clear Aligners |
| Replace a missing tooth | Advanced Oral Surgery / Dental Implant |
| Whiten my teeth | Teeth Whitening |
| Repair a damaged tooth | Restorative Dentistry |
| Family dental care | Everyday Dental Care |
| Get help with tooth pain | Root Canal Treatment |
| Get urgent dental care | Urgent Dental Care |

Definitions and selections are in `static/dental_family/improvement-catalog.json`. The homepage displays the goal cards. Each card opens `/smile-goals/<goal-id>/`, where related treatments are shown as a list. Treatment detail pages do not display the goal section. Per-treatment selections classify treatments into these goals. Existing explicit selections, existing custom options, other content fields, services, category assignments, and pending drafts are retained.

The card photographs were generated specifically for this catalog, using plum, blush, lavender, and ivory. They are illustrative campaign images and dental demonstration models, not patient treatment results. Optimized website files are in `static/dental_family/assets/images/goals/`.

To preview the catalog against a workspace:

```bash
venv/bin/python manage.py populate_improvement_goals
```

To apply it:

```bash
venv/bin/python manage.py populate_improvement_goals --publish
venv/bin/python manage.py collectstatic --noinput
```

The command takes a JSON backup of an existing workspace in `/tmp` before writing. It can be rerun without duplicating options or replacing existing selections. Admins can edit the resulting titles, images, destinations, and per-treatment selections through the Treatments dashboard.

Use `venv/bin/python manage.py populate_improvement_goals --publish --refresh-selections` only when intentionally replacing the treatment-to-goal associations with the catalog. Run `venv/bin/python tools/build_goal_pages.py` to rebuild the standalone homepage section and result pages.
