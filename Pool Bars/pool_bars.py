"""
find_pool_bars.py

Pipeline:
  1. Search Yelp for pool halls / billiards in Philly using multiple terms
  2. Fetch full business details (hours via API, categories, address, etc.)
  3. Add new bars to MasterTable.csv (skip existing aliases)
  4. Upsert into MongoDB mappy_hour.bars collection
  5. Create / update a separate pool_bars collection with pool-specific fields
     pre-populated as None, ready for manual entry

Usage:
  python find_pool_bars.py
"""

import os
import ast
import re
import time
import random
import math
import pandas as pd
from pymongo import MongoClient, UpdateOne
from dotenv import load_dotenv
import yelpapi

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────
_HERE       = os.path.dirname(os.path.abspath(__file__))
_CSV_DIR    = os.path.join(_HERE, "..", "Csv")
MASTER_CSV  = os.path.join(_CSV_DIR, "MasterTable.csv")

MONGO_URI   = os.getenv("MONGODB_URI")
DB_NAME     = "mappy_hour"
BARS_COL    = "bars"           # existing general bars collection
POOL_COL    = "pool_bars"      # new pool-specific collection

SEARCH_TERMS  = ["pool hall", "pool table", "billiards"]
SEARCH_LOCATION = "Philadelphia, PA"
SEARCH_LIMIT    = 50           # Yelp max per request

DAY_INDEX = {0: "Monday", 1: "Tuesday", 2: "Wednesday",
             3: "Thursday", 4: "Friday", 5: "Saturday", 6: "Sunday"}
DAY_COLS  = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


# ── Yelp key loader ───────────────────────────────────────────────────────────
def _load_yelp_keys(env_path=None):
    if env_path is None:
        env_path = os.path.join(_HERE, "..", ".env.example")
    with open(env_path) as f:
        content = f.read()
    match = re.search(r"yelp_api_keys\s*=\s*(\[.*?\])", content, re.DOTALL)
    if not match:
        raise ValueError("yelp_api_keys not found in .env.example")
    return ast.literal_eval(match.group(1))


class YelpClientRotator:
    def __init__(self, keys):
        if not keys:
            raise ValueError("No Yelp API keys provided.")
        self._keys   = keys
        self._index  = 0
        self._client = yelpapi.YelpAPI(keys[0])
        print(f"  Using Yelp key [1/{len(keys)}]")

    def _rotate(self):
        self._index += 1
        if self._index >= len(self._keys):
            raise RuntimeError("All Yelp API keys exhausted.")
        self._client = yelpapi.YelpAPI(self._keys[self._index])
        print(f"  Rotated to key [{self._index + 1}/{len(self._keys)}]")

    def _call(self, method, **kwargs):
        while True:
            try:
                return getattr(self._client, method)(**kwargs)
            except Exception as e:
                msg = str(e).upper()
                if "RATE_LIMIT" in msg or "429" in msg or "TOO_MANY_REQUESTS" in msg:
                    print(f"  Rate limit: {e}")
                    self._rotate()
                else:
                    raise

    def search_query(self, **kwargs): return self._call("search_query", **kwargs)
    def business_query(self, **kwargs): return self._call("business_query", **kwargs)


# ── Hour helpers (from fill_hours.py) ─────────────────────────────────────────
def _fmt_time(t: str) -> str:
    t = t.zfill(4)
    h, m = int(t[:2]), int(t[2:])
    period = "AM" if h < 12 else "PM"
    h12 = h % 12 or 12
    return f"{h12}:{m:02d} {period}"


def _parse_hours(hours_list: list) -> dict:
    day_slots: dict[str, list[str]] = {d: [] for d in DAY_COLS}
    for slot in hours_list:
        day_name = DAY_INDEX.get(slot["day"])
        if day_name is None:
            continue
        day_slots[day_name].append(f"{_fmt_time(slot['start'])} - {_fmt_time(slot['end'])}")
    return {day: " / ".join(slots) if slots else None for day, slots in day_slots.items()}


# ── Fetch full details for one business ───────────────────────────────────────
def _fetch_details(biz: dict, yelp: YelpClientRotator) -> dict:
    """
    Given a search result stub, call the business endpoint for full details
    including hours, categories, address, website, rating.
    """
    alias = biz["alias"]
    name  = biz["name"]

    time.sleep(random.uniform(0.4, 0.9))
    try:
        resp = yelp.business_query(id=alias)
    except Exception as e:
        print(f"    API error for {name}: {e}")
        return None

    categories = [c["title"] for c in resp.get("categories", [])]
    address    = ", ".join(resp["location"]["display_address"])
    coords     = resp.get("coordinates", {})

    # Hours
    hours_data = {}
    hours_blocks = resp.get("hours", [])
    regular = next(
        (h for h in hours_blocks if h.get("hours_type") == "REGULAR"),
        hours_blocks[0] if hours_blocks else None
    )
    if regular:
        hours_data = _parse_hours(regular.get("open", []))

    return {
        "Name":            name,
        "Yelp Alias":      alias,
        "Address":         address,
        "Latitude":        coords.get("latitude"),
        "Longitude":       coords.get("longitude"),
        "Website":         resp.get("url"),   # Yelp page — website not in API response
        "Yelp Rating":     resp.get("rating"),
        "Review Count":    resp.get("review_count"),
        "Price":           resp.get("price"),
        "Phone":           resp.get("phone"),
        "Categories":      categories,
        "Neighborhoods":   None,              # not in API — would need scraping
        "SIPS_PARTICIPANT": "N",
        "RW_PARTICIPANT":   "N",
        **hours_data,
    }


# ── Step 1: Search Yelp for pool bars ─────────────────────────────────────────
def find_pool_bars(yelp: YelpClientRotator, existing_aliases: set) -> list[dict]:
    """Search all terms, deduplicate, skip existing, fetch full details."""
    print("\n=== STEP 1: Searching Yelp for pool bars ===")

    found: dict[str, dict] = {}   # alias → search stub, deduplicated across terms

    for term in SEARCH_TERMS:
        print(f"  Searching: '{term}' in {SEARCH_LOCATION}")
        try:
            results = yelp.search_query(
                term=term,
                location=SEARCH_LOCATION,
                limit=SEARCH_LIMIT,
            )
        except Exception as e:
            print(f"    Error: {e}")
            continue

        for biz in results.get("businesses", []):
            alias = biz["alias"]
            if alias not in found:
                found[alias] = biz
                print(f"    + {biz['name']} ({alias})")

    new = [biz for alias, biz in found.items() if alias not in existing_aliases]
    print(f"\n  Found {len(found)} total, {len(new)} new (not in MasterTable)")
    return new


# ── Step 2: Fetch details for each new bar ────────────────────────────────────
def fetch_all_details(new_bars: list[dict], yelp: YelpClientRotator) -> list[dict]:
    print(f"\n=== STEP 2: Fetching details for {len(new_bars)} new bars ===")
    results = []
    for i, biz in enumerate(new_bars, 1):
        print(f"  [{i}/{len(new_bars)}] {biz['name']}")
        details = _fetch_details(biz, yelp)
        if details:
            results.append(details)
    print(f"  Got details for {len(results)} bars")
    return results


# ── Step 3: Append to MasterTable.csv ────────────────────────────────────────
def update_master_csv(new_data: list[dict]) -> pd.DataFrame:
    print(f"\n=== STEP 3: Updating MasterTable.csv ===")

    if os.path.exists(MASTER_CSV):
        master_df = pd.read_csv(MASTER_CSV, dtype=str)
    else:
        master_df = pd.DataFrame()

    new_df    = pd.DataFrame(new_data)
    master_df = pd.concat([master_df, new_df], ignore_index=True)
    master_df.to_csv(MASTER_CSV, index=False)
    print(f"  MasterTable now has {len(master_df)} rows")
    return master_df


# ── Helpers for MongoDB ───────────────────────────────────────────────────────
def _clean_val(val):
    """Convert NaN / empty strings to None for clean Mongo docs."""
    if val is None:
        return None
    if isinstance(val, float) and math.isnan(val):
        return None
    s = str(val).strip()
    if s.lower() in ("nan", "none", "", "[]", "['']"):
        return None
    return val


def _row_to_doc(row: dict) -> dict:
    return {k: _clean_val(v) for k, v in row.items() if _clean_val(v) is not None}


# ── Step 4: Upsert into mappy_hour.bars ──────────────────────────────────────
def upsert_bars(new_data: list[dict]):
    print(f"\n=== STEP 4: Upserting {len(new_data)} bars into {DB_NAME}.{BARS_COL} ===")
    client = MongoClient(MONGO_URI)
    col    = client[DB_NAME][BARS_COL]

    ops = []
    for row in new_data:
        doc = _row_to_doc(row)
        alias = doc.get("Yelp Alias")
        if not alias:
            continue
        ops.append(UpdateOne(
            {"Yelp Alias": alias},
            {"$setOnInsert": doc},
            upsert=True
        ))

    if ops:
        result = col.bulk_write(ops)
        print(f"  Inserted: {result.upserted_count}, matched existing: {result.matched_count}")
    client.close()


# ── Step 5: Create / update pool_bars collection ─────────────────────────────
def upsert_pool_bars(new_data: list[dict]):
    """
    For each new bar, create a document in pool_bars with:
      - Core identity fields from Yelp
      - Pool-specific fields pre-set to None for manual entry
    """
    print(f"\n=== STEP 5: Upserting into {DB_NAME}.{POOL_COL} ===")
    client = MongoClient(MONGO_URI)
    col    = client[DB_NAME][POOL_COL]

    ops = []
    for row in new_data:
        alias = row.get("Yelp Alias")
        if not alias:
            continue

        # Core identity — always kept up to date
        identity = {
            "Yelp Alias":   alias,
            "Name":         row.get("Name"),
            "Address":      row.get("Address"),
            "Latitude":     row.get("Latitude"),
            "Longitude":    row.get("Longitude"),
            "Phone":        row.get("Phone"),
            "Website":      row.get("Website"),
            "Yelp Rating":  row.get("Yelp Rating"),
            "Review Count": row.get("Review Count"),
            "Price":        row.get("Price"),
            "Categories":   row.get("Categories", []),
            **{day: row.get(day) for day in DAY_COLS},
        }

        # Pool-specific fields — only set on INSERT (don't overwrite manual edits)
        pool_fields = {
            # ── Table info ──────────────────────────────────────────────────
            "Number_of_Tables":    None,   # int
            "Table_Brand":         None,   # e.g. "Brunswick", "Diamond"
            "Table_Size":          None,   # e.g. "7ft", "8ft", "9ft"
            "Table_Type":          None,   # e.g. "Bar Box", "Regulation", "Snooker"

            # ── Pricing ─────────────────────────────────────────────────────
            "Cost_Per_Game":       None,   # float — e.g. 2.50
            "Cost_Per_Hour":       None,   # float — e.g. 15.00
            "Payment_Model":       None,   # "per_game" | "per_hour" | "both" | "free_with_purchase"
            "Min_Spend":           None,   # float — some places require a drink minimum

            # ── Reservation & access ────────────────────────────────────────
            "Reservations":        None,   # "required" | "recommended" | "walk_in_only"
            "Reservation_Link":    None,   # URL string

            # ── Vibe & atmosphere ────────────────────────────────────────────
            "Vibe":                None,   # e.g. "dive", "upscale", "sports bar", "lounge"
            "Noise_Level":         None,   # "quiet" | "moderate" | "loud"
            "Crowd_Type":          None,   # e.g. "regulars", "young professionals", "mixed"
            "Best_Nights":         None,   # e.g. "Friday, Saturday"

            # ── Amenities ───────────────────────────────────────────────────
            "Has_Bar":             None,   # bool
            "Has_Food":            None,   # bool
            "Has_Happy_Hour":      None,   # bool
            "Happy_Hour_Details":  None,   # free text
            "Has_TV":              None,   # bool — good for watching while waiting
            "Has_Other_Games":     None,   # e.g. "darts, shuffleboard, ping pong"
            "Outdoor_Seating":     None,   # bool
            "Parking":             None,   # e.g. "street", "lot", "garage"

            # ── League / events ─────────────────────────────────────────────
            "Has_League":          None,   # bool
            "League_Details":      None,   # free text — day, cost, how to join
            "Hosts_Tournaments":   None,   # bool

            # ── Meta ────────────────────────────────────────────────────────
            "Verified":            False,  # flip to True once manually confirmed
            "Last_Verified":       None,   # ISO date string
            "Notes":               None,   # anything else
        }

        ops.append(UpdateOne(
            {"Yelp Alias": alias},
            {
                "$set": identity,               # always update core identity fields
                "$setOnInsert": pool_fields,    # only set pool fields on first insert
            },
            upsert=True
        ))

    if ops:
        result = col.bulk_write(ops)
        print(f"  Inserted: {result.upserted_count}, updated existing: {result.matched_count}")

    # Create indexes for common query patterns
    col.create_index("Yelp Alias", unique=True)
    col.create_index("Name")
    col.create_index([("Latitude", 1), ("Longitude", 1)])
    col.create_index("Verified")
    print(f"  Indexes created on pool_bars")

    client.close()


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    if not MONGO_URI:
        raise ValueError("MONGODB_URI not set in .env")

    keys = _load_yelp_keys()
    yelp = YelpClientRotator(keys)

    # Load existing aliases so we don't re-fetch
    existing_aliases = set()
    if os.path.exists(MASTER_CSV):
        master_df = pd.read_csv(MASTER_CSV, dtype=str)
        if "Yelp Alias" in master_df.columns:
            existing_aliases = set(master_df["Yelp Alias"].dropna().values)
    print(f"  {len(existing_aliases)} bars already in MasterTable")

    new_bars   = find_pool_bars(yelp, existing_aliases)
    new_data   = fetch_all_details(new_bars, yelp)

    if not new_data:
        print("\nNo new pool bars found — nothing to add.")
        return

    update_master_csv(new_data)
    upsert_bars(new_data)
    upsert_pool_bars(new_data)

    print(f"\nDone — added {len(new_data)} pool bars to MasterTable, bars, and pool_bars.")


if __name__ == "__main__":
    main()