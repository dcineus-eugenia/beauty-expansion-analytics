"""The final arbitration: which country, and GO / CONDITIONAL GO / NO-GO.

Two-step rule, written down BEFORE looking at the result so it can be defended at the oral:
  1. Shortlist by attractiveness score. If the top two are within TIE_MARGIN points, the scoring
     can't separate them: the business case (base-case NPV) breaks the tie.
  2. Recommendation for the chosen country:
       GO              NPV > 0, store payback <= config.DECISION_MAX_PAYBACK_YEARS, pessimistic NPV > 0
       CONDITIONAL GO  NPV > 0 but at least one of the other two conditions fails
       NO-GO           base-case NPV <= 0
"""

import json

import pandas as pd

from beauty_expansion import config

TIE_MARGIN = 2.0
OUTPUT = config.PROCESSED / "decision.json"


def decide(ranking: pd.DataFrame, case: pd.DataFrame) -> dict:
    base = case[case["scenario"] == "base"].set_index("country_code")
    pess = case[case["scenario"] == "pessimistic"].set_index("country_code")

    first, second = ranking.index[0], ranking.index[1]
    gap = ranking.loc[first, "total_score"] - ranking.loc[second, "total_score"]
    if gap < TIE_MARGIN:
        target = max([first, second], key=lambda c: base.loc[c, "plan_npv_meur"])
        how = (f"{config.CANDIDATES[first]} and {config.CANDIDATES[second]} are within {gap:.2f} points; "
               f"tie broken by base-case NPV")
    else:
        target = first
        how = f"highest attractiveness score, {gap:.1f} points ahead"

    b, p = base.loc[target], pess.loc[target]
    payback_ok = pd.notna(b["payback_years"]) and b["payback_years"] <= config.DECISION_MAX_PAYBACK_YEARS
    checks = {
        "npv_positive": bool(b["plan_npv_meur"] > config.DECISION_MIN_NPV),
        "payback_within_limit": bool(payback_ok),
        "pessimistic_npv_positive": bool(p["plan_npv_meur"] > config.DECISION_MIN_NPV),
    }
    if not checks["npv_positive"]:
        rec = "NO-GO"
    elif all(checks.values()):
        rec = "GO"
    else:
        rec = "CONDITIONAL GO"

    decision = {"target": target, "target_name": config.CANDIDATES[target], "recommendation": rec,
                "selection_rule": how, "checks": checks,
                "base_npv_meur": round(float(b["plan_npv_meur"]), 1),
                "pessimistic_npv_meur": round(float(p["plan_npv_meur"]), 1),
                "payback_years": None if pd.isna(b["payback_years"]) else round(float(b["payback_years"]), 2)}
    OUTPUT.write_text(json.dumps(decision, indent=2))
    print(f"  decision: {rec} - {decision['target_name']} ({how})")
    return decision
