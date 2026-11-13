"""Turn the KPIs into one score per candidate country, then test how robust the ranking is."""

import pandas as pd

from beauty_expansion import config

# Alternative weightings for the sensitivity test: if the winner changes with the weights,
# the Comex must know it.
SCENARIOS = {
    "Base case (README weights)": config.KPI_WEIGHTS,
    "Market first": {**{k: 0.04 for k in config.KPI_WEIGHTS},
                     "market_cagr": 0.25, "spend_per_capita_eur": 0.20, "market_size_meur": 0.19},
    "Margin first": {**{k: 0.04 for k in config.KPI_WEIGHTS},
                     "gross_margin_post_tax": 0.40, "prime_rent_eur_m2": 0.24},
    "Low risk / operations": {**{k: 0.04 for k in config.KPI_WEIGHTS},
                              "hub_distance_km": 0.20, "trade_friction": 0.20, "catalogue_eligible_pct": 0.24},
    "Equal weights": {k: 1 / len(config.KPI_WEIGHTS) for k in config.KPI_WEIGHTS},
    # Market axis measured on fragrance (customs data) instead of total personal care; see config.py
    "Fragrance focus": config.FRAGRANCE_FOCUS_WEIGHTS,
}


def normalise(countries: pd.DataFrame, extra: tuple = ()) -> pd.DataFrame:
    """Min-max scale each KPI to 0-100 across candidates; 100 = best (direction-aware).

    `extra` adds KPIs that are not in the base score (the fragrance KPIs of a sensitivity scenario).
    """
    direction_of = {**config.KPI_DIRECTION, **config.FRAGRANCE_KPI_DIRECTION}
    kpi_list = list(config.KPI_WEIGHTS) + [k for k in extra if k not in config.KPI_WEIGHTS]
    cand = countries.loc[list(config.CANDIDATES), kpi_list]
    scores = pd.DataFrame(index=cand.index)
    for kpi in kpi_list:
        direction = direction_of[kpi]
        col = cand[kpi]
        span = col.max() - col.min()
        # Differences under 2 % of the mean are noise: score everyone 50 instead of stretching to 0-100
        if span == 0 or span < 0.02 * abs(col.mean()):
            scaled = pd.Series(50.0, index=col.index)
        else:
            scaled = (col - col.min()) / span * 100
        scores[kpi] = scaled if direction > 0 else 100 - scaled
    return scores


def rank(countries: pd.DataFrame, weights: dict | None = None) -> pd.DataFrame:
    weights = weights or config.KPI_WEIGHTS
    total = sum(weights.values())
    scores = normalise(countries, extra=tuple(weights))
    result = pd.DataFrame({"total_score": sum(scores[k] * w for k, w in weights.items()) / total})
    for axis, kpis in _axes().items():
        w = sum(weights[k] for k in kpis)
        # In "Fragrance focus" the Market axis is carried by fragrance KPIs: no weight left, so no axis score
        result[axis] = sum(scores[k] * weights[k] for k in kpis) / w if w else float("nan")
    result["country"] = result.index.map(config.CANDIDATES)
    return result.sort_values("total_score", ascending=False)


def _axes() -> dict:
    from beauty_expansion.analysis.kpis import AXIS
    axes = {}
    for kpi in config.KPI_WEIGHTS:
        axes.setdefault(AXIS[kpi], []).append(kpi)
    return axes


def sensitivity(countries: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for name, weights in SCENARIOS.items():
        r = rank(countries, weights)
        rows.append({"scenario": name, "winner": r.index[0], "runner_up": r.index[1],
                     "winner_score": round(r["total_score"].iloc[0], 1),
                     "gap_to_runner_up": round(r["total_score"].iloc[0] - r["total_score"].iloc[1], 1)})
    return pd.DataFrame(rows)


def scores_long(countries: pd.DataFrame) -> pd.DataFrame:
    s = normalise(countries).reset_index(names="country_code").melt(
        id_vars="country_code", var_name="kpi", value_name="score_0_100")
    s["weight"] = s["kpi"].map(config.KPI_WEIGHTS)
    return s
