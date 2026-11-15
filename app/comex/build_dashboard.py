"""Build the Comex dashboard: one self-contained HTML file, works offline.

    python app/comex/build_dashboard.py      # after python -m beauty_expansion.pipeline

Reads data/processed/*.csv, decision.json and ai_summary.json, injects them into the 3 templates and writes:
  dashboard_comex.html     dashboard with tabs
  dashboard_comex_v2.html  one-page dashboard + Instructions page
  slides_comex.html        Comex deck, 12 slides (arrow keys to navigate, Cmd+P to export a PDF)
The HTML outputs are committed so the team can open them without running the pipeline.
"""
import json
import pathlib
import re
import subprocess
import sys

import pandas as pd

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]      # app/comex/ -> repo root
P = ROOT / "data" / "processed"


def records(df: pd.DataFrame) -> list:
    return json.loads(df.to_json(orient="records"))      # NaN -> null


config_text = (ROOT / "src" / "beauty_expansion" / "config.py").read_text()
max_payback = float(re.search(r"DECISION_MAX_PAYBACK_YEARS\s*=\s*([\d.]+)", config_text).group(1))
fr_stores = int(re.search(r"FR_STORE_COUNT\s*=\s*(\d+)", config_text).group(1))
fr_revenue = int(re.search(r"FR_REVENUE_2024_MEUR\s*=\s*(\d+)", config_text).group(1))
claude_model = re.search(r"CLAUDE_MODEL\s*=\s*\"([^\"]+)\"", config_text).group(1)

ranking = pd.read_csv(P / "country_ranking.csv", index_col=0).reset_index(names="code")
ranking = ranking.rename(columns={
    "total_score": "score", "Market & potential": "market", "Price & margin": "margin",
    "Network & footprint": "network", "Operations & logistics": "logistics", "Assortment": "assortment",
}).drop(columns=["country"])

case = pd.read_csv(P / "business_case_summary.csv").rename(columns={"country_code": "code"})
case = case[["code", "scenario", "store_revenue_meur", "store_ebitda_margin", "payback_years",
             "plan_revenue_2029_meur", "plan_capex_meur", "plan_npv_meur"]]

plan = pd.read_csv(P / "business_case_plan.csv").rename(columns={"country_code": "code"})
plan = plan.assign(revenue_meur=plan["revenue_eur"] / 1e6, fcf_meur=plan["free_cash_flow_eur"] / 1e6)
plan = plan[["code", "year", "stores_open", "revenue_meur", "fcf_meur"]]

kpis = pd.read_csv(P / "kpis_by_country.csv", index_col=0).reset_index(names="code")
kpis = kpis[["code", "market_size_meur", "market_cagr", "spend_per_capita_eur", "gross_margin_post_tax",
             "catchment_density_per_100k", "prime_rent_eur_m2", "hub_distance_km", "catalogue_eligible_pct",
             "leader_brand", "leader_store_share", "vat_standard_rate", "labour_cost_retail_eur_h",
             "relative_price_index", "scraped_price_index", "effective_price_index", "scraped_products",
             "fragrance_market_meur", "fragrance_per_capita_eur", "fragrance_cagr"]]

fragrance = pd.read_csv(P / "fragrance_competition.csv").rename(columns={"country_code": "code"})
fprices = pd.read_csv(P / "fragrance_price_summary.csv").rename(columns={"country_code": "code"})   # Stephen, issue #3
fitems = pd.read_csv(P / "fragrance_prices.csv").rename(columns={"country_code": "code"})

# Natalia's robustness check (PR #10, analysis/fragrance_breakeven.py): "Fragrance focus" scores, and how far the Dutch
# fragrance level (an upper bound, Rotterdam transit) can fall before Ireland overtakes. Same method: scale market size
# and per-head together, growth unchanged, re-run scoring.rank, bisection.
sys.path.insert(0, str(ROOT / "src"))
from beauty_expansion import config  # noqa: E402
from beauty_expansion.analysis import scoring  # noqa: E402

kfull = pd.read_csv(P / "kpis_by_country.csv", index_col=0)


sens = pd.read_csv(P / "sensitivity.csv")
ff_row = sens[sens["scenario"] == "Fragrance focus"].iloc[0]
FF_WIN, FF_RUN = ff_row["winner"], ff_row["runner_up"]


def ffocus(factor: float) -> pd.Series:
    k = kfull.copy()
    k.loc[FF_WIN, ["fragrance_market_meur", "fragrance_per_capita_eur"]] *= factor
    return scoring.rank(k, config.FRAGRANCE_FOCUS_WEIGHTS)["total_score"]


lo, hi = 0.01, 1.0
breakeven = None
if ffocus(hi)[FF_WIN] > ffocus(hi)[FF_RUN] and ffocus(lo)[FF_WIN] < ffocus(lo)[FF_RUN]:
    for _ in range(50):
        mid = (lo + hi) / 2
        lo, hi = (lo, mid) if ffocus(mid)[FF_WIN] > ffocus(mid)[FF_RUN] else (mid, hi)
    breakeven = hi
fm = pd.read_csv(P / "fragrance_market.csv")
nl_trade = fm[(fm.country_code == FF_WIN) & (fm.year == fm.year.max())].iloc[0]
fcheck = {
    "winner": FF_WIN, "runnerUp": FF_RUN,
    "scores": [{"code": c, "score": float(v)} for c, v in ffocus(1.0).items()],
    "breakevenFactor": breakeven,
    "nlImportsMeur": float(nl_trade.imports_eur / 1e6), "nlExportsMeur": float(nl_trade.exports_eur / 1e6),
    "nlConsumptionMeur": float(nl_trade.apparent_consumption_eur / 1e6),
}

# Rent lever for the slide-12 condition: the model already assumes rent = RENT_FACTOR_VS_PRIME x prime rent, and
# that is what gives the base-case payback. Find the rent share of prime at which the target country's store payback
# reaches the Go threshold (bisection on the model itself), so the slide never quotes a lever that changes nothing.
from beauty_expansion.analysis import business_case as bc  # noqa: E402

target = json.loads((P / "decision.json").read_text())["target"]
bench = bc.fr_store_benchmark(pd.read_csv(P / "internal_stores_fr.csv"))
assumed_rent = config.RENT_FACTOR_VS_PRIME


def payback_at(rent_factor: float) -> float:
    config.RENT_FACTOR_VS_PRIME = rent_factor
    try:
        pb = bc.unit_economics(target, kfull, bench)["payback_years"]
    finally:
        config.RENT_FACTOR_VS_PRIME = assumed_rent
    return float("inf") if pb is None else pb


rent_needed = None                       # share of prime rent (0-1) that meets the payback target; None = rent alone can't
if payback_at(0.0) <= max_payback:
    lo, hi = 0.0, assumed_rent
    if payback_at(hi) <= max_payback:
        rent_needed = hi
    else:
        for _ in range(40):
            mid = (lo + hi) / 2
            lo, hi = (mid, hi) if payback_at(mid) <= max_payback else (lo, mid)
        rent_needed = lo
rent_lever = {"assumed": assumed_rent, "needed": rent_needed,
              "primeRent": float(kfull.loc[target, "prime_rent_eur_m2"])}

# ---------------------------------------------------------------------------------------------------------------
# Figures quoted in the deck text, computed here so the slides follow the data
# ---------------------------------------------------------------------------------------------------------------
AXES = {"market": ["market_cagr", "spend_per_capita_eur", "market_size_meur"], "margin": ["gross_margin_post_tax"],
        "network": ["catchment_density_per_100k", "prime_rent_eur_m2"], "logistics": ["hub_distance_km", "trade_friction"],
        "assortment": ["catalogue_eligible_pct", "personal_care_share_pct"]}
weights = {a: round(sum(config.KPI_WEIGHTS[k] for k in ks) * 100) for a, ks in AXES.items()}
lv = pd.read_csv(P / "lvmh_selective_retailing.csv").sort_values("year")
lv["growth"] = lv["revenue_meur"].pct_change() * 100
lv_peak = lv.loc[lv["growth"].idxmax()]
lv_last = lv.iloc[-1]
schema_sql = (ROOT / "sql" / "schema.sql").read_text()
tables = re.findall(r"CREATE (?:OR REPLACE )?TABLE (?:IF NOT EXISTS )?(\w+)", schema_sql)
dims, facts_t = sorted(t for t in tables if t.startswith("dim_")), sorted(t for t in tables if t.startswith("fact_"))
from beauty_expansion import contracts  # noqa: E402

collected = subprocess.run([sys.executable, "-m", "pytest", "--collect-only", "-q"], cwd=ROOT, capture_output=True, text=True)
n_tests = int(re.search(r"(\d+) tests? collected", collected.stdout).group(1))
case_base = case[case["scenario"] == "base"].set_index("code")
others = case_base.drop(index=target)
plan_b = others["plan_npv_meur"].idxmax()
plan_t = plan[plan["code"] == target].sort_values("year")
first_pos = plan_t.loc[plan_t["fcf_meur"] > 0, "year"]
cand = kfull.loc[list(config.CANDIDATES)]
low_margin = cand["gross_margin_post_tax"].nsmallest(2)
rank_t = ranking.set_index("code")
deck = {
    "frSharePct": fr_revenue / kfull.loc[config.BASELINE, "market_size_meur"] * 100,
    "lvLastYear": int(lv_last["year"]), "lvLastGrowth": float(lv_last["growth"]),
    "lvPeakYear": int(lv_peak["year"]), "lvPeakGrowth": float(lv_peak["growth"]),
    "nKpis": len(config.KPI_WEIGHTS), "weights": weights,
    "nDims": len(dims), "nFacts": len(facts_t), "nContracts": len(contracts.CONTRACTS), "nTests": n_tests,
    "catalogueSize": config.CATALOGUE_SIZE,
    "planTotal": sum(config.PLAN_STORES.values()), "planStart": min(config.PLAN_STORES),
    "planFirst": config.PLAN_STORES[min(config.PLAN_STORES)], "wacc": config.WACC * 100,
    "nScenarios": len(bc.SCENARIO_REVENUE_FACTOR),
    "runnerUp": ranking.sort_values("score", ascending=False)["code"].iloc[1],
    "scores": {a: float(rank_t.loc[target, a]) for a in AXES},
    "lowMargin": list(low_margin.index), "lowMarginVat": float(cand.loc[low_margin.index, "vat_standard_rate"].min() * 100),
    "lowMarginCeil": float(low_margin.max() * 100),
    "nScraped": int(kfull.loc[target, "scraped_products"]),
    "planB": plan_b, "marketRatio": kfull.loc[target, "market_size_meur"] / kfull.loc[plan_b, "market_size_meur"],
    "lastNegYear": int(plan_t.loc[plan_t["fcf_meur"] < 0, "year"].max()),
    "firstPosYear": int(first_pos.min()) if len(first_pos) else None,
}

# Claims written in the templates (titles, prose, Instructions page). If the data or config stop supporting one,
# the build stops here instead of shipping a false sentence: fix the template text, then the check.
fp_t = fprices.set_index("code")
claims = {
    "deck narrative, map and pilot cities are written for the Netherlands": target == "NL",
    "cover: 5 candidates (NL, AT, IE, FI, NO)": set(config.CANDIDATES) == {"NL", "AT", "IE", "FI", "NO"},
    "slide 2: group growth has stalled (< 2 %/yr)": deck["lvLastGrowth"] < 2,
    "slide 3: schema diagram lists these 6 dimensions and 9 facts": dims == sorted(["dim_indicator", "dim_country", "dim_brand", "dim_category", "dim_date", "dim_store"])
        and facts_t == sorted(["fact_macro_indicator", "fact_country_kpi", "fact_competitor_store", "fact_price", "fact_catalogue",
                              "fact_trade", "fact_business_case", "fact_group_financials", "fact_store_pnl"]),
    "slide 5: first under every weighting": (sens["winner"] == target).all(),
    "slide 6: biggest market, best margin, closest hub": cand["market_size_meur"].idxmax() == target
        and cand["gross_margin_post_tax"].idxmax() == target and cand["hub_distance_km"].idxmin() == target,
    "slide 6: competition is the weakest axis": min(deck["scores"], key=deck["scores"].get) == "network",
    "slide 7: same online beauty price as France": abs(kfull.loc[target, "effective_price_index"] - 100) < 1,
    "slide 7: the two lowest margins are the Nordics": set(deck["lowMargin"]) == {"FI", "NO"},
    "slide 8: biggest fragrance market": cand["fragrance_market_meur"].idxmax() == target,
    "slide 8: same fragrance price as France": abs(fp_t.loc[target, "price_index_vs_fr"] - 100) < 1,
    "slide 9: fewer perfumeries per head than France, a few chains hold most shops":
        fragrance.set_index("code").loc[target, "perfumeries_per_100k_top5_cities"] < fragrance.set_index("code").loc["FR", "perfumeries_per_100k_top5_cities"]
        and fragrance.set_index("code").loc[target, "top3_share"] > 0.5,
    "slide 10: plan creates value, cash turns positive": case_base.loc[target, "plan_npv_meur"] > 0 and deck["firstPosYear"] is not None,
    "slide 10: plan B creates more value on a smaller market": case_base.loc[plan_b, "plan_npv_meur"] > case_base.loc[target, "plan_npv_meur"]
        and deck["marketRatio"] > 1,
    "slide 11: target leads the fragrance focus and a break-even exists": FF_WIN == target and breakeven is not None,
    "slide 12: a rent level alone meets the payback target": rent_needed is not None,
    "Instructions: 15 stores of 350 m2 (3 / +5 / +7), NPV at 8 %, 1 % terminal growth": config.PLAN_STORES == {2027: 3, 2028: 5, 2029: 7}
        and config.STORE_SIZE_M2 == 350 and config.WACC == 0.08 and bc.TERMINAL_GROWTH == 0.01,
    "Instructions: payback target 4 years, 10-year payback horizon": max_payback == 4 and len(config.RAMP_UP) + 5 == 10,
    "Instructions: weights 30 / 20 / 20 / 15 / 15": list(weights.values()) == [30, 20, 20, 15, 15],
    "Instructions: scenarios sales -20 % / +10 %": bc.SCENARIO_REVENUE_FACTOR == {"pessimistic": 0.80, "base": 1.00, "optimistic": 1.10},
    "Instructions: 17 products compared, 9 fragrance brands, 100-perfumery threshold, FR revenue 2 511 M€":
        deck["nScraped"] == 17 and int(fprices.set_index("code").loc["FR", "n_brands"]) == 9
        and config.FRAGRANCE_MIN_SHOPS == 100 and fr_revenue == 2511,
}
failed = [k for k, ok in claims.items() if not ok]
if failed:
    raise SystemExit("Template text no longer matches the data, update it before rebuilding:\n  - " + "\n  - ".join(failed))

data = {
    "deck": deck,
    "rentLever": rent_lever,
    "fcheck": fcheck,
    "decision": json.loads((P / "decision.json").read_text()),
    "maxPayback": max_payback,
    "frStores": fr_stores, "frRevenue": fr_revenue, "claudeModel": claude_model,
    "ai": json.loads((P / "ai_summary.json").read_text()),     # AI brick (analysis/ai_summary.py)
    "ranking": records(ranking),
    "case": records(case),
    "plan": records(plan),
    "kpis": records(kpis),
    "fragrance": records(fragrance),
    "fprices": records(fprices),
    "fmarketYear": int(pd.read_csv(P / "fragrance_market.csv")["year"].max()),
    "sensitivity": records(pd.read_csv(P / "sensitivity.csv")),
    "nStores": int(len(pd.read_csv(P / "stores.csv"))),
    "fbrands": records(fitems.groupby(["brand", "code"], as_index=False)["price_per_ml"].median()),
    "builtFrom": pd.Timestamp((P / "decision.json").stat().st_mtime, unit="s").strftime("%Y-%m-%d"),
}

previous_deck = (HERE / "slides_comex.html").read_text() if (HERE / "slides_comex.html").exists() else ""
for template, name in [("template.html", "dashboard_comex.html"), ("template_v2.html", "dashboard_comex_v2.html"), ("template_slides.html", "slides_comex.html")]:
    html = (HERE / template).read_text().replace("/*__DATA__*/null", json.dumps(data, ensure_ascii=False))
    out = HERE / name
    out.write_text(html)
    print(f"wrote {out.relative_to(ROOT)} ({len(html) // 1024} KB)")

pptx = HERE / "Sephora_Europe_2027_Comex.pptx"
if pptx.exists() and (HERE / "slides_comex.html").read_text() != previous_deck:
    print("deck changed: run python app/comex/export_pptx.py to refresh the PPTX")
