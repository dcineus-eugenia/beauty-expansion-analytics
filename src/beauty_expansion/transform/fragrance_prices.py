"""Perfume prices: clean the LOOKFANTASTIC scrape and compute price per ml, ex-VAT (issue #3).

Steps:
1. keep real perfumes only: a fragrance type (EDP, EDT...), one bottle (no sets), a volume;
2. add the country's standard VAT rate (data/manual/country_facts.csv);
3. compute price per ml incl. VAT, price per ml ex-VAT and the discount vs RRP;
4. compare countries like for like: same product (same product_id) vs France.

Outputs in data/processed/:
- fragrance_prices.csv         one row per product and country
- fragrance_price_summary.csv  one row per country
"""

from __future__ import annotations

import pandas as pd

from beauty_expansion import config
from beauty_expansion.extract import lookfantastic


def clean(raw: pd.DataFrame) -> pd.DataFrame:
    """Keep single perfume bottles with a price and a volume."""
    df = raw.copy()
    df = df[df["fragrance_type"].notna()]            # drops make-up, skincare, body lotion...
    df = df[~df["is_set"].astype(bool)]              # drops gift sets (several products in one)
    df = df[df["volume_ml"].notna() & (df["volume_ml"] > 0)]
    df = df[df["price_eur"].notna()]
    df = df.drop_duplicates(subset=["country_code", "product_id"])
    return df.reset_index(drop=True)


def add_prices(df: pd.DataFrame) -> pd.DataFrame:
    """Add VAT, ex-VAT price, price per ml and discount."""
    vat = pd.read_csv(config.MANUAL / "country_facts.csv")[["country_code", "vat_standard_rate"]]
    df = df.merge(vat, on="country_code", how="left")
    df["price_ex_vat_eur"] = df["price_eur"] / (1 + df["vat_standard_rate"])
    df["price_per_ml"] = df["price_eur"] / df["volume_ml"]
    df["price_ex_vat_per_ml"] = df["price_ex_vat_eur"] / df["volume_ml"]
    df["discount_pct"] = 1 - df["price_eur"] / df["rrp_eur"]
    return df


def summarise(df: pd.DataFrame) -> pd.DataFrame:
    """One row per country. The index vs France only uses products sold in both countries."""
    fr = df.loc[df["country_code"] == config.BASELINE, ["product_id", "price_eur", "price_ex_vat_eur"]]
    rows = []
    for country, g in df.groupby("country_code"):
        same = g.merge(fr, on="product_id", how="inner", suffixes=("", "_fr"))
        rows.append({
            "country_code": country,
            "vat_standard_rate": g["vat_standard_rate"].iloc[0],
            "n_products": len(g),
            "n_brands": g["brand"].nunique(),
            "median_price_eur": g["price_eur"].median(),
            "median_price_per_ml": g["price_per_ml"].median(),
            "median_price_ex_vat_per_ml": g["price_ex_vat_per_ml"].median(),
            "median_discount_pct": g["discount_pct"].median(),
            # like-for-like: median of (price here / price in France) on the same products
            "n_products_matched_fr": len(same),
            "price_index_vs_fr": (same["price_eur"] / same["price_eur_fr"]).median() * 100,
            "price_ex_vat_index_vs_fr": (same["price_ex_vat_eur"] / same["price_ex_vat_eur_fr"]).median() * 100,
        })
    return pd.DataFrame(rows).round(3)


def run(refresh: bool = False) -> tuple[pd.DataFrame, pd.DataFrame]:
    raw = lookfantastic.extract_all(refresh=refresh)
    prices = add_prices(clean(raw))
    summary = summarise(prices)

    config.PROCESSED.mkdir(parents=True, exist_ok=True)
    prices.to_csv(config.PROCESSED / "fragrance_prices.csv", index=False)
    summary.to_csv(config.PROCESSED / "fragrance_price_summary.csv", index=False)
    print(f"  fragrance prices: {len(raw)} scraped -> {len(prices)} perfumes kept")
    return prices, summary


if __name__ == "__main__":  # quick test: python -m beauty_expansion.transform.fragrance_prices
    _, s = run()
    print(s.to_string(index=False))
