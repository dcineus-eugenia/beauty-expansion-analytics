"""Project-wide settings: paths, countries, KPI weights and business-case assumptions.

Every hard-coded number that is NOT pulled from a data source lives here, with a comment
explaining where it comes from. Change an assumption here and re-run the pipeline.
"""

from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
RAW = DATA / "raw"              # downloaded files (cache, not committed)
MANUAL = DATA / "manual"        # hand-collected public figures (committed, with sources)
PROCESSED = DATA / "processed"  # pipeline outputs (CSV + DuckDB)
DB_PATH = PROCESSED / "warehouse.duckdb"
SQL_DIR = ROOT / "sql"

# ---------------------------------------------------------------------------
# Countries
# ---------------------------------------------------------------------------
BASELINE = "FR"

# Candidates: European countries where Sephora had no physical store as of 2026-11
# (checked with OpenStreetMap + press search; see data/manual/sephora_presence.csv).
CANDIDATES = {
    "NL": "Netherlands",
    "AT": "Austria",
    "IE": "Ireland",
    "FI": "Finland",
    "NO": "Norway",
}
COUNTRIES = {BASELINE: "France", **CANDIDATES}

# Study area = continental Europe. OpenStreetMap's country areas include overseas territories
# (French Guiana, Réunion, Caribbean Netherlands...), whose stores would distort densities and
# hub distances. (lat_min, lat_max, lon_min, lon_max)
EUROPE_BBOX = (34.0, 72.0, -25.0, 45.0)

# ---------------------------------------------------------------------------
# Competitor brands (OpenStreetMap "brand" tag)
# ---------------------------------------------------------------------------
# Selective / specialist beauty retailers = Sephora's direct competitors.
SELECTIVE_BRANDS = [
    "Sephora", "Douglas", "ICI PARIS XL", "Marionnaud", "Nocibé", "KIKO Milano", "Rituals",
    "Lush", "The Body Shop", "Yves Rocher", "Inglot", "MAC", "KICKS", "Lyko", "Sokos Emotion",
    "Fredrik & Louisa", "Parfymeriet",
]
# Mass-market drugstores: indirect competitors (same categories, lower price point).
DRUGSTORE_BRANDS = [
    "dm", "Rossmann", "Müller", "Bipa", "Kruidvat", "Etos", "HEMA", "Boots", "Superdrug",
    "Normal", "Vita", "Matas", "Life",
]
# Selective chains that sell fragrance as a core category (issue #4). OSM often tags them shop=cosmetics,
# not shop=perfumery, so the fragrance competition counts them from the brand query as well.
# The Perfume Shop (UK chain, also in Ireland) has no OSM brand tag in Ireland: it's only matched by name
# among shop=perfumery results, since it isn't in the brand query.
PERFUMERY_CHAINS = [
    "Sephora", "Douglas", "ICI PARIS XL", "Marionnaud", "Nocibé", "KICKS", "Sokos Emotion",
    "Fredrik & Louisa", "Parfymeriet", "The Perfume Shop",
]
# Below this many perfumeries, one shop missing from OSM moves top3_share by several points:
# the row gets small_sample = True and its shares should not be compared with other countries.
FRAGRANCE_MIN_SHOPS = 100

# ---------------------------------------------------------------------------
# Scoring weights (must sum to 1). Defended in the README, section "KPI choice".
# ---------------------------------------------------------------------------
KPI_WEIGHTS = {
    # Market & potential (30 %)
    "market_cagr": 0.12,
    "spend_per_capita_eur": 0.10,
    "market_size_meur": 0.08,
    # Price & margin (20 %): one KPI. The relative price index stays visible as context but is
    # not scored separately, because it already drives the margin (no double counting).
    "gross_margin_post_tax": 0.20,
    # Network & footprint (20 %)
    "catchment_density_per_100k": 0.10,
    "prime_rent_eur_m2": 0.10,
    # Operations & logistics (15 %)
    "hub_distance_km": 0.08,
    "trade_friction": 0.07,
    # Assortment (15 %)
    "catalogue_eligible_pct": 0.08,
    "personal_care_share_pct": 0.07,
}
# Sensitivity scenario "Fragrance focus" (issue #5). ASSUMPTION: the 30 % Market & potential axis keeps its
# three weights (12 / 10 / 8) but is measured on the fragrance market (customs data, HS 3303) instead of
# total personal-care spending. Every other weight is unchanged. It is a test, not the base score.
FRAGRANCE_KPI_DIRECTION = {"fragrance_cagr": 1, "fragrance_per_capita_eur": 1, "fragrance_market_meur": 1}
FRAGRANCE_FOCUS_WEIGHTS = {
    **KPI_WEIGHTS,
    "market_cagr": 0.0, "spend_per_capita_eur": 0.0, "market_size_meur": 0.0,
    "fragrance_cagr": 0.12, "fragrance_per_capita_eur": 0.10, "fragrance_market_meur": 0.08,
}

# +1 = higher is better, -1 = lower is better
KPI_DIRECTION = {
    "market_cagr": 1, "spend_per_capita_eur": 1, "market_size_meur": 1,
    "gross_margin_post_tax": 1,
    "catchment_density_per_100k": -1, "prime_rent_eur_m2": -1,
    "hub_distance_km": -1, "trade_friction": -1,
    "catalogue_eligible_pct": 1, "personal_care_share_pct": 1,
}

# ---------------------------------------------------------------------------
# Simulated internal data (calibration)
# ---------------------------------------------------------------------------
RANDOM_SEED = 2027
FR_STORE_COUNT = 330                 # ~330 stores in France (Copeps, Statista regional split 2025)
FR_REVENUE_2024_MEUR = 2511          # Sephora SAS 2024 revenue, filed accounts (Xerfi)
FR_ECOMMERCE_SHARE = 0.15            # ASSUMPTION: share of FR revenue made online
CATALOGUE_SIZE = 2000                # ASSUMPTION: SKUs simulated (real catalogue is larger)

# ---------------------------------------------------------------------------
# Business-case assumptions (target country)
# ---------------------------------------------------------------------------
PLAN_STORES = {2027: 3, 2028: 5, 2029: 7}   # new stores opened per year (15 by end 2029)
STORE_SIZE_M2 = 350                          # ASSUMPTION: mid-size mall/high-street format
RENT_FACTOR_VS_PRIME = 0.45                  # ASSUMPTION: mall / secondary-street rent = 45 % of prime high-street rent
FITOUT_CAPEX_EUR_M2 = 3500                   # ASSUMPTION: Sephora concept fit-out per m²
OPENING_COSTS_EUR = 250_000                  # ASSUMPTION: pre-opening (recruiting, training, launch marketing)
STAFF_PER_STORE_FTE = 14                     # ASSUMPTION: calibrated on FR simulated network
HOURS_PER_FTE_YEAR = 1600                    # ASSUMPTION
RAMP_UP = [0.70, 0.90, 1.00, 1.00, 1.00]     # ASSUMPTION: share of mature revenue, year 1..5
DEMAND_ELASTICITY = 0.5                      # ASSUMPTION: store sales grow with sqrt(spend per capita ratio);
                                             #   richer markets also attract more stores sharing the spend
NEW_ENTRANT_FACTOR = 0.85                    # ASSUMPTION: unknown banner reaches 85 % of a mature French store
INVENTORY_DAYS = 90                          # ASSUMPTION: stock held per store (days of COGS), cash out at opening
LOGISTICS_COST_PCT_PER_1000KM = 0.015        # ASSUMPTION: +1.5 % of COGS per 1,000 km from hub
NON_EU_CUSTOMS_ADMIN_PCT = 0.02              # ASSUMPTION: customs clearance/admin, % of COGS (Norway)
CENTRAL_COSTS_PCT = 0.08                     # ASSUMPTION: HQ, marketing, IT allocated, % of revenue
WACC = 0.08                                  # ASSUMPTION: discount rate for NPV
DECISION_MAX_PAYBACK_YEARS = 4               # Go rule: payback within 4 years...
DECISION_MIN_NPV = 0                         # ...and positive 5-year NPV

# ---------------------------------------------------------------------------
# AI summary
# ---------------------------------------------------------------------------
CLAUDE_MODEL = "claude-opus-5-5"
# ---------------------------------------------------------------------------
# Fragrance prices: LOOKFANTASTIC scraper (issue #3)
# ---------------------------------------------------------------------------
# One online retailer present in FR + 3 candidates, so prices are comparable like for like.
# Finland and Norway have no LOOKFANTASTIC site: they are left out of this analysis.
# Scraping rules: https://www.lookfantastic.fr/robots.txt (brand pages and ?pageNumber= allowed;
# sort/filter/search URLs are disallowed and never used).
LOOKFANTASTIC_SITES = {
    "FR": "https://www.lookfantastic.fr",
    "NL": "https://www.lookfantastic.nl",
    "AT": "https://www.lookfantastic.at",
    "IE": "https://www.lookfantastic.ie",
}

# Brand name -> (URL slug, extra listing suffixes to try first).
# The "all products" page has a different name depending on the brand (view-all/, all/,
# all-lancome/, view-all-jpg/...), checked by hand on 2026-11-12.
FRAGRANCE_BRANDS = {
    "Giorgio Armani": ("giorgio-armani", []),
    "Carolina Herrera": ("carolina-herrera", []),
    "Hugo Boss": ("hugo-boss", []),
    "Jean Paul Gaultier": ("jean-paul-gaultier", ["view-all-jpg"]),
    "Yves Saint Laurent": ("yves-saint-laurent", []),
    "Lancôme": ("lancome", ["all-lancome"]),
    "Paco Rabanne": ("paco-rabanne", []),
    # Dior replacements (Dior is not sold on the NL and IE sites). Both are kept: they exist in the 4 countries.
    # Carolina Herrera and Jean Paul Gaultier are missing on the Austrian site (checked by the 2026-11-13 run).
    "Prada": ("prada", []),
    "Valentino": ("valentino", []),
}

SCRAPER_USER_AGENT = "beauty-expansion-analytics student project (Eugenia School)"
SCRAPER_DELAY_S = 2.0      # pause between two requests, to stay polite with the site
SCRAPER_MAX_PAGES = 10     # safety stop per brand listing
