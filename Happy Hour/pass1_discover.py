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


# ── Non-bar filter, driven by the Yelp Categories stored on the bar ──────────
# Yelp tags bars with categories like "Bars", "Pubs", "Breweries", "Cocktail
# Bars", etc. If a venue has categories but none are bar-ish, it's not a bar
# (e.g. &pizza → "Pizza", Jasmine Rice → "Thai", Spread Bagelry → "Bagels").
BAR_TERMS = [r'\bbars?\b', 'pub', 'tavern', 'lounge', 'brew', 'gastropub', 'beer',
             'wine bar', 'cocktail', 'speakeasy', 'distiller', 'taproom', 'tiki',
             'nightlife', 'saloon', 'alehouse', 'ale house', 'winery', 'cider', 'meadery']
NON_BAR_NAME = ['dog run', 'dog park', 'roaster', 'bakery', 'coffee', 'creamery',
                'ice cream', 'gym', 'fitness', 'pharmacy', 'grocery', 'museum', 'library']


def is_probably_bar(bar):
    """Use the Yelp categories to decide. If categories exist, require a bar-ish
    one. If none are stored, fall back to a name blocklist."""
    cats = bar.get('Categories')
    cats_str = (', '.join(cats) if isinstance(cats, list) else str(cats or '')).lower()
    if cats_str.strip():
        return any(re.search(t, cats_str) for t in BAR_TERMS)
    name = (bar.get('Name') or '').lower()
    return not any(k in name for k in NON_BAR_NAME)


# Strict HH phrases for matching surrounding page CONTEXT (a big text blob);
# the broader label set (with 'specials'/'deals') is only used on short link text.
HH_STRICT = ['happy hour', 'happy-hour', 'happyhour']

# Common URL paths to probe directly — many sites have a /happy-hour page that
# isn't linked prominently from the homepage (e.g. Bellini → /happy-hour).
COMMON_HH_PATHS = ['/happy-hour', '/happyhour', '/happy-hour-menu', '/happy-hour-specials',
                   '/specials', '/hh', '/menus/happy-hour', '/menu/happy-hour']


def _probe_hh_paths(website):
    """Guess common happy-hour URLs on the same domain. Returns (type, url) for
    the first that loads and actually mentions 'happy hour', else None."""
    p = urlparse(website)
    root = p.scheme + '://' + p.netloc
    for path in COMMON_HH_PATHS:
        url = root + path
        try:
            r = fetch(url)                      # raises on 404 etc.
        except Exception:
            continue
        if url.lower().endswith('.pdf') or 'pdf' in r.headers.get('Content-Type', '').lower():
            return 'pdf', url
        if 'happy hour' in r.text.lower():      # guard against soft-404 pages
            return 'html', url
    return None


def _links_ctx(soup, base):
    """Each link as (url, label, context). `context` adds the parent/grandparent
    text so a bare "View Menu" button sitting under a "Happy Hour" heading is
    recognized as a happy-hour link (the Village Whiskey case)."""
    out = []
    for a in soup.find_all('a', href=True):
        href = a['href'].strip()
        if href.startswith(('mailto:', 'tel:', '#', 'javascript:')):
            continue
        label = (a.get_text(' ', strip=True) + ' ' + href).lower()
        ctx = label
        try:
            p = a.find_parent()
            if p:
                ctx += ' ' + p.get_text(' ', strip=True).lower()[:300]
                gp = p.find_parent()
                if gp:
                    ctx += ' ' + gp.get_text(' ', strip=True).lower()[:300]
        except Exception:
            pass
        out.append((urljoin(base, href), label, ctx))
    return out


def _hh_link(links):
    """Best happy-hour link: label has an HH word, or the surrounding context
    mentions "happy hour". Prefers a PDF. → (type, url) or None."""
    cands = [absu for absu, label, ctx in links
             if any(w in label for w in HH_WORDS) or any(w in ctx for w in HH_STRICT)]
    if not cands:
        return None
    pdf = next((u for u in cands if u.lower().endswith('.pdf')), None)
    url = pdf or cands[0]
    return ('pdf' if url.lower().endswith('.pdf') else 'html'), url


def _menu_links(links):
    """Generic menu/drink links (no HH wording), best first (PDF preferred)."""
    scored = []
    for absu, label, _ctx in links:
        if any(w in label for w in AVOID_WORDS) and not any(w in label for w in HH_WORDS):
            continue
        if any(w in label for w in MENU_WORDS):
            scored.append((2 if absu.lower().endswith('.pdf') else 0, absu))
    scored.sort(key=lambda x: x[0], reverse=True)
    seen, out = set(), []
    for _, u in scored:
        if u not in seen:
            seen.add(u); out.append(u)
    return out


def _follow_for_hh(url):
    """Fetch a page and return its best happy-hour link (prefer PDF), or None."""
    try:
        s = BeautifulSoup(fetch(url).text, 'html.parser')
    except Exception:
        return None
    return _hh_link(_links_ctx(s, url))


def find_source(website):
    """Return (source_type, source_url, note). source_type:
      'pdf' | 'html'      → a real happy-hour menu (shown on the map)
      'menu_only'         → only a generic menu, no HH section (excluded for now)
      'homepage'          → no menu link at all (excluded)
      None                → fetch error."""
    try:
        soup = BeautifulSoup(fetch(website).text, 'html.parser')
    except Exception as e:
        return None, None, f'homepage fetch failed: {e}'
    links = _links_ctx(soup, website)

    # 1) happy-hour link on the homepage. If it's an HTML page (e.g. /specials/),
    #    follow it — the actual HH menu/PDF usually lives inside that section.
    hh = _hh_link(links)
    if hh:
        if hh[0] == 'pdf':
            return 'pdf', hh[1], 'HH pdf on homepage'
        inner = _follow_for_hh(hh[1])
        if inner:
            return inner[0], inner[1], f'HH menu inside {hh[1]}'
        return 'html', hh[1], 'HH page on homepage'

    # 1.5) probe common /happy-hour URLs directly — catches HH pages that aren't
    #      linked prominently from the homepage (the Bellini case).
    probed = _probe_hh_paths(website)
    if probed:
        if probed[0] == 'html':
            inner = _follow_for_hh(probed[1])      # the HH page may link to a PDF menu
            if inner:
                return inner[0], inner[1], f'HH menu inside {probed[1]}'
        return probed[0], probed[1], f'guessed HH path {probed[1]}'

    # 2) follow up to 3 generic menu pages, looking for a happy-hour link inside.
    menus = _menu_links(links)
    for murl in [u for u in menus if not u.lower().endswith('.pdf')][:3]:
        inner = _follow_for_hh(murl)
        if inner:
            return inner[0], inner[1], f'HH link inside {murl}'

    # 3) only a generic menu (no HH section) — exclude from the map for now.
    if menus:
        return 'menu_only', menus[0], 'menu only — no happy-hour section'

    # 4) nothing menu-like — homepage only.
    return 'homepage', website, 'no menu/HH link found'


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
    cur = db.bars.find(q, {'Name': 1, 'Website': 1, 'Yelp Alias': 1, 'Categories': 1})
    if args.limit:
        cur = cur.limit(args.limit)

    found = homepage = skipped = errors = 0
    for bar in cur:
        name, website = bar.get('Name'), bar.get('Website')

        # Skip venues that clearly aren't bars (coffee roasters, dog runs, …).
        if not is_probably_bar(bar):
            skipped += 1
            print(f'[skip-nonbar] {name}')
            continue

        try:
            stype, surl, note = find_source(website)
            if stype in ('homepage', 'menu_only'):
                # No happy-hour-specific source — record but mark excluded so the
                # map only shows real HH menus (revisit in a later pass).
                doc = {'bar_name': name, 'yelp_alias': bar.get('Yelp Alias'), 'website': website,
                       'source_type': stype, 'source_url': surl, 'menu_text': '',
                       'status': stype, 'note': note,
                       'hh_times_raw': None, 'hh_days': None, 'hh_start': None, 'hh_end': None}
                homepage += 1
                tag = 'homepage ' if stype == 'homepage' else 'menu-only'
                print(f'[{tag}] {name:<34} ({note} — excluded from map)')
            else:
                text = extract_text(stype, surl) if surl else ''
                times = parse_hh_times(text)
                doc = {
                    'bar_name': name, 'yelp_alias': bar.get('Yelp Alias'), 'website': website,
                    'source_type': stype, 'source_url': surl,
                    'menu_text': (text or '')[:20000],   # cap stored text
                    'status': 'found' if text else 'no_source', 'note': note, **times,
                }
                if text:
                    found += 1
                print(f'[{doc["status"]:9}] {name:<34} {stype or "-":>4}  {surl or note or ""}'
                      + (f'   ⏰ {times["hh_times_raw"]}' if times.get('hh_times_raw') else ''))
            if not args.dry_run:
                db.happy_hours.update_one({'bar_name': name}, {'$set': doc}, upsert=True)
        except Exception as e:
            errors += 1
            print(f'[error    ] {name:<34} {e}', file=sys.stderr)
            if not args.dry_run:
                db.happy_hours.update_one(
                    {'bar_name': name},
                    {'$set': {'bar_name': name, 'website': website, 'status': 'error', 'note': str(e)[:200]}},
                    upsert=True)
        time.sleep(args.sleep)

    print(f'\nPass 1 complete — HH sources found: {found}, excluded (homepage/menu-only): {homepage}, '
          f'non-bars skipped: {skipped}, errors: {errors}'
          + ('  (dry run, nothing written)' if args.dry_run else ''))


if __name__ == '__main__':
    main()
