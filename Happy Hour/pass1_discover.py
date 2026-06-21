"""
pass1_discover.py  —  Happy Hour pipeline, PASS 1 (acquire).

For each bar in the `bars` collection that has a Website, this:
  1. crawls the site for a happy-hour / drinks / menu link (or PDF),
  2. pulls the raw text of that source (HTML or PDF),
  3. best-effort parses the happy-hour day/time window from the text,
and upserts one document per bar into the `happy_hours` collection.

PASS 2 (pass2_extract.py) then reads happy_hours.menu_text, extracts each
item + price, and normalizes the drink type.

Usage:
  python pass1_discover.py                 # all bars with a Website
  python pass1_discover.py --limit 25      # first 25 (good for a trial run)
  python pass1_discover.py --bar "Fado"    # only bars whose Name matches
  python pass1_discover.py --dry-run       # discover + print, write nothing

Requires: requests, beautifulsoup4, pymupdf (fitz). See requirements.txt.
"""

import argparse
import re
import sys
import time
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from db import get_db

HEADERS = {'User-Agent': 'MappyHourBot/1.0 (+happy-hour discovery)'}
TIMEOUT = 15

# Link scoring — prefer happy-hour, then drink/menu pages; avoid food-only pages.
HH_WORDS    = ['happy hour', 'happy-hour', 'happyhour', 'hh ', 'specials', 'deals']
MENU_WORDS  = ['menu', 'drinks', 'drink', 'beverage', 'cocktail', 'beer', 'wine', 'bar']
AVOID_WORDS = ['lunch', 'dinner', 'brunch', 'breakfast', 'catering', 'private',
               'event', 'gift', 'careers', 'contact', 'reservation', 'order', 'food']

DAYS = r'(?:mon|tue|wed|thu|fri|sat|sun|monday|tuesday|wednesday|thursday|friday|saturday|sunday)'
TIME = r'\d{1,2}(?::\d{2})?\s*(?:am|pm)?'
# "Happy Hour: Mon-Fri 3-6pm", "Happy Hour 4:00pm - 7:00pm daily", etc.
HH_TIME_RE = re.compile(
    r'happy hour[^.\n]{0,60}?'
    r'(?P<days>(?:' + DAYS + r'\s*(?:-|to|through|–|&|,)?\s*)+)?'
    r'[^.\n]{0,20}?'
    r'(?P<start>' + TIME + r')\s*(?:-|to|–|until|til)\s*(?P<end>' + TIME + r')',
    re.IGNORECASE)


def fetch(url):
    r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    return r


def find_source(website):
    """Return (source_type, source_url) — the best happy-hour/menu link or PDF."""
    try:
        resp = fetch(website)
    except Exception as e:
        return None, None, f'homepage fetch failed: {e}'

    soup = BeautifulSoup(resp.text, 'html.parser')
    candidates = []  # (score, is_pdf, absolute_url)
    for a in soup.find_all('a', href=True):
        href = a['href'].strip()
        if href.startswith(('mailto:', 'tel:', '#', 'javascript:')):
            continue
        absu = urljoin(website, href)
        label = (a.get_text(' ', strip=True) + ' ' + href).lower()
        if any(w in label for w in AVOID_WORDS) and not any(w in label for w in HH_WORDS):
            continue
        score = 0
        if any(w in label for w in HH_WORDS):
            score += 10
        if any(w in label for w in MENU_WORDS):
            score += 3
        if absu.lower().endswith('.pdf'):
            score += 2
        if score:
            candidates.append((score, absu.lower().endswith('.pdf'), absu))

    if not candidates:
        # No dedicated link — treat the homepage itself as the source.
        return 'html', website, 'no menu link; using homepage'
    candidates.sort(key=lambda c: c[0], reverse=True)
    _, is_pdf, url = candidates[0]
    return ('pdf' if is_pdf else 'html'), url, None


def extract_text(source_type, source_url):
    if source_type == 'pdf':
        import fitz  # PyMuPDF
        data = fetch(source_url).content
        doc = fitz.open(stream=data, filetype='pdf')
        return '\n'.join(page.get_text() for page in doc)
    soup = BeautifulSoup(fetch(source_url).text, 'html.parser')
    for tag in soup(['script', 'style', 'nav', 'footer', 'header']):
        tag.decompose()
    return soup.get_text(separator='\n')


def parse_hh_times(text):
    m = HH_TIME_RE.search(text or '')
    if not m:
        return {'hh_times_raw': None, 'hh_days': None, 'hh_start': None, 'hh_end': None}
    return {
        'hh_times_raw': m.group(0).strip()[:160],
        'hh_days': (m.group('days') or '').strip() or None,
        'hh_start': (m.group('start') or '').strip() or None,
        'hh_end': (m.group('end') or '').strip() or None,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--limit', type=int, default=0)
    ap.add_argument('--bar', type=str, default=None)
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--sleep', type=float, default=1.0, help='seconds between bars (be polite)')
    args = ap.parse_args()

    db = get_db()
    q = {'Website': {'$nin': [None, '']}}
    if args.bar:
        q['Name'] = {'$regex': re.escape(args.bar), '$options': 'i'}
    cur = db.bars.find(q, {'Name': 1, 'Website': 1, 'Yelp Alias': 1})
    if args.limit:
        cur = cur.limit(args.limit)

    found = errors = 0
    for bar in cur:
        name, website = bar.get('Name'), bar.get('Website')
        try:
            stype, surl, note = find_source(website)
            text = extract_text(stype, surl) if surl else ''
            times = parse_hh_times(text)
            doc = {
                'bar_name': name,
                'yelp_alias': bar.get('Yelp Alias'),
                'website': website,
                'source_type': stype,
                'source_url': surl,
                'menu_text': (text or '')[:20000],   # cap stored text
                'status': 'found' if text else 'no_source',
                'note': note,
                **times,
            }
            print(f'[{doc["status"]:9}] {name:<34} {stype or "-":>4}  {surl or note or ""}'
                  + (f'   ⏰ {times["hh_times_raw"]}' if times['hh_times_raw'] else ''))
            if not args.dry_run:
                db.happy_hours.update_one({'bar_name': name}, {'$set': doc}, upsert=True)
            found += 1 if text else 0
        except Exception as e:
            errors += 1
            print(f'[error    ] {name:<34} {e}', file=sys.stderr)
            if not args.dry_run:
                db.happy_hours.update_one(
                    {'bar_name': name},
                    {'$set': {'bar_name': name, 'website': website, 'status': 'error', 'note': str(e)[:200]}},
                    upsert=True)
        time.sleep(args.sleep)

    print(f'\nPass 1 complete — sources found: {found}, errors: {errors}'
          + ('  (dry run, nothing written)' if args.dry_run else ''))


if __name__ == '__main__':
    main()
