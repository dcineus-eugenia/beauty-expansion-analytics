"""Run the whole study end to end.

    python -m beauty_expansion.pipeline            # uses cached downloads when present
    python -m beauty_expansion.pipeline --refresh  # re-download Eurostat, OpenStreetMap, customs data and
                                                   #   re-scrape LOOKFANTASTIC perfume prices (~5 min)

Steps: extract -> transform -> load (DuckDB star schema) -> KPIs -> scoring -> business case -> decision -> AI summary.
Outputs land in data/processed/ (CSV + warehouse.duckdb + ai_summary.json); the Streamlit app reads them.
"""

import argparse
from datetime import date

import pandas as pd
import requests

from beauty_expansion import config, contracts
from beauty_expansion.analysis import ai_summary, business_case, decision, kpis, scoring
from beauty_expansion.extract import comext, eurostat, internal, lvmh, osm, prices
from beauty_expansion.transform import fragrance_competition
from beauty_expansion.load import warehouse
from beauty_expansion.transform import fragrance_prices, geo


def run(refresh: bool = False) -> None:
    config.PROCESSED.mkdir(parents=True, exist_ok=True)
    countries = list(config.COUNTRIES)

    print("1/6 Extract")
    macro = eurostat.extract_all(countries, refresh=refresh)
    stores, cities = osm.extract_all(countries, refresh=refresh)
    try:    # optional fragrance step (issue #4): a busy Overpass server must not stop the whole study
        perfumeries = osm.extract_perfumeries(countries, refresh=refresh)   # shop=perfumery, chains + independents
    except (requests.RequestException, RuntimeError) as err:    # network error or Overpass timeout only
        perfumeries = None
        fragrance_competition.clear_outputs()    # never leave an older CSV that looks like today's result
        print(f"  WARNING: perfumery extract failed, fragrance competition skipped, old outputs removed ({err})")
    price_table = prices.extract_all()
    trade = comext.extract_all(countries, refresh=refresh)
    group_fin = lvmh.selective_retailing()
    country_facts = pd.read_csv(config.MANUAL / "country_facts.csv")
    # Supply only from hubs inside the EU customs union: since Brexit, Coventry (UK) -> Ireland means customs
    hubs = pd.read_csv(config.MANUAL / "logistics_hubs.csv").query("in_eu_customs_union")
    labour_fr = macro[(macro["indicator"] == "labour_cost_retail_eur_h") & (macro["geo"] == "FR")]
    stores_fr = internal.stores_fr(labour_fr.sort_values("year")["value"].iloc[-1])
    catalogue = internal.catalogue()
    print(f"  internal (simulated): {len(stores_fr)} French stores, {len(catalogue)} SKUs")

    print("2/6 Transform")
    stores = geo.add_nearest_hub(stores, hubs)
    # Who sells fragrance, and how much of the French fragrance range is sellable (issue #4)
    if perfumeries is not None:
        fragrance_competition.run(perfumeries, stores, cities, macro, catalogue)
    catchment = geo.catchment_density(stores, cities)
    fragrance = comext.fragrance_market(trade, macro)     # imports - exports, per capita (fragrance, HS 3303)
    # Perfume shelf prices (LOOKFANTASTIC FR/NL/AT/IE): price per ml, ex-VAT index vs France.
    # Writes data/processed/fragrance_prices.csv and fragrance_price_summary.csv
    perfume_prices, perfume_price_summary = fragrance_prices.run(refresh=refresh)

    print("3/6 Load star schema ->", config.DB_PATH.relative_to(config.ROOT))
    con = warehouse.connect()
    keys = warehouse.load(con, macro=macro, stores=stores, prices=price_table, stores_fr=stores_fr,
                          catalogue=catalogue, group_fin=group_fin, country_facts=country_facts,
                          scrape_year=date.today().year)
    warehouse.write_trade(con, fragrance, keys["country_key"], comext.HS_CODE)
    print("  fragrance market, latest year (NaN = net exporter, not measurable with trade data):")
    print(comext.summary(fragrance).round(1).to_string())

    print("4/6 KPIs and scoring")
    k = kpis.compute(con, catchment)
    frag = comext.summary(fragrance)    # fragrance KPIs, used by the "Fragrance focus" scenario (NaN for France)
    k["fragrance_cagr"] = frag["cagr_pct"] / 100
    k["fragrance_per_capita_eur"] = frag["per_capita_eur"]
    k["fragrance_market_meur"] = frag["market_meur"]
    ranking = scoring.rank(k)
    sens = scoring.sensitivity(k)
    long = kpis.to_long(k).merge(scoring.scores_long(k), on=["country_code", "kpi"], how="left")
    warehouse.write_kpis(con, long, keys["country_key"])
    print(ranking[["country", "total_score"]].round(1).to_string())

    print("5/6 Business case")
    case, plans = business_case.evaluate(k, stores_fr)
    warehouse.write_business_case(con, plans, keys["country_key"])
    print(case[case["scenario"] == "base"][["country_code", "store_revenue_meur", "store_ebitda_margin",
                                             "payback_years", "plan_npv_meur", "go"]].round(2).to_string(index=False))

    print("6/6 Decision and AI summary")
    verdict = decision.decide(ranking, case)
    ai_summary.generate(k, ranking, sens, case, verdict)

    # Flat exports for the dashboard / Power BI users. Each file is checked against its data contract
    # (contracts.py) before it is written, so a broken file never reaches the dashboard.
    exports = {
        "kpis_by_country.csv": k.rename_axis("country_code").reset_index(),
        "country_ranking.csv": ranking.rename_axis("country_code").reset_index(),
        "sensitivity.csv": sens,
        "business_case_summary.csv": case,
        "business_case_plan.csv": plans,
        "catchment_density.csv": catchment,
        "stores.csv": stores,
        "prices.csv": price_table,
        "lvmh_selective_retailing.csv": group_fin,
        "internal_stores_fr.csv": stores_fr,
        "fragrance_market.csv": fragrance,
    }
    for file, df in exports.items():
        contracts.validate(file, df).to_csv(config.PROCESSED / file, index=False)
    errors = contracts.validate_outputs()
    if errors:
        raise contracts.ContractError("Data contract errors:\n  - " + "\n  - ".join(errors))
    print(f"  data contracts: all {len(exports)} files pass")
    con.close()
    print("Done. Launch the dashboard with: streamlit run app/streamlit_app.py")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--refresh", action="store_true", help="re-download Eurostat, OpenStreetMap, customs data and LOOKFANTASTIC prices")
    run(parser.parse_args().refresh)
