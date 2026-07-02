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


def split_segments(raw):
    """Free text → candidate segments (lines, pipe/semicolon/bullet-separated)."""
    return [p.strip() for p in re.split(r'[\n|;•·]+', str(raw or '')) if p.strip()]


def parse_windows(raw):
    """Best-effort MULTI-window parse of free text. Pairs day expressions with
    time ranges segment by segment; a window's days and times may sit on the
    same segment ("Mon-Fri 4-6pm") or adjacent lines (time first, days after —
    the American Sardine layout). Returns [{'days', 'start_min', 'end_min'}]."""
    wins = []
    pend_days = pend_time = None
    for seg in split_segments(raw):
        d = parse_days(seg)
        t = parse_time_range(seg)
        t = t if (t[0] is not None and t[1] is not None) else None
        if d and t:
            wins.append({'days': d, 'start_min': t[0], 'end_min': t[1]})
            pend_days = pend_time = None
        elif t:
            if pend_days:
                wins.append({'days': pend_days, 'start_min': t[0], 'end_min': t[1]})
                pend_days = None
            else:
                pend_time = t
        elif d:
            if pend_time:
                wins.append({'days': d, 'start_min': pend_time[0], 'end_min': pend_time[1]})
                pend_time = None
            else:
                pend_days = d
    return wins


def _win_label(days, start_min, end_min):
    dl = days_label(days)
    tl = f'{fmt12(start_min)}-{fmt12(end_min)}' if (start_min is not None and end_min is not None) else ''
    return f'{dl} - {tl}' if dl and tl else (dl or tl or '')


def normalize(hh):
    """Return the canonical fields for one happy_hours doc (multi-window)."""
    # 1) Windows stored by the LLM pass (authoritative when present).
    wins = []
    for w in (hh.get('hh_windows') or []):
        days = parse_days(w.get('days'))
        s, e = to_min(w.get('start')), to_min(w.get('end'))
        if days or (s is not None and e is not None):
            wins.append({'days': days, 'start_min': s, 'end_min': e})

    # 2) Legacy single-window fields.
    if not wins:
        days = parse_days(hh.get('hh_days_list') or hh.get('hh_days'))
        s, e = to_min(hh.get('hh_start')), to_min(hh.get('hh_end'))
        if days or (s is not None and e is not None):
            wins = [{'days': days, 'start_min': s, 'end_min': e}]

    # 3) Free text — use it when it reveals MORE windows than the fields did,
    #    or fills a gap (no windows / missing times).
    raw_wins = parse_windows(hh.get('hh_times_raw'))
    if len(raw_wins) > len(wins):
        wins = raw_wins
    elif wins and raw_wins and wins[0]['start_min'] is None:
        wins = raw_wins

    # Windows still missing times (e.g. days came from fields, time only in raw
    # text with no day tokens like "4-6pm") → fill from the raw text's range.
    if any(w['start_min'] is None or w['end_min'] is None for w in wins):
        a, b = parse_time_range(hh.get('hh_times_raw'))
        if a is not None and b is not None:
            for w in wins:
                if w['start_min'] is None:
                    w['start_min'] = a
                if w['end_min'] is None:
                    w['end_min'] = b

    primary = wins[0] if wins else {'days': [], 'start_min': None, 'end_min': None}
    label = '; '.join(filter(None, (_win_label(w['days'], w['start_min'], w['end_min']) for w in wins)))
    return {
        'hh_windows': [{'days': w['days'],
                        'start': fmt24(w['start_min']) if w['start_min'] is not None else None,
                        'end': fmt24(w['end_min']) if w['end_min'] is not None else None}
                       for w in wins],
        'hh_days_list': primary['days'],
        'hh_days': ','.join(primary['days']) if primary['days'] else None,
        'hh_start': fmt24(primary['start_min']) if primary['start_min'] is not None else None,
        'hh_end': fmt24(primary['end_min']) if primary['end_min'] is not None else None,
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

    # Multi-window: American Sardine layout (time line, then days line, twice).
    sardine = {'hh_times_raw': 'Happy Hour\n4pm to 6pm\nMonday thru Friday\n'
                               'Late Nite Happy Hour\n10pm to 12am\nMonday and Tuesday'}
    n = normalize(sardine)
    print('\nsardine ->', n)
    assert len(n['hh_windows']) == 2
    assert n['hh_windows'][0] == {'days': ['mon', 'tue', 'wed', 'thu', 'fri'], 'start': '16:00', 'end': '18:00'}
    assert n['hh_windows'][1] == {'days': ['mon', 'tue'], 'start': '22:00', 'end': '00:00'}
    assert n['hh_days_list'] == ['mon', 'tue', 'wed', 'thu', 'fri']   # primary fills legacy fields

    # Multi-window: Bar Bombon pipe-separated layout (3 windows on one line).
    bombon = {'hh_times_raw': 'MON-WED 5 TO 6PM | THUR-FRI 3 TO 6PM | FRI-SAT 9-11PM'}
    n = normalize(bombon)
    print('bombon  ->', n)
    assert len(n['hh_windows']) == 3
    assert n['hh_windows'][0] == {'days': ['mon', 'tue', 'wed'], 'start': '17:00', 'end': '18:00'}
    assert n['hh_windows'][2] == {'days': ['fri', 'sat'], 'start': '21:00', 'end': '23:00'}

    # LLM-stored windows are authoritative over raw text.
    stored = {'hh_windows': [{'days': ['mon', 'fri'], 'start': '16:00', 'end': '18:00'}],
              'hh_times_raw': 'whatever 4-6pm'}
    assert normalize(stored)['hh_windows'] == [{'days': ['mon', 'fri'], 'start': '16:00', 'end': '18:00'}]

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
        'bar_name': 1, 'hh_windows': 1, 'hh_days_list': 1, 'hh_days': 1,
        'hh_start': 1, 'hh_end': 1, 'hh_times_raw': 1,
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
