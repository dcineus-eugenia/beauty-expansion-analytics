"""SIMULATED internal databases of Sephora France (the brief allows "bases internes simulées").

We have no access to Sephora's real systems, so we generate realistic data, CALIBRATED on public
figures so that the totals are right even if individual rows are synthetic:
  - store count ~330 and revenue 2024 = 2,511 M€ (Sephora SAS accounts), 15 % of it online (assumption)
  - staff cost = FTE x Eurostat French retail labour cost per hour (real, passed in)
  - network operating margin lands near LVMH Selective Retailing's published ~9-10 %

Everything is seeded (config.RANDOM_SEED), so the same "internal" data comes back on every run.
Outputs:
  stores_fr   one row per French store with a yearly P&L
  catalogue   one row per SKU with price, cost, and the flags used for country eligibility
"""

import numpy as np
import pandas as pd

from beauty_expansion import config

REGIONS = {  # weights roughly follow the 2025 regional split (Ile-de-France > 75 stores)
    "Île-de-France": 0.24, "Auvergne-Rhône-Alpes": 0.12, "Provence-Alpes-Côte d'Azur": 0.10,
    "Occitanie": 0.09, "Nouvelle-Aquitaine": 0.09, "Hauts-de-France": 0.08, "Grand Est": 0.085,
    "Pays de la Loire": 0.055, "Bretagne": 0.05, "Normandie": 0.04, "Centre-Val de Loire": 0.03,
    "Bourgogne-Franche-Comté": 0.03,
}
FORMATS = {
    #           share   size m² (mean)  revenue index
    "flagship": (0.03, 1200, 4.0),
    "city":     (0.45, 380, 1.15),
    "mall":     (0.52, 280, 0.75),
}
CATEGORY_MIX = {"fragrance": 0.30, "makeup": 0.30, "skincare": 0.28, "haircare": 0.07, "bath_body": 0.05}
BRAND_TYPES = {"selective_brand": 0.70, "exclusive_brand": 0.18, "sephora_collection": 0.12}

# Share of selective brands bound by an exclusive local distributor (not sellable by Sephora at launch).
# ASSUMPTION, higher where a strong local selective chain exists (KICKS in the Nordics, ICI Paris XL in NL).
EXCLUSIVE_DISTRIBUTION_RATE = {"FR": 0.0, "NL": 0.10, "AT": 0.06, "IE": 0.05, "FI": 0.14, "NO": 0.16}
# Sephora Collection packaging already exists in these languages (FR, EN, DE, NL); FI and NO need relabelling.
PRIVATE_LABEL_READY = {"FR": True, "NL": True, "AT": True, "IE": True, "FI": False, "NO": False}


def stores_fr(labour_cost_fr_eur_h: float) -> pd.DataFrame:
    rng = np.random.default_rng(config.RANDOM_SEED)
    n = config.FR_STORE_COUNT
    formats = rng.choice(list(FORMATS), size=n, p=[f[0] for f in FORMATS.values()])
    regions = rng.choice(list(REGIONS), size=n, p=np.array(list(REGIONS.values())) / sum(REGIONS.values()))

    size = np.array([rng.normal(FORMATS[f][1], FORMATS[f][1] * 0.2) for f in formats]).clip(120, 2500)
    raw_revenue = np.array([FORMATS[f][2] for f in formats]) * rng.lognormal(0, 0.25, n)

    store_revenue_total = config.FR_REVENUE_2024_MEUR * 1e6 * (1 - config.FR_ECOMMERCE_SHARE)
    revenue = raw_revenue / raw_revenue.sum() * store_revenue_total     # calibrate on the real total

    gross_margin_rate = rng.normal(0.44, 0.02, n)                        # selective beauty retail
    rent_eur_m2 = np.where(formats == "flagship", 4500, np.where(formats == "city", 1500, 1100))
    rent = size * rent_eur_m2 * rng.normal(1, 0.15, n)
    fte = (revenue / 470_000).round(1).clip(5)                           # productivity per FTE
    staff_cost = fte * config.HOURS_PER_FTE_YEAR * labour_cost_fr_eur_h
    other_opex = revenue * rng.normal(0.06, 0.01, n)

    df = pd.DataFrame({
        "store_id": [f"FR{i:04d}" for i in range(1, n + 1)],
        "region": regions,
        "format": formats,
        "size_m2": size.round(0),
        "opening_year": rng.integers(1996, 2025, n),
        "revenue_eur": revenue.round(0),
        "cogs_eur": (revenue * (1 - gross_margin_rate)).round(0),
        "rent_eur": rent.round(0),
        "staff_fte": fte,
        "staff_cost_eur": staff_cost.round(0),
        "other_opex_eur": other_opex.round(0),
    })
    df["store_ebitda_eur"] = df["revenue_eur"] - df[["cogs_eur", "rent_eur", "staff_cost_eur", "other_opex_eur"]].sum(axis=1)
    return df


def catalogue() -> pd.DataFrame:
    rng = np.random.default_rng(config.RANDOM_SEED + 1)
    n = config.CATALOGUE_SIZE
    category = rng.choice(list(CATEGORY_MIX), size=n, p=list(CATEGORY_MIX.values()))
    brand_type = rng.choice(list(BRAND_TYPES), size=n, p=list(BRAND_TYPES.values()))

    base_price = {"fragrance": 95, "makeup": 32, "skincare": 48, "haircare": 30, "bath_body": 22}
    price = np.array([base_price[c] for c in category]) * rng.lognormal(0, 0.35, n)
    cost_rate = np.where(brand_type == "sephora_collection", 0.38, np.where(brand_type == "exclusive_brand", 0.52, 0.58))

    df = pd.DataFrame({
        "sku": [f"SKU{i:05d}" for i in range(1, n + 1)],
        "brand_id": rng.integers(1, 220, n),
        "brand_type": brand_type,
        "category": category,
        "price_fr_incl_vat_eur": price.round(2),
        "alcohol_based": (category == "fragrance"),
        "annual_units_fr": rng.lognormal(7.5, 1.0, n).round(0),
    })
    df["unit_cost_eur"] = (df["price_fr_incl_vat_eur"] / 1.20 * cost_rate).round(2)

    # Eligibility flags per country, decided at BRAND level (a distribution contract covers a whole brand)
    brand_rng = np.random.default_rng(config.RANDOM_SEED + 2)
    brands = df["brand_id"].unique()
    for cc, rate in EXCLUSIVE_DISTRIBUTION_RATE.items():
        locked = set(brands[brand_rng.random(len(brands)) < rate])
        df[f"eligible_{cc}"] = ~(
            (df["brand_type"] == "selective_brand") & df["brand_id"].isin(locked)        # exclusive distributor
            | (df["brand_type"] == "sephora_collection") & (not PRIVATE_LABEL_READY[cc])  # labels not translated
            | (cc == "NO") & df["alcohol_based"] & (brand_rng.random(n) < 0.30)          # NO alcohol approval pending
        )
    return df
