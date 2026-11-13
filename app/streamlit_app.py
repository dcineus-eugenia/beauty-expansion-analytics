"""Sephora European expansion: Comex dashboard.

Run the pipeline first, then:   streamlit run app/streamlit_app.py
"""

import json

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from beauty_expansion import config
from beauty_expansion.extract import comext

P = config.PROCESSED
FOCUS = "#2a78d6"       # the recommended country
OTHER = "#a3a29c"       # other candidates
BASE = "#52514e"        # France baseline
SEQ = ["#e8f0fb", "#9ec3f0", "#2a78d6", "#0d3f80"]   # one hue, light -> dark

st.set_page_config(page_title="Sephora · European expansion", page_icon="💄", layout="wide")


@st.cache_data
def load():
    need = ["kpis_by_country.csv", "country_ranking.csv", "business_case_summary.csv", "ai_summary.json", "decision.json"]
    if not all((P / f).exists() for f in need):
        return None
    d = {
        "kpis": pd.read_csv(P / "kpis_by_country.csv", index_col=0),
        "ranking": pd.read_csv(P / "country_ranking.csv", index_col=0),
        "sens": pd.read_csv(P / "sensitivity.csv"),
        "case": pd.read_csv(P / "business_case_summary.csv"),
        "plan": pd.read_csv(P / "business_case_plan.csv"),
        "catchment": pd.read_csv(P / "catchment_density.csv"),
        "stores": pd.read_csv(P / "stores.csv"),
        "prices": pd.read_csv(P / "prices.csv"),
        "lvmh": pd.read_csv(P / "lvmh_selective_retailing.csv"),
        "ai": json.loads((P / "ai_summary.json").read_text()),
        "decision": json.loads((P / "decision.json").read_text()),
    }
    # Fragrance files: produced by issues #2 (market), #3 (prices) and #4 (competition). Each one is optional,
    # the Fragrance tab says what is missing instead of failing.
    for key, name in [("frag_market", "fragrance_market.csv"), ("frag_prices", "fragrance_price_summary.csv"),
                      ("frag_comp", "fragrance_competition.csv")]:
        d[key] = pd.read_csv(P / name) if (P / name).exists() else None
    return d


d = load()
if d is None:
    st.error("No results yet. Run `python -m beauty_expansion.pipeline` first.")
    st.stop()

kpis, ranking, case, ai = d["kpis"], d["ranking"], d["case"], d["ai"]
verdict = d["decision"]
winner = verdict["target"]
names = {**config.COUNTRIES}


def color_of(cc: str) -> str:
    return FOCUS if cc == winner else (BASE if cc == config.BASELINE else OTHER)


def bar(df: pd.DataFrame, x: str, y: str, title: str, fmt: str, xlabel: str = "", ref: float | None = None):
    df = df.copy()
    df["label"] = df.index.map(names)
    fig = go.Figure(go.Bar(
        x=df[x], y=df["label"], orientation="h",
        marker=dict(color=[color_of(c) for c in df.index], cornerradius=4),
        text=[format(v, fmt) for v in df[x]], textposition="outside",
        hovertemplate="%{y}: %{x:" + fmt + "}<extra></extra>",
    ))
    if ref is not None:
        fig.add_vline(x=ref, line_dash="dot", line_color=BASE, annotation_text="France", annotation_position="top")
    fig.update_layout(title=title, height=300, margin=dict(l=10, r=40, t=50, b=30),
                      xaxis=dict(title=xlabel, showgrid=True, gridcolor="rgba(128,128,128,0.15)"),
                      yaxis=dict(autorange="reversed"), bargap=0.35, showlegend=False)
    return fig


def comment(key: str):
    text = ai.get("chart_comments", {}).get(key)
    if text:
        st.caption(f"🤖 {text}")


# ---------------------------------------------------------------- header
st.title("Sephora · Which European country for 2027-2029?")
st.caption("Is opening stores in the target country feasible and profitable? "
           "Candidates are European countries with no Sephora store in 2026-11.")

rec = ai["recommendation"]
base_case = case[(case["country_code"] == winner) & (case["scenario"] == "base")].iloc[0]
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Recommendation", rec)
c2.metric("Target country", names[winner], f"score {ranking.loc[winner, 'total_score']:.0f}/100", delta_color="off")
c3.metric("Plan NPV (15 stores)", f"{base_case['plan_npv_meur']:.0f} M€", delta_color="off")
c4.metric("Store payback", f"{base_case['payback_years']:.1f} yrs" if pd.notna(base_case["payback_years"]) else "> 10 yrs",
          f"rule ≤ {config.DECISION_MAX_PAYBACK_YEARS} yrs", delta_color="off")
c5.metric("Revenue 2029", f"{base_case['plan_revenue_2029_meur']:.0f} M€", delta_color="off")

tabs = st.tabs(["🧭 Summary", "📈 Market", "💶 Price & margin", "🗺️ Network", "🚚 Operations & assortment",
                "🧮 Business case", "⚖️ Robustness", "📚 Data & sources", "🌸 Fragrance"])

# ---------------------------------------------------------------- summary
with tabs[0]:
    left, right = st.columns([3, 2])
    with left:
        st.subheader(ai["headline"])
        st.write(ai["executive_summary"])
        st.markdown("**Key insights**")
        for i in ai["key_insights"]:
            st.markdown(f"- **{i['title']}**: {i['detail']}")
        cols = st.columns(3)
        for col, title, items in zip(cols, ["Risks", "Conditions for success", "Next steps"],
                                     [ai["risks"], ai["conditions_for_success"], ai["next_steps"]]):
            col.markdown(f"**{title}**")
            for item in items:
                col.markdown(f"- {item}")
        st.markdown(f"**Decision rule.** Selection: {verdict['selection_rule']}. Checks: "
                    + ", ".join(f"{'✅' if ok else '❌'} {k.replace('_', ' ')}" for k, ok in verdict["checks"].items()))
        st.caption(f"Text generated by: {ai.get('generated_by')}. It explains the computed figures; "
                   "the country and the recommendation come from the written decision rule.")
    with right:
        st.plotly_chart(bar(ranking[["total_score"]], "total_score", None, "Weighted attractiveness score", ".0f",
                            "score / 100"), width="stretch")
        comment("ranking")
        axes = ranking.drop(columns=["total_score", "country"])
        axes.index = axes.index.map(names)
        fig = px.imshow(axes.round(0), text_auto=True, color_continuous_scale=SEQ, zmin=0, zmax=100, aspect="auto")
        fig.update_layout(title="Score by axis (100 = best candidate)", height=300, margin=dict(l=10, r=10, t=50, b=10),
                          coloraxis_showscale=False)
        fig.update_traces(hovertemplate="%{y} · %{x}: %{z:.0f}<extra></extra>")
        st.plotly_chart(fig, width="stretch")

# ---------------------------------------------------------------- market
with tabs[1]:
    a, b = st.columns(2)
    a.plotly_chart(bar(kpis[["spend_per_capita_eur"]], "spend_per_capita_eur", None,
                       "Personal-care spend per inhabitant (€/yr)", ",.0f", "€", kpis.loc["FR", "spend_per_capita_eur"]),
                   width="stretch")
    b.plotly_chart(bar(kpis[["market_cagr"]] * 100, "market_cagr", None, "Market growth, CAGR 2019 → latest (%)", ".1f",
                       "% per year", kpis.loc["FR", "market_cagr"] * 100), width="stretch")
    a.plotly_chart(bar(kpis.drop(index="FR")[["market_size_meur"]], "market_size_meur", None,
                       "Personal-care market size (M€)", ",.0f", "M€"), width="stretch")
    lead = kpis.drop(index="FR")[["leader_brand", "leader_store_share"]].copy()
    lead["leader_store_share"] = (lead["leader_store_share"] * 100).round(0)
    lead.index = lead.index.map(names)
    b.markdown("**Leading selective competitor (share of selective beauty stores)**")
    b.dataframe(lead.rename(columns={"leader_brand": "Leader", "leader_store_share": "Store share %"}),
                width="stretch")
    b.metric("Sephora's share of French personal-care spend (2024)", f"{kpis.loc['FR', 'sephora_fr_market_share']:.1%}")
    comment("market")

# ---------------------------------------------------------------- price & margin
with tabs[2]:
    a, b = st.columns(2)
    a.plotly_chart(bar(kpis[["relative_price_index"]], "relative_price_index", None,
                       "Shelf price level vs France (France = 100)", ".0f", "index", 100), width="stretch")
    a.caption("Eurostat price level index, 'miscellaneous goods & services' (includes personal care). "
              f"The margin uses the effective beauty shelf price instead: scraped where available, else "
              f"Eurostat x {kpis['price_passthrough'].iloc[0]:.0%} pass-through.")
    b.plotly_chart(bar(kpis[["gross_margin_post_tax"]] * 100, "gross_margin_post_tax", None,
                       "Estimated gross margin after VAT, logistics & customs (%)", ".1f", "%",
                       kpis.loc["FR", "gross_margin_post_tax"] * 100), width="stretch")
    pr = d["prices"]
    if len(pr):
        piv = pr.pivot_table(index=["brand", "product_id"], columns="country_code", values="price_eur")
        idx = (piv.drop(columns="FR").div(piv["FR"], axis=0) * 100).round(0)
        b.markdown(f"**Online check: same {len(piv)} products scraped on LOOKFANTASTIC (France = 100)**")
        b.dataframe(idx.median().rename("median index").to_frame().T, width="stretch")
        b.caption("Online prices are harmonised across the eurozone, so physical shelf-price gaps come from local retail.")
    comment("price_margin")

# ---------------------------------------------------------------- network
with tabs[3]:
    a, b = st.columns([2, 3])
    a.plotly_chart(bar(kpis[["catchment_density_per_100k"]], "catchment_density_per_100k", None,
                       "Selective beauty stores within 10 km of the 5 largest cities, per 100k inhabitants", ".1f",
                       "stores / 100k", kpis.loc["FR", "catchment_density_per_100k"]), width="stretch")
    a.plotly_chart(bar(kpis[["prime_rent_eur_m2"]].drop(index="FR"), "prime_rent_eur_m2", None,
                       "Prime high-street rent (€/m²/yr)", ",.0f", "€/m²/yr"), width="stretch")
    a.caption(f"Paris Champs-Élysées: {kpis.loc['FR', 'prime_rent_eur_m2']:,.0f} €/m²/yr (off scale). Source: Cushman & Wakefield 2025.")
    country = b.selectbox("Country map", list(config.CANDIDATES), index=list(config.CANDIDATES).index(winner),
                          format_func=names.get)
    s = d["stores"][(d["stores"]["country_code"] == country)]
    fig = px.scatter_map(s, lat="lat", lon="lon", color="segment", hover_name="brand", hover_data={"city": True, "lat": False, "lon": False},
                         color_discrete_map={"selective": FOCUS, "drugstore": OTHER}, zoom=5, height=520)
    fig.update_layout(map_style="carto-positron", margin=dict(l=0, r=0, t=10, b=0), legend_title_text="")
    b.plotly_chart(fig, width="stretch")
    b.caption(f"{(s['segment'] == 'selective').sum()} selective and {(s['segment'] == 'drugstore').sum()} drugstore "
              "locations in OpenStreetMap (coverage is incomplete, especially in the Nordics).")
    comment("network")

# ---------------------------------------------------------------- operations & assortment
with tabs[4]:
    a, b = st.columns(2)
    a.plotly_chart(bar(kpis[["hub_distance_km"]], "hub_distance_km", None,
                       "Average road distance from the nearest Sephora hub (km)", ",.0f", "km"), width="stretch")
    a.plotly_chart(bar(kpis[["labour_cost_retail_eur_h"]], "labour_cost_retail_eur_h", None,
                       "Retail labour cost (€/hour, Eurostat)", ".1f", "€/h", kpis.loc["FR", "labour_cost_retail_eur_h"]),
                   width="stretch")
    b.plotly_chart(bar(kpis[["catalogue_eligible_pct"]].drop(index="FR"), "catalogue_eligible_pct", None,
                       "% of French catalogue sellable at launch (revenue-weighted)", ".0f", "%"), width="stretch")
    taxes = kpis[["vat_standard_rate", "corporate_tax_rate", "trade_friction"]].copy()
    taxes[["vat_standard_rate", "corporate_tax_rate"]] *= 100
    taxes.index = taxes.index.map(names)
    b.markdown("**Taxes & trade friction**")
    b.dataframe(taxes.rename(columns={"vat_standard_rate": "VAT %", "corporate_tax_rate": "Corporate tax %",
                                      "trade_friction": "Customs + FX friction (pts)"}).round(1), width="stretch")

# ---------------------------------------------------------------- business case
with tabs[5]:
    country = st.selectbox("Country", list(config.CANDIDATES), index=list(config.CANDIDATES).index(winner),
                           format_func=names.get, key="bc")
    plan = d["plan"][d["plan"]["country_code"] == country]
    a, b = st.columns(2)
    last = plan[plan["year"] == plan["year"].max()].iloc[0]
    steps = ["revenue_eur", "gross_margin_eur", "rent_eur", "staff_cost_eur", "other_costs_eur", "ebitda_eur"]
    fig = go.Figure(go.Waterfall(
        x=["Revenue", "COGS", "Rent", "Staff", "Other & central", "EBITDA"],
        measure=["absolute", "relative", "relative", "relative", "relative", "total"],
        y=[last["revenue_eur"] / 1e6, -(last["revenue_eur"] - last["gross_margin_eur"]) / 1e6, -last["rent_eur"] / 1e6,
           -last["staff_cost_eur"] / 1e6, -last["other_costs_eur"] / 1e6, 0],
        increasing=dict(marker_color=FOCUS), decreasing=dict(marker_color=OTHER), totals=dict(marker_color=FOCUS),
        connector=dict(line=dict(color="rgba(128,128,128,0.4)")),
        hovertemplate="%{x}: %{y:,.1f} M€<extra></extra>",
    ))
    fig.update_layout(title=f"{names[country]}: P&L of the 15-store network in {int(last['year'])} (M€)", height=380,
                      margin=dict(l=10, r=10, t=50, b=10))
    a.plotly_chart(fig, width="stretch")
    fig = go.Figure()
    fig.add_bar(x=plan["year"], y=plan["free_cash_flow_eur"] / 1e6, marker=dict(
        color=[FOCUS if v >= 0 else OTHER for v in plan["free_cash_flow_eur"]], cornerradius=4),
        hovertemplate="%{x}: %{y:,.1f} M€<extra></extra>", name="Free cash flow")
    fig.update_layout(title="Free cash flow per year (M€): capex years are negative", height=380,
                      margin=dict(l=10, r=10, t=50, b=10), showlegend=False)
    b.plotly_chart(fig, width="stretch")
    t = case[case["country_code"] == country].set_index("scenario")[
        ["store_revenue_meur", "store_ebitda_margin", "payback_years", "plan_capex_meur", "plan_npv_meur", "go"]]
    st.dataframe(t.rename(columns={"store_revenue_meur": "Mature store revenue (M€)", "store_ebitda_margin": "Store EBITDA margin",
                                   "payback_years": "Payback (yrs)", "plan_capex_meur": "Capex (M€)",
                                   "plan_npv_meur": "NPV (M€)", "go": "Go?"}).round(2), width="stretch")
    comment("business_case")
    with st.expander("Assumptions (edit src/beauty_expansion/config.py and re-run)"):
        st.write({k: getattr(config, k) for k in ["PLAN_STORES", "STORE_SIZE_M2", "RENT_FACTOR_VS_PRIME",
                                                  "FITOUT_CAPEX_EUR_M2", "OPENING_COSTS_EUR", "RAMP_UP",
                                                  "CENTRAL_COSTS_PCT", "WACC", "DECISION_MAX_PAYBACK_YEARS"]})

# ---------------------------------------------------------------- robustness
with tabs[6]:
    sens = d["sens"].copy()
    sens["winner"] = sens["winner"].map(names)
    sens["runner_up"] = sens["runner_up"].map(names)
    st.markdown("**Does the winner change if the Comex weighs the axes differently?**")
    st.dataframe(sens, width="stretch", hide_index=True)
    comment("sensitivity")
    all_cases = case.pivot_table(index="country_code", columns="scenario", values="plan_npv_meur")
    all_cases.index = all_cases.index.map(names)
    st.markdown("**Plan NPV (M€) by revenue scenario: pessimistic −20 %, optimistic +10 %**")
    st.dataframe(all_cases[["pessimistic", "base", "optimistic"]].round(0), width="stretch")

# ---------------------------------------------------------------- data
with tabs[7]:
    lv = d["lvmh"]
    a, b = st.columns(2)
    fig = go.Figure(go.Bar(x=lv["year"], y=lv["revenue_meur"], marker=dict(color=BASE, cornerradius=4),
                           hovertemplate="%{x}: %{y:,.0f} M€<extra></extra>"))
    fig.update_layout(title="LVMH Selective Retailing revenue (M€)", height=300, margin=dict(l=10, r=10, t=50, b=10))
    a.plotly_chart(fig, width="stretch")
    fig = go.Figure(go.Scatter(x=lv["year"], y=lv["operating_margin"] * 100, mode="lines+markers",
                               line=dict(color=BASE, width=2), marker=dict(size=8),
                               hovertemplate="%{x}: %{y:.1f} %<extra></extra>"))
    fig.update_layout(title="Operating margin (%)", height=300, margin=dict(l=10, r=10, t=50, b=10))
    b.plotly_chart(fig, width="stretch")
    st.caption("Selective Retailing = Sephora + DFS + Le Bon Marché (LVMH does not publish Sephora alone).")
    st.markdown("""
| Source | Type | Used for |
|---|---|---|
| Eurostat API (demo_pjan, nama_10_pc, nama_10_cp18, prc_hicp_aind, prc_ppp_ind_1, lc_lci_lev) | Open data API | population, spending, growth, price levels, labour cost |
| OpenStreetMap Overpass API | Open data API | competitor & Sephora store locations, city populations |
| LOOKFANTASTIC country sites | Web scraper | same-product online prices FR / NL / AT / IE |
| LVMH ESG Data Book 2025 + results releases | Public Excel / press | headcount, Selective Retailing revenue & margin |
| Cushman & Wakefield Main Streets 2025, EC VAT, OECD, national customs | Manual (cited) | rents, taxes, duties |
| Sephora France stores & catalogue | **Simulated** internal DB, calibrated on public totals | store P&L, catalogue eligibility |
""")
    st.markdown("**Full KPI table**")
    st.dataframe(kpis.round(3), width="stretch")

# ---------------------------------------------------------------- fragrance
with tabs[8]:
    st.caption("Fragrance (perfumes and toilet waters, HS 3303) is measured on its own: customs data for the market, "
               "LOOKFANTASTIC for prices, OpenStreetMap for perfumeries.")
    fm, fp, fc = d["frag_market"], d["frag_prices"], d["frag_comp"]

    # --- market (issue #2)
    if fm is None:
        st.info("Market data missing: run `python -m beauty_expansion.pipeline` (issue #2, fragrance_market.csv).")
    else:
        latest = fm.sort_values("year").groupby("country_code").tail(1).set_index("country_code")
        year = int(latest["year"].max())
        a, b = st.columns(2)
        pc = latest[["per_capita_eur"]].dropna()
        a.plotly_chart(bar(pc, "per_capita_eur", None, f"Fragrance market per inhabitant, {year} (€)", ".1f", "€ per inhabitant"),
                       width="stretch")
        a.caption("Apparent consumption = imports − exports of HS 3303 (customs values, not retail prices). "
                  "France is a net exporter (exports 10x imports), so its market can't be measured this way: "
                  "no reference line here. Source: Eurostat Comext DS-045409, Statistics Norway 08801.")
        growth = (comext.cagr(fm).dropna() * 100).to_frame("cagr")
        b.plotly_chart(bar(growth, "cagr", None, "Fragrance market growth, CAGR 2019 → 2025 (%)", ".1f", "% per year"),
                       width="stretch")
        b.caption("The Dutch growth is an upper bound: some Rotterdam transit remains in imports − exports.")

        nl = fm[fm["country_code"] == "NL"].sort_values("year")
        fig = go.Figure()
        fig.add_bar(x=nl["year"], y=nl["imports_eur"] / 1e6, name="Raw imports", marker=dict(color=OTHER, cornerradius=4),
                    hovertemplate="%{x}: %{y:,.0f} M€<extra>Raw imports</extra>")
        fig.add_bar(x=nl["year"], y=nl["apparent_consumption_eur"] / 1e6, name="Apparent consumption (imports − exports)",
                    marker=dict(color=FOCUS, cornerradius=4),
                    hovertemplate="%{x}: %{y:,.0f} M€<extra>Apparent consumption</extra>")
        fig.update_layout(title="Netherlands: raw imports vs apparent consumption (M€), the Rotterdam re-export effect",
                          barmode="group", height=360, margin=dict(l=10, r=10, t=50, b=10),
                          legend=dict(orientation="h", y=-0.15))
        st.plotly_chart(fig, width="stretch")
        st.caption("Most Dutch imports leave again (exports), so raw imports overstate the local market.")

    # --- prices (issue #3)
    st.markdown("#### Prices")
    if fp is None:
        st.info("Waiting for issue #3 (perfume prices, `fragrance_price_summary.csv`): chart appears once its pull request is merged.")
    else:
        fp = fp.set_index("country_code")
        a, b = st.columns(2)
        a.plotly_chart(bar(fp[["price_ex_vat_index_vs_fr"]].dropna(), "price_ex_vat_index_vs_fr", None,
                           "Perfume price index ex-VAT, same products (France = 100)", ".1f", "index", 100), width="stretch")
        b.plotly_chart(bar(fp[["median_price_per_ml"]].dropna(), "median_price_per_ml", None,
                           "Median perfume price per ml, incl. VAT (€/ml)", ".2f", "€ per ml",
                           fp["median_price_per_ml"].get("FR")), width="stretch")
        st.caption("Online prices on LOOKFANTASTIC only (FR, NL, AT, IE); Finland and Norway have no site. "
                   "Source: issue #3 scraper.")

    # --- competition (issue #4)
    st.markdown("#### Competition")
    if fc is None:
        st.info("Waiting for issue #4 (perfumery competition, `fragrance_competition.csv`): charts appear once its pull request is merged.")
    else:
        fc = fc.set_index("country_code")
        a, b = st.columns(2)
        a.plotly_chart(bar(fc[["perfumeries_per_100k"]], "perfumeries_per_100k", None,
                           "Perfumeries per 100k inhabitants", ".1f", "shops / 100k",
                           fc["perfumeries_per_100k"].get("FR")), width="stretch")
        share = fc[["top3_share"]].dropna() * 100
        b.plotly_chart(bar(share, "top3_share", None, "Share of perfumeries held by the 3 biggest chains (%)", ".0f", "% of shops"),
                       width="stretch")
        if "small_sample" in fc:
            fragile = [names[c] for c in fc.index[fc["small_sample"].fillna(False).astype(bool)]]
            if fragile:
                st.caption("Few perfumeries in OpenStreetMap for " + ", ".join(fragile) + ": their shares are fragile.")
        st.caption("Shares are of shop count, not of sales. Source: OpenStreetMap (issue #4).")
    comment("fragrance")
