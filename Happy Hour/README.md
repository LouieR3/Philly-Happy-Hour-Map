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
| `fetcher.py` | **Playwright** renderer for JS-heavy sites (returns rendered text + links + screenshot). |
| `pass1_llm.py` | **Accurate pass 1 (recommended).** Render homepage → the LLM picks the HH link (or "none") → render it → the LLM extracts structured days/times. Stores confidence + provenance; reads few-shot `examples_pass1.jsonl`. |
| `llm_client.py` | Provider-agnostic LLM call. **Defaults to a local Ollama model — free, private, no Anthropic tokens.** Switch with `LLM_PROVIDER` (`ollama` \| `openai` \| `anthropic`). |
| `pass1_discover.py` | Heuristic pass 1 (requests + keywords). No LLM/Playwright needed; lower accuracy — kept as a fallback. |
| `pass2_extract.py` | Read `happy_hours.menu_text` → items + prices → normalize → `happy_hour_items`. `--llm` for Claude extraction. |
| `llm_extract.py` | Claude menu-item extractor used by `pass2_extract.py --llm`. |
| `drink_normalizer.py` | The stdlib type system for drink normalization (corpus + `difflib`; optional scikit-learn). |
| `db.py` | Mongo connection (`mappy_hour`), reads `MONGODB_URI` from env or `../.env`. |

### LLM backend (local by default — no Anthropic cost)
`pass1_llm.py` calls whatever `llm_client.py` is pointed at. The default is a
**local Ollama model**, so it's free and nothing leaves your machine:

```bash
# one-time: install Ollama from https://ollama.com, then pull a model
ollama pull llama3.1            # ~4.7GB; good default. Alts: qwen2.5, llama3.2:3b (faster/smaller)
python pass1_llm.py --check-llm # sends one tiny structured prompt to confirm it works
```

Override per shell if you ever want a different backend (still no Anthropic cost for the first two):
```bash
$env:OLLAMA_MODEL="qwen2.5"                     # different local model
$env:LLM_PROVIDER="openai"; $env:OPENAI_BASE_URL="https://api.groq.com/openai/v1"  # free Groq tier, etc.
$env:LLM_PROVIDER="anthropic"                   # opt-in, COSTS TOKENS
```

> Trade-off: a local 7–8B model is less accurate than Claude at the messiest pages.
> That's fine for the accuracy-first loop below — human review catches misses and the
> `examples_pass1.jsonl` few-shots improve the next run. Start with `--limit`/`--neighborhood`.

### Recommended workflow (accuracy first, then scale)
1. Install Ollama + `ollama pull llama3.1`; `pip install -r requirements.txt && python -m playwright install chromium`; set `MONGODB_URI`.
2. **Small batch:** `python pass1_llm.py --limit 30` → review the results (esp. `needs_review`/`uncertain`) in the admin queue. Scope to one neighborhood with `--neighborhood Rittenhouse` (point-in-polygon against `philadelphia-neighborhoods.geojson`; the cap applies *after* the filter, so `--limit 30 --neighborhood Rittenhouse` = up to 30 Rittenhouse bars).
3. **Correct + teach:** append each human correction as a line in `examples_pass1.jsonl` — those become few-shot examples that improve the next run (the learning loop).
4. Once pass 1 is reliable on the batch, ship the **day/time map** (no menu items needed), then run `pass2_extract.py --llm` for items, and widen the batch.

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
