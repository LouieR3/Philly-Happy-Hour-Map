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
from dotenv import load_dotenv
from pymongo.errors import BulkWriteError

load_dotenv()
# ─── Configuration ────────────────────────────────────────────────────────────
MONGO_URI = os.getenv("MONGODB_URI", "")
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


def fetch_team_details(team_id: str) -> dict:
    """Fetch complete team details using the lookup endpoint for better data quality."""
    url = f"{API_BASE}/lookupteam.php"
    resp = requests.get(url, params={"id": team_id}, timeout=15)
    resp.raise_for_status()
    result = resp.json().get("teams")
    return result[0] if result else {}


def build_doc(raw: dict, league_key: str) -> dict:
    """Map TheSportsDB fields to our sports_teams schema.
    
    Note: The lookup endpoint (used in fetch_team_details) returns more complete data
    than search_all_teams, particularly for strTeamBadge and strStadiumDescription
    which contain better city/location info for international teams.
    """
    # Extract city with fallback logic
    city = (raw.get("strCity") or "").strip()
    # If city is missing, try strCountry as a fallback, but prefer stadium location if available
    if not city:
        # Some teams have location info in stadium-related fields
        city = (raw.get("strCountry") or "").strip()
    
    return {
        "team_name":    (raw.get("strTeam") or "").strip(),
        "league":       league_key,
        "city":         city,
        "abbreviation": (raw.get("strTeamShort") or "").strip(),
        # strTeamBadge from the lookup endpoint is more reliable than search endpoint
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
    total_teams_found = 0

    for league_key, league_name in LEAGUES.items():
        print(f"Fetching {league_key:15s} ({league_name}) … ", end="", flush=True)
        try:
            teams = fetch_teams(league_name)
        except Exception as exc:
            print(f"FAILED — {exc}")
            continue

        print(f"{len(teams)} teams found")

        # For each team, fetch full details using the lookup endpoint
        for raw in teams:
            team_id = raw.get("idTeam")
            if not team_id:
                continue
            
            try:
                # Fetch full team details (includes better logo and city data)
                full_team = fetch_team_details(str(team_id))
                if not full_team:
                    continue
                    
                doc = build_doc(full_team, league_key)
                if not doc["team_name"]:
                    continue
                    
                ops.append(
                    UpdateOne(
                        {"team_name": doc["team_name"], "league": league_key},
                        {"$set": doc},
                        upsert=True,
                    )
                )
                total_teams_found += 1
                
                # Be polite to the free tier — delay between lookups
                time.sleep(DELAY)
            except Exception as exc:
                print(f"  ⚠ Failed to lookup team {team_id}: {exc}")
                continue

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
