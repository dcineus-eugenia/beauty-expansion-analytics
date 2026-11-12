"""Load clean DataFrames into the DuckDB star schema (sql/schema.sql)."""

import duckdb
import pandas as pd

from beauty_expansion import config

INDICATOR_META = {
    "population": ("persons", "https://ec.europa.eu/eurostat/databrowser/view/demo_pjan/default/table"),
    "gdp_per_capita_pps": ("PPS per inhabitant", "https://ec.europa.eu/eurostat/databrowser/view/nama_10_pc/default/table"),
    "personal_care_spend_meur": ("million EUR", "https://ec.europa.eu/eurostat/databrowser/view/nama_10_cp18/default/table"),
    "personal_care_spend_eur_hab": ("EUR per inhabitant", "https://ec.europa.eu/eurostat/databrowser/view/nama_10_cp18/default/table"),
    "personal_care_share_pct": ("% of household consumption", "https://ec.europa.eu/eurostat/databrowser/view/nama_10_cp18/default/table"),
    "hicp_personal_care": ("index 2015=100", "https://ec.europa.eu/eurostat/databrowser/view/prc_hicp_aind/default/table"),
    "price_level_index_misc": ("EU27=100", "https://ec.europa.eu/eurostat/databrowser/view/prc_ppp_ind_1/default/table"),
    "labour_cost_retail_eur_h": ("EUR per hour", "https://ec.europa.eu/eurostat/databrowser/view/lc_lci_lev/default/table"),
}


def connect(rebuild: bool = True) -> duckdb.DuckDBPyConnection:
    """Open the warehouse. The pipeline rebuilds it from scratch on each run (foreign keys
    prevent replacing a dimension table that facts still point to)."""
    config.PROCESSED.mkdir(parents=True, exist_ok=True)
    if rebuild:
        config.DB_PATH.unlink(missing_ok=True)
    return duckdb.connect(str(config.DB_PATH))


def _keyed(values, start=1) -> dict:
    return {v: i for i, v in enumerate(values, start=start)}


def load(con, *, macro, stores, prices, stores_fr, catalogue, group_fin, country_facts, scrape_year) -> dict:
    """Create the schema and fill dimensions + raw facts. Returns the key maps for later facts."""
    con.execute((config.SQL_DIR / "schema.sql").read_text())

    # --- dim_country
    cf = country_facts.copy()
    cf["country_name"] = cf["country_code"].map(config.COUNTRIES)
    cf["role"] = cf["country_code"].map(lambda c: "baseline" if c == config.BASELINE else "candidate")
    country_key = _keyed(list(config.COUNTRIES))
    cf["country_key"] = cf["country_code"].map(country_key)
    dim_country = cf[["country_key", "country_code", "country_name", "role", "in_eu_customs_union", "currency",
                      "vat_standard_rate", "corporate_tax_rate", "customs_duty_cosmetics",
                      "prime_rent_eur_m2_year", "prime_rent_location"]]
    con.register("dim_country_df", dim_country)
    con.execute("INSERT INTO dim_country SELECT * FROM dim_country_df")

    # --- dim_date: actuals, the 2027-2029 strategic plan, and projection years for the NPV
    years = range(2019, 2033)
    dim_date = pd.DataFrame({"year_key": list(years), "year": list(years)})
    dim_date["period"] = dim_date["year"].map(lambda y: "plan" if 2027 <= y <= 2029 else ("projection" if y > 2029 else "actual"))
    con.register("dim_date_df", dim_date)
    con.execute("INSERT INTO dim_date SELECT * FROM dim_date_df")

    # --- dim_indicator + fact_macro_indicator
    ind = macro[["indicator", "dataset"]].drop_duplicates().reset_index(drop=True)
    ind.insert(0, "indicator_key", range(1, len(ind) + 1))
    ind["unit"] = ind["indicator"].map(lambda i: INDICATOR_META[i][0])
    ind["source_url"] = ind["indicator"].map(lambda i: INDICATOR_META[i][1])
    con.register("dim_indicator_df", ind)
    con.execute("INSERT INTO dim_indicator SELECT * FROM dim_indicator_df")

    m = macro.merge(ind[["indicator", "indicator_key"]], on="indicator")
    m["country_key"] = m["geo"].map(country_key)
    fact_macro = m[["indicator_key", "country_key", "year", "value"]].rename(columns={"year": "year_key"})
    con.register("fact_macro_df", fact_macro)
    con.execute("INSERT INTO fact_macro_indicator SELECT * FROM fact_macro_df")

    # --- dim_brand + fact_competitor_store
    brands = stores[["brand", "segment"]].drop_duplicates().sort_values("brand").reset_index(drop=True)
    brands.insert(0, "brand_key", range(1, len(brands) + 1))
    con.register("dim_brand_df", brands)
    con.execute("INSERT INTO dim_brand SELECT * FROM dim_brand_df")
    s = stores.merge(brands[["brand", "brand_key"]], on="brand")
    s["country_key"] = s["country_code"].map(country_key)
    s = s.drop_duplicates("osm_id")
    con.register("fact_store_df", s[["osm_id", "brand_key", "country_key", "city", "lat", "lon", "km_to_nearest_hub"]])
    con.execute("INSERT INTO fact_competitor_store SELECT * FROM fact_store_df")

    # --- dim_category (union of catalogue + price categories) + fact_price + fact_catalogue
    cats = sorted(set(catalogue["category"]) | set(prices["category"] if len(prices) else []))
    category_key = _keyed(cats)
    con.register("dim_category_df", pd.DataFrame({"category_key": list(category_key.values()), "category": list(category_key)}))
    con.execute("INSERT INTO dim_category SELECT * FROM dim_category_df")

    if len(prices):
        p = prices.assign(category_key=prices["category"].map(category_key),
                          country_key=prices["country_code"].map(country_key),
                          year_key=scrape_year)
        con.register("fact_price_df", p[["product_id", "name", "brand", "category_key", "country_key", "year_key", "price_eur"]])
        con.execute("INSERT INTO fact_price SELECT * FROM fact_price_df")

    cat_rows = []
    for cc in config.COUNTRIES:
        c = catalogue[["sku", "category", "brand_type", "price_fr_incl_vat_eur", "unit_cost_eur", "annual_units_fr", f"eligible_{cc}"]].copy()
        c = c.rename(columns={f"eligible_{cc}": "is_eligible"})
        c["country_key"] = country_key[cc]
        cat_rows.append(c)
    cat = pd.concat(cat_rows)
    cat["category_key"] = cat["category"].map(category_key)
    con.register("fact_catalogue_df", cat[["sku", "category_key", "country_key", "brand_type", "price_fr_incl_vat_eur",
                                           "unit_cost_eur", "annual_units_fr", "is_eligible"]])
    con.execute("INSERT INTO fact_catalogue SELECT * FROM fact_catalogue_df")

    # --- dim_store + fact_store_pnl (simulated, financial year 2024 = latest filed accounts)
    st = stores_fr.copy()
    st.insert(0, "store_key", range(1, len(st) + 1))
    con.register("dim_store_df", st[["store_key", "store_id", "region", "format", "size_m2", "opening_year"]])
    con.execute("INSERT INTO dim_store SELECT * FROM dim_store_df")
    st["year_key"] = 2024
    con.register("fact_pnl_df", st[["store_key", "year_key", "revenue_eur", "cogs_eur", "rent_eur", "staff_fte",
                                    "staff_cost_eur", "other_opex_eur", "store_ebitda_eur"]])
    con.execute("INSERT INTO fact_store_pnl SELECT * FROM fact_pnl_df")

    # --- fact_group_financials
    gf = group_fin.rename(columns={"year": "year_key"})[["year_key", "revenue_meur", "recurring_profit_meur", "headcount", "operating_margin"]]
    con.register("fact_gf_df", gf)
    con.execute("INSERT INTO fact_group_financials SELECT * FROM fact_gf_df")

    return {"country_key": country_key, "category_key": category_key}


def write_kpis(con, kpis: pd.DataFrame, country_key: dict) -> None:
    k = kpis.assign(country_key=kpis["country_code"].map(country_key))
    con.register("kpi_df", k[["country_key", "kpi", "axis", "value", "score_0_100", "weight"]])
    con.execute("DELETE FROM fact_country_kpi; INSERT INTO fact_country_kpi SELECT * FROM kpi_df")


def write_business_case(con, plan: pd.DataFrame, country_key: dict) -> None:
    b = plan.assign(country_key=plan["country_code"].map(country_key), year_key=plan["year"])
    cols = ["country_key", "year_key", "stores_open", "revenue_eur", "gross_margin_eur", "rent_eur",
            "staff_cost_eur", "other_costs_eur", "ebit_eur", "capex_eur", "free_cash_flow_eur"]
    con.register("bc_df", b[cols])
    con.execute("DELETE FROM fact_business_case; INSERT INTO fact_business_case SELECT * FROM bc_df")
