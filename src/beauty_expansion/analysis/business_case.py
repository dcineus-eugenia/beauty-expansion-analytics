"""Is the expansion profitable? Store-level unit economics and a 2027-2031 roll-out plan.

Method
------
1. Mature revenue of one new store = average French store (simulated network, calibrated on
   Sephora's real revenue) x local demand ratio x assortment coverage x competition factor.
   - local demand ratio = personal-care spend per inhabitant (target / France), converted to
     net-of-VAT revenue with each country's VAT rate, dampened by config.DEMAND_ELASTICITY
     [Eurostat + EC VAT], then x config.NEW_ENTRANT_FACTOR (unknown banner)
   - assortment coverage: half of the sales of non-eligible SKUs is lost, half is substituted
   - competition factor: (France catchment density / target density) ** 0.25, capped to [0.85, 1.15]
2. Costs: COGS at the country's post-tax gross margin [kpis.py], rent = prime rent x factor [C&W],
   staff = FTE x local retail labour cost [Eurostat], other opex + central costs [assumptions].
3. Roll-out: config.PLAN_STORES, ramp-up curve, capex at opening, depreciation over 8 years,
   corporate tax [OECD], NPV at config.WACC with a terminal value after 2031.
Go/No-Go rule: unit payback <= config.DECISION_MAX_PAYBACK_YEARS and plan NPV > 0.
"""

import pandas as pd

from beauty_expansion import config

DEPRECIATION_YEARS = 8
TERMINAL_GROWTH = 0.01
PROJECTION_END = 2031
SCENARIO_REVENUE_FACTOR = {"pessimistic": 0.80, "base": 1.00, "optimistic": 1.10}


def fr_store_benchmark(stores_fr: pd.DataFrame) -> dict:
    """Average French non-flagship store: the format we would replicate abroad."""
    s = stores_fr[stores_fr["format"] != "flagship"]
    return {
        "revenue_eur": s["revenue_eur"].mean(),
        "other_opex_pct": (s["other_opex_eur"] / s["revenue_eur"]).mean(),
        "revenue_per_fte": (s["revenue_eur"] / s["staff_fte"]).mean(),
        "ebitda_margin": (s["store_ebitda_eur"].sum() / s["revenue_eur"].sum()),
    }


def mature_store(cc: str, kpis: pd.DataFrame, bench: dict) -> dict:
    k, fr = kpis.loc[cc], kpis.loc[config.BASELINE]
    spend_ratio = (k["spend_per_capita_eur"] / fr["spend_per_capita_eur"]) * (1 + fr["vat_standard_rate"]) / (1 + k["vat_standard_rate"])
    demand = spend_ratio ** config.DEMAND_ELASTICITY * config.NEW_ENTRANT_FACTOR
    coverage = 1 - 0.5 * (1 - k["catalogue_eligible_pct"] / 100)
    competition = min(1.15, max(0.85, (fr["catchment_density_per_100k"] / k["catchment_density_per_100k"]) ** 0.25))
    revenue = bench["revenue_eur"] * demand * coverage * competition

    fte = max(config.STAFF_PER_STORE_FTE * 0.6, revenue / bench["revenue_per_fte"])
    return {
        "country_code": cc,
        "demand_factor": demand, "assortment_factor": coverage, "competition_factor": competition,
        "revenue_eur": revenue,
        "gross_margin_eur": revenue * k["gross_margin_post_tax"],
        "rent_eur": config.STORE_SIZE_M2 * k["prime_rent_eur_m2"] * config.RENT_FACTOR_VS_PRIME,
        "staff_fte": fte,
        "staff_cost_eur": fte * config.HOURS_PER_FTE_YEAR * k["labour_cost_retail_eur_h"],
        "other_costs_eur": revenue * (bench["other_opex_pct"] + config.CENTRAL_COSTS_PCT),
        "capex_eur": config.STORE_SIZE_M2 * config.FITOUT_CAPEX_EUR_M2 + config.OPENING_COSTS_EUR,
        "inventory_eur": revenue * (1 - k["gross_margin_post_tax"]) * config.INVENTORY_DAYS / 365,
    }


def unit_economics(cc: str, kpis: pd.DataFrame, bench: dict, revenue_factor: float = 1.0) -> dict:
    m = mature_store(cc, kpis, bench)
    tax = kpis.loc[cc, "corporate_tax_rate"]
    cash, cumulative, payback = [], -(m["capex_eur"] + m["inventory_eur"]), None
    for age, ramp in enumerate(config.RAMP_UP + [1.0] * 5, start=1):
        rev = m["revenue_eur"] * ramp * revenue_factor
        ebitda = (rev * kpis.loc[cc, "gross_margin_post_tax"] - m["rent_eur"] - m["staff_cost_eur"]
                  - rev * (m["other_costs_eur"] / m["revenue_eur"]))
        ebit = ebitda - m["capex_eur"] / DEPRECIATION_YEARS
        fcf = ebitda - max(ebit, 0) * tax
        cash.append(fcf)
        prev = cumulative
        cumulative += fcf
        if payback is None and cumulative >= 0 and fcf > 0:
            payback = age - 1 + (-prev / fcf)
    mature_ebitda = (m["gross_margin_eur"] * revenue_factor - m["rent_eur"] - m["staff_cost_eur"]
                     - m["other_costs_eur"] * revenue_factor)
    return {**m, "mature_ebitda_eur": mature_ebitda,
            "mature_ebitda_margin": mature_ebitda / (m["revenue_eur"] * revenue_factor),
            "payback_years": payback}


def rollout(cc: str, kpis: pd.DataFrame, bench: dict, revenue_factor: float = 1.0) -> pd.DataFrame:
    m = mature_store(cc, kpis, bench)
    tax = kpis.loc[cc, "corporate_tax_rate"]
    cohorts = {y: n for y, n in config.PLAN_STORES.items()}
    rows = []
    for year in range(min(cohorts), PROJECTION_END + 1):
        revenue = staff = rent = capex = depreciation = 0.0
        stores_open = 0
        for open_year, n in cohorts.items():
            if open_year > year:
                continue
            age = year - open_year
            ramp = config.RAMP_UP[min(age, len(config.RAMP_UP) - 1)]
            stores_open += n
            revenue += n * m["revenue_eur"] * ramp * revenue_factor
            staff += n * m["staff_cost_eur"]
            rent += n * m["rent_eur"]
            depreciation += n * m["capex_eur"] / DEPRECIATION_YEARS
            if open_year == year:
                capex += n * (m["capex_eur"] + m["inventory_eur"])
        gross = revenue * kpis.loc[cc, "gross_margin_post_tax"]
        other = revenue * (m["other_costs_eur"] / m["revenue_eur"])
        ebitda = gross - rent - staff - other
        ebit = ebitda - depreciation
        fcf = ebitda - max(ebit, 0) * tax - capex     # capex here includes opening inventory
        rows.append({"country_code": cc, "year": year, "stores_open": stores_open, "revenue_eur": revenue,
                     "gross_margin_eur": gross, "rent_eur": rent, "staff_cost_eur": staff,
                     "other_costs_eur": other, "ebitda_eur": ebitda, "ebit_eur": ebit, "capex_eur": capex,
                     "free_cash_flow_eur": fcf})
    return pd.DataFrame(rows)


def npv(plan: pd.DataFrame) -> float:
    start = plan["year"].min()
    flows = plan["free_cash_flow_eur"].values
    discounted = sum(f / (1 + config.WACC) ** (y - start + 1) for f, y in zip(flows, plan["year"]))
    terminal = flows[-1] * (1 + TERMINAL_GROWTH) / (config.WACC - TERMINAL_GROWTH)
    return discounted + terminal / (1 + config.WACC) ** (plan["year"].max() - start + 1)


def evaluate(kpis: pd.DataFrame, stores_fr: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Unit economics + plan NPV for every candidate and scenario; base-case plan table."""
    bench = fr_store_benchmark(stores_fr)
    summary, plans = [], []
    for cc in config.CANDIDATES:
        for scenario, factor in SCENARIO_REVENUE_FACTOR.items():
            u = unit_economics(cc, kpis, bench, factor)
            plan = rollout(cc, kpis, bench, factor)
            summary.append({
                "country_code": cc, "scenario": scenario,
                "store_revenue_meur": u["revenue_eur"] * factor / 1e6,
                "store_ebitda_margin": u["mature_ebitda_margin"],
                "payback_years": u["payback_years"],
                "plan_revenue_2029_meur": plan.loc[plan["year"] == 2029, "revenue_eur"].iloc[0] / 1e6,
                "plan_capex_meur": plan["capex_eur"].sum() / 1e6,
                "plan_npv_meur": npv(plan) / 1e6,
                "demand_factor": u["demand_factor"], "assortment_factor": u["assortment_factor"],
                "competition_factor": u["competition_factor"],
            })
            if scenario == "base":
                plans.append(plan)
    s = pd.DataFrame(summary)
    s["go"] = (s["payback_years"].notna() & (s["payback_years"] <= config.DECISION_MAX_PAYBACK_YEARS)
               & (s["plan_npv_meur"] > config.DECISION_MIN_NPV))
    return s, pd.concat(plans, ignore_index=True)
