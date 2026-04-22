#!/usr/bin/env python3
"""
test_api.py — Quick script to test TheSportsDB API and print first team from each league
"""

import time
import requests

API_BASE = "https://www.thesportsdb.com/api/v1/json/3"
DELAY = 2.0

LEAGUES = {
    "NFL":            "NFL",
    "NBA":            "NBA",
    "MLB":            "MLB",
    "NHL":            "NHL",
    # "MLS":            "Major League Soccer",
    "Premier League": "English Premier League",
}

def fetch_teams(sportsdb_league_name: str) -> list:
    """Call TheSportsDB and return the raw teams list for a given league."""
    url = f"{API_BASE}/search_all_teams.php"
    print(f"  Fetching: {url}?l={sportsdb_league_name}")
    resp = requests.get(url, params={"l": sportsdb_league_name}, timeout=15)
    resp.raise_for_status()
    return resp.json().get("teams") or []


def fetch_team_details(team_id: str) -> dict:
    """Fetch complete team details using the lookup endpoint."""
    url = f"{API_BASE}/lookupteam.php"
    resp = requests.get(url, params={"id": team_id}, timeout=15)
    resp.raise_for_status()
    result = resp.json().get("teams")
    return result[0] if result else {}


print("Testing TheSportsDB API — First team from each league:\n")

for league_key, league_name in LEAGUES.items():
    print(f"{league_key:15s} ({league_name})")
    try:
        teams = fetch_teams(league_name)
        print(f"  → Got {len(teams)} teams")
        
        if teams:
            first = teams[0]
            print(f"  First team: {first.get('strTeam')} (ID: {first.get('idTeam')})")
            print(f"    City:     {first.get('strCity') or first.get('strStadiumLocation')}")
            print(f"    Location: {first.get('strStadiumLocation')}")
            print(f"    Badge:    {first.get('strTeamBadge') or first.get('strBadge')}")
        else:
            print(f"  → No teams returned!")
    except Exception as exc:
        print(f"  ERROR: {exc}")
    
    print()
    time.sleep(DELAY)

print("Done!")
