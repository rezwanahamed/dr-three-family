"""Rebuild homepage review markup from the supplied Google widget snapshot."""
import json
import re
from datetime import date
from html import escape
from pathlib import Path
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
data = json.loads((ROOT / 'static/dental_family/reviews.json').read_text())
star = (ROOT / 'static/dental_family/assets/icons/phosphor/star-fill.svg').read_text()
star = re.sub(r'<svg[^>]*>', '<svg aria-hidden="true" focusable="false" viewBox="0 0 256 256" fill="currentColor">', star, count=1)

def stars(rating):
    return '<span class="review-rating--stars">'+''.join('<span class="review-star'+(' review-star--empty' if i >= rating else '')+'">'+star+'</span>' for i in range(5))+'</span>'

def google_wordmark():
    return '<img class="review-google-wordmark" src="/static/dental_family/assets/images/brand/google-wordmark.svg" alt="Google" width="74" height="25" loading="lazy" decoding="async"/>'


section = '''<section class="google-style-reviews" aria-labelledby="patient-stories-title"><div class="wrap">
<header class="google-style-reviews--heading"><div><div class="eyebrow">IN OUR PATIENTS’ WORDS</div><h2 id="patient-stories-title">Good care. <em>Kind words.</em></h2><p>Real experiences from the people behind the smiles.</p></div><a class="google-style-reviews--googleLink" href="'''+escape(data['reviews_url'],quote=True)+'''" target="_blank" rel="noopener noreferrer">Read reviews on Google <span aria-hidden="true">↗</span></a></header>
<div class="google-style-reviews--body"><aside class="google-style-reviews--summary" aria-label="Google review summary">
'''+google_wordmark()+'''<a class="review-clinic-name" href="'''+escape(data['reviews_url'],quote=True)+'''" target="_blank" rel="noopener noreferrer">'''+escape(data['clinic_name'])+'''</a>
<div class="google-style-reviews--score"><strong>'''+format(data['rating'],'.1f')+'''</strong><span role="img" aria-label="'''+str(data['rating'])+''' out of 5 stars">'''+stars(round(data['rating']))+'''</span></div><p class="review-google-count">Based on '''+str(data['review_count'])+''' Google reviews</p><a class="review-google-write" href="'''+escape(data['write_review_url'],quote=True)+'''" target="_blank" rel="noopener noreferrer">Review us on Google <span aria-hidden="true">↗</span></a></aside>
<div class="google-style-reviews--carousel" data-review-strip><div class="google-style-reviews--track" id="patient-review-cards" tabindex="0" role="region" aria-label="Google patient reviews. Scroll to read more.">'''
for i,r in enumerate(data['reviews']):
    initials=''.join(p[0] for p in r['name'].split()[:2]).upper()
    timestamp=date.fromisoformat(r['date'])
    date_label=timestamp.strftime('%b ') + str(timestamp.day) + timestamp.strftime(', %Y')
    section+='''<article class="google-style-review" aria-label="Review by '''+escape(r['name'],quote=True)+'''"><header><span class="google-style-review--avatar google-style-review--avatar-'''+str(i%3)+'''" aria-hidden="true"><span>'''+escape(initials)+'''</span><img data-review-avatar src="'''+escape(r['image'],quote=True)+'''" alt="" width="42" height="42" loading="lazy" decoding="async"/></span><div><h3><a href="'''+escape(r['profile_url'],quote=True)+'''" target="_blank" rel="noopener noreferrer">'''+escape(r['name'])+'''</a></h3><time datetime="'''+r['date']+'''">'''+date_label+'''</time></div></header><div class="google-style-review--rating" role="img" aria-label="'''+str(r['rating'])+''' out of 5 stars">'''+stars(r['rating'])+'''</div>'''
    if r['text']:
        section+='<blockquote>'+escape(r['text'])+'</blockquote>'
    else:
        section+='<p class="review-rating-only">This reviewer left a star rating.</p>'
    section+='<footer>'+google_wordmark()+'<a href="'+escape(r['profile_url'],quote=True)+'" target="_blank" rel="noopener noreferrer">View on Google <span aria-hidden="true">↗</span></a></footer></article>'
section+='''</div><div class="google-style-reviews--bottom"><p>'''+str(len(data['reviews']))+''' featured Google reviews.</p><div class="google-style-reviews--controls"><span data-review-position aria-live="polite">1–3 of '''+str(len(data['reviews']))+'''</span><button type="button" data-review-previous aria-label="Previous reviews" aria-controls="patient-review-cards">←</button><button type="button" data-review-next aria-label="Next reviews" aria-controls="patient-review-cards">→</button></div></div></div></div></div></section>'''
for name in ['pages/index.html','templates/dental_family/pages/index.html']:
    path=ROOT/name
    text=path.read_text()
    start=text.index('<section class="google-style-reviews"')
    end=text.index('</section>',start)+len('</section>')
    block=section
    if name.startswith('templates'):
        block=re.sub(r'/static/(dental_family/[^"\s]+)',lambda match:"{% static '"+match[1]+"' %}",block)
    path.write_text(text[:start]+block+text[end:])
print('Updated homepage section with',len(data['reviews']),'Google reviews.')
