#!/usr/bin/env python3
"""Extract existing FAQ answers without rewriting clinic content."""
import json
import re
from html import unescape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def plain(markup):
    markup = re.sub(r'</(?:p|li)>|<br\s*/?>', '\n', markup)
    return '\n'.join(' '.join(unescape(re.sub(r'<[^>]+>', '', line)).split()) for line in markup.splitlines() if re.sub(r'<[^>]+>', '', line).strip()).strip()

def build():
    index = (ROOT / 'pages/faq/index.html').read_text()
    topics = []
    records = []
    for url, body in re.findall(r'<a\b[^>]*class="topic-card"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', index, re.S):
        title = plain(re.search(r'<h3[^>]*>(.*?)</h3>', body, re.S)[1])
        topic = {'id': url.strip('/'), 'title': title, 'url': url}
        topics.append(topic)
        page = (ROOT / 'pages' / url.strip('/') / 'index.html').read_text()
        parts = re.split(r'<div class="accordion-item[^\"]*">', page)[1:]
        for order, part in enumerate(parts, 1):
            question = re.search(r'<h3><button[^>]*>(.*?)<span', part, re.S)
            answer = re.search(r'class="accordion-panel"[^>]*><div>(.*?)</div>', part, re.S)
            if not question or not answer:
                raise ValueError(f'Missing FAQ question or answer: {url}, {order}')
            records.append(dict(id=f'faq-{topic["id"]}-{order}', section='faqs', title=plain(question[1]), description=plain(answer[1]), topic=topic['id'], order=order, url=url, image='', status='Website snapshot'))
    if len(topics) != 5 or not records:
        raise ValueError('Expected the five existing FAQ topics and their questions')
    target = ROOT / 'static/dental_family/js/faq-data.js'
    target.write_text('/* Generated from the exported FAQ pages by tools/build_faq.py. */\nwindow.DashboardFAQTopics = '+json.dumps(topics, indent=2)+';\nwindow.DashboardFAQs = '+json.dumps(records, indent=2)+';\n')
    return topics, records

if __name__ == '__main__':
    topics, records = build()
    print(f'{len(records)} questions across {len(topics)} topics')
    for topic in topics:
        group = [r for r in records if r['topic'] == topic['id']]
        print(f'{topic["title"]}: {len(group)} questions; empty answers: {sum(not r["description"] for r in group)}')
