#!/usr/bin/env python3
"""
populate_sports_bars.py  —  Deliverable 2
Reads the master `bars` collection, filters for documents whose `categories`
field contains "sports bar" (case-insensitive), then upserts them into a new
`sports_bars` collection with additional sports-specific default fields.

Usage:
    MONGODB_URI="mongodb+srv://..." python populate_sports_bars.py

Idempotent:
  - Base bar fields (Name, Address, Latitude, etc.) are always synced from source.
  - Sports-specific fields (philly_affiliates, team_ids, etc.) use $setOnInsert
    so manual admin edits are never overwritten on re-run.
"""

import os
import re
import sys
from pymongo import MongoClient, UpdateOne
from pymongo.errors import BulkWriteError
from dotenv import load_dotenv

load_dotenv()
# ─── Configuration ────────────────────────────────────────────────────────────
MONGO_URI = os.getenv("MONGODB_URI", "")
DB_NAME    = "mappy_hour"
SOURCE_COL = "bars"
DEST_COL   = "sports_bars"

# Matches "sports bar", "sports_bar", "SportsBar", "sports-bar", etc.
SPORTS_BAR_RE = re.compile(r"sports[\s_\-]?bar", re.IGNORECASE)

# New fields added to sports bar documents; only written on first insert
SPORTS_DEFAULTS = {
    # Philadelphia-specific team affiliations (Eagles, Phillies, Flyers, Sixers, Union)
    "philly_affiliates":             [],
    # Non-Philly teams from the Big 4 + NHL that the bar shows
    "other_nhl_nba_mlb_nfl_teams":   [],
    # Single Premier League team (most bars only show one)
    "premier_league_team":           None,
    # Any additional soccer teams (La Liga, Bundesliga, etc.)
    "other_soccer_teams":            [],
    # ObjectId references to sports_teams documents (for joins)
    "team_ids":                      [],
}

# ─── Helpers ──────────────────────────────────────────────────────────────────

def is_sports_bar(doc: dict) -> bool:
    """Return True when any category value looks like 'sports bar'."""
    # categories may be a list of strings or a single comma-separated string
    cats = doc.get("categories") or doc.get("Categories") or []
    if isinstance(cats, str):
        cats = [c.strip() for c in cats.split(",")]
    elif not isinstance(cats, list):
        cats = [str(cats)]
    return any(SPORTS_BAR_RE.search(str(c)) for c in cats)


def build_upsert_op(bar: dict) -> UpdateOne:
    """
    Construct a bulk-write UpdateOne that:
      - Always syncs base bar fields from the master bars collection ($set)
      - Only initialises sports-specific fields on first insert ($setOnInsert)
    """
    oid = bar["_id"]
    # Everything except _id and the sports-specific defaults goes into $set
    base = {k: v for k, v in bar.items()
            if k != "_id" and k not in SPORTS_DEFAULTS}

    return UpdateOne(
        {"_id": oid},
        {
            "$set": base,
            "$setOnInsert": dict(SPORTS_DEFAULTS),  # shallow copy of defaults
        },
        upsert=True,
    )


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    if not MONGO_URI:
        print("ERROR: Set MONGODB_URI or MONGO_URI environment variable.")
        sys.exit(1)

    client   = MongoClient(MONGO_URI, tls=True, tlsAllowInvalidCertificates=True,
                           serverSelectionTimeoutMS=15000)
    db       = client[DB_NAME]
    source   = db[SOURCE_COL]
    dest     = db[DEST_COL]

    print(f"Connected → scanning {DB_NAME}.{SOURCE_COL} …")
    all_bars    = list(source.find({}))
    sports_bars = [b for b in all_bars if is_sports_bar(b)]

    print(f"  Total bars in source  : {len(all_bars)}")
    print(f"  Matched as sports bars: {len(sports_bars)}")

    if not sports_bars:
        print("\nNo sports bars found. Check that your categories field contains")
        print("values like 'Sports Bars' or 'Sports Bar' in the bars collection.")
        client.close()
        return

    # Print a sample of matched bar names for verification
    print("\nSample matches (first 10):")
    for bar in sports_bars[:10]:
        cats = bar.get("categories") or bar.get("Categories") or []
        print(f"  {bar.get('Name', '—'):40s}  {cats}")

    ops = [build_upsert_op(b) for b in sports_bars]

    print(f"\nUpserting {len(ops)} records into {DB_NAME}.{DEST_COL} … ", end="", flush=True)
    try:
        result = dest.bulk_write(ops, ordered=False)
        print("done.")
        print(f"  New inserts : {result.upserted_count}")
        print(f"  Updated     : {result.modified_count}")
        print(f"  Unchanged   : {result.matched_count - result.modified_count}")
    except BulkWriteError as bwe:
        print(f"\nBulk write errors: {bwe.details}")

    total = dest.count_documents({})
    print(f"\nFinished — {DEST_COL} has {total} documents.")
    print("\nNext steps:")
    print("  1. Run populate_sports_teams.py to seed the sports_teams collection.")
    print("  2. Use the admin panel to fill in philly_affiliates / team affiliations.")
    client.close()


if __name__ == "__main__":
    main()
