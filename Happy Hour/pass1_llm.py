"""
pass1_llm.py — Happy Hour PASS 1, LLM-driven (the accurate path).

For each bar: render the homepage with Playwright, let Claude pick the correct
happy-hour link (or say there isn't one), render that page, then let Claude
extract the structured happy-hour day/time window. Everything is stored with a
confidence score and provenance (the links it considered, its reasoning) so the
admin review queue can correct it — and those corrections feed back as few-shot
examples (examples_pass1.jsonl) that make the next run smarter.

Writes one doc per bar to `happy_hours` with structured days/times so the map's
day/time filter is exact:
    hh_days_list: ["mon","tue","wed","thu","fri"]   # precise filtering
    hh_days:      "mon,tue,wed,thu,fri"              # back-compat string for the current map filter
    hh_start:     "16:00"   hh_end: "18:00"   hh_times_raw: "Mon-Fri 4-6pm"
    confidence, needs_review, llm_reason, candidates (provenance)

Usage:
    pip install playwright anthropic && python -m playwright install chromium
    export ANTHROPIC_API_KEY=...   export MONGODB_URI=...

    python pass1_llm.py --limit 30            # small batch (recommended to start)
    python pass1_llm.py --bar "Bellini"       # one bar
    python pass1_llm.py --limit 30 --dry-run  # decide + print, write nothing
    python pass1_llm.py --self-test           # offline: candidate/resolve plumbing, no network/LLM
"""

import argparse
import json
import os
import re
import sys
import time
from urllib.parse import urljoin, urlparse

EXAMPLES_FILE = os.path.join(os.path.dirname(__file__), 'examples_pass1.jsonl')

# Links we never want as a happy-hour source.
SKIP_HREF = ('mailto:', 'tel:', '#', 'javascript:')
SKIP_DOMAINS = ('facebook.com', 'instagram.com', 'twitter.com', 'x.com', 'tiktok.com',
                'yelp.com', 'google.com', 'maps.', 'doordash.com', 'ubereats.com',
                'grubhub.com', 'opentable.com', 'resy.com', 'youtube.com', 'linkedin.com')

DAYS = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']

# Neighborhood gating. Bars have no stored neighborhood — the map buckets them by
# point-in-polygon against this GeoJSON (LISTNAME), so --neighborhood does the same.
NEIGHBORHOODS_GEOJSON = os.path.join(
    os.path.dirname(__file__), '..', 'public', 'assets', 'philadelphia-neighborhoods.geojson')


def _ring_contains(ring, x, y):
    """Ray-casting: is point (x=lon, y=lat) inside this single ring?"""
    inside, j = False, len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


def _poly_contains(rings, x, y):
    # First ring is the outer boundary; any further rings are holes.
    return bool(rings) and _ring_contains(rings[0], x, y) and \
        not any(_ring_contains(h, x, y) for h in rings[1:])


def _geom_contains(geom, x, y):
    t = (geom or {}).get('type')
    if t == 'Polygon':
        return _poly_contains(geom['coordinates'], x, y)
    if t == 'MultiPolygon':
        return any(_poly_contains(p, x, y) for p in geom['coordinates'])
    return False


def load_neighborhood(name, path=NEIGHBORHOODS_GEOJSON):
    """Geometries for features whose LISTNAME matches `name` (case-insensitive substring)."""
    with open(path, encoding='utf-8') as f:
        gj = json.load(f)
    want = name.strip().lower()
    geoms = [ft['geometry'] for ft in gj.get('features', [])
             if want in (ft.get('properties', {}).get('LISTNAME') or '').lower()]
    if not geoms:
        raise SystemExit(f'No neighborhood LISTNAME matching {name!r} in {os.path.basename(path)}')
    return geoms


def bar_in_geoms(bar, geoms):
    """True if the bar's stored lat/long falls inside any of the geometries."""
    try:
        lon, lat = float(bar.get('Longitude')), float(bar.get('Latitude'))
    except (TypeError, ValueError):
        return False  # missing/blank coords → can't place it, so exclude
    return any(_geom_contains(g, lon, lat) for g in geoms)

# ── Structured-output schemas ────────────────────────────────────────────────
SOURCE_SCHEMA = {
    'type': 'object', 'additionalProperties': False,
    'properties': {
        'has_happy_hour': {'type': 'boolean',
                           'description': 'Does this bar appear to offer a happy hour at all?'},
        'on_homepage': {'type': 'boolean',
                        'description': 'Are the happy-hour details on the homepage text itself?'},
        'chosen_index': {'type': 'integer',
                         'description': 'Index of the best happy-hour link in the candidate list, or -1 if none fits.'},
        'guessed_path': {'type': 'string',
                         'description': "A likely path not in the list (e.g. '/happy-hour'), else empty string."},
        'source_type': {'type': 'string', 'enum': ['html', 'pdf', 'image', 'none']},
        'confidence': {'type': 'number', 'description': '0.0–1.0 confidence in this choice.'},
        'reason': {'type': 'string', 'description': 'One sentence: why this link / why none.'},
    },
    'required': ['has_happy_hour', 'on_homepage', 'chosen_index', 'guessed_path',
                 'source_type', 'confidence', 'reason'],
}

TIME_SCHEMA = {
    'type': 'object', 'additionalProperties': False,
    'properties': {
        'is_happy_hour': {'type': 'boolean',
                          'description': 'Does this page actually describe a happy hour (not a regular menu)?'},
        'days': {'type': 'array', 'items': {'type': 'string', 'enum': DAYS},
                 'description': 'Days the happy hour runs.'},
        'start': {'type': 'string', 'description': "Start time 24h 'HH:MM', or '' if unknown."},
        'end': {'type': 'string', 'description': "End time 24h 'HH:MM', or '' if unknown."},
        'raw': {'type': 'string', 'description': "The time window as written, e.g. 'Mon-Fri 4-6pm'."},
        'confidence': {'type': 'number'},
        'notes': {'type': 'string'},
    },
    'required': ['is_happy_hour', 'days', 'start', 'end', 'raw', 'confidence', 'notes'],
}


# ── Candidate links ───────────────────────────────────────────────────────────
def build_candidates(links, limit=45):
    """Dedupe/clean rendered links into a numbered candidate list for the LLM."""
    seen, out = set(), []
    for ln in links or []:
        href = (ln.get('href') or '').strip()
        if not href or href.startswith(SKIP_HREF):
            continue
        low = href.lower()
        if any(d in low for d in SKIP_DOMAINS):
            continue
        if href in seen:
            continue
        seen.add(href)
        out.append({'text': (ln.get('text') or '').strip(), 'href': href})
        if len(out) >= limit:
            break
    return out


def _load_examples(path=EXAMPLES_FILE, n=8):
    """Few-shot examples from prior human-verified corrections (the learning loop)."""
    try:
        with open(path, encoding='utf-8') as f:
            rows = [json.loads(line) for line in f if line.strip()]
        return rows[-n:]
    except FileNotFoundError:
        return []


def find_source_messages(bar, homepage_text, candidates, examples):
    cand_lines = '\n'.join(f'[{i}] {c["text"][:70]!r} -> {c["href"]}' for i, c in enumerate(candidates))
    ex_block = ''
    if examples:
        ex_block = '\nVerified examples from past corrections (learn the patterns):\n' + \
                   '\n'.join('- ' + json.dumps(e, ensure_ascii=False) for e in examples) + '\n'
    system = (
        "You locate a bar's HAPPY HOUR menu/info page. You are given a homepage's visible text and "
        "its links. Choose the single best link to the happy-hour deals (days/times and/or HH menu). "
        "Prefer a page specifically about happy hour over a generic full menu. If the HH info is on the "
        "homepage itself, set on_homepage. If you believe a standard path exists that isn't linked "
        "(e.g. /happy-hour), put it in guessed_path. If the bar has no happy hour, set has_happy_hour=false."
    )
    user = (
        f"Bar: {bar.get('Name')}\nWebsite: {bar.get('Website')}\n{ex_block}\n"
        f"HOMEPAGE TEXT (truncated):\n{(homepage_text or '')[:4000]}\n\n"
        f"CANDIDATE LINKS:\n{cand_lines or '(none)'}\n"
    )
    return system, user


def resolve_source(decision, candidates, website):
    """Turn the LLM decision into (source_type, source_url, on_homepage)."""
    if not decision.get('has_happy_hour'):
        return 'none', '', False
    if decision.get('on_homepage'):
        return 'html', website, True
    idx = decision.get('chosen_index', -1)
    url = ''
    if isinstance(idx, int) and 0 <= idx < len(candidates):
        url = candidates[idx]['href']
    elif decision.get('guessed_path'):
        p = urlparse(website)
        url = urljoin(f'{p.scheme}://{p.netloc}', decision['guessed_path'])
    if not url:
        return 'none', '', False
    stype = 'pdf' if url.lower().endswith('.pdf') else (decision.get('source_type') or 'html')
    if stype not in ('html', 'pdf', 'image'):
        stype = 'html'
    return stype, url, False


def extract_messages(text):
    system = (
        "You read a happy-hour page and extract the day/time window. Return the days the happy hour runs, "
        "start and end times in 24-hour HH:MM, and the raw text. If the page is a regular menu with no "
        "happy hour, set is_happy_hour=false. Only report times you can actually find."
    )
    user = f"PAGE TEXT (truncated):\n{(text or '')[:6000]}\n"
    return system, user


# ── LLM call (structured output) ──────────────────────────────────────────────
# Backend is chosen by LLM_PROVIDER (default: local Ollama — no token cost).
from llm_client import complete_json


def _pdf_text(url):
    import requests, fitz  # PyMuPDF
    data = requests.get(url, timeout=20, headers={'User-Agent': 'MappyHourBot/1.0'}).content
    doc = fitz.open(stream=data, filetype='pdf')
    return '\n'.join(page.get_text() for page in doc)


def process_bar(ctx, bar, examples):
    import fetcher
    website = bar.get('Website')
    home = fetcher.render(ctx, website)
    candidates = build_candidates(home['links'])

    decision = complete_json(*find_source_messages(bar, home['text'], candidates, examples), SOURCE_SCHEMA)
    stype, surl, on_home = resolve_source(decision, candidates, website)
    base = {
        'bar_name': bar.get('Name'), 'yelp_alias': bar.get('Yelp Alias'), 'website': website,
        'source_type': stype, 'source_url': surl, 'on_homepage': on_home,
        'has_happy_hour': bool(decision.get('has_happy_hour')),
        'find_confidence': decision.get('confidence'),
        'llm_reason': decision.get('reason'),
        'candidates': [c['href'] for c in candidates],   # provenance for review/learning
    }

    if stype == 'none':
        base.update(status='no_happy_hour', needs_review=False, menu_text='',
                    hh_days=None, hh_days_list=[], hh_start=None, hh_end=None, hh_times_raw=None)
        return base

    # Get the source text (rendered HTML, PDF, or homepage we already have).
    if on_home:
        src_text, surl = home['text'], website
    elif stype == 'pdf':
        src_text = _pdf_text(surl)
    else:
        rendered = fetcher.render(ctx, surl)
        src_text, surl = rendered['text'], rendered['final_url']
        base['source_url'] = surl

    ext = complete_json(*extract_messages(src_text), TIME_SCHEMA)
    days = [d for d in (ext.get('days') or []) if d in DAYS]
    conf = round(min(float(decision.get('confidence', 0.5)), float(ext.get('confidence', 0.5))), 2)
    base.update(
        status='found' if ext.get('is_happy_hour') else 'uncertain',
        menu_text=(src_text or '')[:20000],
        hh_days=','.join(days) or None,        # back-compat string for the current map filter
        hh_days_list=days,                      # structured, for exact day filtering
        hh_start=ext.get('start') or None,
        hh_end=ext.get('end') or None,
        hh_times_raw=ext.get('raw') or None,
        confidence=conf,
        extract_notes=ext.get('notes'),
        needs_review=(conf < 0.7) or (not ext.get('is_happy_hour')),
    )
    return base


# ── CLI ───────────────────────────────────────────────────────────────────────
def _self_test():
    sample_links = [
        {'text': 'Home', 'href': 'https://bar.test/'},
        {'text': 'Happy Hour', 'href': 'https://bar.test/happy-hour'},
        {'text': 'Order on DoorDash', 'href': 'https://doordash.com/store/123'},
        {'text': 'Menus', 'href': 'https://bar.test/menus'},
        {'text': 'Happy Hour', 'href': 'https://bar.test/happy-hour'},  # dup
    ]
    cands = build_candidates(sample_links)
    print('candidates (social/dupe filtered):')
    for i, c in enumerate(cands):
        print(f'  [{i}] {c["text"]!r} -> {c["href"]}')
    for label, decision in [
        ('chose HH link', {'has_happy_hour': True, 'on_homepage': False, 'chosen_index': 1,
                           'guessed_path': '', 'source_type': 'html'}),
        ('guessed path',  {'has_happy_hour': True, 'on_homepage': False, 'chosen_index': -1,
                           'guessed_path': '/happy-hour', 'source_type': 'html'}),
        ('on homepage',   {'has_happy_hour': True, 'on_homepage': True, 'chosen_index': -1,
                           'guessed_path': '', 'source_type': 'html'}),
        ('no happy hour', {'has_happy_hour': False, 'on_homepage': False, 'chosen_index': -1,
                           'guessed_path': '', 'source_type': 'none'}),
    ]:
        print(f'resolve_source [{label}] ->', resolve_source(decision, cands, 'https://bar.test/'))
    s, u = find_source_messages({'Name': 'Test Bar', 'Website': 'https://bar.test/'},
                                'Welcome to Test Bar. Happy hour daily!', cands, _load_examples())
    print('\n--- find_source prompt (user) ---\n' + u[:600])

    # Point-in-polygon: unit square contains its center, excludes an outside point.
    square = {'type': 'Polygon', 'coordinates': [[[0, 0], [0, 1], [1, 1], [1, 0], [0, 0]]]}
    assert _geom_contains(square, 0.5, 0.5) and not _geom_contains(square, 2, 2)
    print('\npoint-in-polygon: unit-square center inside / outside excluded -> OK')

    # Real geojson: Rittenhouse loads, and Rittenhouse Square (-75.1718, 39.9496) is inside it.
    try:
        geoms = load_neighborhood('Rittenhouse')
        center = {'Latitude': '39.9496', 'Longitude': '-75.1718'}
        far = {'Latitude': '39.9526', 'Longitude': '-75.1182'}  # ~Old City, outside
        print(f"Rittenhouse: {len(geoms)} geom(s); square center inside={bar_in_geoms(center, geoms)}, "
              f"Old City point inside={bar_in_geoms(far, geoms)}")
    except (SystemExit, FileNotFoundError) as e:
        print(f'(skipped real-geojson check: {e})')

    print('\nOK (offline plumbing verified; no network/LLM used).')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--limit', type=int, default=0)
    ap.add_argument('--bar', type=str, default=None)
    ap.add_argument('--neighborhood', type=str, default=None,
                    help='Only bars inside this neighborhood LISTNAME (e.g. "Rittenhouse").')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--sleep', type=float, default=0.0)
    ap.add_argument('--self-test', action='store_true')
    ap.add_argument('--check-llm', action='store_true',
                    help='Send one tiny structured prompt through the configured backend and exit.')
    args = ap.parse_args()

    if args.self_test:
        _self_test()
        return

    import llm_client
    print(f'LLM backend: {llm_client.provider_info()}')

    try:
        llm_client.preflight()   # fail fast with a clear message before rendering anything
    except RuntimeError as e:
        print(e, file=sys.stderr)
        sys.exit(1)

    if args.check_llm:
        out = llm_client.complete_json(
            'Reply only with structured JSON.',
            'Is "Mon-Fri 4-6pm" a happy hour? Give days, start, end (24h), raw, confidence, notes.',
            TIME_SCHEMA)
        print('check-llm OK ->', json.dumps(out, ensure_ascii=False))
        return

    import fetcher
    from db import get_db
    db = get_db()
    examples = _load_examples()

    q = {'Website': {'$nin': [None, '']}}
    if args.bar:
        q['Name'] = {'$regex': re.escape(args.bar), '$options': 'i'}
    # Latitude/Longitude are needed only when gating by neighborhood.
    bars = list(db.bars.find(q, {'Name': 1, 'Website': 1, 'Yelp Alias': 1,
                                 'Latitude': 1, 'Longitude': 1}))
    if args.neighborhood:
        geoms = load_neighborhood(args.neighborhood)
        bars = [b for b in bars if bar_in_geoms(b, geoms)]
        print(f'{len(bars)} bar(s) with a website inside neighborhood {args.neighborhood!r}')
    if args.limit:
        bars = bars[:args.limit]  # cap AFTER the neighborhood filter

    found = uncertain = none = errors = 0
    with fetcher.browser_session() as ctx:
        for bar in bars:
            name = bar.get('Name')
            try:
                doc = process_bar(ctx, bar, examples)
                st = doc['status']
                found += st == 'found'
                uncertain += st == 'uncertain'
                none += st == 'no_happy_hour'
                flag = ' ⚠review' if doc.get('needs_review') else ''
                print(f'[{st:13}] {name:<32} conf={doc.get("confidence", "-")} '
                      f'{doc.get("source_url") or doc.get("llm_reason", "")}{flag}'
                      + (f'  ⏰ {doc["hh_times_raw"]}' if doc.get('hh_times_raw') else ''))
                if not args.dry_run:
                    db.happy_hours.update_one({'bar_name': name}, {'$set': doc}, upsert=True)
            except Exception as e:
                errors += 1
                print(f'[error        ] {name:<32} {e}', file=sys.stderr)
                if not args.dry_run:
                    db.happy_hours.update_one(
                        {'bar_name': name},
                        {'$set': {'bar_name': name, 'website': bar.get('Website'),
                                  'status': 'error', 'llm_reason': str(e)[:200], 'needs_review': True}},
                        upsert=True)
            time.sleep(args.sleep)

    print(f'\nPass 1 (LLM) complete — found: {found}, uncertain: {uncertain}, '
          f'no HH: {none}, errors: {errors}'
          + ('  (dry run, nothing written)' if args.dry_run else ''))


if __name__ == '__main__':
    main()
