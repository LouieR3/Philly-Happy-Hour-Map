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

# Section headings to ignore (they're not items). Only treated as a header when
# the line has no price — "Red $9" is an item, "WINE" alone is a heading.
SECTION_WORDS = {
    'cocktails', 'cocktail', 'wine', 'wines', 'beer', 'beers', 'draft', 'drafts',
    'draught', 'bottles', 'cans', 'bottle', 'can', 'snacks', 'food', 'bites',
    'spirits', 'drinks', 'menu', 'happy hour', 'shareables', 'starters', 'sides',
    'by the glass', 'specials', 'featured', 'seltzers', 'on tap', 'to share',
    'small plates', 'apps', 'appetizers', 'desserts',
}


def _is_caps(s):
    """True when the line is mostly uppercase — i.e. a drink/dish NAME line."""
    letters = [c for c in s if c.isalpha()]
    if len(letters) < 2:
        return False
    return sum(1 for c in letters if c.isupper()) / len(letters) >= 0.7


def _line_price(line):
    """Return (price|None, core_without_price). Strips ABV (4.1%) and a trailing
    price, so 'Philadelphia | 4.1% 5' -> (5.0, 'Philadelphia')."""
    s = re.sub(r'\d{1,2}(?:\.\d)?\s*%', ' ', line)          # drop ABV
    m = re.search(r'\$?\s*(\d{1,3}(?:\.\d{1,2})?)\s*(?:ea\.?|each|/ea)?\s*$', s.strip())
    if not m:
        return None, s.strip()
    try:
        price = float(m.group(1))
    except ValueError:
        return None, s.strip()
    core = s[:s.rstrip().rfind(m.group(0).strip())].strip(' .|-–—\t')
    return price, core


# Menus list items across several lines: an ALL-CAPS name (sometimes 2-3 lines),
# then mixed-case description/region/ABV lines, with the price at the end of the
# block. This walks line-by-line, accumulating the caps NAME until a price closes
# the item — e.g. "KENWOOD LIGHT" / "LAGER" / "Philadelphia | 4.1% 5" -> ("KENWOOD LIGHT LAGER", 5).
def extract_items(text):
    seen, out = set(), []
    name_parts, desc_seen = [], False

    def emit(name, price):
        name = re.sub(r'\s{2,}', ' ', name).strip(' .,-–—|')
        if len(name) < 2 or not (PRICE_MIN <= price <= PRICE_MAX):
            return
        key = (name.lower(), price)
        if key not in seen:
            seen.add(key)
            out.append((name, price))

    for raw in (text or '').splitlines():
        line = raw.strip()
        if not line:
            continue
        price, core = _line_price(line)
        if price is None and core.lower() in SECTION_WORDS:        # section heading
            name_parts, desc_seen = [], False
            continue
        caps = _is_caps(core)
        if price is None:
            if caps:
                if desc_seen:
                    name_parts = []                                # a new item is starting
                name_parts.append(core)
                desc_seen = False
            else:
                desc_seen = True                                   # description line
            continue
        # price found → close the current item
        if name_parts:
            if caps:
                name_parts.append(core)                            # e.g. "ARANCINI 7"
            emit(' '.join(name_parts), price)
        elif core:
            emit(core, price)                                      # inline "Margarita 9"
        name_parts, desc_seen = [], False

    for item, price in out:
        yield item, price


# Day + time window, even without the words "happy hour" nearby (the doc IS the
# HH menu): "EVERY DAY | 4:30pm—6:30pm", "Mon-Fri 4-6pm", "Daily 3 - 6 PM".
TIME_RANGE_RE = re.compile(
    r'(\d{1,2}(?::\d{2})?\s*(?:am|pm)?)\s*(?:-|–|—|to|until|til)\s*(\d{1,2}(?::\d{2})?\s*(?:am|pm)?)', re.I)
DAY_PHRASE_RE = re.compile(
    r'(every\s*day|daily|weekdays?|weekends?|'
    r'(?:mon|tue|wed|thu|fri|sat|sun)[a-z]*(?:\s*[-–—to&,/]+\s*(?:mon|tue|wed|thu|fri|sat|sun)[a-z]*)*)', re.I)


def extract_hh_time(text):
    for raw in (text or '').splitlines():
        line = raw.strip()
        m = TIME_RANGE_RE.search(line)
        if not m:
            continue
        days = DAY_PHRASE_RE.search(line)
        return {
            'hh_times_raw': line[:160],
            'hh_days': days.group(0).strip() if days else None,
            'hh_start': m.group(1).strip(),
            'hh_end': m.group(2).strip(),
        }
    return None


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

# Real multi-line PDF text (Wilder) — name on one/two caps lines, region+ABV+price
# on a later line. Exercises the block parser + time extraction.
WILDER_MENU = """
EVERY DAY | 4:30pm—6:30pm
Bar, lounge, & outside seating | No reservations
COCKTAILS
WINE
SNACKS
UV INDEX
Hpnotiq, lime, chili,
bubbles
BLENDER’S BROKEN
Rum, orange,
lime 9
CRISPY DC (N/A)
Pathfinder N/A Spirit,
red verjus, diet cola 5
KENWOOD LIGHT
LAGER
Philadelphia | 4.1% 5
TALEA “FRESH COAST”
WEST COAST IPA
Brooklyn | 6% 5
WHITE BLEND
Brisa Suave,
Vinho Verde 8
ORANGE VIOGNIER
Poppelvej,
Adelaide Hills 8
PINOT NOIR ROSÈ
D. Bosler,
Uco Valley 8
SCAMORZA STUFFED ARANCINI 7
RICOTTA & HONEY TOAST 5
SPICY MEATBALL PIZZA 12
"""


def llm_rows(data):
    """Convert an llm_extract result into happy_hour_items rows."""
    rows = []
    for it in data.get('items', []):
        cat = (it.get('category') or 'other').lower()
        price = it.get('price')
        rows.append({
            'raw_item': it.get('name', ''),
            'hh_price': price,
            'category': cat,
            'normalized_item': it.get('normalized_item') or it.get('name'),
            'confidence': 0.9,                      # LLM extraction is high-confidence
            'needs_review': cat == 'other' or price in (None, ''),
            'time_window': data.get('happy_hour_times') or None,
        })
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--bar', type=str, default=None)
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--self-test', action='store_true')
    ap.add_argument('--llm', action='store_true',
                    help='Use an LLM (default: local Ollama, no token cost) to read messy menus; '
                         'set LLM_PROVIDER to switch backends. Falls back to the heuristic parser per-bar on failure.')
    args = ap.parse_args()

    norm = DrinkNormalizer()

    if args.self_test:
        for label, menu in [('SIMPLE SAMPLE', SAMPLE_MENU), ('WILDER (multi-line PDF)', WILDER_MENU)]:
            t = extract_hh_time(menu)
            print(f'\n=== {label} ===')
            print('time:', (t.get('hh_times_raw') if t else '(none)'),
                  '| days=', (t or {}).get('hh_days'), 'start=', (t or {}).get('hh_start'), 'end=', (t or {}).get('hh_end'))
            rows = process_text(norm, menu, time_window=(t or {}).get('hh_times_raw'))
            print(f'{"RAW":<34} {"CATEGORY":<9} {"NORMALIZED":<20} PRICE  CONF REVIEW')
            print('-' * 86)
            for r in rows:
                print(f'{r["raw_item"]:<34} {r["category"]:<9} {str(r["normalized_item"]):<20} '
                      f'${r["hh_price"]:<5} {r["confidence"]:<4} {"!" if r["needs_review"] else ""}')
            print(f'{len(rows)} items')
        return

    use_llm = False
    if args.llm:
        import llm_extract
        use_llm = llm_extract.available()
        if not use_llm:
            print('[--llm requested but no LLM backend reachable (is Ollama running? `ollama pull llama3.1`); '
                  'using heuristic parser]')
        else:
            import llm_client
            print(f'[--llm using {llm_client.provider_info()}]')

    from db import get_db
    db = get_db()
    q = {'status': 'found'}
    if args.bar:
        q['bar_name'] = {'$regex': re.escape(args.bar), '$options': 'i'}

    total = flagged = timed = 0
    for hh in db.happy_hours.find(q):
        text = hh.get('menu_text', '')
        time_window = hh.get('hh_times_raw')

        # --- choose extractor: Claude (robust) or heuristic ---
        rows = None
        if use_llm:
            try:
                data = llm_extract.extract_with_llm(text, hh.get('bar_name', ''))
                rows = llm_rows(data)
                if not time_window and data.get('happy_hour_times'):
                    time_window = data['happy_hour_times']
            except Exception as e:
                print(f'  [llm failed for {hh.get("bar_name")}: {e}; falling back]', file=sys.stderr)

        # Log the HH day/time window (the user wants this captured) — from pass 1,
        # the LLM, or the heuristic time parser, whichever we have.
        if not time_window:
            t = extract_hh_time(text)
            if t:
                time_window = t['hh_times_raw']
        if time_window and not hh.get('hh_times_raw') and not args.dry_run:
            parsed = extract_hh_time(time_window) or {'hh_times_raw': time_window}
            db.happy_hours.update_one({'_id': hh['_id']}, {'$set': parsed})
            timed += 1

        if rows is None:
            rows = process_text(norm, text, time_window)
        else:
            for r in rows:
                r['time_window'] = time_window

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

    print(f'\nPass 2 complete — items: {total}, flagged for review: {flagged}, '
          f'HH times newly logged: {timed}'
          + ('  (dry run, nothing written)' if args.dry_run else ''))


if __name__ == '__main__':
    main()
