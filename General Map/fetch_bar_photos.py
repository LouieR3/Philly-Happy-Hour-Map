"""
fetch_bar_photos.py

For every bar in mappy_hour.bars that has a Yelp Alias but no Photos field,
fetches up to 3 photo URLs from the Yelp business details endpoint and writes
them to a Photos array on the document.

Usage:
    python fetch_bar_photos.py

    # Overwrite existing Photos fields (re-fetch all):
    python fetch_bar_photos.py --overwrite

Requires in .env (at repo root):
    MONGODB_URI=mongodb+srv://...
    (Yelp keys read from .env.example yelp_api_keys list)
"""

import os
import ast
import re
import sys
import time
import random
import argparse

import yelpapi
from pymongo import MongoClient, UpdateOne
from dotenv import load_dotenv

# ── Config ────────────────────────────────────────────────────────────────────
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.join(_HERE, "..")

load_dotenv(os.path.join(_ROOT, ".env"))

MONGO_URI = os.getenv("MONGODB_URI", "")
DB_NAME   = "mappy_hour"
COLL_NAME = "bars"


# ── Yelp key loading (same as update_bars_mongo.py) ───────────────────────────
def _load_yelp_keys():
    env_path = os.path.join(_ROOT, ".env.example")
    with open(env_path) as f:
        content = f.read()
    m = re.search(r"yelp_api_keys\s*=\s*(\[.*?\])", content, re.DOTALL)
    if not m:
        raise ValueError("yelp_api_keys list not found in .env.example")
    return ast.literal_eval(m.group(1))


class YelpRotator:
    def __init__(self, keys):
        if not keys:
            raise ValueError("No Yelp API keys provided.")
        self._keys   = keys
        self._index  = 0
        self._client = yelpapi.YelpAPI(keys[0])
        print(f"  [Yelp] Using key 1/{len(keys)}")

    def _rotate(self):
        self._index += 1
        if self._index >= len(self._keys):
            raise RuntimeError("All Yelp API keys exhausted — stopping.")
        self._client = yelpapi.YelpAPI(self._keys[self._index])
        print(f"  [Yelp] Rotated to key {self._index + 1}/{len(self._keys)}")

    def details(self, alias):
        while True:
            try:
                return self._client.business_query(id=alias)
            except Exception as e:
                msg = str(e).upper()
                if any(x in msg for x in ("RATE_LIMIT", "429", "TOO_MANY_REQUESTS")):
                    print(f"  [Yelp] Rate limit on key {self._index + 1}: {e}")
                    self._rotate()
                else:
                    raise


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--overwrite", action="store_true",
                        help="Re-fetch photos even if Photos field already exists")
    args = parser.parse_args()

    if not MONGO_URI:
        sys.exit("ERROR: MONGODB_URI not set in .env")

    print("\n=== Connecting to MongoDB ===")
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=15000)
    coll   = client[DB_NAME][COLL_NAME]

    # Find bars with a Yelp Alias
    query = {"Yelp Alias": {"$exists": True, "$ne": ""}}
    if not args.overwrite:
        # Skip any that already have photos
        query["Photos"] = {"$exists": False}

    bars = list(coll.find(query, {"_id": 1, "Name": 1, "Yelp Alias": 1}))
    print(f"  {len(bars)} bars to process")

    if not bars:
        print("  Nothing to do — all bars already have photos. Use --overwrite to re-fetch.")
        client.close()
        return

    print("\n=== Loading Yelp keys ===")
    keys = _load_yelp_keys()
    yelp = YelpRotator(keys)

    print("\n=== Fetching photos ===")
    ops     = []
    success = 0
    no_photo = 0
    failed  = 0
    total   = len(bars)

    for i, bar in enumerate(bars, 1):
        alias = bar["Yelp Alias"]
        name  = bar.get("Name", alias)
        print(f"  [{i}/{total}] {name} ({alias})")
        time.sleep(random.uniform(0.4, 0.8))

        try:
            detail = yelp.details(alias)
        except Exception as e:
            print(f"    Error: {e} — skipping")
            failed += 1
            continue

        photos = detail.get("photos", [])
        if not photos:
            print(f"    No photos returned")
            no_photo += 1
            continue

        print(f"    {len(photos)} photo(s) found")
        ops.append(
            UpdateOne(
                {"_id": bar["_id"]},
                {"$set": {"Photos": photos}},
            )
        )
        success += 1

        if len(ops) >= 50:
            result = coll.bulk_write(ops, ordered=False)
            print(f"    → Flushed {len(ops)} ops (modified={result.modified_count})")
            ops = []

    if ops:
        result = coll.bulk_write(ops, ordered=False)
        print(f"  → Final flush: {len(ops)} ops (modified={result.modified_count})")

    client.close()

    print(f"\n=== Done ===")
    print(f"  Total: {total}  |  Photos written: {success}  |  No photos: {no_photo}  |  Errors: {failed}")


if __name__ == "__main__":
    main()
