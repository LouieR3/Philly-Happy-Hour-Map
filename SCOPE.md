# Project Scope: Philly Mappy Hour
**Version:** 2.0  
**Status:** Active Development  
**Target Platform:** Mobile-First Web App  
**Live URL:** https://www.philly-mappy-hour.com  
**API (Railway):** https://philly-happy-hour-map-production.up.railway.app

---

## 1a. Executive Summary
Philly Mappy Hour is a hyper-local geospatial application designed to help Philadelphia residents navigate the city's bar scene with granular precision. Moving beyond generic discovery apps, it focuses on three high-value verticals: **Quizzo**, **Happy Hours (with pricing analytics)**, and **Niche Amenities** (Pool tables and Sports-specific bars). The platform also hosts an internal **Pennoni Softball League tracker** for team stat management.

---

## 1b. Project Objectives
* **Intelligent Geospatial Search:** Resolve the conflict between subjective neighborhood names and official city boundaries using GeoJSON polygons.
* **Data-Driven Happy Hour Grades:** Use LLM-powered scraping to extract drink prices and "grade" deals based on neighborhood averages.
* **Advanced Filtering:** Additive, multi-filter system (Time buckets, Day selectors, Amenity overlays).
* **Community Verification:** User-submitted data gated behind authentication; admin moderation workflow to keep the database fresh.

---

## 2. Competitive Landscape

### City Wide (App)
* **Strengths:** Dedicated mobile app; strong social presence; lists specific deal times and clean mobile map UI.
* **Weaknesses:** Data frequently outdated; inconsistent formatting; lacks niche details like table quality or drink-level price searches.

### Djour (Web Map)
* **Strengths:** High brand trust; highlights "vibe" items like espresso martinis and pool tables.
* **Weaknesses:** Hard-coded Leaflet structures; limited filter UX; data entry is manually intensive and hard to scale.

### Pooltables.nyc (Niche Map)
* **Strengths:** Gold standard for amenity-specific mapping; includes table sizes, brands, pricing models.
* **Weaknesses:** NYC only; lacks happy hour or non-pool context.

**The Philly Mappy Hour Edge:** AI automation for menu parsing + GeoJSON-accurate neighborhood search + community-verified data behind authentication.

---

## 3. What's Already Built

### Bar Map Features
* Leaflet map with custom marker clustering
* Quizzo filter: day, start-time buckets (6–7, 7–8, 8–9 PM), neighborhood
* Pool bar map with table specs, pricing model, and Yelp enrichment
* Sports bar map filterable by league and team affiliation
* Bar detail cards with photos, hours, Yelp rating, and happy hour info

### Admin System
* Two-factor login: custom image CAPTCHA (select Vitruvian Man grid) → password
* Admin dashboard at `/admin.html` for approving/rejecting bar submissions and edits
* Admin-only controls on softball tracker (Clear stats, delete game)
* Cookie-based session (`adminToken`, `SameSite: None; Secure` in production for cross-origin Railway ↔ static host)
* CAPTCHA token stored server-side in memory map (not a cookie); single-use, 30-minute expiry

### Softball League Tracker (`/softball.html`)
* 2026 season schedule pre-seeded in MongoDB (12 games)
* Per-game stat entry: AB, H, 2B, 3B, HR, RBI, R with drag-to-reorder rows, live totals row
* Copy previous game's roster into next game form
* Special results: Win by Forfeit (7–0, no stats) and Rain Out (no score or stats)
* Box score view per game with computed TB, AVG, SLG, OPS
* Season stats tab: aggregated AVG, SLG, OPS, RC, WAR (matching softball.py formula) with sortable columns and formula info tooltips
* Record banner (W-L-T) + run differential; WF counts as Win +7 run diff, RO ignored
* WAR formula: replacement pool = bottom-5 eligible batters (≥ 6 AB) by AVG; `WAR = (RC − Replacement_RC) / 12`

### Backend / Infrastructure
* Express.js on Railway with two MongoDB Atlas connections: `quizzo_bars` DB and `mappy_hour` DB
* Static files served from `www.philly-mappy-hour.com` (separate static host); API always at Railway URL
* Firebase Admin SDK initialized for token verification (user auth groundwork laid)
* Rate limiting on public search endpoints

---

## 4. Core Functional Requirements

### A. The Mapping Engine
* **Hybrid Neighborhood Logic:** GeoJSON polygon layer identifies exact neighborhood; macro-area searches capture sub-neighborhoods (e.g., "Center City" → Rittenhouse, Wash West, Logan Square).
* **Geospatial Indexing:** MongoDB `$geoWithin` queries for precise location-based results.

### B. Advanced Filter System (Additive Logic)
* **Time:** Start-time bucket filter (6–7, 7–8, 8–9 PM).
* **Day of Week:** Multi-select chips.
* **Amenity Overlays:** Toggle Quizzo / Pool / Sports layers without losing geographic filters.

### C. Authentication & Access Control *(Next Priority)*

#### Current State
* Admin-only login: image CAPTCHA + password. Session cookie valid 24 hours.
* No user-level accounts; bar submissions are open to anyone.

#### Target State
* **Google OAuth + Email/Password login** via Firebase Authentication for general users.
* **Admin access** determined by identity, not a separate password page:
  * If the user is logged in with `lou3@lourodriguez.com` (or other designated admin emails), the admin dashboard is unlocked automatically — no separate login flow needed.
  * The CAPTCHA remains as the single gate for the pure-password admin path (fallback for direct admin access without a Google account).
* **Submission gating:** Only authenticated users (Google or email login) can submit new bars or edit existing bars. Anonymous users see the map but get a "Sign in to contribute" prompt on the submit form.
* **Session persistence:** Firebase ID tokens stored client-side; verified server-side on protected routes.

### D. The Scraper & LLM Pipeline *(Phase 2)*
* **Automated Ingestion:** Crawl bar websites and PDFs found via Yelp API metadata.
* **Structured Extraction:** LLM (Claude/GPT-4o) parses raw menu text into structured JSON:
  * `drink_name`, `drink_type` (beer/wine/cocktail/shot), `standard_price`, `happy_hour_price`, `time_window`.
* **Analytics:** "Martini Index" / "Citywide Special Index" comparing bar value against neighborhood medians.

### E. Niche Vertical Features
* **Pool Bar Map:** Table count, pricing model (hourly vs. coin-op), cue/table condition. *(Live)*
* **Sports Bar Map:** Filter by team support (Premier League, Big 5, NFL, etc.). *(Live)*

---

## 5. Implementation Roadmap

### Phase 1: Foundation ✅ (Complete)
* Bar map with Quizzo, Pool, and Sports layers
* Admin dashboard with moderation workflow
* Bar submission and edit submission flows
* Softball League tracker (full 2026 season)

### Phase 2: Authentication & Submission Gating *(Current Focus)*
* Firebase Google OAuth + email/password login UI (sign-in modal or dedicated page)
* Server middleware to verify Firebase ID tokens on POST `/submit-bar` and POST `/submit-edit`
* Admin role check: if decoded Firebase UID matches admin email (`lou3@lourodriguez.com`), grant admin session automatically — no CAPTCHA needed
* "Sign in to contribute" prompt on submission forms for unauthenticated users; map browsing remains public
* User profile page (submitted bars history, saved bars placeholder)

### Phase 3: Location Services
* **Share location:** Browser Geolocation API prompt to share current position
* **"You are here" marker:** User's position shown on the map as a distinct pin
* **Nearby bar query:** Spatial query (MongoDB `$near`) to find bars within a configurable radius of the user
* **Sidebar sorted by distance:** When location is active, the sidebar bar list re-sorts by walking/straight-line distance; distance label shown per entry ("0.3 mi")
* **"Near Me" filter toggle:** One-tap button to switch between default sort and proximity sort without losing other active filters

### Phase 4: User Engagement — Saves, Ratings & Friends
* **Save bars:** Logged-in users can bookmark bars to a personal list; "Saved" icon on bar cards
* **Want-to-Visit list:** Separate from saves — a wishlist bucket distinct from bars already visited
* **Bar ratings (per category):** Users rate each bar on:
  * Price value (1–5)
  * Vibe (1–5)
  * Noise level (1–5)
  * Drink quality (1–5)
  * Overall (1–5)
  * Optional short text tip
  * Ratings available on Quizzo, Pool, and Sports bar maps independently
* **Aggregated scores:** Each bar shows average community ratings alongside individual user rating
* **Friends system:**
  * Search for other users by name or username
  * Send / accept friend requests
  * Friends activity feed: see what bars friends saved, rated, or visited
  * Friends' ratings visible on bar detail cards ("Your friend Alex rated this 4/5 for vibe")

### Phase 5: Happy Hour Discovery Map (MVP)
**Goal:** Let users find bars with active happy hours and verify info at the source.

* Identify bars that advertise happy hours via website, PDF menu, or publicly available sources
* Display participating bars on an interactive map layer (toggleable alongside Quizzo/Pool/Sports)
* Bar detail panel shows: happy hour days, start time, end time, source link
* Filter by:
  * Day of week
  * Happy hour start time / end time
  * Neighborhood
* Link users directly to the original source (website URL, PDF, Instagram)
* **Success criteria:** Users can identify bars with active happy hours and verify info from the source

### Phase 6: Happy Hour Menu Extraction & Normalization
**Goal:** Transform unstructured happy hour menus into searchable, comparable data.

* **Scraper pipeline:** Playwright-based crawler for bar website URLs and PDF menu links stored in MongoDB
* **ML/LLM menu extraction:**
  * Accept both PDF uploads and live web URLs as input
  * Use Claude or GPT-4o to parse unstructured formats: image-based PDFs, HTML menus, Instagram link-in-bios
  * Extract: drink names, food items, happy hour prices, discount descriptions, time windows
  * Flag low-confidence extractions for human review in admin dashboard
  * Output: `{ item_name, category, standard_price, happy_hour_price, time_window, confidence_score }`
* **Drink normalization:**
  * "Miller Lite" → Light Beer | "Yards Philly Pale Ale" → Pale Ale | "Stella Artois" → Lager
  * "House Cabernet" → Red Wine | "Casamigos Margarita" → Margarita
  * Classify by: beer (style + brewery), wine (varietal/region), cocktails, shots, wine-by-the-glass
* **Data enrichment:** Assign neighborhood to each venue; standardize drink and food categories
* **Success criteria:** Happy hour offerings are searchable across venues; similar drinks are grouped consistently

### Phase 7: Full Menu Price Intelligence
**Goal:** Enable comparisons between regular menu pricing and happy hour pricing.

* Scrape full drink menus where available alongside happy hour menus
* Extract standard (non-HH) menu prices and normalize using the same category system
* Associate regular menu items with happy hour equivalents
* **Analytics:**
  * Regular price vs. happy hour price per item
  * Savings amount and discount percentage
  * Pricing breakdowns by drink type, neighborhood, venue, and bar category
* **Example queries the platform should answer:**
  * Cheapest Espresso Martini in Center City
  * Average Margarita happy hour price by neighborhood
  * Largest discount on draft lager
  * Best value Old Fashioned in Philadelphia
* **Success criteria:** Users can compare pricing across venues; platform supports meaningful deal analysis

### Phase 8: Happy Hour Scoring & Recommendation Engine
**Goal:** Surface the best happy hours through scoring, filtering, and rankings.

* **Happy Hour Value Score** per bar, factoring:
  * Number of discounted items
  * Average discount percentage
  * Drink and food variety
  * Price competitiveness vs. neighborhood median
  * Uniqueness of offerings
* **Drink-specific rankings:** Best Margarita / Beer / Wine / Cocktail happy hours
* **Advanced filters:** drink category, specific drink type, price range, neighborhood, day, time window, HH score
* **Rankings & Insights pages:**
  * Best Happy Hours in Philadelphia (overall)
  * Best Happy Hours by Neighborhood
  * Cheapest Drinks by Category
  * Highest Value Cocktail Programs
  * Neighborhood Happy Hour Comparisons
* **Success criteria:** Users discover high-value happy hours quickly; platform becomes a destination for deal discovery

### Phase 9: B2B Partner Portal
* **"Claim Your Bar" flow:** Bar owners verify ownership and get a dashboard to update hours, menu, and deals directly
* **Photo-to-menu tool:** Owner uploads a menu photo → LLM parses → owner reviews and confirms extracted items
* **Verified badge + search priority** for partner bars
* **Analytics for owners:** "150 people searched for Espresso Martinis in your zip code this week"

### Phase 10: Mobile App
* **PWA hardening:** Offline support, home-screen install prompt, push notifications for saved bar happy hour alerts
* **React Native conversion:** Full native app wrapping current feature set using Expo or bare React Native
* **App Store submission:** Apple App Store (TestFlight → public release) and Google Play Store
* **Native features:** GPS background location, push notifications, native share sheet, haptic feedback on ratings
* **Deep linking:** Bar detail URLs open directly in the app if installed

---

## 6. Technical Stack
* **Frontend:** Vanilla JS / HTML / CSS (current); React/Next.js migration planned for Phase 8+ to enable React Native app sharing
* **Mapping:** Leaflet.js with custom clustering
* **Server (Railway):** Node.js / Express deployed on Railway — handles **all** server-side interactions: API routes, MongoDB queries, auth verification, cookie management, Yelp API proxying, CSV export, and any future LLM/scraper jobs. Railway is the single server; the static host has no server-side capability whatsoever.
* **Database:** MongoDB Atlas (two DBs: `quizzo_bars`, `mappy_hour`)
* **Auth:** Firebase Authentication (Google OAuth + email/password); Firebase Admin SDK runs on Railway for server-side token verification
* **AI/Automation:** Playwright (scraping), Claude API / OpenAI (menu extraction), PDF.js or pdf-parse (PDF ingestion)
* **Mobile:** Expo / React Native (Phase 10); PWA manifest + service worker as intermediate step
* **Hosting:** Static files on `www.philly-mappy-hour.com`; all server interactions go through Railway at `https://philly-happy-hour-map-production.up.railway.app`

---

## 7. Success Metrics
* **Data Accuracy:** <5% error rate in LLM-extracted pricing
* **Auth Adoption:** >80% of submissions come from authenticated users within 1 month of launch
* **Menu Coverage:** LLM pipeline able to extract structured data from >70% of bar menu formats (PDF, HTML, image)
* **Engagement:** Return-user rate for "Search by Drink Price" queries
* **Community Growth:** 20+ verified user-submitted edits or bar additions per month

---

## 8. Known Architecture Notes

### Railway is the only server
Every server-side interaction in this project goes through Railway — database reads/writes, authentication checks, Yelp API proxying, CSV generation, cookie issuance, and future scraper jobs. `www.philly-mappy-hour.com` is a **static file host only** (no routing, no middleware, no server logic). Any request to a path on that domain that isn't a static file returns a 404. This is the most common source of bugs: never point `API_BASE` at the static domain.

* **`API_BASE` rule:** In every JS file that makes fetch calls, `API_BASE` in production must always be `https://philly-happy-hour-map-production.up.railway.app`. Relative URLs (`API_BASE = ''`) will 404 because the static host has no routes.
* **Cross-origin cookies:** Admin session cookie uses `SameSite: None; Secure: true` in production to allow `credentials: 'include'` fetch calls from the static host to Railway. Locally: `SameSite: Lax; Secure: false`.
* **Softball data:** Lives in `mappy_hour` DB, `softball_games` collection. Schedule seeded on server startup (idempotent).
* **Admin email:** `lou3@lourodriguez.com` — designated for auto-admin access under the Firebase auth model.
* **Environment:** Railway sets `NODE_ENV=production` automatically. Local dev uses `.env` with `dotenv`.
* **Admin email:** `lou3@lourodriguez.com` — this is the target identity for auto-admin access under the new auth model.
