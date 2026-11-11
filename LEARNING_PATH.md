# Learning Path

This project teaches Python by answering the Comex's question:

> **Is opening stores in the target country feasible and profitable?**

The company is a French beauty and cosmetics retailer. We don't pick the country by hand.
Python scores 5 candidate countries and the data chooses the winner.

Each module is one script in `lessons/`. Run it, read the comments, then do the
`# EXERCISE` blocks. When a module is finished, its useful code moves into `src/beauty_expansion/`
(the real pipeline). By the end, the lessons are your notes and `src/` is your deliverable.

Run a lesson from the project root:

```bash
source .venv/bin/activate
python lessons/00_python_refresher.py
```

---

## Phase 1: Foundations (get back into Python)

| # | Script | You learn | Project output |
|---|--------|-----------|----------------|
| 00 | `00_python_refresher.py` | variables, lists, dicts, loops, functions, f-strings | a dict describing the company and 5 candidate countries |
| 01 | `01_pandas_basics.py` | DataFrame, select/filter, new columns, groupby, sort, CSV | first country comparison table |

## Phase 2: Collect the data (Sources, 15 pts)

| # | Script | You learn | Project output |
|---|--------|-----------|----------------|
| 02 | `02_excel_financials.py` | `pd.read_excel`, messy headers, types, missing values, dates, currency cleanup | clean **simulated internal data**: French store P&L |
| 03 | `03_api_eurostat.py` | `requests`, JSON, query parameters, pagination, error handling | population, GDP/capita, beauty spending, cosmetics price index, retail growth |
| 04 | `04_api_openstreetmap.py` | Overpass API, geodata, haversine distance | competitor store locations (Sephora, Douglas, Primor, Kiko...) → competitive density |
| 05 | `05_web_scraping.py` | `BeautifulSoup`, CSS selectors, politeness (robots.txt, delays), fallbacks | product prices FR vs target country → relative price index |

## Phase 3: Model the data (Modelling, 20 pts)

| # | Script | You learn | Project output |
|---|--------|-----------|----------------|
| 06 | `06_sql_star_schema.py` | SQL with DuckDB: CREATE, INSERT, JOIN, GROUP BY, views; facts vs dimensions | star schema: `fact_market`, `fact_price`, `fact_store_pnl`, `dim_country`, `dim_category`, `dim_date`, `dim_competitor` |

## Phase 4: Analyse (KPI choice, 30 pts)

| # | Script | You learn | Project output |
|---|--------|-----------|----------------|
| 07 | `07_kpis_scoring.py` | functions returning DataFrames, normalisation, weighted scoring, scenarios | the 10 KPIs from the brief, a country scorecard, and the selected country |
| 08 | `08_profitability.py` | simple financial model: revenue, gross margin after VAT, rent, payback | P&L for one new store and a break-even analysis |

## Phase 5: Deliver (DataViz & decision impact, 35 pts; arbitration, 15 pts)

| # | Script | You learn | Project output |
|---|--------|-----------|----------------|
| 09 | `09_dataviz_plotly.py` | Plotly bar/scatter/map/waterfall, chart design for executives | key Comex charts |
| 10 | `10_ai_summary_claude.py` | Anthropic SDK, prompts, structured JSON output, API keys with `.env` | AI-written executive summary and comments on each chart |
| 11 | `app/streamlit_app.py` | Streamlit layout, caching, filters, combining charts and AI text | **the dashboard deliverable** |
| 12 | `src/beauty_expansion/pipeline.py` | modules, imports, `main()`, one-command run | the automated pipeline: `python -m beauty_expansion.pipeline` |

---

## The KPIs we will compute (from the brief)

| Axis | KPI | Source |
|------|-----|--------|
| Market & potential | Annual beauty sector growth rate | Eurostat retail trade / household spending (COICOP 12.1.3) |
| | Our market share in France | simulated internal data + market size |
| | Main competitor's market share in target country | public reports + store counts (OSM) |
| Price & margin | Relative price index (target vs France) | Eurostat HICP cosmetics + scraped prices |
| | Estimated gross margin after tax | internal COGS + local VAT rate |
| Network | Competitive density per catchment area | OpenStreetMap stores / population per city |
| | Average commercial rent per m² | public real-estate reports (manual CSV) |
| Logistics | Average distance from existing French hubs | haversine from our warehouses to target cities |
| | Customs duties / local taxes | EU single market (0 duty) + VAT rates |
| Assortment | Category penetration locally | Eurostat spending by category |
| | % of French catalogue eligible | catalogue x EU cosmetics regulation flags |

## Candidate countries

Spain, Italy, Germany, Belgium, Netherlands. You can change this in `lessons/00_python_refresher.py` and later in
`src/beauty_expansion/config.py`.

## Progress tracker

- [ ] 00 Python refresher
- [ ] 01 pandas basics
- [ ] 02 Excel & financials
- [ ] 03 Eurostat API
- [ ] 04 OpenStreetMap API
- [ ] 05 Web scraping
- [ ] 06 Star schema (SQL)
- [ ] 07 KPIs & country scoring
- [ ] 08 Profitability model
- [ ] 09 Plotly charts
- [ ] 10 Claude AI summary
- [ ] 11 Streamlit dashboard
- [ ] 12 Automated pipeline
- [ ] README deliverable complete
- [ ] Comex slides
