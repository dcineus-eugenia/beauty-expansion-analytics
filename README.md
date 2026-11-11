# European Expansion Study: [Company name]

> **Question from the Comex:** is opening stores in the target country feasible and profitable?
> **Strategy horizon:** 2027–2029

_Fill each section as the matching module in [LEARNING_PATH.md](LEARNING_PATH.md) is completed._

---

## 1. Company presentation

| | |
|---|---|
| **Name** | _TODO_ (fictional) |
| **Business** | Selective beauty & cosmetics retail: fragrance, make-up, skincare, haircare |
| **Stores in France (X)** | _TODO_ (e.g. 180) |
| **Catalogue** | _TODO_ number of SKUs, brands, private label share |
| **Target country** | _Chosen by the scoring model in module 07_ |
| **Team** | _First name LAST NAME_ (role) × 3–4 |

## 2. Scope & data dictionary

### Business terms
| Term | Definition |
|------|-----------|
| Catchment area (zone d'achalandage) | _TODO_ |
| Gross margin after tax | _TODO_ |
| Relative price index | _TODO_ |

### Metrics
| Metric | Formula | Unit | Grain |
|--------|---------|------|-------|
| _TODO_ | | | |

### Dimensions
| Dimension | Attributes |
|-----------|-----------|
| `dim_country` | _TODO_ |
| `dim_category` | |
| `dim_date` | |
| `dim_competitor` | |

### Business rules
- _TODO_ (e.g. "prices are compared VAT-included, converted to EUR")

## 3. Architecture & data sources

_Star schema diagram goes here (module 06)._

| Source | Type | Data | Why it's relevant | Refresh |
|--------|------|------|-------------------|---------|
| Eurostat | Open data API | population, GDP, HICP cosmetics, retail trade | official, comparable across EU | yearly/monthly |
| OpenStreetMap (Overpass) | API | competitor store locations | free, geolocated | on demand |
| Retailer websites | Scraper | product prices | real shelf prices FR vs target | on demand |
| Internal store P&L | Simulated internal DB (Excel) | revenue, COGS, rent per store | baseline for the business case | monthly |

## 4. Organisation & roadmap

| Member | Role |
|--------|------|
| _TODO_ | Data engineering (collection, pipeline) |
| _TODO_ | Data modelling & SQL |
| _TODO_ | Analysis & KPIs |
| _TODO_ | DataViz, AI & presentation |

**Method:** _TODO_ (e.g. weekly sprints, Git branches + pull requests)

**Next steps (post-study recommendations):** _TODO_

## 5. Technical stack

```
Eurostat API ─┐
OSM Overpass ─┼─► Python (requests, BeautifulSoup, pandas) ─► DuckDB star schema ─► KPIs ─► Plotly + Streamlit
Scraper ──────┤                                                                          └─► Claude API (AI summary)
Excel (P&L) ──┘
```

## How to run

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # add your ANTHROPIC_API_KEY
python -m beauty_expansion.pipeline   # (module 12) collects, models, and scores
streamlit run app/streamlit_app.py    # opens the dashboard
```
