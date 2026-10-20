# Google review section

Source: the Google reviews widget HTML supplied by the user. The homepage uses its 5.0 overall rating, 46-review total, place ID, and 11 individual reviews. This is an imported snapshot rather than a live Google API integration.

The structured snapshot is in `static/dental_family/reviews.json`. Original names, per-review ratings (including four-star reviews), dates, text, and Google contributor links are preserved. Reviews without text are labelled as rating-only. Calendar dates are derived from the supplied Unix timestamps in Bangladesh time, rather than copying stale relative dates.

Reviewer photos from the supplied widget are bundled under `static/dental_family/assets/images/reviews/` at up to 100 × 100 pixels. They do not require third-party image requests at runtime.

Run `venv/bin/python tools/update_review_section.py` after updating the snapshot to regenerate both homepage variants. Styling is in `theme.css`, and carousel controls use the existing review-strip behavior in `site.js`. After changes, run `venv/bin/python manage.py collectstatic --noinput`.

Google wordmark SVG: `static/dental_family/assets/images/brand/google-wordmark.svg`, sourced from https://commons.wikimedia.org/wiki/File:Google_2015_logo.svg. The original vector artwork is bundled locally and retains its original colors and aspect ratio.
