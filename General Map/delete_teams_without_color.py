#!/usr/bin/env python3
"""
delete_teams_without_color.py
Deletes all records from sports_teams collection that don't have team_color field.
"""

import os
import sys
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGODB_URI", "")
DB_NAME  = "mappy_hour"
COLLECTION = "sports_teams"

def main():
    if not MONGO_URI:
        print("ERROR: Set MONGODB_URI environment variable.")
        sys.exit(1)

    client = MongoClient(MONGO_URI, tls=True, tlsAllowInvalidCertificates=True,
                         serverSelectionTimeoutMS=15000)
    col = client[DB_NAME][COLLECTION]
    
    print(f"Connected → {DB_NAME}.{COLLECTION}\n")
    
    # Count before deletion
    before = col.count_documents({})
    print(f"Total records before: {before}")
    
    # Delete records without team_color
    result = col.delete_many({
        "$or": [
            {"team_color": {"$exists": False}},
            {"team_color": ""},
            {"team_color": None}
        ]
    })
    
    print(f"Deleted: {result.deleted_count} records\n")
    
    # Count after deletion
    after = col.count_documents({})
    print(f"Total records after: {after}")
    
    client.close()

if __name__ == "__main__":
    main()
