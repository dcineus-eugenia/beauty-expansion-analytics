"""AI brick of the brief: Claude writes the executive summary and chart comments for the Comex.

Design choices (to defend at the oral):
  - Claude receives ONLY the computed numbers (KPI table, ranking, sensitivity, business case) and the
    decision already taken by the written rule (analysis/decision.py). It explains them; it doesn't
    choose the country and never invents figures.
  - Structured output (JSON schema) -> the dashboard always gets the same sections.
  - Server-side refusal fallback ("fallbacks": "default") so a rare safety decline doesn't break the run.
  - No API key? We write a rule-based summary instead and label it clearly, so the pipeline still runs.
"""

import json
import os

import pandas as pd
from dotenv import load_dotenv

from beauty_expansion import config

OUTPUT = config.PROCESSED / "ai_summary.json"

SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["recommendation", "target_country", "headline", "executive_summary", "key_insights",
                 "risks", "conditions_for_success", "next_steps", "chart_comments"],
    "properties": {
        "recommendation": {"type": "string", "enum": ["GO", "CONDITIONAL GO", "NO-GO"]},
        "target_country": {"type": "string"},
        "headline": {"type": "string", "description": "One sentence for the first slide."},
        "executive_summary": {"type": "string", "description": "120-180 words for board members."},
        "key_insights": {"type": "array", "items": {
            "type": "object", "additionalProperties": False, "required": ["title", "detail"],
            "properties": {"title": {"type": "string"}, "detail": {"type": "string"}}}},
        "risks": {"type": "array", "items": {"type": "string"}},
        "conditions_for_success": {"type": "array", "items": {"type": "string"}},
        "next_steps": {"type": "array", "items": {"type": "string"}},
        "chart_comments": {
            "type": "object", "additionalProperties": False,
            "required": ["ranking", "market", "price_margin", "network", "business_case", "sensitivity"],
            "properties": {k: {"type": "string"} for k in
                           ["ranking", "market", "price_margin", "network", "business_case", "sensitivity"]},
        },
    },
}

SYSTEM = """You are the lead data analyst of Sephora's strategy team, writing for the Comex (executive board).
Context: Sephora (LVMH, Selective Retailing) studies opening physical stores in ONE new European country
over the 2027-2029 strategic plan. The question: is it feasible and profitable?

Rules:
- Use ONLY the figures given in the data block. Never invent a number, a source or a competitor.
- Quote the key numbers you rely on, with units, rounded sensibly.
- The recommendation and target country are decided by the written decision rule given in the data:
  restate them exactly, explain why, and state the conditions that would change them.
- Name the main limitations of the data (simulated internal data, OpenStreetMap coverage, proxies).
- Plain business English, short sentences, no jargon, no markdown."""


def _payload(kpis, ranking, sensitivity, case, verdict: dict) -> str:
    cols = ["market_size_meur", "spend_per_capita_eur", "market_cagr", "relative_price_index",
            "scraped_price_index", "effective_price_index", "gross_margin_post_tax", "catchment_density_per_100k", "leader_brand",
            "leader_store_share", "prime_rent_eur_m2", "labour_cost_retail_eur_h", "hub_distance_km",
            "trade_friction", "catalogue_eligible_pct", "vat_standard_rate", "corporate_tax_rate"]
    return "\n\n".join([
        "KPI TABLE (FR = baseline, others = candidates):\n" + kpis[[c for c in cols if c in kpis]].round(3).to_csv(),
        "WEIGHTED RANKING (0-100):\n" + ranking.round(1).to_csv(),
        "SENSITIVITY OF THE WINNER TO THE WEIGHTS:\n" + sensitivity.to_csv(index=False),
        "BUSINESS CASE (15 stores 2027-2029, NPV at 8% WACC, payback of one store):\n" + case.round(2).to_csv(index=False),
        "DECISION (computed by the written rule, restate it):\n" + json.dumps(verdict, indent=2),
        f"RULE: GO = NPV > 0 AND store payback <= {config.DECISION_MAX_PAYBACK_YEARS} years AND pessimistic NPV > 0; "
        "CONDITIONAL GO = NPV > 0 but another condition fails; NO-GO = NPV <= 0.",
    ])


def _rule_based(ranking: pd.DataFrame, case: pd.DataFrame, verdict: dict) -> dict:
    """Fallback without an API key: same structure, deterministic text built from the numbers."""
    target = verdict["target"]
    base = case[(case["country_code"] == target) & (case["scenario"] == "base")].iloc[0]
    name = verdict["target_name"]
    failed = [k.replace("_", " ") for k, ok in verdict["checks"].items() if not ok]
    return {
        "recommendation": verdict["recommendation"],
        "target_country": name,
        "headline": f"{verdict['recommendation']} for {name}: base-case NPV {verdict['base_npv_meur']:.0f} M€, "
                    f"store payback {base['payback_years']:.1f} years.",
        "executive_summary": "[Rule-based summary: set ANTHROPIC_API_KEY to generate the AI version.] "
                             f"{name} was selected ({verdict['selection_rule']}). A 15-store plan reaches "
                             f"{base['plan_revenue_2029_meur']:.0f} M€ revenue in 2029 for "
                             f"{base['plan_capex_meur']:.0f} M€ invested. "
                             + (f"Conditions not met: {', '.join(failed)}." if failed else "All Go conditions are met."),
        "key_insights": [{"title": "Ranking", "detail": ", ".join(
            f"{config.CANDIDATES[i]}: {s:.0f}" for i, s in ranking["total_score"].items())}],
        "risks": ["Internal data is simulated", "OpenStreetMap store coverage is incomplete"],
        "conditions_for_success": [f"Store payback below {config.DECISION_MAX_PAYBACK_YEARS} years"],
        "next_steps": ["Validate rents with local brokers", "Pilot 3 stores in 2027"],
        "chart_comments": {k: "" for k in SCHEMA["properties"]["chart_comments"]["required"]},
        "generated_by": "rule-based",
    }


def generate(kpis, ranking, sensitivity, case, verdict: dict) -> dict:
    load_dotenv(config.ROOT / ".env")
    fallback = _rule_based(ranking, case, verdict)
    if not (os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_AUTH_TOKEN")):
        summary = fallback
    else:
        summary = _call_claude(_payload(kpis, ranking, sensitivity, case, verdict)) or fallback
    # The decision belongs to the rule, not to the model: enforce it
    summary["recommendation"], summary["target_country"] = verdict["recommendation"], verdict["target_name"]
    OUTPUT.write_text(json.dumps(summary, indent=2, ensure_ascii=False))
    print(f"  ai summary: {summary['recommendation']} - {summary['target_country']} ({summary['generated_by']})")
    return summary


def _call_claude(data: str) -> dict | None:
    import anthropic

    client = anthropic.Anthropic()
    try:
        response = client.beta.messages.create(
            model=config.CLAUDE_MODEL,
            max_tokens=16000,
            system=SYSTEM,
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            output_config={"effort": "high", "format": {"type": "json_schema", "schema": SCHEMA}},
            messages=[{"role": "user", "content": "Write the Comex summary from this data.\n\n" + data}],
        )
    except anthropic.AuthenticationError:
        print("  ai summary: invalid API key, using the rule-based summary")
        return None
    except anthropic.RateLimitError:
        print("  ai summary: rate limited, using the rule-based summary")
        return None
    except anthropic.APIStatusError as e:
        print(f"  ai summary: API error {e.status_code}, using the rule-based summary")
        return None
    except anthropic.APIConnectionError:
        print("  ai summary: no network, using the rule-based summary")
        return None

    if response.stop_reason == "refusal":
        print("  ai summary: request declined, using the rule-based summary")
        return None
    text = "".join(block.text for block in response.content if block.type == "text")
    summary = json.loads(text)
    summary["generated_by"] = response.model
    return summary
