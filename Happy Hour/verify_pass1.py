"""
verify_pass1.py — inspect what pass 1 wrote to the `happy_hours` collection.

Usage:
  python verify_pass1.py                 # summary + a few samples
  python verify_pass1.py --status found  # only docs with that status
  python verify_pass1.py --with-times    # only docs where HH times were parsed
  python verify_pass1.py --sample 20     # how many sample docs to print
"""

import argparse
from db import get_db


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--status', default=None)
    ap.add_argument('--with-times', action='store_true')
    ap.add_argument('--sample', type=int, default=10)
    args = ap.parse_args()

    db = get_db()
    hh = db.happy_hours

    total = hh.count_documents({})
    print(f'happy_hours: {total} docs total\n')

    print('by status:')
    for row in hh.aggregate([{'$group': {'_id': '$status', 'n': {'$sum': 1}}}, {'$sort': {'n': -1}}]):
        print(f'   {row["_id"] or "(none)":<12} {row["n"]}')

    print('\nby source_type:')
    for row in hh.aggregate([{'$group': {'_id': '$source_type', 'n': {'$sum': 1}}}, {'$sort': {'n': -1}}]):
        print(f'   {row["_id"] or "(none)":<12} {row["n"]}')

    with_times = hh.count_documents({'hh_times_raw': {'$nin': [None, '']}})
    with_text = hh.count_documents({'menu_text': {'$nin': [None, '']}})
    print(f'\nwith parsed HH times: {with_times}')
    print(f'with menu text:       {with_text}')

    q = {}
    if args.status:
        q['status'] = args.status
    if args.with_times:
        q['hh_times_raw'] = {'$nin': [None, '']}

    print(f'\n--- {args.sample} sample docs ---')
    for d in hh.find(q).limit(args.sample):
        print(f'\n• {d.get("bar_name")}')
        print(f'    status:  {d.get("status")}   source: {d.get("source_type")}')
        print(f'    url:     {d.get("source_url")}')
        if d.get('hh_times_raw'):
            print(f'    ⏰ times: {d.get("hh_times_raw")}')
        txt = (d.get('menu_text') or '').strip().replace('\n', ' ')
        if txt:
            print(f'    text:    {txt[:140]}…  ({len(d.get("menu_text"))} chars)')

    print('\nTip: also run  python pass2_extract.py --dry-run  to preview extracted items,')
    print('or open the collection in MongoDB Atlas / Compass.')


if __name__ == '__main__':
    main()
