"""
set_pool_neighborhoods.py

For every document in mappy_hour.pool_bars:
  1. Uses the bar's Latitude/Longitude to find which neighborhood polygon
     it falls inside (via shapely point-in-polygon against the GeoJSON).
  2. Sets  Neighborhood  = NAME of the matched polygon  (human-readable, single value)
  3. Sets  Philly_Region = GENERAL_AREA of that polygon     (blank → None)
  4. Removes the old plural  Neighborhoods  field.

Also fixes the pool_bars documents created via approve-pool-submission
that incorrectly stored the value in 'Neighborhoods' (plural).

Usage:
    pip install shapely pymongo python-dotenv
    python set_pool_neighborhoods.py

The GeoJSON file path defaults to the location in the repo; override with
the NEIGHBORHOODS_GEOJSON env var if needed.
"""

import os
import sys
import json
from dotenv import load_dotenv
from pymongo import MongoClient, UpdateOne

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────
MONGO_URI   = os.getenv("MONGODB_URI")
GEOJSON_PATH = os.getenv(
    "NEIGHBORHOODS_GEOJSON",
    os.path.join(os.path.dirname(os.path.abspath(__file__)),
                 "..", "public", "assets", "philadelphia-neighborhoods.geojson")
)

if not MONGO_URI:
    sys.exit("MONGODB_URI not set in .env")

try:
    from shapely.geometry import shape, Point
except ImportError:
    sys.exit("Run: pip install shapely")

# ── Load GeoJSON ──────────────────────────────────────────────────────────────
print(f"Loading GeoJSON from {GEOJSON_PATH}")
with open(GEOJSON_PATH) as f:
    geojson = json.load(f)

# Build list of (polygon, NAME, NAME, GENERAL_AREA)
polygons = []
for feature in geojson["features"]:
    try:
        poly   = shape(feature["geometry"])
        props  = feature["properties"]
        name   = props.get("NAME", "").replace("_", " ").title()
        area   = props.get("GENERAL_AREA", "").strip() or None
        polygons.append((poly, name, area))
    except Exception as e:
        print(f"  Skipping invalid geometry: {e}")

print(f"  Loaded {len(polygons)} neighborhood polygons")

def find_neighborhood(lat, lng):
    """Return (neighborhood_name, general_area) for the polygon containing
    the point, or (None, None) if no polygon matches."""
    if lat is None or lng is None:
        return None, None
    pt = Point(lng, lat)   # GeoJSON is (longitude, latitude)
    for poly, name, area in polygons:
        if poly.contains(pt):
            return name, area
    return None, None

# ── Connect to MongoDB ────────────────────────────────────────────────────────
MAPPY_HOUR_URI = MONGO_URI.replace("quizzo_bars", "mappy_hour")
client   = MongoClient(MAPPY_HOUR_URI)
pool_col = client["mappy_hour"]["pool_bars"]

bars = list(pool_col.find({}, {
    "_id": 1, "Name": 1, "Latitude": 1, "Longitude": 1,
    "Neighborhood": 1, "Neighborhoods": 1, "Philly_Region": 1,
}))
print(f"\n{len(bars)} pool bars found\n")

ops          = []
matched      = 0
no_coords    = []
no_polygon   = []

for bar in bars:
    name = bar.get("Name", str(bar["_id"]))
    lat  = bar.get("Latitude")
    lng  = bar.get("Longitude")

    if not lat or not lng:
        no_coords.append(name)
        # Still clean up the old Neighborhoods field even without coords
        ops.append(UpdateOne(
            {"_id": bar["_id"]},
            {"$unset": {"Neighborhoods": ""}}
        ))
        continue

    neighborhood, region = find_neighborhood(lat, lng)

    if not neighborhood:
        no_polygon.append(f"{name} ({lat}, {lng})")
        # Still remove old plural field even if outside Philly polygons
        ops.append(UpdateOne(
            {"_id": bar["_id"]},
            {"$unset": {"Neighborhoods": ""}}
        ))
        continue

    set_fields   = {"Neighborhood": neighborhood}
    unset_fields = {"Neighborhoods": ""}           # remove old plural field

    if region:
        set_fields["Philly_Region"] = region
    else:
        unset_fields["Philly_Region"] = ""         # remove if previously set to blank

    ops.append(UpdateOne(
        {"_id": bar["_id"]},
        {"$set": set_fields, "$unset": unset_fields}
    ))
    matched += 1
    print(f"  ✓ {name:<40} → {neighborhood:<30} | {region or '—'}")

# ── Write ─────────────────────────────────────────────────────────────────────
if ops:
    result = pool_col.bulk_write(ops)
    print(f"\nModified {result.modified_count} documents")
else:
    print("\nNothing to write")

if no_coords:
    print(f"\n{len(no_coords)} bars had no coordinates (Neighborhoods field still cleaned up):")
    for n in no_coords:
        print(f"  ✗ {n}")

if no_polygon:
    print(f"\n{len(no_polygon)} bars were outside all Philadelphia polygons (suburban bars):")
    for n in no_polygon:
        print(f"  ✗ {n}")

client.close()
print("\nDone.")