"""Fragrance competition and assortment, per country (issue #4).

Two questions:
1. Who already sells fragrance? OpenStreetMap shops tagged shop=perfumery + stores of the perfumery chains
   (config.PERFUMERY_CHAINS, often tagged shop=cosmetics):
   count, density per 100k inhabitants (national and around the 5 largest cities), share of the
   3 biggest chains, leading chain.
2. Can Sephora sell its French fragrance range there? Share of fragrance SKUs eligible at launch in the
   SIMULATED internal catalogue, and why the others are excluded.

Outputs in data/processed/:
- fragrance_competition.csv  one row per country
- fragrance_assortment.csv   one row per country x exclusion reason (SIMULATED catalogue)
"""

from __future__ import annotations

import pandas as pd

from beauty_expansion import config
from beauty_expansion.transform import geo

CATALOGUE_SOURCE = "simulated internal catalogue"


def latest_population(macro: pd.DataFrame) -> pd.Series:
    """Latest Eurostat population per country (demo_pjan)."""
    pop = macro[macro["indicator"] == "population"].sort_values("year")
    return pop.groupby("geo")["value"].last()


def combine(perfumeries: pd.DataFrame, stores: pd.DataFrame) -> pd.DataFrame:
    """All shops selling fragrance as a core category: shop=perfumery + perfumery-chain stores.

    Data-quality fixes (found on the 2026-11-13 extract):
    - OSM tags many chain stores shop=cosmetics (Sephora, most Nocibé, KICKS...), so shop=perfumery
      alone finds 2 perfumeries in Finland. We add the chain stores from the brand query.
    - Some independents list the brands they carry in their `brand` tag ("JANZEN;Il Bucato di Adele").
      An unknown brand seen only once in a country counts as independent.
    """
    chain_stores = stores[stores["brand"].isin(config.PERFUMERY_CHAINS)]
    chain_stores = chain_stores.assign(name=chain_stores["brand"], chain=chain_stores["brand"], segment="perfumery")
    shops = pd.concat([perfumeries, chain_stores[perfumeries.columns]], ignore_index=True).drop_duplicates("osm_id")

    known = set(config.SELECTIVE_BRANDS + config.DRUGSTORE_BRANDS)
    seen = shops.groupby(["country_code", "chain"])["osm_id"].transform("size")
    shops.loc[~shops["chain"].isin(known) & (seen < 2), "chain"] = "independent"
    return shops


def competition(perfumeries: pd.DataFrame, cities: pd.DataFrame, population: pd.Series) -> pd.DataFrame:
    """One row per country: perfumery count, density, top-3 chain share and leader."""
    rows = []
    for cc in config.COUNTRIES:
        p = perfumeries[perfumeries["country_code"] == cc]
        chains = p.loc[p["chain"] != "independent", "chain"].value_counts()
        rows.append({
            "country_code": cc,
            "perfumeries": len(p),
            "perfumeries_per_100k": len(p) / population[cc] * 1e5 if len(p) else 0.0,
            # share of ALL perfumeries (independents included) held by the 3 biggest chains
            "top3_share": chains.head(3).sum() / len(p) if len(p) else None,
            "leader": chains.index[0] if len(chains) else None,
            "independent_share": (p["chain"] == "independent").mean() if len(p) else None,
        })
    out = pd.DataFrame(rows)

    # Same catchment as the selective-store KPI: 10 km around the 5 largest cities
    catchment = geo.catchment_density(perfumeries, cities, segment="perfumery")
    top5 = catchment.groupby("country_code").apply(
        lambda g: g["selective_stores_10km"].sum() / g["population"].sum() * 1e5, include_groups=False)
    out["perfumeries_per_100k_top5_cities"] = out["country_code"].map(top5)
    return out


def assortment(catalogue: pd.DataFrame) -> tuple[pd.Series, pd.DataFrame]:
    """% of fragrance SKUs eligible per country, and the exclusion reasons (SIMULATED catalogue)."""
    frag = catalogue[catalogue["category"] == "fragrance"]
    eligible_pct = pd.Series({cc: frag[f"eligible_{cc}"].mean() * 100 for cc in config.COUNTRIES})

    rows = []
    for cc in config.COUNTRIES:
        reasons = frag[f"exclusion_{cc}"].fillna("eligible").value_counts()
        for reason, skus in reasons.items():
            rows.append({"country_code": cc, "reason": reason, "skus": int(skus),
                         "pct_of_fragrance_skus": skus / len(frag) * 100, "source": CATALOGUE_SOURCE})
    return eligible_pct, pd.DataFrame(rows)


def run(perfumeries: pd.DataFrame, stores: pd.DataFrame, cities: pd.DataFrame, macro: pd.DataFrame,
        catalogue: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    table = competition(combine(perfumeries, stores), cities, latest_population(macro))
    eligible_pct, reasons = assortment(catalogue)
    table["fragrance_skus_eligible_pct"] = table["country_code"].map(eligible_pct)
    table["fragrance_skus_source"] = CATALOGUE_SOURCE

    columns = ["country_code", "perfumeries", "perfumeries_per_100k", "top3_share", "leader",
               "fragrance_skus_eligible_pct", "perfumeries_per_100k_top5_cities", "independent_share",
               "fragrance_skus_source"]
    table = table[columns].round(3)
    reasons = reasons.round(2)

    config.PROCESSED.mkdir(parents=True, exist_ok=True)
    table.to_csv(config.PROCESSED / "fragrance_competition.csv", index=False)
    reasons.to_csv(config.PROCESSED / "fragrance_assortment.csv", index=False)
    print("  fragrance competition (perfumeries: OSM; eligible SKUs: SIMULATED catalogue):")
    print(table.drop(columns=["fragrance_skus_source"]).to_string(index=False))
    return table, reasons
