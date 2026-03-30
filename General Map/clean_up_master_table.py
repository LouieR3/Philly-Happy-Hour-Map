"""
clean_and_upload.py

Cleans MasterTable.csv and uploads to MongoDB as a new collection.

Cleaning steps:
  1. Parse Neighborhoods → clean comma-separated string
  2. Parse Categories    → proper Python list
  3. Drop SIPS/RW detail columns
  4. Set SIPS_PARTICIPANT and RW_PARTICIPANT to "N"
  5. Drop any duplicate .1 columns
  6. Upload to MongoDB
"""

import os
import re
import ast
import json
import pandas as pd
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────
_HERE      = os.path.dirname(os.path.abspath(__file__))
MASTER_CSV = os.path.join(_HERE, "..", "Csv", "MasterTable.csv")

MONGO_URI   = os.getenv("MONGODB_URI")
DB_NAME     = "mappy_hour"          # change if needed
COLLECTION  = "bars"                # new collection name

# Columns to drop entirely
DROP_COLS = [
    "SIPS_URL", "SIPS_COCKTAILS", "SIPS_WINE", "SIPS_BEER",
    "SIPS_HALFPRICEDAPPS", "RW_URL", "RW_DETAILS", "RW_DEALS",
    "RW_MENU", "RW_PHOTO", "RW_Score",
]

# ── Helpers ───────────────────────────────────────────────────────────────────

def _parse_list_field(val) -> list:
    """Parse a value that might be a Python list literal string, a
    comma-separated string, or already a list. Returns a clean Python list."""
    if pd.isna(val) or val == "" or val == "[]" or val == "['']":
        return []
    if isinstance(val, list):
        return [v.strip() for v in val if v and str(v).strip()]
    s = str(val).strip()
    # Try ast.literal_eval first (handles "['a', 'b']" style)
    if s.startswith("["):
        try:
            parsed = ast.literal_eval(s)
            if isinstance(parsed, list):
                return [str(v).strip() for v in parsed if v and str(v).strip()]
        except Exception:
            # Strip the brackets and treat as comma-separated
            s = s.strip("[]").replace("'", "").replace('"', "")
    # Split on comma
    return [v.strip() for v in s.split(",") if v.strip()]


def _clean_neighborhoods(val) -> str | None:
    """
    Normalise the messy Neighborhoods column into a clean comma-separated string.

    Input can look like any of:
      "Rittenhouse Square, Penn Center"
      "['Art Museum District', 'Logan Square']"
      "Penn Center, Logan Square['Market East']Rittenhouse Square"   ← mixed mess

    Strategy: extract every quoted token and every bare word-run, deduplicate,
    return as "A, B, C" or None if empty.
    """
    if pd.isna(val) or str(val).strip() in ("", "[]", "['']", '[""]'):
        return None

    s = str(val)

    # Pull out all single-quoted strings from list literals
    quoted = re.findall(r"'([^']+)'", s)

    # Remove list-literal fragments to get bare comma-separated parts
    bare = re.sub(r"\[.*?\]", ",", s)
    bare_parts = [p.strip() for p in bare.split(",") if p.strip()]

    all_parts = quoted + bare_parts

    # Deduplicate preserving order
    seen = set()
    result = []
    for p in all_parts:
        p = p.strip()
        if p and p.lower() not in seen:
            seen.add(p.lower())
            result.append(p)

    return ", ".join(result) if result else None


def _clean_value(val):
    """Convert NaN / 'nan' / empty strings to None for clean MongoDB docs."""
    if val is None:
        return None
    if isinstance(val, float):
        import math
        return None if math.isnan(val) else val
    s = str(val).strip()
    if s.lower() in ("nan", "none", "", "[]", "['']", '[""]'):
        return None
    return val


# ── Main ──────────────────────────────────────────────────────────────────────

def clean(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # 1. Drop .1 duplicate columns
    dup_cols = [c for c in df.columns if c.endswith(".1")]
    if dup_cols:
        # For each .1 col, try to merge into the base column first
        for col in dup_cols:
            base = col[:-2]
            if base in df.columns:
                df[base] = df[base].where(
                    df[base].notna() & (df[base].astype(str).str.strip() != ""),
                    df[col]
                )
        df.drop(columns=dup_cols, inplace=True)
        print(f"  Dropped duplicate columns: {dup_cols}")

    # 2. Drop SIPS/RW detail columns
    to_drop = [c for c in DROP_COLS if c in df.columns]
    df.drop(columns=to_drop, inplace=True, errors="ignore")
    print(f"  Dropped SIPS/RW columns: {to_drop}")

    # 3. Set SIPS_PARTICIPANT and RW_PARTICIPANT to N
    for col in ("SIPS_PARTICIPANT", "RW_PARTICIPANT"):
        df[col] = "N"
    print("  Set SIPS_PARTICIPANT and RW_PARTICIPANT to N")

    # 4. Clean Neighborhoods
    if "Neighborhoods" in df.columns:
        df["Neighborhoods"] = df["Neighborhoods"].apply(_clean_neighborhoods)
        print("  Cleaned Neighborhoods column")

    # 5. Parse Categories into real lists
    if "Categories" in df.columns:
        df["Categories"] = df["Categories"].apply(_parse_list_field)
        print("  Parsed Categories into lists")

    return df


def to_mongo_docs(df: pd.DataFrame) -> list[dict]:
    """Convert DataFrame rows to clean MongoDB documents."""
    docs = []
    for _, row in df.iterrows():
        doc = {}
        for col, val in row.items():
            cleaned = _clean_value(val)
            if cleaned is not None:
                doc[col] = cleaned
        docs.append(doc)
    return docs


def upload(docs: list[dict]):
    if not MONGO_URI:
        raise ValueError("MONGODB_URI not set in .env")

    client = MongoClient(MONGO_URI)
    db     = client[DB_NAME]
    col    = db[COLLECTION]

    # Drop existing collection so this is a clean load
    col.drop()
    print(f"\n  Dropped existing '{COLLECTION}' collection (if any)")

    result = col.insert_many(docs)
    print(f"  Inserted {len(result.inserted_ids)} documents into {DB_NAME}.{COLLECTION}")
    client.close()


def main():
    print(f"Reading {MASTER_CSV}")
    df = pd.read_csv(MASTER_CSV, dtype=str)
    print(f"  {len(df)} rows, {len(df.columns)} columns")

    print("\nCleaning...")
    df = clean(df)
    print(f"  After cleaning: {len(df.columns)} columns")

    # Save a cleaned CSV alongside the original for reference
    cleaned_path = MASTER_CSV.replace("MasterTable.csv", "MasterTable_cleaned.csv")
    df.to_csv(cleaned_path, index=False)
    print(f"  Saved cleaned CSV to {cleaned_path}")

    print("\nConverting to MongoDB documents...")
    docs = to_mongo_docs(df)
    print(f"  {len(docs)} documents ready")

    print(f"\nUploading to MongoDB ({DB_NAME}.{COLLECTION})...")
    upload(docs)

    print("\nDone.")


if __name__ == "__main__":
    main()