"""
pass2_extract.py  —  Happy Hour pipeline, PASS 2 (read + normalize).

Reads each `happy_hours` doc's raw `menu_text`, pulls out (item, price) lines,
and runs each through DrinkNormalizer to get a category + normalized item
("Sam Adams Lager" -> beer/Lager, "Lime Margarita" -> cocktail/Margarita).
Writes one document per item to `happy_hour_items`, flagging low-confidence
rows (needs_review=True) for the admin dashboard.

Usage:
  python pass2_extract.py                  # all bars with status=found
  python pass2_extract.py --bar "Fado"
  python pass2_extract.py --dry-run        # print, write nothing
  python pass2_extract.py --self-test      # run on a built-in sample menu (no DB)

Requires: pymongo (except --self-test). Normalizer needs only the stdlib.
"""

import argparse
import re
import sys

from drink_normalizer import DrinkNormalizer

PRICE_MIN, PRICE_MAX = 1.0, 60.0   # ignore stray numbers / food platters / typos

# Preferred: an explicit dollar price anywhere ("Sam Adams Lager .... $5").
DOLLAR_RE = re.compile(r'^(?P<item>.*?[A-Za-z].*?)[\s.\-–—]*\$\s*(?P<price>\d{1,3}(?:\.\d{1,2})?)\b')
# Fallback: a bare price at end of line after a separator ("Margarita — 9", "Prosecco  8").
# Restricted to 1-2 digit (optionally .NN) numbers to avoid catching ABV/sizes.
TRAILING_RE = re.compile(r'^(?P<item>.*?[A-Za-z].*?)\s*(?:[-–—:]|\.{2,}|\s{2,})\s*(?P<price>\d{1,2}(?:\.\d{2})?)\s*$')


def _match_line(line):
    return DOLLAR_RE.match(line) or (TRAILING_RE.match(line) if '$' not in line else None)


def extract_items(text):
    """Yield (raw_item, price_float) from raw menu text."""
    seen = set()
    for raw_line in (text or '').splitlines():
        line = raw_line.strip()
        m = _match_line(line)
        if not m:
            continue
        item = re.sub(r'\s{2,}', ' ', m.group('item')).strip(' .-–—\t')
        try:
            price = float(m.group('price'))
        except ValueError:
            continue
        if not item or len(item) < 3 or not (PRICE_MIN <= price <= PRICE_MAX):
            continue
        key = (item.lower(), price)
        if key in seen:
            continue
        seen.add(key)
        yield item, price


def process_text(norm, text, time_window=None):
    rows = []
    for raw_item, price in extract_items(text):
        n = norm.normalize(raw_item)
        rows.append({
            'raw_item': raw_item,
            'hh_price': price,
            'category': n['category'],
            'normalized_item': n['normalized_item'],
            'confidence': n['confidence'],
            'needs_review': n['needs_review'],
            'time_window': time_window,
        })
    return rows


SAMPLE_MENU = """
HAPPY HOUR  —  Mon-Fri 4-6pm
Draft Beers
Yards Philly Pale Ale  $5
Miller Lite Bottle ........ $4
Dogfish Head 60 Min IPA  $6
Wine
House Cabernet  $7
Glass of Prosecco — 8
Cocktails
Lime Margarita  $9
Espresso Martini   $12
Aperol Spritz  $10
Food
1/2 Price Wings  $7
Truly Hard Seltzer  $5
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--bar', type=str, default=None)
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--self-test', action='store_true')
    args = ap.parse_args()

    norm = DrinkNormalizer()

    if args.self_test:
        rows = process_text(norm, SAMPLE_MENU, time_window='Mon-Fri 4-6pm')
        print(f'{"RAW":<34} {"CATEGORY":<9} {"NORMALIZED":<20} PRICE  CONF  REVIEW')
        print('-' * 84)
        for r in rows:
            print(f'{r["raw_item"]:<34} {r["category"]:<9} {str(r["normalized_item"]):<20} '
                  f'${r["hh_price"]:<5} {r["confidence"]:<5} {"!" if r["needs_review"] else ""}')
        print(f'\n{len(rows)} items extracted from sample (no DB writes).')
        return

    from db import get_db
    db = get_db()
    q = {'status': 'found'}
    if args.bar:
        q['bar_name'] = {'$regex': re.escape(args.bar), '$options': 'i'}

    total = flagged = 0
    for hh in db.happy_hours.find(q):
        rows = process_text(norm, hh.get('menu_text', ''), hh.get('hh_times_raw'))
        for r in rows:
            r['bar_name'] = hh.get('bar_name')
            r['source_url'] = hh.get('source_url')
            total += 1
            flagged += 1 if r['needs_review'] else 0
            if not args.dry_run:
                db.happy_hour_items.update_one(
                    {'bar_name': r['bar_name'], 'raw_item': r['raw_item'], 'hh_price': r['hh_price']},
                    {'$set': r}, upsert=True)
        print(f'{hh.get("bar_name"):<34} {len(rows):>3} items')

    print(f'\nPass 2 complete — items: {total}, flagged for review: {flagged}'
          + ('  (dry run, nothing written)' if args.dry_run else ''))


if __name__ == '__main__':
    main()
