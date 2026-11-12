-- =============================================================================
-- Star schema: Sephora European expansion study (DuckDB)
--
--   Dimensions describe "who / where / when / what"; facts hold the measures.
--   Every fact joins to dim_country and (when relevant) dim_date, so any KPI can be
--   sliced by country and year with the same joins.
--
--                         dim_date
--                            |
--   dim_indicator -- fact_macro_indicator -- dim_country -- fact_competitor_store -- dim_brand
--                            |                    |
--        dim_category -- fact_price          fact_catalogue -- dim_category
--                            |                    |
--        dim_store -- fact_store_pnl         fact_country_kpi / fact_business_case
-- =============================================================================

-- ---------------------------------------------------------------- dimensions
CREATE OR REPLACE TABLE dim_country (
    country_key            INTEGER PRIMARY KEY,
    country_code           VARCHAR NOT NULL UNIQUE,   -- ISO 3166-1 alpha-2
    country_name           VARCHAR NOT NULL,
    role                   VARCHAR NOT NULL,          -- baseline | candidate
    in_eu_customs_union    BOOLEAN,
    currency               VARCHAR,
    vat_standard_rate      DOUBLE,
    corporate_tax_rate     DOUBLE,
    customs_duty_cosmetics DOUBLE,
    prime_rent_eur_m2_year DOUBLE,
    prime_rent_location    VARCHAR
);

CREATE OR REPLACE TABLE dim_date (
    year_key    INTEGER PRIMARY KEY,   -- = calendar year
    year        INTEGER NOT NULL,
    period      VARCHAR NOT NULL       -- actual | plan (2027-2029 strategy) | projection
);

CREATE OR REPLACE TABLE dim_indicator (
    indicator_key INTEGER PRIMARY KEY,
    indicator     VARCHAR NOT NULL UNIQUE,
    dataset       VARCHAR NOT NULL,    -- Eurostat dataset code
    unit          VARCHAR,
    source_url    VARCHAR
);

CREATE OR REPLACE TABLE dim_brand (
    brand_key INTEGER PRIMARY KEY,
    brand     VARCHAR NOT NULL UNIQUE,
    segment   VARCHAR NOT NULL         -- selective | drugstore
);

CREATE OR REPLACE TABLE dim_category (
    category_key INTEGER PRIMARY KEY,
    category     VARCHAR NOT NULL UNIQUE
);

CREATE OR REPLACE TABLE dim_store (
    store_key    INTEGER PRIMARY KEY,
    store_id     VARCHAR NOT NULL UNIQUE,
    region       VARCHAR,
    format       VARCHAR,
    size_m2      DOUBLE,
    opening_year INTEGER
);

-- ---------------------------------------------------------------- facts
-- Grain: one indicator, one country, one year (Eurostat)
CREATE OR REPLACE TABLE fact_macro_indicator (
    indicator_key INTEGER REFERENCES dim_indicator(indicator_key),
    country_key   INTEGER REFERENCES dim_country(country_key),
    year_key      INTEGER REFERENCES dim_date(year_key),
    value         DOUBLE NOT NULL
);

-- Grain: one physical store of a tracked beauty brand (OpenStreetMap snapshot)
CREATE OR REPLACE TABLE fact_competitor_store (
    osm_id      VARCHAR PRIMARY KEY,
    brand_key   INTEGER REFERENCES dim_brand(brand_key),
    country_key INTEGER REFERENCES dim_country(country_key),
    city        VARCHAR,
    lat         DOUBLE,
    lon         DOUBLE,
    km_to_nearest_hub DOUBLE
);

-- Grain: one product, one country, one scrape date (LOOKFANTASTIC)
CREATE OR REPLACE TABLE fact_price (
    product_id   VARCHAR,
    product_name VARCHAR,
    brand        VARCHAR,
    category_key INTEGER REFERENCES dim_category(category_key),
    country_key  INTEGER REFERENCES dim_country(country_key),
    year_key     INTEGER REFERENCES dim_date(year_key),
    price_eur    DOUBLE
);

-- Grain: one French store, one year (SIMULATED internal P&L)
CREATE OR REPLACE TABLE fact_store_pnl (
    store_key        INTEGER REFERENCES dim_store(store_key),
    year_key         INTEGER REFERENCES dim_date(year_key),
    revenue_eur      DOUBLE,
    cogs_eur         DOUBLE,
    rent_eur         DOUBLE,
    staff_fte        DOUBLE,
    staff_cost_eur   DOUBLE,
    other_opex_eur   DOUBLE,
    store_ebitda_eur DOUBLE
);

-- Grain: one SKU, one country (SIMULATED catalogue + eligibility rules)
CREATE OR REPLACE TABLE fact_catalogue (
    sku                   VARCHAR,
    category_key          INTEGER REFERENCES dim_category(category_key),
    country_key           INTEGER REFERENCES dim_country(country_key),
    brand_type            VARCHAR,
    price_fr_incl_vat_eur DOUBLE,
    unit_cost_eur         DOUBLE,
    annual_units_fr       DOUBLE,
    is_eligible           BOOLEAN
);

-- Grain: one year (LVMH Selective Retailing, public)
CREATE OR REPLACE TABLE fact_group_financials (
    year_key              INTEGER REFERENCES dim_date(year_key),
    revenue_meur          DOUBLE,
    recurring_profit_meur DOUBLE,
    headcount             INTEGER,
    operating_margin      DOUBLE
);

-- Grain: one country, one KPI (analysis output)
CREATE OR REPLACE TABLE fact_country_kpi (
    country_key INTEGER REFERENCES dim_country(country_key),
    kpi         VARCHAR,
    axis        VARCHAR,
    value       DOUBLE,
    score_0_100 DOUBLE,
    weight      DOUBLE
);

-- Grain: one country, one plan year (business case output)
CREATE OR REPLACE TABLE fact_business_case (
    country_key       INTEGER REFERENCES dim_country(country_key),
    year_key          INTEGER REFERENCES dim_date(year_key),
    stores_open       INTEGER,
    revenue_eur       DOUBLE,
    gross_margin_eur  DOUBLE,
    rent_eur          DOUBLE,
    staff_cost_eur    DOUBLE,
    other_costs_eur   DOUBLE,
    ebit_eur          DOUBLE,
    capex_eur         DOUBLE,
    free_cash_flow_eur DOUBLE
);
