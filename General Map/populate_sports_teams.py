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
DELAY    = 1.0   # seconds between league API calls

# Friendly league key → TheSportsDB league name string
LEAGUES = {
    "NFL":            "NFL",
    "NBA":            "NBA",
    "MLB":            "MLB",
    "NHL":            "NHL",
    # "MLS":            "Major League Soccer",
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
    """Map TheSportsDB search_all_teams fields to our sports_teams schema.
    
    For American sports (NFL, NBA, MLB, NHL):
    - Uses strTeamAlternate as team name
    - Extracts city by removing strTeamAlternate from strTeam
    
    For other sports (e.g., Premier League):
    - Uses strTeam as team name
    - Extracts city from strLocation: "Neighborhood, City, Country" format
    """
    american_sports = {"NFL", "NBA", "MLB", "NHL"}
    
    # Extract team name and city based on league type
    if league_key in american_sports:
        team_name = (raw.get("strTeamAlternate") or "").strip()
        full_team = (raw.get("strTeam") or "").strip()
        # Extract city by removing the team alternate name from full team name
        if team_name and full_team.endswith(team_name):
            city = full_team[:-len(team_name)].strip()
        else:
            city = ""
    else:
        # For non-American sports, use strTeam as team name
        team_name = (raw.get("strTeam") or "").strip()
        # Extract city from strLocation (format: "Neighborhood, City, Country")
        city = ""
        if raw.get("strLocation"):
            parts = [p.strip() for p in raw.get("strLocation", "").split(",")]
            if len(parts) >= 2:
                city = parts[1]  # Middle part is the city
            elif len(parts) == 1:
                city = parts[0]  # Fallback to first part if only one
        
        # If location-based extraction failed, try strCity
        if not city:
            city = (raw.get("strCity") or "").strip()
        
        # If still no city, try country as last resort
        if not city:
            city = (raw.get("strCountry") or "").strip()
    
    # Try both badge field names for maximum compatibility
    logo_url = (raw.get("strTeamBadge") or "").strip()
    if not logo_url:
        logo_url = (raw.get("strBadge") or "").strip()
    
    return {
        "team_name":    team_name,
        "league":       league_key,
        "city":         city,
        "abbreviation": (raw.get("strTeamShort") or "").strip(),
        "logo_url":     logo_url,
        "team_color":   (raw.get("strColour1") or "").strip(),
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

        # Process each team directly from search results
        for raw in teams:
            if not raw.get("strTeam"):
                continue
            
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
            total_teams_found += 1
            
            # Modest delay between records
            time.sleep(0.1)

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
