# Project Scope: Philly Mappy Hour
**Version:** 1.0  
**Status:** Draft / Planning  
**Target Platform:** Mobile-First Web App (PWA)

## 1a. Executive Summary
Philly Mappy Hour is a hyper-local geospatial application designed to help Philadelphia residents navigate the city's bar scene with granular precision. Moving beyond generic discovery apps, it focuses on three high-value verticals: **Quizzo**, **Happy Hours (with pricing analytics)**, and **Niche Amenities** (Pool tables and Sports-specific bars).

---

## 1b. Project Objectives
* **Intelligent Geospatial Search:** Resolve the conflict between subjective neighborhood names and official city boundaries using GeoJSON polygons.
* **Data-Driven Happy Hour Grades:** Use LLM-powered scraping to extract drink prices and "grade" deals based on neighborhood averages.
* **Advanced Filtering:** Transition from single-select dropdowns to an additive, multi-filter system (Time Sliders, Day Selectors, Amenity Tags).
* **Community Verification:** Create a loop for user-submitted data and admin moderation to keep the database fresh.

---

## 2. Competitive Landscape
*Analyzing existing solutions to identify white space and competitive advantages.*

### City Wide (App)
* **Strengths:** Dedicated mobile app; strong social media presence (TikTok/Instagram); lists specific deal times and clean mobile map UI.
* **Weaknesses:** Data is frequently outdated; inconsistent formatting; lacks granular "niche" details like specific table quality or drink-level price searches.

### Djour (Web Map)
* **Strengths:** High brand trust and massive local following; highlights "vibe" items like espresso martinis and pool tables.
* **Weaknesses:** Built on "hard-coded" Leaflet structures; UI/UX for map filtering is limited; data entry is manually intensive and difficult to scale.

### Pooltables.nyc (Niche Map)
* **Strengths:** The gold standard for amenity-specific mapping; includes table sizes, brands, and specific pricing models (per game vs. per hour).
* **Weaknesses:** Geographically restricted to NYC; lacks broader context like happy hour deals or non-pool amenities.

**The Philly Mappy Hour Edge:** Using **AI automation** to scrape and "grade" deals, combined with a **GeoJSON-accurate search** that understands Philly's overlapping neighborhood logic better than a generic API.

---

## 3. Core Functional Requirements

### A. The Mapping Engine
* **Hybrid Neighborhood Logic:** Use a GeoJSON polygon layer to identify exactly which neighborhood a bar is in, while allowing "Macro-Area" searches (e.g., searching "Center City" captures Rittenhouse, Wash West, and Logan Square).
* **Geospatial Indexing:** Implement MongoDB `$geoWithin` queries for precise location-based results.

### B. Advanced Filter System (Additive Logic)
* **Time:** A slider or clock-face UI to filter bars active *at a specific time*.
* **Day of Week:** Multi-select chips (e.g., find bars with Quizzo on "Mon" AND "Tue").
* **Amenity Overlays:** Toggle between "Quizzo," "Pool," and "Sports" layers without losing active geographic filters.

### C. The Scraper & LLM Pipeline
* **Automated Ingestion:** Scrape bar websites and PDFs identified via Yelp API metadata.
* **Structured Extraction:** Use an LLM (GPT-4o/Claude) to parse raw menu text into structured JSON:
    * `drink_name`, `standard_price`, `happy_hour_price`, `time_window`.
* **Analytics:** Calculate the "Martini Index" or "Citywide Special Index" to compare bar value against neighborhood medians.

### D. Niche Vertical Features
* **Pool Bar Map:** Track table count, pricing model (Hourly vs. Coin-op), and cue/table condition.
* **Sports Bar Map:** Filter by team support (Premier League, Big 5, NFL, etc.) and fan-base intensity.

---

## 4. The Grand Vision: A Universal Bar Database
### The Problem: Fragmentation
Drink pricing is unmaintained and volatile. This creates a massive manual overhead for discovery apps and inconsistent information for users.

### The Solution: The Bar Partner Portal
Phase 4 of this project involves transitioning from a **Scraper Model** to a **Partner Model** where bars maintain their own data:
1.  **The Lead Magnet:** Show bars how they appear on the platform (via scraped data) and offer a free dashboard to "claim" their page.
2.  **Incentives for Early Adopters:**
    * **Visibility:** Partnered bars get "Verified" status and priority in search results.
    * **Analytics:** Bars receive data on local search trends (e.g., "150 people searched for Espresso Martinis in your zip code this week").
    * **Low Friction:** Owners can update menus instantly via a direct link or by uploading a photo of their menu for the LLM to process.

---

## 5. Implementation Roadmap

### Phase 1: Foundation & UI Overhaul (Month 1)
* **Data Cleanup:** Map subjective neighborhood strings to official GeoJSON polygons.
* **Filter Logic:** Rewrite frontend state to support additive filtering.
* **Admin Dashboard:** Build the "Accept/Reject" workflow for user-submitted edits.

### Phase 2: The Intelligence Layer (Month 2)
* **Scraper Dev:** Build the pipeline to crawl URLs and extract PDFs.
* **LLM Integration:** Prompt engineering for structured menu data extraction.
* **Pricing Engine:** Develop the "Deal Grade" algorithm based on aggregate data.

### Phase 3: Vertical Expansion & Social (Month 3)
* **Niche Maps:** Launch the Pool and Sports-specific filtering layers.
* **User Accounts:** Implement Auth (NextAuth or Clerk) for "Saved Bars" and "Visited" logs.
* **Social Beta:** Enable following friends to see their reviews and map activity.

### Phase 4: B2B Integration (Month 4+)
* **Owner Portal:** Launch the "Claim Your Bar" features and the photo-to-menu update tool.

---

## 6. Technical Stack
* **Frontend:** React / Next.js (Tailwind CSS for mobile-first UI).
* **Mapping:** Leaflet, maybe Mapbox GL JS if needed later.
* **Backend:** Node.js (Express) or Python (FastAPI).
* **Database:** MongoDB (Geospatial indexes).
* **AI/Automation:** Playwright (Scraping), OpenAI/Anthropic API (Data curation).

---

## 7. Success Metrics
* **Data Accuracy:** <5% error rate in LLM-extracted pricing.
* **Engagement:** High return-user rate for "Search by Drink Price" queries.
* **Community Growth:** Average of 20+ user-submitted edits or bar additions per month.