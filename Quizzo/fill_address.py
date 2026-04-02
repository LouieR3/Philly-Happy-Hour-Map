"""
fill_quizzo_addresses.py

For every record in quizzo_bars DB ('Quizzo Bars' collection) that is missing
ADDRESS_STREET or Latitude/Longitude:

  Stage 1 — MasterTable match
    Fuzzy-match BUSINESS name against mappy_hour.bars (Name field).
    If confidence >= threshold, copy Address, Latitude, Longitude and split
    the address into ADDRESS_STREET / ADDRESS_CITY / ADDRESS_STATE / ADDRESS_ZIP.

  Stage 2 — Yelp API match (for records that still need data after Stage 1)
    Search Yelp using business name + neighborhood/city/state.
    Use the best match (name similarity >= threshold) to fill in the gaps.

Run:
    pip install pymongo python-dotenv yelpapi thefuzz
    python fill_quizzo_addresses.py
"""

import os
import re
import ast
import sys
import time
import random
import math
from dotenv import load_dotenv
from pymongo import MongoClient, UpdateOne

load_dotenv()

MONGO_URI = os.getenv("MONGODB_URI")
if not MONGO_URI:
    sys.exit("MONGODB_URI not set in .env")

MAPPY_HOUR_URI = MONGO_URI.replace("quizzo_bars", "mappy_hour")

# ── fuzzy match ───────────────────────────────────────────────────────────────
try:
    from thefuzz import fuzz
except ImportError:
    sys.exit("Run: pip install thefuzz python-Levenshtein")

# ── Yelp key loader ───────────────────────────────────────────────────────────
def _load_yelp_keys(env_path=None):
    if env_path is None:
        env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env.example")
    with open(env_path) as f:
        content = f.read()
    match = re.search(r"yelp_api_keys\s*=\s*(\[.*?\])", content, re.DOTALL)
    if not match:
        raise ValueError("yelp_api_keys not found in .env.example")
    return ast.literal_eval(match.group(1))

try:
    import yelpapi
    keys = _load_yelp_keys()
    yelp_client = yelpapi.YelpAPI(keys[0])
    YELP_AVAILABLE = True
    print(f"  Yelp API ready ({len(keys)} key(s))")
except Exception as e:
    YELP_AVAILABLE = False
    print(f"  Yelp API not available: {e} — will use Stage 1 only")

# ── Config ────────────────────────────────────────────────────────────────────
NAME_MATCH_THRESHOLD  = 75    # minimum fuzz score (0-100) to accept a match
YELP_NAME_THRESHOLD   = 70    # slightly more lenient for Yelp since we also filter by location
CHECKPOINT_EVERY      = 25    # save to MongoDB every N records

# ── Connect ───────────────────────────────────────────────────────────────────
quizzo_client   = MongoClient(MONGO_URI)
mappy_client    = MongoClient(MAPPY_HOUR_URI)

quizzo_col = quizzo_client["quizzo_bars"]["Quizzo Bars"]
bars_col   = mappy_client["mappy_hour"]["bars"]

# ── Helpers ───────────────────────────────────────────────────────────────────
def is_incomplete(bar):
    """True if missing street address OR coordinates."""
    missing_address = not (bar.get("ADDRESS_STREET") or "").strip()
    missing_coords  = (
        bar.get("Latitude") in (None, "", 0) or
        bar.get("Longitude") in (None, "", 0) or
        (isinstance(bar.get("Latitude"),  float) and math.isnan(bar["Latitude"])) or
        (isinstance(bar.get("Longitude"), float) and math.isnan(bar["Longitude"]))
    )
    return missing_address or missing_coords


def parse_address(address_str):
    """
    Split a full address string like '123 Main St, Philadelphia, PA 19103'
    into component parts. Returns dict with ADDRESS_STREET, ADDRESS_CITY,
    ADDRESS_STATE, ADDRESS_ZIP.
    """
    parts = [p.strip() for p in str(address_str).split(",")]
    result = {"ADDRESS_STREET": None, "ADDRESS_CITY": None,
              "ADDRESS_STATE": None, "ADDRESS_ZIP": None}

    if len(parts) >= 1:
        result["ADDRESS_STREET"] = parts[0]
    if len(parts) >= 2:
        result["ADDRESS_CITY"] = parts[1]
    if len(parts) >= 3:
        # last part may be "PA 19103" or just "PA"
        last = parts[-1].strip()
        state_zip = re.match(r"^([A-Z]{2})\s*(\d{5})?$", last)
        if state_zip:
            result["ADDRESS_STATE"] = state_zip.group(1)
            if state_zip.group(2):
                result["ADDRESS_ZIP"] = state_zip.group(2)
        else:
            # may be split as separate parts
            result["ADDRESS_STATE"] = parts[-1].strip()
            if len(parts) >= 4:
                zip_match = re.search(r"\d{5}", parts[-1])
                if zip_match:
                    result["ADDRESS_ZIP"] = zip_match.group(0)
    return result


def build_update(bar, source_name, address_str, lat, lng, extra=None):
    """Build a MongoDB $set dict from the resolved data."""
    update = {}
    if lat and lng:
        update["Latitude"]  = float(lat)
        update["Longitude"] = float(lng)

    if address_str:
        parsed = parse_address(address_str)
        update["Full_Address"] = address_str
        for k, v in parsed.items():
            if v:
                update[k] = v.upper() if k in ("ADDRESS_CITY","ADDRESS_STATE") else v

    if extra:
        update.update(extra)

    return update


# ── Stage 1: MasterTable match ────────────────────────────────────────────────
print("\n=== Stage 1: Building MasterTable lookup ===")

master_bars = list(bars_col.find(
    {},
    {"Name": 1, "Address": 1, "Latitude": 1, "Longitude": 1,
     "Yelp Alias": 1, "Neighborhoods": 1, "Neighborhood": 1}
))
print(f"  {len(master_bars)} bars in mappy_hour.bars")

def master_match(business_name):
    """Find the best-matching bar in MasterTable by fuzzy name comparison."""
    best_score = 0
    best_bar   = None
    name_upper = business_name.upper().strip()
    for b in master_bars:
        candidate = (b.get("Name") or "").upper().strip()
        if not candidate:
            continue
        score = max(
            fuzz.ratio(name_upper, candidate),
            fuzz.token_sort_ratio(name_upper, candidate),
            fuzz.partial_ratio(name_upper, candidate),
        )
        if score > best_score:
            best_score = score
            best_bar   = b
    return best_bar, best_score


# ── Stage 2: Yelp match ───────────────────────────────────────────────────────
def yelp_match(business_name, neighborhood, city, state):
    """Search Yelp and return the best matching business result, or None."""
    if not YELP_AVAILABLE:
        return None

    location_parts = []
    if neighborhood:
        location_parts.append(neighborhood)
    location_parts.append(city or "Philadelphia")
    if state:
        location_parts.append(state)
    location = ", ".join(location_parts)

    time.sleep(random.uniform(0.4, 0.9))
    try:
        results = yelp_client.search_query(
            term=business_name,
            location=location,
            limit=5,
        )
    except Exception as e:
        print(f"    Yelp error: {e}")
        return None

    businesses = results.get("businesses", [])
    if not businesses:
        return None

    name_upper = business_name.upper().strip()
    best_score = 0
    best_biz   = None

    for biz in businesses:
        score = max(
            fuzz.ratio(name_upper, biz["name"].upper()),
            fuzz.token_sort_ratio(name_upper, biz["name"].upper()),
        )
        if score > best_score:
            best_score = score
            best_biz   = biz

    if best_score >= YELP_NAME_THRESHOLD:
        return best_biz, best_score
    return None


# ── Main loop ─────────────────────────────────────────────────────────────────
print("\n=== Finding incomplete quizzo bar records ===")
all_quizzo = list(quizzo_col.find({}))
incomplete  = [b for b in all_quizzo if is_incomplete(b)]
print(f"  {len(incomplete)} of {len(all_quizzo)} records are incomplete\n")

ops              = []
stage1_matched   = 0
stage2_matched   = 0
still_incomplete = []

for i, bar in enumerate(incomplete, 1):
    name        = bar.get("BUSINESS", "").strip()
    neighborhood= bar.get("NEIGHBORHOOD", "").strip()
    city        = (bar.get("ADDRESS_CITY") or "Philadelphia").strip()
    state       = (bar.get("ADDRESS_STATE") or "PA").strip()

    print(f"  [{i}/{len(incomplete)}] {name}")

    # ── Stage 1 ──────────────────────────────────────────────────────────────
    master_bar, score = master_match(name)
    if score >= NAME_MATCH_THRESHOLD and master_bar:
        address = master_bar.get("Address") or ""
        lat     = master_bar.get("Latitude")
        lng     = master_bar.get("Longitude")

        if address or (lat and lng):
            update = build_update(bar, "MasterTable", address, lat, lng)
            if update:
                ops.append(UpdateOne({"_id": bar["_id"]}, {"$set": update}))
                stage1_matched += 1
                print(f"    ✓ Stage 1 [{score}] → {address or f'{lat},{lng}'}")
                continue

    # ── Stage 2 ──────────────────────────────────────────────────────────────
    result = yelp_match(name, neighborhood, city, state)
    if result:
        biz, yscore = result
        loc     = biz.get("location", {})
        coords  = biz.get("coordinates", {})
        street  = loc.get("address1", "")
        ycity   = loc.get("city", city)
        ystate  = loc.get("state", state)
        yzip    = loc.get("zip_code", "")
        lat     = coords.get("latitude")
        lng     = coords.get("longitude")
        address = ", ".join(filter(None, [street, ycity, ystate, yzip]))

        extra = {}
        if biz.get("alias"):
            extra["Yelp_Alias"] = biz["alias"]

        update = build_update(bar, "Yelp", address, lat, lng, extra)
        if update:
            ops.append(UpdateOne({"_id": bar["_id"]}, {"$set": update}))
            stage2_matched += 1
            print(f"    ✓ Stage 2 [{yscore}] → {address}")
            continue

    still_incomplete.append(name)
    print(f"    ✗ No match found")

    # Checkpoint
    if ops and i % CHECKPOINT_EVERY == 0:
        quizzo_col.bulk_write(ops)
        print(f"\n  — checkpoint saved ({i}/{len(incomplete)}) —\n")
        ops = []

# ── Final write ───────────────────────────────────────────────────────────────
if ops:
    result = quizzo_col.bulk_write(ops)
    print(f"\nFinal write: modified {result.modified_count} records")

print(f"""
=== Summary ===
Total incomplete:   {len(incomplete)}
Stage 1 (Master):   {stage1_matched}
Stage 2 (Yelp):     {stage2_matched}
Still incomplete:   {len(still_incomplete)}
""")

if still_incomplete:
    print("Unresolved records:")
    for n in still_incomplete:
        print(f"  ✗ {n}")

quizzo_client.close()
mappy_client.close()
print("Done.")