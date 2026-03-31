"""
populate_bars_neighborhoods.py

For every document in mappy_hour.bars:
  1. Uses the bar's Latitude/Longitude to find which neighborhood polygon
     it falls inside (via shapely point-in-polygon against the GeoJSON).
  2. Sets Neighborhood = NAME of the matched polygon (human-readable, title case)

Usage:
    pip install shapely pymongo python-dotenv
    python populate_bars_neighborhoods.py
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

# Build list of (polygon, NAME)
polygons = []
for feature in geojson["features"]:
    try:
        poly   = shape(feature["geometry"])
        props  = feature["properties"]
        name   = props.get("NAME", "").replace("_", " ").title()
        polygons.append((poly, name))
    except Exception as e:
        print(f"  Skipping invalid geometry: {e}")

print(f"  Loaded {len(polygons)} neighborhood polygons\n")

def find_neighborhood(lat, lng):
    """Return neighborhood_name for the polygon containing the point, or None."""
    if lat is None or lng is None:
        return None
    pt = Point(lng, lat)   # GeoJSON is (longitude, latitude)
    for poly, name in polygons:
        if poly.contains(pt):
            return name
    return None

# ── Connect to MongoDB ────────────────────────────────────────────────────────
MAPPY_HOUR_URI = MONGO_URI.replace("quizzo_bars", "mappy_hour")
client   = MongoClient(MAPPY_HOUR_URI)
bars_col = client["mappy_hour"]["bars"]

bars = list(bars_col.find({}, {
    "_id": 1, "Name": 1, "Latitude": 1, "Longitude": 1, "Neighborhood": 1,
}))
print(f"{len(bars)} bars found\n")

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
        continue

    neighborhood, _ = find_neighborhood(lat, lng), None
    
    if neighborhood:
        matched += 1
        ops.append(UpdateOne(
            {"_id": bar["_id"]},
            {"$set": {"Neighborhood": neighborhood}}
        ))
        print(f"  ✓ {name} → {neighborhood}")
    else:
        no_polygon.append(name)
        print(f"  ✗ {name} (no polygon match)")

# ── Execute bulk update ───────────────────────────────────────────────────────
if ops:
    print(f"\nExecuting {len(ops)} updates...")
    result = bars_col.bulk_write(ops)
    print(f"  Modified: {result.modified_count}")
else:
    print("No updates to execute.")

# ── Summary ────────────────────────────────────────────────────────────────────
print(f"\n{'─' * 70}")
print(f"Results:")
print(f"  Matched & updated: {matched}")
print(f"  No coordinates: {len(no_coords)}")
print(f"  Outside all polygons: {len(no_polygon)}")
print(f"  Total bars: {len(bars)}")

if no_coords:
    print(f"\nBars without coordinates: {', '.join(no_coords[:5])}")
if no_polygon and no_polygon != no_coords:
    print(f"\nBars outside all neighborhoods: {', '.join(no_polygon[:5])}")
