"""Compute the strategic KPIs of the brief for France (baseline) and each candidate country.

Everything is read back from the DuckDB star schema with SQL, so the KPIs only depend on the
modelled data, not on intermediate Python objects.

Axes and KPIs (brief, slide "Guide des KPIs Stratégiques"):
  Market & potential   market_cagr, spend_per_capita_eur, market_size_meur,
                       (context) sephora_fr_market_share, leader_store_share
  Price & margin       relative_price_index, gross_margin_post_tax, (context) scraped_price_index
  Network              catchment_density_per_100k, prime_rent_eur_m2
  Operations           hub_distance_km, trade_friction
  Assortment           catalogue_eligible_pct, personal_care_share_pct
"""

import pandas as pd

from beauty_expansion import config

AXIS = {
    "market_cagr": "Market & potential", "spend_per_capita_eur": "Market & potential",
    "market_size_meur": "Market & potential", "sephora_fr_market_share": "Market & potential",
    "leader_store_share": "Market & potential",
    "relative_price_index": "Price & margin", "gross_margin_post_tax": "Price & margin",
    "scraped_price_index": "Price & margin", "effective_price_index": "Price & margin",
    "catchment_density_per_100k": "Network & footprint", "prime_rent_eur_m2": "Network & footprint",
    "selective_stores_per_100k_national": "Network & footprint",
    "hub_distance_km": "Operations & logistics", "trade_friction": "Operations & logistics",
    "catalogue_eligible_pct": "Assortment", "personal_care_share_pct": "Assortment",
    "labour_cost_retail_eur_h": "Operations & logistics",
}


def _latest(con, indicator: str) -> pd.Series:
    """Most recent value of a Eurostat indicator for each country."""
    df = con.execute("""
        SELECT c.country_code, f.value
        FROM fact_macro_indicator f
        JOIN dim_indicator i USING (indicator_key)
        JOIN dim_country  c USING (country_key)
        WHERE i.indicator = ?
        QUALIFY ROW_NUMBER() OVER (PARTITION BY c.country_code ORDER BY f.year_key DESC) = 1
    """, [indicator]).df()
    return df.set_index("country_code")["value"]


def market_cagr(con) -> pd.Series:
    """Compound annual growth of household personal-care spending, 2019 -> latest year."""
    df = con.execute("""
        WITH s AS (
            SELECT c.country_code, f.year_key AS year, f.value
            FROM fact_macro_indicator f
            JOIN dim_indicator i USING (indicator_key)
            JOIN dim_country  c USING (country_key)
            WHERE i.indicator = 'personal_care_spend_meur'
        ),
        bounds AS (
            SELECT country_code, MIN(year) AS y0, MAX(year) AS y1 FROM s GROUP BY country_code
        )
        SELECT b.country_code,
               POWER(e.value / s0.value, 1.0 / (b.y1 - b.y0)) - 1 AS cagr
        FROM bounds b
        JOIN s s0 ON s0.country_code = b.country_code AND s0.year = b.y0
        JOIN s e  ON e.country_code  = b.country_code AND e.year  = b.y1
    """).df()
    return df.set_index("country_code")["cagr"]


def compute(con, catchment: pd.DataFrame) -> pd.DataFrame:
    countries = pd.DataFrame(index=list(config.COUNTRIES))
    facts = con.execute("SELECT * FROM dim_country").df().set_index("country_code")

    # ---- Market & potential
    countries["market_size_meur"] = _latest(con, "personal_care_spend_meur")
    countries["spend_per_capita_eur"] = _latest(con, "personal_care_spend_eur_hab")
    countries["market_cagr"] = market_cagr(con)
    countries["personal_care_share_pct"] = _latest(con, "personal_care_share_pct")
    population = _latest(con, "population")

    fr_spend_2024 = con.execute("""
        SELECT f.value FROM fact_macro_indicator f JOIN dim_indicator i USING (indicator_key)
        JOIN dim_country c USING (country_key)
        WHERE i.indicator = 'personal_care_spend_meur' AND c.country_code = 'FR' AND f.year_key = 2024
    """).fetchone()[0]
    countries.loc["FR", "sephora_fr_market_share"] = config.FR_REVENUE_2024_MEUR / fr_spend_2024

    stores = con.execute("""
        SELECT c.country_code, b.brand, b.segment, s.km_to_nearest_hub
        FROM fact_competitor_store s JOIN dim_brand b USING (brand_key) JOIN dim_country c USING (country_key)
    """).df()
    selective = stores[(stores["segment"] == "selective") & (stores["brand"] != "Sephora")]
    by_brand = selective.groupby(["country_code", "brand"]).size()
    countries["leader_store_share"] = by_brand.groupby(level=0).max() / by_brand.groupby(level=0).sum()
    countries["leader_brand"] = by_brand.groupby(level=0).idxmax().map(lambda t: t[1])

    # ---- Price & margin
    pli = _latest(con, "price_level_index_misc")
    countries["relative_price_index"] = pli / pli["FR"] * 100

    scraped = con.execute("""
        WITH p AS (
            SELECT f.product_id, c.country_code, f.price_eur
            FROM fact_price f JOIN dim_country c USING (country_key)
        )
        SELECT t.country_code, MEDIAN(t.price_eur / fr.price_eur) * 100 AS idx, COUNT(*) AS n
        FROM p t JOIN p fr ON fr.product_id = t.product_id AND fr.country_code = 'FR'
        GROUP BY t.country_code
    """).df().set_index("country_code")
    countries["scraped_price_index"] = scraped["idx"] if len(scraped) else None
    countries["scraped_products"] = scraped["n"] if len(scraped) else 0

    # Which price will Sephora actually charge? The same products sell at ~the same price online across
    # the eurozone (scraped index ~100) even where the general price level is much higher (Eurostat).
    # Effective index = scraped evidence where we have it; elsewhere Eurostat level x the pass-through
    # observed in the scraped countries (how much of the price-level gap reaches beauty shelf prices).
    both = countries.dropna(subset=["scraped_price_index"]).drop(index=config.BASELINE, errors="ignore")
    gap = both["relative_price_index"] - 100
    passthrough = ((both["scraped_price_index"] - 100) / gap.where(gap.abs() > 1)).median() if len(both) else 0.0
    passthrough = float(min(1.0, max(0.0, 0.0 if pd.isna(passthrough) else passthrough)))
    countries["price_passthrough"] = passthrough
    countries["effective_price_index"] = countries["scraped_price_index"].fillna(
        100 + passthrough * (countries["relative_price_index"] - 100))
    countries.loc[config.BASELINE, "effective_price_index"] = 100.0

    countries["vat_standard_rate"] = facts["vat_standard_rate"]
    countries["hub_distance_km"] = selective.groupby("country_code")["km_to_nearest_hub"].mean()

    non_eu = ~facts["in_eu_customs_union"].astype(bool)
    fx = facts["currency"] != "EUR"
    countries["trade_friction"] = (
        facts["customs_duty_cosmetics"] * 100
        + non_eu * config.NON_EU_CUSTOMS_ADMIN_PCT * 100
        + fx * 1.0                      # ASSUMPTION: 1 pt for currency risk / hedging cost
    )

    cat = con.execute("""
        SELECT c.country_code, f.price_fr_incl_vat_eur, f.unit_cost_eur, f.annual_units_fr, f.is_eligible
        FROM fact_catalogue f JOIN dim_country c USING (country_key)
    """).df()
    cat["revenue_fr"] = cat["price_fr_incl_vat_eur"] * cat["annual_units_fr"]
    eligible_share = cat[cat["is_eligible"]].groupby("country_code")["revenue_fr"].sum() / cat.groupby("country_code")["revenue_fr"].sum()
    countries["catalogue_eligible_pct"] = eligible_share * 100

    # Gross margin after VAT: same products, local shelf price, local VAT, cost + logistics + customs
    margins = {}
    for cc in countries.index:
        basket = cat[(cat["country_code"] == cc) & cat["is_eligible"]]
        local_price = basket["price_fr_incl_vat_eur"] * countries.loc[cc, "effective_price_index"] / 100
        net_price = local_price / (1 + facts.loc[cc, "vat_standard_rate"])
        cost_uplift = (config.LOGISTICS_COST_PCT_PER_1000KM * countries.loc[cc, "hub_distance_km"] / 1000
                       + facts.loc[cc, "customs_duty_cosmetics"]
                       + (config.NON_EU_CUSTOMS_ADMIN_PCT if non_eu[cc] else 0))
        cost = basket["unit_cost_eur"] * (1 + cost_uplift)
        units = basket["annual_units_fr"]
        margins[cc] = 1 - (cost * units).sum() / (net_price * units).sum()
    countries["gross_margin_post_tax"] = pd.Series(margins)

    # ---- Network & footprint
    countries["catchment_density_per_100k"] = catchment.groupby("country_code").apply(
        lambda g: g["selective_stores_10km"].sum() / g["population"].sum() * 1e5, include_groups=False)
    countries["selective_stores_per_100k_national"] = (
        stores[stores["segment"] == "selective"].groupby("country_code").size() / population * 1e5)
    countries["prime_rent_eur_m2"] = facts["prime_rent_eur_m2_year"]
    countries["labour_cost_retail_eur_h"] = _latest(con, "labour_cost_retail_eur_h")
    countries["corporate_tax_rate"] = facts["corporate_tax_rate"]
    countries["population"] = population
    return countries


def to_long(countries: pd.DataFrame) -> pd.DataFrame:
    """Tidy (country, kpi, value) table for the warehouse and the dashboard."""
    numeric = countries.drop(columns=["leader_brand"]).select_dtypes("number")
    long = numeric.reset_index(names="country_code").melt(id_vars="country_code", var_name="kpi", value_name="value")
    long["axis"] = long["kpi"].map(AXIS).fillna("Context")
    return long.dropna(subset=["value"])
