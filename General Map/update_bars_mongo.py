"""
update_bars_mongo.py

Searches Yelp for bars in Philly neighborhoods (including a "Happy Hour"
pass), fetches full details via the Yelp API for each new bar, and upserts
records directly into MongoDB (mappy_hour.bars collection).

No scraping — API only.

Usage:
    python update_bars_mongo.py

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

NEIGHBORHOODS = [
    "Rittenhouse Square, Philadelphia",
    "Graduate Hospital, Philadelphia",
    "Italian Market, Philadelphia",
    "Passyunk, Philadelphia",
    "Queen Village, Philadelphia",
    "Point Breeze, Philadelphia",
    "Center City, Philadelphia",
    "Old City, Philadelphia",
    "Northern Liberties, Philadelphia",
    "Fishtown, Philadelphia",
    "South Philadelphia, Philadelphia",
    "Fairmount, Philadelphia",
    "Chinatown, Philadelphia",
    "University City, Philadelphia",
    "Temple University, Philadelphia",
    "Port Richmond, Philadelphia",
    "Kensington, Philadelphia",
    "Manayunk, Philadelphia",
    "East Passyunk, Philadelphia",
    "Germantown, Philadelphia",
    "West Philadelphia, Philadelphia",
]

SEARCH_TERMS = ["bars", "Happy Hour bars"]
LIMIT        = 50   # Yelp max per call
PRICE_TIERS  = "1,2,3"  # exclude $$$$


# ── Yelp key loading ──────────────────────────────────────────────────────────
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

    def _call(self, method, **kwargs):
        while True:
            try:
                return getattr(self._client, method)(**kwargs)
            except Exception as e:
                msg = str(e).upper()
                if any(x in msg for x in ("RATE_LIMIT", "429", "TOO_MANY_REQUESTS")):
                    print(f"  [Yelp] Rate limit on key {self._index + 1}: {e}")
                    self._rotate()
                else:
                    raise

    def search(self, **kwargs):
        return self._call("search_query", **kwargs)

    def details(self, alias):
        return self._call("business_query", id=alias)


# ── Hours parsing (from fill_hours.py) ───────────────────────────────────────
DAY_INDEX = {0: "Monday", 1: "Tuesday", 2: "Wednesday",
             3: "Thursday", 4: "Friday", 5: "Saturday", 6: "Sunday"}
DAY_COLS  = list(DAY_INDEX.values())


def _fmt_time(t: str) -> str:
    t = t.zfill(4)
    h, m = int(t[:2]), int(t[2:])
    period = "AM" if h < 12 else "PM"
    return f"{h % 12 or 12}:{m:02d} {period}"


def _parse_hours(hours_blocks: list) -> dict:
    regular = next(
        (h for h in hours_blocks if h.get("hours_type") == "REGULAR"),
        hours_blocks[0] if hours_blocks else None,
    )
    if not regular:
        return {}
    slots: dict[str, list] = {d: [] for d in DAY_COLS}
    for slot in regular.get("open", []):
        day = DAY_INDEX.get(slot["day"])
        if day:
            slots[day].append(f"{_fmt_time(slot['start'])} - {_fmt_time(slot['end'])}")
    return {day: " / ".join(v) for day, v in slots.items() if v}


# ── Build a document from Yelp API detail response ───────────────────────────
def _build_doc(detail: dict) -> dict:
    cats       = [c["title"] for c in detail.get("categories", [])]
    address    = ", ".join(detail.get("location", {}).get("display_address", []))
    coords     = detail.get("coordinates", {})
    hours      = _parse_hours(detail.get("hours", []))

    doc = {
        "Name":          detail.get("name"),
        "Yelp Alias":    detail.get("alias"),
        "Address":       address,
        "Latitude":      coords.get("latitude"),
        "Longitude":     coords.get("longitude"),
        "Phone":         detail.get("display_phone") or detail.get("phone") or "",
        "Website":       detail.get("url", ""),
        "Yelp Rating":   detail.get("rating"),
        "Review Count":  detail.get("review_count"),
        "Price":         detail.get("price", ""),
        "Categories":    ", ".join(cats),
        **hours,
    }
    return {k: v for k, v in doc.items() if v is not None and v != ""}


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    if not MONGO_URI:
        sys.exit("ERROR: MONGODB_URI not set in .env")

    print("\n=== Connecting to MongoDB ===")
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=15000)
    coll   = client[DB_NAME][COLL_NAME]

    # Pre-load existing aliases so we know what to skip
    existing_aliases = set(
        doc["Yelp Alias"]
        for doc in coll.find({"Yelp Alias": {"$exists": True, "$ne": ""}}, {"Yelp Alias": 1})
        if doc.get("Yelp Alias")
    )
    print(f"  {len(existing_aliases)} bars already in collection")

    print("\n=== Loading Yelp keys ===")
    keys = _load_yelp_keys()
    yelp = YelpRotator(keys)

    # ── Step 1: Discover aliases across neighborhoods + search terms ──────────
    print("\n=== Step 1: Discovering bar aliases ===")
    new_aliases: dict[str, str] = {}  # alias → name

    for neighborhood in NEIGHBORHOODS:
        for term in SEARCH_TERMS:
            print(f"  Searching '{term}' in {neighborhood} …")
            try:
                results = yelp.search(
                    term=term,
                    location=neighborhood,
                    price=PRICE_TIERS,
                    limit=LIMIT,
                )
            except Exception as e:
                print(f"    Search error: {e} — skipping")
                continue

            for biz in results.get("businesses", []):
                alias = biz.get("alias")
                name  = biz.get("name", alias)
                if alias and alias not in existing_aliases and alias not in new_aliases:
                    new_aliases[alias] = name
                    print(f"    + {name}")

            time.sleep(random.uniform(0.3, 0.7))

    print(f"\n  Found {len(new_aliases)} new bars to fetch details for")

    if not new_aliases:
        print("  Nothing new — done.")
        client.close()
        return

    # ── Step 2: Fetch details and upsert into MongoDB ─────────────────────────
    print("\n=== Step 2: Fetching details & upserting into MongoDB ===")
    ops      = []
    success  = 0
    failed   = 0
    total    = len(new_aliases)

    for i, (alias, name) in enumerate(new_aliases.items(), 1):
        print(f"  [{i}/{total}] {name} ({alias})")
        time.sleep(random.uniform(0.4, 0.9))

        try:
            detail = yelp.details(alias)
        except Exception as e:
            print(f"    Detail error: {e} — skipping")
            failed += 1
            continue

        doc = _build_doc(detail)
        if not doc.get("Name"):
            print("    No name in response — skipping")
            failed += 1
            continue

        ops.append(
            UpdateOne(
                {"Yelp Alias": alias},
                {"$set": doc},
                upsert=True,
            )
        )
        success += 1

        # Flush every 50 ops
        if len(ops) >= 50:
            result = coll.bulk_write(ops, ordered=False)
            print(f"    → Flushed {len(ops)} ops "
                  f"(upserted={result.upserted_count}, modified={result.modified_count})")
            ops = []

    # Final flush
    if ops:
        result = coll.bulk_write(ops, ordered=False)
        print(f"  → Final flush: {len(ops)} ops "
              f"(upserted={result.upserted_count}, modified={result.modified_count})")

    client.close()

    print(f"\n=== Done ===")
    print(f"  Processed: {total}  |  Written: {success}  |  Failed: {failed}")


if __name__ == "__main__":
    main()
