"""
fill_hours.py

For every row in MasterTable.csv where Sunday is empty:
  1. Hit the Yelp business API for that alias
  2. Parse the hours[] array → translate to "HH:MM AM - HH:MM PM" per day
  3. Write Monday-Sunday columns back into the CSV

Also reconciles RESERVATION_LINK / RESERVATION_LINK.1 into one column.
"""

import os
import ast
import re
import time
import random
import pandas as pd
import yelpapi

# ── Config ────────────────────────────────────────────────────────────────────
_HERE    = os.path.dirname(os.path.abspath(__file__))
_CSV_DIR = os.path.join(_HERE, "..", "Csv")
MASTER_CSV = os.path.join(_CSV_DIR, "MasterTable.csv")

DAY_COLS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
# Yelp API day index: 0=Mon … 6=Sun
DAY_INDEX = {0: "Monday", 1: "Tuesday", 2: "Wednesday",
             3: "Thursday", 4: "Friday", 5: "Saturday", 6: "Sunday"}


# ── Load Yelp keys (same loader as restaurants.py) ────────────────────────────
def _load_yelp_keys(env_path=None):
    if env_path is None:
        env_path = os.path.join(_HERE, "..", ".env.example")
    with open(env_path) as f:
        content = f.read()
    match = re.search(r"yelp_api_keys\s*=\s*(\[.*?\])", content, re.DOTALL)
    if not match:
        raise ValueError("yelp_api_keys list not found in .env.example")
    return ast.literal_eval(match.group(1))


class YelpClientRotator:
    def __init__(self, keys):
        if not keys:
            raise ValueError("No Yelp API keys provided.")
        self._keys  = keys
        self._index = 0
        self._client = yelpapi.YelpAPI(keys[0])
        print(f"  Using Yelp key [1/{len(keys)}]")

    def _rotate(self):
        self._index += 1
        if self._index >= len(self._keys):
            raise RuntimeError("All Yelp API keys exhausted.")
        self._client = yelpapi.YelpAPI(self._keys[self._index])
        print(f"  Rotated to key [{self._index + 1}/{len(self._keys)}]")

    def business_query(self, **kwargs):
        while True:
            try:
                return self._client.business_query(**kwargs)
            except Exception as e:
                msg = str(e).upper()
                if "RATE_LIMIT" in msg or "429" in msg or "TOO_MANY_REQUESTS" in msg:
                    print(f"  Rate limit on key {self._index + 1}: {e}")
                    self._rotate()
                else:
                    raise


# ── Hour formatting ───────────────────────────────────────────────────────────
def _fmt_time(t: str) -> str:
    """Convert '1045' → '10:45 AM' / '2130' → '9:30 PM'."""
    t = t.zfill(4)
    h, m = int(t[:2]), int(t[2:])
    period = "AM" if h < 12 else "PM"
    h12 = h % 12 or 12
    return f"{h12}:{m:02d} {period}"


def _parse_hours(hours_list: list) -> dict:
    """
    Parse the Yelp API hours[0]["open"] list into a dict of
    {day_name: "HH:MM AM - HH:MM PM"}.

    Handles overnight spans by carrying over to the next day label,
    and multiple shifts on the same day (e.g. lunch + dinner) by
    joining with " / ".
    """
    day_slots: dict[str, list[str]] = {d: [] for d in DAY_COLS}

    for slot in hours_list:
        day_name = DAY_INDEX.get(slot["day"])
        if day_name is None:
            continue
        start_str = _fmt_time(slot["start"])
        end_str   = _fmt_time(slot["end"])
        day_slots[day_name].append(f"{start_str} - {end_str}")

    return {day: " / ".join(slots) if slots else None
            for day, slots in day_slots.items()}


# ── Main logic ────────────────────────────────────────────────────────────────
def main():
    df = pd.read_csv(MASTER_CSV, dtype=str)

    # Ensure day columns exist
    for col in DAY_COLS:
        if col not in df.columns:
            df[col] = None

    # ── Reconcile RESERVATION_LINK / RESERVATION_LINK.1 ──────────────────────
    if "RESERVATION_LINK" in df.columns and "RESERVATION_LINK.1" in df.columns:
        # Prefer the non-.1 value; fall back to .1 where non-.1 is blank
        df["RESERVATION_LINK"] = df["RESERVATION_LINK"].where(
            df["RESERVATION_LINK"].notna() & (df["RESERVATION_LINK"].str.strip() != ""),
            df["RESERVATION_LINK.1"]
        )
        df.drop(columns=["RESERVATION_LINK.1"], inplace=True)
        print("Reconciled RESERVATION_LINK / RESERVATION_LINK.1 → RESERVATION_LINK")
    elif "RESERVATION_LINK.1" in df.columns:
        df.rename(columns={"RESERVATION_LINK.1": "RESERVATION_LINK"}, inplace=True)
        print("Renamed RESERVATION_LINK.1 → RESERVATION_LINK")

    # ── Find rows missing Sunday ──────────────────────────────────────────────
    needs_hours = (
        df["Yelp Alias"].notna() &
        (df["Sunday"].isna() | (df["Sunday"].str.strip() == ""))
    )
    targets = df[needs_hours]
    total   = len(targets)
    print(f"\n{total} bars missing Sunday hours — fetching from Yelp API\n")

    keys = _load_yelp_keys()
    yelp = YelpClientRotator(keys)

    for i, (idx, row) in enumerate(targets.iterrows(), 1):
        alias = row["Yelp Alias"]
        name  = row.get("Name", alias)
        print(f"  [{i}/{total}] {name} ({alias})")

        time.sleep(random.uniform(0.4, 0.9))   # API is friendlier than scraping

        try:
            response = yelp.business_query(id=alias)
        except Exception as e:
            print(f"    API error: {e} — skipping")
            continue

        hours_blocks = response.get("hours", [])
        regular = next(
            (h for h in hours_blocks if h.get("hours_type") == "REGULAR"),
            hours_blocks[0] if hours_blocks else None
        )

        if regular is None:
            print(f"    No hours in response — skipping")
            continue

        parsed = _parse_hours(regular.get("open", []))

        filled = []
        for day, value in parsed.items():
            if value:                           # only write days that have data
                df.at[idx, day] = value
                filled.append(day[:3])

        print(f"    Filled: {', '.join(filled) if filled else 'none'}")

        # Checkpoint every 25 rows
        if i % 25 == 0:
            df.to_csv(MASTER_CSV, index=False)
            print(f"  — checkpoint saved ({i}/{total}) —")

    df.to_csv(MASTER_CSV, index=False)
    print(f"\nDone — saved {MASTER_CSV}")

    # Summary
    still_missing = df["Sunday"].isna() | (df["Sunday"].str.strip() == "")
    print(f"Rows still missing Sunday: {still_missing.sum()}")


if __name__ == "__main__":
    main()