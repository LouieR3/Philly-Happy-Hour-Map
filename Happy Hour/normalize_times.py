"""
normalize_times.py — clean happy_hours day/time data into one canonical shape.

The pipeline stores happy-hour timing in a few shapes (structured hh_days_list +
hh_start/hh_end, a loose hh_days string, or only free-text hh_times_raw). This
rewrites each doc so the stored data is consistent and filterable:

    hh_days_list : ["mon","tue","wed","thu","fri"]   # canonical, ordered
    hh_days      : "mon,tue,wed,thu,fri"             # back-compat string
    hh_start     : "16:00"   hh_end: "18:00"         # 24h, or null
    hh_time_label: "Mon-Fri - 4:00-6:00 PM"          # clean display string

Anything that isn't a real day-range or time-range is dropped (set to null/[]).
This mirrors normalizeHHTime() in server.js, so the map filters the same way
whether or not you've run this — running it just makes the stored docs clean.

Usage:
    python normalize_times.py --self-test     # offline parser checks, no DB
    python normalize_times.py --dry-run        # show changes, write nothing
    python normalize_times.py                  # write canonical fields back
"""

import argparse
import re
import sys

DAYS = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']
DAY_ALIASES = {
    'mon': 'mon', 'monday': 'mon', 'tue': 'tue', 'tues': 'tue', 'tuesday': 'tue',
    'wed': 'wed', 'weds': 'wed', 'wednesday': 'wed', 'thu': 'thu', 'thur': 'thu',
    'thurs': 'thu', 'thursday': 'thu', 'fri': 'fri', 'friday': 'fri',
    'sat': 'sat', 'saturday': 'sat', 'sun': 'sun', 'sunday': 'sun',
}
DAY_CAP = {'mon': 'Mon', 'tue': 'Tue', 'wed': 'Wed', 'thu': 'Thu', 'fri': 'Fri', 'sat': 'Sat', 'sun': 'Sun'}


def _canon_day(tok):
    t = str(tok or '').strip().lower().rstrip('.')
    return DAY_ALIASES.get(t) or DAY_ALIASES.get(t[:3])


def _expand_range(a, b):
    ia, ib = DAYS.index(a), DAYS.index(b)
    out, i = [], ia
    for _ in range(7):
        out.append(DAYS[i])
        if i == ib:
            break
        i = (i + 1) % 7
    return out


def parse_days(value):
    if isinstance(value, (list, tuple)):
        found = {d for d in (_canon_day(x) for x in value) if d}
        return [d for d in DAYS if d in found]
    s = str(value or '').lower()
    if not s:
        return []
    if re.search(r'dai|every\s*day|all\s*week|7\s*days|mon\s*[-–—]\s*sun', s):
        return list(DAYS)
    out = set()
    if 'weekday' in s:
        out.update(_expand_range('mon', 'fri'))
    if 'weekend' in s:
        out.update(['sat', 'sun'])
    for m in re.finditer(r'([a-z]{3,9})\s*(?:-|–|—|to|thru|through)\s*([a-z]{3,9})', s):
        a, b = _canon_day(m.group(1)), _canon_day(m.group(2))
        if a and b:
            out.update(_expand_range(a, b))
    for tok in re.split(r'[^a-z]+', s):
        d = _canon_day(tok)
        if d:
            out.add(d)
    return [d for d in DAYS if d in out]


def to_min(value):
    if value is None:
        return None
    s = str(value).strip().lower()
    if not s:
        return None
    apm = re.search(r'([ap])m?\b', s)
    ap = apm.group(1) if apm else None
    m = re.search(r'(\d{1,2}):(\d{2})', s)
    if m:
        hh, mm = int(m.group(1)), int(m.group(2))
    else:
        m = re.search(r'(\d{1,2})', s)
        if not m:
            return None
        hh, mm = int(m.group(1)), 0
    if ap == 'p' and hh < 12:
        hh += 12
    if ap == 'a' and hh == 12:
        hh = 0
    if hh > 24 or mm > 59:
        return None
    return hh * 60 + mm


def parse_time_range(raw):
    s = str(raw or '').lower()
    m = re.search(r'(\d{1,2}(?::\d{2})?)\s*([ap]m?)?\s*(?:-|–|—|to|until|til|till)\s*(\d{1,2}(?::\d{2})?)\s*([ap]m?)?', s)
    if not m:
        return None, None
    ap1 = m.group(2) or m.group(4)
    ap2 = m.group(4) or m.group(2)
    return to_min(m.group(1) + (ap1 or '')), to_min(m.group(3) + (ap2 or ''))


def fmt24(mn):
    h, m = (mn // 60) % 24, mn % 60
    return f'{h:02d}:{m:02d}'


def fmt12(mn):
    if mn >= 1440:
        return '12:00 AM'
    h, m = (mn // 60) % 24, mn % 60
    ap = 'PM' if h >= 12 else 'AM'
    h = h % 12 or 12
    return f'{h}:{m:02d} {ap}'


def days_label(days):
    if not days:
        return ''
    if len(days) == 7:
        return 'Daily'
    idx = sorted(DAYS.index(d) for d in days)
    contiguous = all(idx[i] == idx[i - 1] + 1 for i in range(1, len(idx)))
    if contiguous and len(idx) >= 3:
        return f'{DAY_CAP[DAYS[idx[0]]]}-{DAY_CAP[DAYS[idx[-1]]]}'
    return ', '.join(DAY_CAP[DAYS[i]] for i in idx)


def normalize(hh):
    """Return the canonical fields for one happy_hours doc."""
    days = parse_days(hh.get('hh_days_list') or hh.get('hh_days'))
    if not days and hh.get('hh_times_raw'):
        days = parse_days(hh.get('hh_times_raw'))

    start_min = to_min(hh.get('hh_start'))
    end_min = to_min(hh.get('hh_end'))
    if (start_min is None or end_min is None) and hh.get('hh_times_raw'):
        a, b = parse_time_range(hh.get('hh_times_raw'))
        start_min = start_min if start_min is not None else a
        end_min = end_min if end_min is not None else b

    dl = days_label(days)
    tl = f'{fmt12(start_min)}-{fmt12(end_min)}' if (start_min is not None and end_min is not None) else ''
    label = f'{dl} - {tl}' if dl and tl else (dl or tl or '')
    return {
        'hh_days_list': days,
        'hh_days': ','.join(days) if days else None,
        'hh_start': fmt24(start_min) if start_min is not None else None,
        'hh_end': fmt24(end_min) if end_min is not None else None,
        'hh_time_label': label or None,
    }


def _self_test():
    cases = [
        {'hh_days_list': ['mon', 'tue', 'wed', 'thu', 'fri'], 'hh_start': '16:00', 'hh_end': '18:00'},
        {'hh_days': 'Mon-Fri', 'hh_times_raw': '4-6pm'},
        {'hh_times_raw': 'Every day 4:30pm-6:30pm'},
        {'hh_days': 'weekdays', 'hh_times_raw': 'happy hour 3 to 7 pm'},
        {'hh_times_raw': 'Mon, Wed, Fri 5-7pm'},
        {'hh_times_raw': 'come visit us'},   # no real time → dropped
    ]
    for c in cases:
        print(repr(c), '->', normalize(c))
    assert normalize(cases[0])['hh_time_label'] == 'Mon-Fri - 4:00 PM-6:00 PM'
    assert normalize(cases[1])['hh_days_list'] == ['mon', 'tue', 'wed', 'thu', 'fri']
    assert normalize(cases[1])['hh_start'] == '16:00' and normalize(cases[1])['hh_end'] == '18:00'
    assert normalize(cases[2])['hh_days_list'] == DAYS
    assert normalize(cases[3])['hh_start'] == '15:00' and normalize(cases[3])['hh_end'] == '19:00'
    assert normalize(cases[4])['hh_days_list'] == ['mon', 'wed', 'fri']
    assert normalize(cases[5])['hh_days_list'] == [] and normalize(cases[5])['hh_start'] is None
    print('\nOK (offline parser verified; no DB used).')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--self-test', action='store_true')
    args = ap.parse_args()

    if args.self_test:
        _self_test()
        return

    from db import get_db
    db = get_db()
    docs = list(db.happy_hours.find({}, {
        'bar_name': 1, 'hh_days_list': 1, 'hh_days': 1, 'hh_start': 1, 'hh_end': 1, 'hh_times_raw': 1,
    }))
    changed = 0
    for d in docs:
        norm = normalize(d)
        if any(d.get(k) != v for k, v in norm.items()):
            changed += 1
            label = norm['hh_time_label'] or '(no time)'
            print(f'{d.get("bar_name", "?"):<32} -> {label}')
            if not args.dry_run:
                db.happy_hours.update_one({'_id': d['_id']}, {'$set': norm})
    print(f'\n{changed}/{len(docs)} docs {"would change" if args.dry_run else "updated"}.')


if __name__ == '__main__':
    main()
