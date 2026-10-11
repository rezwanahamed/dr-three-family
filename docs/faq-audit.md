# FAQ audit and dashboard management

Audited the exported FAQ pages and their dashboard classification on 11 October 2026.

| Topic | Existing questions |
| --- | ---: |
| Teeth whitening | 5 |
| 3D intraoral scanning | 7 |
| Clear aligners | 15 |
| Dental implants | 5 |
| Dental braces | 16 |
| **Total** | **48** |

All five topics linked from `/faq/` have exported pages. Every accordion has a question and a nonempty answer. There are no duplicate questions within a topic. The public accordion controls already include expanded state, panel associations, and keyboard-operable buttons.

Previously, the dashboard classified the five topic pages as articles and provided no individual FAQ editor. Topic pages now belong to Pages, and their individual questions are seeded into a separate FAQs library. Existing answers are preserved as plain text with paragraph breaks; public pages have not been rewritten.

The new dashboard section at `/dashboard/#faqs` provides question and answer search, topic and status filters, question sorting, add/edit forms, topic selection, numeric display order, and confirmed deletion. It shares the existing fonts, colour tokens, animations, responsive table behaviour, local draft storage, and JSON export. Question, answer, topic, and positive integer display order are required. No image or website path is requested for an FAQ.

Content review remains advisable: several existing answers use superlatives such as “world’s no.1” and “most advanced,” and the aligner cost answer uses USD. These claims and pricing have no references or review dates in the exported content. This audit checks content structure and dashboard integration; it does not verify clinical claims or replace a clinician’s review.

Changes follow the dashboard’s existing local draft workflow. They persist in this browser and can be exported with topic identifiers, question text (`title`), answer text (`description`), and display order. They do not publish to the public website automatically.

Refresh the FAQ snapshot with `python3 tools/build_faq.py`. The existing `tools/build_dashboard.py` also invokes this extractor. FAQ data comes from the five exported pages, not invented answers.

## Topic management

Use the **Manage topics** section above the FAQ library on the FAQs dashboard to manage topics. Add topic opens a dialog; Edit opens the same dialog to rename a topic. Remove opens a confirmation dialog that also offers question reassignment. Names are checked case-insensitively for duplicates. Renaming preserves the topic identifier, existing route, and question associations. Removing a populated topic requires moving its questions to another topic; moved questions are appended in their original order. The last populated topic cannot be removed without first adding a destination or removing its questions. Drag handles reorder topics with pointer/touch input or up/down arrow keys. The saved order is used by the topic list, FAQ filters, and FAQ editor topic dropdown. Topic changes and removal records persist in local storage and export as `faq_topics` and `deleted_faq_topics`, alongside the question drafts.

The export includes `faq_topic_order` and a one-based `order` on each exported topic. Removal requires confirmation; Cancel or Escape leaves the topic and its questions unchanged.
