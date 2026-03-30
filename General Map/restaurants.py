import os
import ast
import random
import pandas as pd
import yelpapi
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import json
import re
import time
import numpy as np
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# ------------------------------------------------
# Full pipeline: find Philly bars → get Yelp info →
# geocode (lat/long from Yelp) → find reservation
# links → clean up → output CSV with yelp_alias
# and website fields.
#
# Steps:
#   1. Search Yelp by neighborhood → YelpAliases.csv
#   2. Fetch detailed data for new bars → MasterTable.csv
#   3. Consolidate multi-column attributes
#   4. Find OpenTable/Resy/Tock links from bar websites
#   5. Final column cleanup
#   6. Write output CSV
# ------------------------------------------------

# --- Load API keys from .env.example ------------------------------------
def _load_yelp_keys(env_path=None):
    """Parse the yelp_api_keys list from .env.example."""
    if env_path is None:
        env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env.example")
    with open(env_path, "r") as f:
        content = f.read()
    match = re.search(r"yelp_api_keys\s*=\s*(\[.*?\])", content, re.DOTALL)
    if not match:
        raise ValueError("yelp_api_keys list not found in .env.example")
    return ast.literal_eval(match.group(1))


class YelpClientRotator:
    """Wraps yelpapi and rotates to the next API key on rate-limit errors."""

    def __init__(self, keys):
        if not keys:
            raise ValueError("No Yelp API keys provided.")
        self._keys = keys
        self._index = 0
        self._client = yelpapi.YelpAPI(keys[0])
        print(f"  Using Yelp key [{self._index + 1}/{len(self._keys)}]")

    def _rotate(self):
        self._index += 1
        if self._index >= len(self._keys):
            raise RuntimeError("All Yelp API keys have hit their rate limit.")
        self._client = yelpapi.YelpAPI(self._keys[self._index])
        print(f"  Rotated to Yelp key [{self._index + 1}/{len(self._keys)}]")

    def _call(self, method_name, **kwargs):
        while True:
            try:
                return getattr(self._client, method_name)(**kwargs)
            except Exception as e:
                msg = str(e).upper()
                if "RATE_LIMIT" in msg or "429" in msg or "TOO_MANY_REQUESTS" in msg:
                    print(f"  Rate limit hit on key {self._index + 1}: {e}")
                    self._rotate()
                else:
                    raise

    def search_query(self, **kwargs):
        return self._call("search_query", **kwargs)

    def business_query(self, **kwargs):
        return self._call("business_query", **kwargs)

    def business_match_query(self, **kwargs):
        return self._call("business_match_query", **kwargs)


# --- Config -----------------------------------------------------------
_HERE = os.path.dirname(os.path.abspath(__file__))
_CSV_DIR = os.path.join(_HERE, "..", "Csv")
ALIASES_CSV = os.path.join(_CSV_DIR, "YelpAliases.csv")
MASTER_CSV = os.path.join(_CSV_DIR, "MasterTable.csv")
OUTPUT_CSV = os.path.join(_CSV_DIR, "MasterTable.csv")
YELP_BASE_URL = "https://www.yelp.com/biz/"

# --- Browser-like session for Yelp scraping ---------------------------
def _make_yelp_session():
    """Create a requests Session that looks like a real browser to Yelp."""
    session = requests.Session()
    retry = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503])
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Referer": "https://www.yelp.com/",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
        "Upgrade-Insecure-Requests": "1",
    })
    # Seed the session with cookies by hitting the homepage first
    try:
        session.get("https://www.yelp.com", timeout=10)
    except Exception:
        pass
    return session

_YELP_SESSION = None  # lazily initialised on first scrape

NEIGHBORHOODS = [
    "Rittenhouse Square, Philadelphia",
    "Gayborhood, Philadelphia",
    "Grad Hospital, Philadelphia",
    "Reading Terminal, Philadelphia",
    "Italian Market, Philadelphia",
    "Passyunk, Philadelphia",
    "Queen Village, Philadelphia",
    "Point Breeze, Philadelphia",
    "Center City, Philadelphia",
    "Old City, Philadelphia",
    "Northern Liberties, Philadelphia",
    "Fishtown, Philadelphia",
    "South Philly, Philadelphia",
    "Fairmount, Philadelphia",
    "Chinatown, Philadelphia",
    "University City, Philadelphia",
    "Temple, Philadelphia",
    "Port Richmond, Philadelphia",
]
# -----------------------------------------------------------------------


# ═══════════════════════════════════════════════════════════════════════
# STEP 1 — Find new bars by neighborhood, update YelpAliases.csv
# ═══════════════════════════════════════════════════════════════════════
def step1_find_new_bars(yelp):
    """Search each neighborhood for bars and add new ones to YelpAliases.csv."""
    print("\n=== STEP 1: Finding new bars by neighborhood ===")

    if os.path.exists(ALIASES_CSV):
        aliases_df = pd.read_csv(ALIASES_CSV)
    else:
        aliases_df = pd.DataFrame(columns=["Name", "Yelp Alias"])

    for neighborhood in NEIGHBORHOODS:
        print(f"  Searching: {neighborhood}")
        try:
            results = yelp.search_query(
                location=neighborhood,
                price=2,
                categories="Bars",
                limit=50,
            )
        except Exception as e:
            print(f"    Error searching {neighborhood}: {e}")
            continue

        for biz in results.get("businesses", []):
            alias = biz["alias"]
            name = biz["name"]
            if alias not in aliases_df["Yelp Alias"].values:
                print(f"    + {name}")
                new_row = pd.DataFrame([{"Name": name, "Yelp Alias": alias}])
                aliases_df = pd.concat([aliases_df, new_row], ignore_index=True)

    aliases_df.to_csv(ALIASES_CSV, index=False)
    print(f"  Saved {len(aliases_df)} aliases to {ALIASES_CSV}")
    return aliases_df


# ═══════════════════════════════════════════════════════════════════════
# STEP 2 — Fetch detailed Yelp data (lat/long, website, hours, etc.)
# ═══════════════════════════════════════════════════════════════════════
def _find_business_website(json_obj):
    """Recursively find a BusinessWebsite URL in the Yelp page JSON."""
    if isinstance(json_obj, dict):
        if json_obj.get("__typename") == "BusinessWebsite":
            return json_obj.get("url")
        for value in json_obj.values():
            result = _find_business_website(value)
            if result:
                return result
    elif isinstance(json_obj, list):
        for item in json_obj:
            result = _find_business_website(item)
            if result:
                return result
    return None


def _find_first_rating(d):
    """Recursively find the first 'rating' value in a nested dict."""
    for key, value in d.items():
        if isinstance(value, dict):
            result = _find_first_rating(value)
            if result is not None:
                return result
        if key == "rating":
            return value
    return None


def _fetch_bar_details(row, yelp):
    """Fetch full details for one bar via the Yelp API + Yelp page scrape."""
    yelp_alias = row["Yelp Alias"]
    restaurant_name = row["Name"]
    print(f"  Fetching: {restaurant_name} ({yelp_alias})")

    try:
        response = yelp.business_query(id=yelp_alias)
    except Exception as e:
        print(f"    Error fetching {yelp_alias}: {e}")
        return None

    categories = [c["title"] for c in response.get("categories", [])]
    address = ", ".join(response["location"]["display_address"])

    # --- scrape Yelp page for extra attributes ---
    api_only_result = {
        "Name": restaurant_name,
        "Yelp Alias": yelp_alias,
        "Address": address,
        "Latitude": response["coordinates"]["latitude"],
        "Longitude": response["coordinates"]["longitude"],
        "Website": None,
        "Review Count": response.get("review_count"),
        "Price": response.get("price"),
        "Categories": categories,
        "Neighborhoods": [],
        "Yelp Rating": response.get("rating"),
        "Open Table Link": None,
        "Sips Participant": "N",
        "Restaurant Week Participant": "N",
    }

    scrape_result = _scrape_yelp_page(yelp_alias, restaurant_name)
    if scrape_result is None:
        return api_only_result

    business_properties, hours_properties, neighborhoods_json, website, rating = scrape_result

    return {
        **api_only_result,
        "Website": website,
        "Neighborhoods": neighborhoods_json,
        "Yelp Rating": rating or response.get("rating"),
        **business_properties,
        **hours_properties,
    }


def step2_fetch_bar_details(aliases_df, yelp):
    """Fetch Yelp details for bars not already in MasterTable, then append."""
    print("\n=== STEP 2: Fetching details for new bars ===")

    if os.path.exists(MASTER_CSV):
        master_df = pd.read_csv(MASTER_CSV)
        existing = set(master_df["Yelp Alias"].dropna().values) if "Yelp Alias" in master_df.columns else set()
    else:
        master_df = pd.DataFrame()
        existing = set()

    new_bars = aliases_df[~aliases_df["Yelp Alias"].isin(existing)]
    print(f"  {len(new_bars)} new bars to fetch (skipping {len(aliases_df) - len(new_bars)} already in MasterTable)")

    new_data = []
    for _, row in new_bars.iterrows():
        details = _fetch_bar_details(row, yelp)
        if details:
            new_data.append(details)

    if new_data:
        new_df = pd.DataFrame(new_data)
        master_df = pd.concat([master_df, new_df], ignore_index=True)

    master_df = _calculate_scores(master_df)
    master_df.to_csv(MASTER_CSV, index=False)
    print(f"  MasterTable now has {len(master_df)} rows — saved to {MASTER_CSV}")
    return master_df


def _scrape_yelp_page(yelp_alias, name):
    """Scrape a single Yelp page and return (business_properties, hours_properties,
    neighborhoods_json, website, rating) or None on failure.

    Handles 403 / Cloudflare blocks explicitly so callers can decide whether
    to retry or skip.
    """
    global _YELP_SESSION
    if _YELP_SESSION is None:
        _YELP_SESSION = _make_yelp_session()

    url = YELP_BASE_URL + yelp_alias
    time.sleep(random.uniform(2.0, 4.5))  # slightly longer delay to reduce blocks

    try:
        resp = _YELP_SESSION.get(url, timeout=15)
    except Exception as e:
        print(f"    Request error for {name}: {e}")
        return None

    if resp.status_code == 403:
        print(f"    403 Cloudflare block for {name} — resetting session and retrying once")
        _YELP_SESSION = _make_yelp_session()  # fresh cookies
        time.sleep(random.uniform(5.0, 9.0))
        try:
            resp = _YELP_SESSION.get(url, timeout=15)
        except Exception as e:
            print(f"    Retry failed for {name}: {e}")
            return None
        if resp.status_code == 403:
            print(f"    Still blocked after retry — skipping {name}")
            return None

    if resp.status_code != 200:
        print(f"    HTTP {resp.status_code} for {name} — skipping")
        return None

    soup = BeautifulSoup(resp.text, "html.parser")

    # Detect Cloudflare JS challenge page (returns 200 but no real content)
    if "enable JS and disable any ad blocker" in resp.text or "captcha-delivery.com" in resp.text:
        print(f"    Cloudflare JS challenge for {name} — skipping")
        return None

    script_tag = soup.find("script", {"data-apollo-state": True})
    if script_tag is None:
        print(f"    No Apollo state tag for {name} (status {resp.status_code})")
        return None

    json_str = re.sub(r"&quot;", '"', script_tag.text[4:-3])
    try:
        json_object = json.loads(json_str)
    except json.JSONDecodeError as e:
        print(f"    JSON parse error for {name}: {e}")
        return None

    day_map = {
        "Mon": "Monday", "Tue": "Tuesday", "Wed": "Wednesday",
        "Thu": "Thursday", "Fri": "Friday", "Sat": "Saturday", "Sun": "Sunday",
    }
    business_properties = {}
    neighborhoods_json = []
    hours_properties = {}

    for value in json_object.values():
        if not isinstance(value, dict):
            continue

        if "displayText" in value:
            display_text = value["displayText"]
            is_active = value["isActive"]
            replacements = [
                ("&amp;", "and"), ("Not Good", "Good"),
                ("Not Wheelchair Accessible", "Wheelchair Accessible"),
                ("Dogs Not Allowed", "Dogs Allowed"), ("Very Loud", "Loud"),
                ("Free Wi-fi", "Wi-fi"), ("Smoking Allowed", "Smoking"),
                ("Happy Hour Specials", "Happy Hour"),
                ("Many Vegetarian Options", "Vegetarian Options"),
                ("Casual Dress", "Casual"),
            ]
            for old, new in replacements:
                if old in display_text:
                    if old.startswith("Not ") or old == "Dogs Not Allowed":
                        is_active = not is_active
                    display_text = display_text.replace(old, new)
            if "Takes Reservations" in display_text:
                display_text = display_text.replace("Takes ", "")
            if "No " in display_text:
                display_text = display_text.replace("No ", "")
                is_active = not is_active
            if "Paid Wi-Fi" in display_text:
                continue
            if "Best nights on" in display_text:
                for part in display_text.split("Best nights on ")[1].split(","):
                    business_properties[f"Best nights on {part.strip()}"] = is_active
            else:
                for text in [t.strip() for t in display_text.split(",")]:
                    business_properties[text] = is_active

        if "neighborhoods" in value:
            nbhd = value["neighborhoods"]
            if isinstance(nbhd, dict):
                neighborhoods_json = nbhd.get("json", neighborhoods_json)
            elif isinstance(nbhd, list):
                neighborhoods_json = nbhd

        if "regularHours" in value and "dayOfWeekShort" in value:
            short_day = value["dayOfWeekShort"]
            full_day = day_map.get(short_day, short_day)
            hours_list = value["regularHours"].get("json", [])
            if hours_list:
                hours_properties[full_day] = hours_list[0]

    raw_website = _find_business_website(json_object)
    website = raw_website.replace("&#x2F;", "/") if raw_website else None
    rating = _find_first_rating(json_object)

    return business_properties, hours_properties, neighborhoods_json, website, rating


# --- Column mapping: raw scraped property → target consolidated column --------
# Used in step2b to write scraped values directly into the right final columns
# instead of dumping everything as raw boolean columns.
_PROP_TO_COLUMN = {
    # Parking
    "Street Parking": "Parking", "Bike Parking": "Parking",
    "Valet Parking": "Parking", "Validated Parking": "Parking",
    "Garage Parking": "Parking", "Private Lot Parking": "Parking",
    # Best nights
    "Best nights on Monday": "Best_Nights", "Best nights on Tuesday": "Best_Nights",
    "Best nights on Wednesday": "Best_Nights", "Best nights on Thursday": "Best_Nights",
    "Best nights on Friday": "Best_Nights", "Best nights on Saturday": "Best_Nights",
    "Best nights on Sunday": "Best_Nights",
    # Payment
    "Accepts Credit Cards": "Payment", "Accepts Android Pay": "Payment",
    "Accepts Apple Pay": "Payment", "Accepts Cryptocurrency": "Payment",
    # Offers
    "Offers Delivery": "Offers", "Offers Takeout": "Offers",
    "Offers Catering": "Offers", "Offers Military Discount": "Offers",
    "Online ordering-only": "Offers", "Delivery": "Offers", "Takeout": "Offers",
    # Options (dietary)
    "Vegan Options": "Options", "Vegetarian Options": "Options",
    "Limited Vegetarian Options": "Options", "Pescatarian Options": "Options",
    "Keto Options": "Options", "Soy-Free Options": "Options",
    "Dairy-Free Options": "Options", "Gluten-Free Options": "Options",
    # Vibes
    "Trendy": "Vibes", "Classy": "Vibes", "Intimate": "Vibes",
    "Romantic": "Vibes", "Upscale": "Vibes", "Dressy": "Vibes",
    "Hipster": "Vibes", "Touristy": "Vibes", "Divey": "Vibes",
    "Casual": "Vibes", "Quiet": "Vibes", "Loud": "Vibes", "Moderate Noise": "Vibes",
    # Accessibility
    "Open to All": "Accessibility", "Wheelchair Accessible": "Accessibility",
    "Gender-neutral restrooms": "Accessibility",
    # Dogs
    "Dogs Allowed": "Dogs_Allowed",
    # Smoking
    "Smoking": "Smoking",
    # Reservation type
    "By Appointment Only": "Reservation_Type", "Walk-ins Welcome": "Reservation_Type",
    "Reservations": "Reservation_Type", "Takes Reservations": "Reservation_Type",
    # Seating
    "Outdoor Seating": "Seating", "Heated Outdoor Seating": "Seating",
    "Covered Outdoor Seating": "Seating", "Private Dining": "Seating",
    "Drive-Thru": "Seating",
    # Meal types
    "Lunch": "Meal_Types", "Dessert": "Meal_Types",
    "Brunch": "Meal_Types", "Dinner": "Meal_Types",
    # Music
    "Live Music": "Music", "DJ": "Music", "Background Music": "Music",
    "Juke Box": "Music", "Karaoke": "Music",
    # Alcohol
    "Alcohol": "Alcohol_Options", "Happy Hour": "Alcohol_Options",
    "Beer and Wine Only": "Alcohol_Options", "Full Bar": "Alcohol_Options",
    # Amenities
    "TV": "Amenities", "Pool Table": "Amenities",
    "Wi-Fi": "Amenities", "EV charging station available": "Amenities",
}

# Strip these prefixes when building the consolidated value string
_COL_STRIP_PREFIX = {
    "Best_Nights": "Best nights on ",
    "Payment": "Accepts ",
}


def _append_to_col(current_val, new_item, strip_prefix=""):
    """Append new_item to a comma-separated column value, avoiding duplicates."""
    item = new_item.replace(strip_prefix, "").strip()
    if not item:
        return current_val
    if pd.isna(current_val) or current_val == "":
        return item
    existing = [v.strip() for v in str(current_val).split(",")]
    if item not in existing:
        return current_val + ", " + item
    return current_val


def step2b_refresh_missing_attributes(master_df):
    """Re-scrape Yelp pages for rows missing Sunday hours (proxy for a failed
    scrape), and write results directly into the target consolidated columns."""
    print("\n=== STEP 2b: Re-fetching attributes for bars missing scraped data ===")

    alias_col = "Yelp Alias"
    sunday_col = "Sunday"
    target_cols = [
        "Neighborhoods", "Monday", "Tuesday", "Wednesday", "Thursday",
        "Friday", "Saturday", "Sunday", "Smoking", "Parking", "Best_Nights",
        "Payment", "Minority_Owned", "Good_For", "Offers", "Options", "Vibes",
        "Accessibility", "Dogs_Allowed", "Packaging", "Reservation_Type",
        "Seating", "Meal_Types", "Music", "Alcohol_Options", "Amenities",
    ]

    # Ensure all target columns exist
    for col in target_cols:
        if col not in master_df.columns:
            master_df[col] = None

    if sunday_col not in master_df.columns:
        master_df[sunday_col] = None

    needs_refresh = (
        master_df[alias_col].notna() &
        (master_df[sunday_col].isna() | (master_df[sunday_col] == ""))
    )
    targets = master_df[needs_refresh]
    print(f"  {len(targets)} bars need attribute refresh")

    blocked_count = 0

    for idx, row in targets.iterrows():
        yelp_alias = row[alias_col]
        name = row["Name"]

        result = _scrape_yelp_page(yelp_alias, name)
        if result is None:
            blocked_count += 1
            # After 3 consecutive blocks, reset session and pause longer
            if blocked_count >= 3:
                print(f"  3 blocks in a row — resetting session and pausing 30s")
                _YELP_SESSION = None
                time.sleep(30)
                blocked_count = 0
            continue

        blocked_count = 0  # reset on success
        business_properties, hours_properties, neighborhoods_json, website, rating = result

        # --- Write hours directly into day columns ---
        for day, hours_val in hours_properties.items():
            if day in master_df.columns:
                master_df.at[idx, day] = hours_val

        # --- Write neighborhoods ---
        if neighborhoods_json:
            cleaned = ", ".join([v for v in neighborhoods_json if v]) if isinstance(neighborhoods_json, list) else neighborhoods_json
            master_df.at[idx, "Neighborhoods"] = cleaned or None

        # --- Map each business property to its target consolidated column ---
        for prop, is_active in business_properties.items():
            if not is_active:
                continue
            target_col = _PROP_TO_COLUMN.get(prop)
            if target_col is None:
                continue  # unknown property — skip rather than creating a new raw column
            strip = _COL_STRIP_PREFIX.get(target_col, "")
            master_df.at[idx, target_col] = _append_to_col(
                master_df.at[idx, target_col], prop, strip_prefix=strip
            )

        # --- Website and rating (only fill if currently missing) ---
        if website:
            ws_col = "Website"
            if ws_col in master_df.columns and (pd.isna(master_df.at[idx, ws_col]) or master_df.at[idx, ws_col] == ""):
                master_df.at[idx, ws_col] = website

        if rating is not None:
            rating_col = "Yelp_Rating" if "Yelp_Rating" in master_df.columns else "Yelp Rating" if "Yelp Rating" in master_df.columns else None
            if rating_col and (pd.isna(master_df.at[idx, rating_col])):
                master_df.at[idx, rating_col] = rating

        print(f"    Refreshed: {name}")

        # Checkpoint save every 25 rows so progress isn't lost on a crash
        if (list(targets.index).index(idx) + 1) % 25 == 0:
            master_df.to_csv(MASTER_CSV, index=False)
            print(f"  Checkpoint saved ({list(targets.index).index(idx) + 1}/{len(targets)})")

    master_df.to_csv(MASTER_CSV, index=False)
    print(f"  Saved refreshed MasterTable")
    return master_df


def _calculate_scores(df):
    """Compute Popularity Score and Restaurant Week Score."""
    if "Review Count" not in df.columns or "Yelp Rating" not in df.columns:
        return df

    price_mapping = {"$": 1, "$$": 2, "$$$": 3, "$$$$": 4}
    df = df.copy()
    df["_price_num"] = df["Price"].map(price_mapping).fillna(2)
    df["Yelp Rating"] = pd.to_numeric(df["Yelp Rating"], errors="coerce")

    for col in ["Review Count", "Yelp Rating", "_price_num"]:
        mn, mx = df[col].min(), df[col].max()
        df[f"_{col}_scaled"] = (df[col] - mn) / (mx - mn) if mx != mn else 0

    df["Popularity Score"] = (
        0.3 * df["_Review Count_scaled"]
        + 0.7 * df["_Yelp Rating_scaled"]
        + 0.7 * df["__price_num_scaled"]
    )
    mn, mx = df["Popularity Score"].min(), df["Popularity Score"].max()
    if mx != mn:
        df["Popularity Score"] = (
            1 + (df["Popularity Score"] - mn) / (mx - mn) * 99
        ).round()
        df["Restaurant Week Score"] = df["Popularity Score"]

    df.drop(
        columns=[c for c in df.columns if c.startswith("_")],
        inplace=True,
        errors="ignore",
    )
    return df


# ═══════════════════════════════════════════════════════════════════════
# STEP 3 — Consolidate multi-column attribute fields
# ═══════════════════════════════════════════════════════════════════════
def _combine_columns(df, cols, new_col, strip_prefix=""):
    """Combine boolean columns into a comma-separated string column.

    For rows that have raw boolean data (new bars), compute from raw cols.
    For rows that already have a consolidated value (old bars), keep it.
    """
    present = [c for c in cols if c in df.columns]
    if not present:
        return df

    has_raw = df[present].notna().any(axis=1)  # True for rows with raw data
    df[present] = df[present].fillna(False)
    combined = df[present].apply(
        lambda x: ", ".join(x.index[x]).replace(strip_prefix, ""), axis=1
    )

    if new_col in df.columns:
        existing_good = df[new_col].notna() & (df[new_col] != "") & ~has_raw
        df[new_col] = df[new_col].where(existing_good, combined)
    else:
        df[new_col] = combined

    df.drop(columns=present, inplace=True)
    return df


def step3_consolidate_columns(df):
    """Merge many boolean attribute columns into readable combined columns."""
    print("\n=== STEP 3: Consolidating attribute columns ===")
    df = df.copy()

    # Parking
    df = _combine_columns(
        df,
        ["Street Parking", "Bike Parking", "Valet Parking",
         "Validated Parking", "Garage Parking", "Private Lot Parking"],
        "Parking",
    )

    # Best Nights
    df = _combine_columns(
        df,
        ["Best nights on Monday", "Best nights on Tuesday", "Best nights on Wednesday",
         "Best nights on Thursday", "Best nights on Friday", "Best nights on Saturday",
         "Best nights on Sunday"],
        "Best_Nights",
        strip_prefix="Best nights on ",
    )

    # Payment
    df = _combine_columns(
        df,
        ["Accepts Credit Cards", "Accepts Android Pay", "Accepts Apple Pay", "Accepts Cryptocurrency"],
        "Payment",
        strip_prefix="Accepts ",
    )

    # Minority-owned (drop only)
    minority_cols = ["Women-owned", "Latinx-owned", "Asian-owned", "Black-owned", "Veteran-owned", "LGBTQ-owned"]
    df.drop(columns=[c for c in minority_cols if c in df.columns], inplace=True)

    # Good For
    if "Good For Groups" in df.columns and "Good for Groups" in df.columns:
        df["Good For Groups"] = df["Good For Groups"].fillna(df["Good for Groups"])
        df.drop(columns="Good for Groups", inplace=True)
    good_for_cols = [
        "Good For Dinner", "Good For Kids", "Good For Lunch", "Good For Dancing",
        "Good For Working", "Good For Brunch", "Good For Dessert", "Good For Breakfast",
        "Good For Groups", "Good For Late Night", "All Ages", "Late Night", "Good For Working.1",
    ]
    df.drop(columns=[c for c in good_for_cols if c in df.columns], inplace=True)

    # Offers
    if "Offers Delivery" in df.columns and "Delivery" in df.columns:
        df["Offers Delivery"] = df["Offers Delivery"].fillna(df["Delivery"])
        df.drop(columns="Delivery", inplace=True)
    if "Offers Takeout" in df.columns and "Takeout" in df.columns:
        df["Offers Takeout"] = df["Offers Takeout"].fillna(df["Takeout"])
        df.drop(columns="Takeout", inplace=True)
    df = _combine_columns(
        df,
        ["Offers Delivery", "Offers Takeout", "Offers Catering", "Offers Military Discount", "Online ordering-only"],
        "Offers",
    )

    # Dietary options
    if "Vegetarian Options" in df.columns and "Many Vegetarian Options" in df.columns:
        df["Vegetarian Options"] = df["Vegetarian Options"].fillna(df["Many Vegetarian Options"])
        df.drop(columns="Many Vegetarian Options", inplace=True)
    df = _combine_columns(
        df,
        ["Vegan Options", "Limited Vegetarian Options", "Pescatarian Options",
         "Keto Options", "Vegetarian Options", "Soy-Free Options", "Dairy-Free Options", "Gluten-Free Options"],
        "Options",
    )

    # Vibes
    if "Casual" in df.columns and "Casual Dress" in df.columns:
        df["Casual"] = df["Casual"].fillna(df["Casual Dress"])
        df.drop(columns="Casual Dress", inplace=True)
    df = _combine_columns(
        df,
        ["Trendy", "Classy", "Intimate", "Romantic", "Upscale", "Dressy",
         "Hipster", "Touristy", "Divey", "Casual", "Quiet", "Loud", "Moderate Noise"],
        "Vibes",
    )

    # Accessibility
    if "Wheelchair Accessible" in df.columns and "Not Wheelchair Accessible" in df.columns:
        df["Wheelchair Accessible"] = df["Wheelchair Accessible"] | ~df["Not Wheelchair Accessible"].fillna(False)
        df["Wheelchair Accessible"] = df["Wheelchair Accessible"].mask(df["Wheelchair Accessible"] == False, np.nan)
        df.drop(columns="Not Wheelchair Accessible", inplace=True)
    df = _combine_columns(
        df, ["Open to All", "Wheelchair Accessible", "Gender-neutral restrooms"], "Accessibility"
    )

    # Dogs
    if "Dogs Allowed" in df.columns and "Dogs Not Allowed" in df.columns:
        df["Dogs_Allowed"] = df["Dogs Allowed"] | ~df["Dogs Not Allowed"].fillna(False)
        df["Dogs_Allowed"] = df["Dogs_Allowed"].mask(df["Dogs_Allowed"] == False, np.nan)
        df.drop(columns=["Dogs Not Allowed", "Dogs Allowed"], inplace=True, errors="ignore")

    # Smoking
    if "Smoking Allowed" in df.columns:
        df["Smoking"] = df.get("Smoking", pd.Series(dtype=object)).fillna(df["Smoking Allowed"])
        df.drop(columns=["Smoking Allowed"], inplace=True, errors="ignore")
    if "Smoking Outside Only" in df.columns:
        df.drop(columns="Smoking Outside Only", inplace=True)

    # Eco packaging (drop)
    eco_cols = ["Plastic-free packaging", "Provides reusable tableware",
                "Compostable containers available", "Bring your own container allowed"]
    df.drop(columns=[c for c in eco_cols if c in df.columns], inplace=True)

    # Reservations
    if "Takes Reservations" in df.columns and "Reservations" in df.columns:
        df["Takes Reservations"] = df["Takes Reservations"].fillna(df["Reservations"])
        df.drop(columns="Reservations", inplace=True)
    df = _combine_columns(
        df, ["By Appointment Only", "Walk-ins Welcome", "Takes Reservations"], "Reservation_Type"
    )

    # Seating
    df = _combine_columns(
        df,
        ["Outdoor Seating", "Heated Outdoor Seating", "Covered Outdoor Seating", "Private Dining", "Drive-Thru"],
        "Seating",
    )

    # Meal types
    df = _combine_columns(df, ["Lunch", "Dessert", "Brunch", "Dinner"], "Meal_Types")

    # Music
    df = _combine_columns(df, ["Live Music", "DJ", "Background Music", "Juke Box", "Karaoke"], "Music")

    # Alcohol / Happy Hour
    if "Happy Hour" in df.columns and "Happy Hour Specials" in df.columns:
        df["Happy Hour"] = df["Happy Hour"].fillna(df["Happy Hour Specials"])
        df.drop(columns="Happy Hour Specials", inplace=True)
    df = _combine_columns(df, ["Alcohol", "Happy Hour", "Beer and Wine Only", "Full Bar"], "Alcohol_Options")

    # Amenities
    if "Wi-Fi" in df.columns and "Free Wi-Fi" in df.columns:
        df["Wi-Fi"] = df["Wi-Fi"].fillna(df["Free Wi-Fi"])
        df.drop(columns="Free Wi-Fi", inplace=True)
    if "Loud" in df.columns and "Very Loud" in df.columns:
        df["Loud"] = df["Loud"].fillna(df["Very Loud"])
        df.drop(columns="Very Loud", inplace=True)
    df = _combine_columns(df, ["TV", "Pool Table", "Wi-Fi", "EV charging station available"], "Amenities")
    for col in ["Virtual restaurant", "Waiter Service", "Paid Wi-Fi"]:
        if col in df.columns:
            df.drop(columns=col, inplace=True)

    # Sips / RW nulls
    if "Sips Participant" in df.columns:
        df["Sips Participant"] = df["Sips Participant"].fillna("N")
    if "Restaurant Week Participant" in df.columns:
        df["Restaurant Week Participant"] = df["Restaurant Week Participant"].fillna("N")

    # Neighborhoods: [] or [''] → blank
    if "Neighborhoods" in df.columns:
        def _clean_neighborhoods(val):
            if isinstance(val, list):
                filtered = [v for v in val if v]
                return ", ".join(filtered) if filtered else None
            if isinstance(val, str):
                stripped = val.strip()
                if stripped in ("[]", "", "['']", '[""]'):
                    return None
            return val if val else None
        df["Neighborhoods"] = df["Neighborhoods"].apply(_clean_neighborhoods)

    # Drop duplicate .1 columns created by earlier bad merges
    dup_cols = [c for c in df.columns if c.endswith(".1")]
    if dup_cols:
        df.drop(columns=dup_cols, inplace=True)
        print(f"  Dropped duplicate columns: {dup_cols}")

    print(f"  Columns after consolidation: {len(df.columns)}")
    return df


# ═══════════════════════════════════════════════════════════════════════
# STEP 4 — Find OpenTable / Resy / Tock reservation links
# ═══════════════════════════════════════════════════════════════════════
def _check_for_res_link(url):
    """Scrape a bar's website for OpenTable, Resy, or Tock reservation links."""
    try:
        response = requests.get(url, timeout=15)
        if response.status_code != 200:
            return None
        soup = BeautifulSoup(response.text, "html.parser")

        ot = soup.find("a", {"href": lambda x: x and "opentable" in x.lower()})
        resy = soup.find("a", {"href": lambda x: x and "resy" in x.lower()})
        tock = soup.find("a", {"href": lambda x: x and "exploretock" in x.lower()})

        if ot:
            return ot.get("href")
        if resy:
            return resy.get("href")
        if tock:
            return tock.get("href")

        # Check a /reservations sub-page
        res_page = soup.find("a", {"href": lambda x: x and "reservations" in x.lower()})
        if res_page:
            res_url = urljoin(url, res_page.get("href"))
            try:
                res_resp = requests.get(res_url, timeout=15)
                if res_resp.status_code == 200:
                    res_soup = BeautifulSoup(res_resp.text, "html.parser")
                    ot2 = res_soup.find("a", {"href": lambda x: x and "opentable" in x.lower()})
                    resy2 = res_soup.find("a", {"href": lambda x: x and "resy" in x.lower()})
                    tock2 = res_soup.find("a", {"href": lambda x: x and "exploretock" in x.lower()})
                    if ot2:
                        return ot2.get("href")
                    if resy2:
                        return resy2.get("href")
                    if tock2:
                        return tock2.get("href")
                    return res_url
            except Exception:
                return res_url
        return None
    except Exception as e:
        print(f"    Link check error ({url}): {e}")
        return None


def step4_find_reservation_links(df):
    """For bars with a website but no reservation link, scrape for one."""
    print("\n=== STEP 4: Finding reservation links ===")

    if "Open Table Link" not in df.columns:
        df["Open Table Link"] = None

    for index, row in df.iterrows():
        has_link = not (pd.isna(row["Open Table Link"]) or row["Open Table Link"] == "")
        has_site = not pd.isna(row.get("Website"))
        if not has_link and has_site:
            result = _check_for_res_link(row["Website"])
            df.at[index, "Open Table Link"] = result
            if result:
                print(f"  Found link for {row['Name']}: {result}")

    return df


# ═══════════════════════════════════════════════════════════════════════
# STEP 5 — Rename columns and write final CSV
# ═══════════════════════════════════════════════════════════════════════
def step5_rename_and_export(df):
    """Rename columns to final names and save the output CSV."""
    print("\n=== STEP 5: Renaming columns and exporting ===")

    column_mapping = {
        "Sips Url": "SIPS_URL",
        "Cocktails": "SIPS_COCKTAILS",
        "Wine": "SIPS_WINE",
        "Beer": "SIPS_BEER",
        "Half-Priced Appetizers": "SIPS_HALFPRICEDAPPS",
        "RW Url": "RW_URL",
        "Details": "RW_DETAILS",
        "Deals Offered": "RW_DEALS",
        "Deal Website": "RW_MENU",
        "Photo": "RW_PHOTO",
        "Sips Participant": "SIPS_PARTICIPANT",
        "Restaurant Week Participant": "RW_PARTICIPANT",
        "Open Table Link": "RESERVATION_LINK",
        "Yelp Rating": "Yelp_Rating",
        "Review Count": "Review_Count",
        "Restaurant Week Score": "RW_Score",
        "Popularity Score": "Popularity",
    }
    df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns}, inplace=True)

    # Ensure key fields are present
    for col in ["Yelp Alias", "Website", "Latitude", "Longitude"]:
        if col not in df.columns:
            df[col] = None

    df.to_csv(OUTPUT_CSV, index=False)
    print(f"  Exported {len(df)} rows to {OUTPUT_CSV}")
    print(f"  Columns: {list(df.columns)}")
    return df


# ═══════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════
def main():
    start = time.time()

    keys = _load_yelp_keys()
    yelp = YelpClientRotator(keys)

    # aliases_df = step1_find_new_bars(yelp)
    aliases_df = pd.read_csv(ALIASES_CSV)
    master_df = step2_fetch_bar_details(aliases_df, yelp)
    master_df = step2b_refresh_missing_attributes(master_df)
    master_df = step3_consolidate_columns(master_df)
    master_df = step4_find_reservation_links(master_df)
    master_df = step5_rename_and_export(master_df)

    print(f"\nDone in {time.time() - start:.1f}s — {len(master_df)} bars in {OUTPUT_CSV}")


if __name__ == "__main__":
    _YELP_SESSION = None  # lazily initialised on first scrape
    # global _YELP_SESSION
    if _YELP_SESSION is None:
        _YELP_SESSION = _make_yelp_session()
    url = YELP_BASE_URL + "balcony-bar-the-kimmel-center-philadelphia"
    time.sleep(random.uniform(1.5, 3.0))  # randomised delay to avoid bot detection
    print(url)
    try:
        yelp_response = _YELP_SESSION.get(url, timeout=15)
        print(f"Status code: {yelp_response.status_code}")
        soup = BeautifulSoup(yelp_response.text, "html.parser")
        print(soup.prettify()[:1000])  # print the first 1000 chars of the page for debugging
        script_tag = soup.find("script", {"data-apollo-state": True})
        print(script_tag)  # print the first 1000 chars of the page for debugging
    except Exception as e:
        print(f"    Scrape error for balcony-bar-the-kimmel-center-philadelphia: {e}")
    
    # main()