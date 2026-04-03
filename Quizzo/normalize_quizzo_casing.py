"""
normalize_quizzo_casing.py

Normalises text casing in the quizzo_bars > 'Quizzo Bars' collection:

  BUSINESS      — fuzzy-matched against mappy_hour.bars.Name (case-insensitive).
                  If a confident match is found (score >= threshold) the canonical
                  Name from bars is used; otherwise the value is title-cased.

  NEIGHBORHOOD  — title-cased  (e.g. "EAST PASSYUNK" → "East Passyunk")
  ADDRESS_STREET — title-cased
  ADDRESS_CITY   — title-cased
  HOST           — title-cased
  BUSINESS_TAGS  — title-cased
  PRIZE_1/2/3_TYPE — title-cased

  WEEKDAY, TIME, EVENT_TYPE, OCCURRENCE_TYPES, ADDRESS_STATE, ADDRESS_ZIP
    are left untouched — the JS filters depend on their exact format.

Run:
    pip install pymongo python-dotenv thefuzz python-Levenshtein
    python normalize_quizzo_casing.py

    # Dry-run (print changes, don't write):
    python normalize_quizzo_casing.py --dry-run
"""

import os
import re
import sys
import argparse
from dotenv import load_dotenv
from pymongo import MongoClient, UpdateOne

load_dotenv()

MONGO_URI = os.getenv("MONGODB_URI")
if not MONGO_URI:
    sys.exit("MONGODB_URI not set in .env")

MAPPY_HOUR_URI = MONGO_URI.replace("quizzo_bars", "mappy_hour")

try:
    from thefuzz import fuzz
except ImportError:
    sys.exit("Run: pip install thefuzz python-Levenshtein")

# ── Config ────────────────────────────────────────────────────────────────────
NAME_MATCH_THRESHOLD = 85   # min fuzz score to accept mappy_hour name as canonical
CHECKPOINT_EVERY     = 50

# Words that stay lowercase in title-case (unless first word)
_LOWERCASE_WORDS = {
    "a", "an", "the", "and", "but", "or", "for", "nor",
    "on", "at", "to", "by", "in", "of", "up", "as",
}
# Always-uppercase tokens (state abbreviations etc.)
_ALWAYS_UPPER = {"pa", "nj", "de", "ny"}

# Fields to title-case (BUSINESS handled separately)
TITLECASE_FIELDS = [
    "NEIGHBORHOOD",
    "ADDRESS_STREET",
    "ADDRESS_CITY",
    "HOST",
    "BUSINESS_TAGS",
    "PRIZE_1_TYPE",
    "PRIZE_2_TYPE",
    "PRIZE_3_TYPE",
]

# Fields whose existing format must be preserved
SKIP_FIELDS = {"WEEKDAY", "TIME", "EVENT_TYPE", "OCCURRENCE_TYPES",
               "ADDRESS_STATE", "ADDRESS_ZIP", "Full_Address",
               "Latitude", "Longitude"}


# ── Helpers ───────────────────────────────────────────────────────────────────
def smart_title(text: str) -> str:
    """Title-case that respects common small words and always-uppercase tokens."""
    if not text:
        return text
    # Replace underscores with spaces for display
    words = text.replace("_", " ").split()
    result = []
    for i, word in enumerate(words):
        low = word.lower()
        if low in _ALWAYS_UPPER:
            result.append(low.upper())
        elif i == 0 or low not in _LOWERCASE_WORDS:
            # Capitalise first letter, lowercase rest — but preserve internal
            # caps like "McSorley's"
            result.append(word[0].upper() + word[1:].lower() if word.isalpha() else word.capitalize())
        else:
            result.append(low)
    return " ".join(result)


def build_bars_lookup(bars_col):
    """Return a list of (name_upper, canonical_name) for fast fuzzy matching."""
    return [
        (b["Name"].upper().strip(), b["Name"])
        for b in bars_col.find({}, {"Name": 1})
        if b.get("Name")
    ]


def best_bars_match(name: str, lookup: list):
    """
    Fuzzy-match name against mappy_hour.bars names.
    Returns (canonical_name, score) or (None, 0).
    """
    target = name.upper().strip()
    best_score = 0
    best_name  = None
    for upper, canonical in lookup:
        score = max(
            fuzz.ratio(target, upper),
            fuzz.token_sort_ratio(target, upper),
        )
        if score > best_score:
            best_score = score
            best_name  = canonical
    return best_name, best_score


# ── Connect ───────────────────────────────────────────────────────────────────
quizzo_client = MongoClient(MONGO_URI)
mappy_client  = MongoClient(MAPPY_HOUR_URI)

quizzo_col = quizzo_client["quizzo_bars"]["Quizzo Bars"]
bars_col   = mappy_client["mappy_hour"]["bars"]

# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true",
                        help="Print planned changes without writing to MongoDB")
    args = parser.parse_args()

    print("\n=== Building mappy_hour bars lookup ===")
    bars_lookup = build_bars_lookup(bars_col)
    print(f"  {len(bars_lookup)} bars loaded")

    print("\n=== Loading quizzo bars ===")
    all_bars = list(quizzo_col.find({}))
    print(f"  {len(all_bars)} quizzo bars loaded\n")

    ops            = []
    changed        = 0
    name_from_bars = 0
    name_titlecase = 0

    for i, bar in enumerate(all_bars, 1):
        updates = {}

        # ── BUSINESS name ────────────────────────────────────────────────────
        current_name = (bar.get("BUSINESS") or "").strip()
        if current_name:
            canonical, score = best_bars_match(current_name, bars_lookup)
            if canonical and score >= NAME_MATCH_THRESHOLD:
                if canonical != current_name:
                    updates["BUSINESS"] = canonical
                    name_from_bars += 1
                    print(f"  [{i}] BUSINESS: '{current_name}' → '{canonical}'  [{score}]")
            else:
                titled = smart_title(current_name)
                if titled != current_name:
                    updates["BUSINESS"] = titled
                    name_titlecase += 1
                    if score > 0:
                        print(f"  [{i}] BUSINESS (title): '{current_name}' → '{titled}'  [best score {score} < {NAME_MATCH_THRESHOLD}]")
                    else:
                        print(f"  [{i}] BUSINESS (title): '{current_name}' → '{titled}'")

        # ── Other text fields ────────────────────────────────────────────────
        for field in TITLECASE_FIELDS:
            val = bar.get(field)
            if not val or not isinstance(val, str):
                continue
            titled = smart_title(val.strip())
            if titled != val.strip():
                updates[field] = titled
                print(f"  [{i}] {field}: '{val}' → '{titled}'")

        if updates:
            changed += 1
            if not args.dry_run:
                ops.append(UpdateOne({"_id": bar["_id"]}, {"$set": updates}))

        # Checkpoint
        if not args.dry_run and ops and i % CHECKPOINT_EVERY == 0:
            result = quizzo_col.bulk_write(ops, ordered=False)
            print(f"\n  — checkpoint: {i}/{len(all_bars)}, modified {result.modified_count} —\n")
            ops = []

    # Final flush
    if not args.dry_run and ops:
        result = quizzo_col.bulk_write(ops, ordered=False)
        print(f"\n  Final flush: modified {result.modified_count}")

    quizzo_client.close()
    mappy_client.close()

    print(f"""
=== Summary {'(DRY RUN)' if args.dry_run else ''} ===
Total bars:              {len(all_bars)}
Records with changes:    {changed}
  BUSINESS from bars:    {name_from_bars}
  BUSINESS title-cased:  {name_titlecase}
{'(No writes performed)' if args.dry_run else 'Done.'}
""")


if __name__ == "__main__":
    main()
