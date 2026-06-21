# Happy Hour pipeline (v1.0)

Two-pass system that finds each bar's happy-hour menu, extracts the items and
prices, and normalizes every drink to a comparable type
("Sam Adams Lager" → **Lager**, "Lime Margarita" → **Margarita**).

It reuses the labeled corpus already in `../Sips/Sips ML Test Data/`
(`cocktails.txt`, `wines.txt`, `beers.txt`) plus a beer-style lexicon.

---

## 1.0 scope & current focus

This maps to SCOPE Phases 5–6. The goal of **1.0** is: *for as many Philly bars
as possible, know whether they have a happy hour, when it is, where the source
is, and what's on it as structured, normalized, priced items.* That's the data
foundation the map and (later) the scoring/Phase 7–8 analytics sit on.

| In scope for 1.0 | Deferred (post-1.0) |
|---|---|
| Discover HH menu **link/PDF** per bar (pass 1) | Playwright/JS-rendered menus (pass 1 is `requests`+BS4 only) |
| Parse HH **day/time window** (best-effort) | Instagram link-in-bio / image-only menus (OCR) |
| Extract **item + price** from HTML/PDF text (pass 2) | Regular (non-HH) menu prices + savings % (Phase 7) |
| **Normalize** drink → category + canonical type (pass 2) | HH Value Score / rankings (Phase 8) |
| Confidence + `needs_review` flag for admin moderation | LLM extraction for the hardest formats (hook noted below) |
| Store in Mongo (`happy_hours`, `happy_hour_items`) | Map layer + filters UI (serving layer — see "Next") |

**Pipeline = two passes** (run pass 1, then pass 2):

```
bars ──pass1──> happy_hours ──pass2──> happy_hour_items
       (find link/pdf,        (extract item+price,
        times, raw text)       normalize type)
```

---

## Files

| File | Role |
|---|---|
| `drink_normalizer.py` | **The ML/type system.** `DrinkNormalizer.normalize(raw)` → `{category, normalized_item, confidence, needs_review}`. Stdlib-only (corpus + `difflib` fuzzy); optional scikit-learn path. |
| `pass1_discover.py` | Crawl each bar's site → best HH/menu link or PDF → raw text + HH times → upsert `happy_hours`. |
| `pass2_extract.py` | Read `happy_hours.menu_text` → `(item, price)` lines → normalize → upsert `happy_hour_items`. |
| `db.py` | Mongo connection (`mappy_hour`), reads `MONGODB_URI` from env or `../.env`. |
| `requirements.txt` | `pip install -r requirements.txt` |

## Mongo collections written

```jsonc
// happy_hours  (one per bar)
{ bar_name, yelp_alias, website, source_type: "html"|"pdf",
  source_url, hh_times_raw, hh_days, hh_start, hh_end,
  menu_text, status: "found"|"no_source"|"error", note }

// happy_hour_items  (one per extracted item)
{ bar_name, source_url, raw_item, normalized_item, category,
  hh_price, time_window, confidence, needs_review }
```

## Run

```bash
pip install -r requirements.txt
export MONGODB_URI="mongodb+srv://…/quizzo_bars?…"   # valid creds (Railway/.env)

# verify the ML with no DB/network needed:
python drink_normalizer.py --self-test
python pass2_extract.py --self-test

# real run (start small):
python pass1_discover.py --limit 25 --dry-run     # preview discovery
python pass1_discover.py --limit 25               # write happy_hours
python pass2_extract.py --dry-run                 # preview items
python pass2_extract.py                           # write happy_hour_items
```

## How normalization works

1. **Clean** the raw string (strip price, ABV, packaging words like
   *can/draft/bottle/house*).
2. **Category**: food → seltzer → cider → wine → beer → cocktail/spirit, by
   corpus membership + keyword lexicons.
3. **Normalized item** per category:
   - *cocktail* → canonical name from `cocktails.txt` (substring, else `difflib` fuzzy).
   - *beer* → **style** from the style lexicon (lager/IPA/pale ale/stout/…); brand-only ⇒ `Beer`.
   - *wine* → varietal/color from `wines.txt` + keyword map.
4. **Confidence** drives `needs_review` (`<0.6` or category `other`) so the admin
   dashboard can show low-confidence rows for a human pass.

## Known limitations / next

- Pass 1 uses `requests`+BeautifulSoup, so **JS-rendered** menus and
  **image-only PDFs** won't yield text — add Playwright + OCR later, or wire the
  **LLM hook** (Claude/GPT) in pass 2 for the messiest formats (the scope's
  "flag low-confidence for review" already feeds that).
- **Serving layer (to make it a *map*)**: add `GET /api/happy-hours` to
  `server.js` reading these two collections, then a toggleable Happy Hour layer
  on the front-end (filter by day/time/neighborhood, popup shows items + source
  link). The data model here is built to drop straight into that.
