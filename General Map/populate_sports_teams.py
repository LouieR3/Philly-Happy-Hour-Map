#!/usr/bin/env python3
"""
populate_sports_teams.py  —  Deliverable 1
Fetches all teams for NHL, MLB, NFL, NBA, MLS, and Premier League from
TheSportsDB's free v1 API, then upserts them into MongoDB sports_teams.

Usage:
    MONGODB_URI="mongodb+srv://..." python populate_sports_teams.py

Idempotent: safe to re-run; uses upsert on (team_name, league).
"""

import os
import sys
import time
import requests
from pymongo import MongoClient, UpdateOne
from pymongo.errors import BulkWriteError

# ─── Configuration ────────────────────────────────────────────────────────────
MONGO_URI  = os.environ.get("MONGODB_URI") or os.environ.get("MONGO_URI")
DB_NAME    = "mappy_hour"
COLLECTION = "sports_teams"

API_BASE = "https://www.thesportsdb.com/api/v1/json/3"
DELAY    = 0.6   # seconds between API calls — be polite to the free tier

# Friendly league key → TheSportsDB league name string
LEAGUES = {
    "NFL":            "NFL",
    "NBA":            "NBA",
    "MLB":            "MLB",
    "NHL":            "NHL",
    "MLS":            "Major League Soccer",
    "Premier League": "English Premier League",
}

# ─── Helpers ──────────────────────────────────────────────────────────────────

def fetch_teams(sportsdb_league_name: str) -> list:
    """Call TheSportsDB and return the raw teams list for a given league."""
    url = f"{API_BASE}/search_all_teams.php"
    resp = requests.get(url, params={"l": sportsdb_league_name}, timeout=15)
    resp.raise_for_status()
    return resp.json().get("teams") or []


def build_doc(raw: dict, league_key: str) -> dict:
    """Map TheSportsDB fields to our sports_teams schema."""
    return {
        "team_name":    (raw.get("strTeam") or "").strip(),
        "league":       league_key,
        # strCity can be missing for some international clubs; fall back to country
        "city":         (raw.get("strCity") or raw.get("strCountry") or "").strip(),
        "abbreviation": (raw.get("strTeamShort") or "").strip(),
        # strTeamBadge is a stable CDN image hosted by TheSportsDB
        "logo_url":     (raw.get("strTeamBadge") or "").strip(),
        "sportsdb_id":  str(raw.get("idTeam") or ""),
    }


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    if not MONGO_URI:
        print("ERROR: Set MONGODB_URI or MONGO_URI environment variable.")
        sys.exit(1)

    client = MongoClient(MONGO_URI, tls=True, tlsAllowInvalidCertificates=True,
                         serverSelectionTimeoutMS=15000)
    col = client[DB_NAME][COLLECTION]

    # Unique compound index — makes upserts idempotent across re-runs
    col.create_index([("team_name", 1), ("league", 1)], unique=True)
    print(f"Connected → {DB_NAME}.{COLLECTION}\n")

    ops = []

    for league_key, league_name in LEAGUES.items():
        print(f"Fetching {league_key:15s} ({league_name}) … ", end="", flush=True)
        try:
            teams = fetch_teams(league_name)
        except Exception as exc:
            print(f"FAILED — {exc}")
            continue

        print(f"{len(teams)} teams")

        for raw in teams:
            doc = build_doc(raw, league_key)
            if not doc["team_name"]:
                continue
            ops.append(
                UpdateOne(
                    {"team_name": doc["team_name"], "league": league_key},
                    {"$set": doc},
                    upsert=True,
                )
            )

        time.sleep(DELAY)

    if not ops:
        print("\nNo records to insert — check API responses above.")
        client.close()
        return

    print(f"\nUpserting {len(ops)} team records … ", end="", flush=True)
    try:
        result = col.bulk_write(ops, ordered=False)
        print("done.")
        print(f"  Inserted : {result.upserted_count}")
        print(f"  Modified : {result.modified_count}")
        print(f"  Matched  : {result.matched_count}")
    except BulkWriteError as bwe:
        print(f"\nBulk write errors: {bwe.details}")

    total = col.count_documents({})
    print(f"\nFinished — sports_teams has {total} documents.")
    client.close()


if __name__ == "__main__":
    main()
