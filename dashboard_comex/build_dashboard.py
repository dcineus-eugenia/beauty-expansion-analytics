"""Build the Comex dashboard: one self-contained HTML file, works offline.

    python dashboard_comex/build_dashboard.py      # after python -m beauty_expansion.pipeline

Reads data/processed/*.csv, decision.json and ai_summary.json, injects them into the 3 templates and writes:
  dashboard_comex.html     dashboard with tabs
  dashboard_comex_v2.html  one-page dashboard + Instructions page
  slides_comex.html        Comex deck, 12 slides (arrow keys to navigate, Cmd+P to export a PDF)
The HTML outputs are committed so the team can open them without running the pipeline.
"""
import json
import pathlib
import re

import pandas as pd

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
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

data = {
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

for template, name in [("template.html", "dashboard_comex.html"), ("template_v2.html", "dashboard_comex_v2.html"), ("template_slides.html", "slides_comex.html")]:
    html = (HERE / template).read_text().replace("/*__DATA__*/null", json.dumps(data, ensure_ascii=False))
    out = HERE / name
    out.write_text(html)
    print(f"wrote {out.relative_to(ROOT)} ({len(html) // 1024} KB)")
