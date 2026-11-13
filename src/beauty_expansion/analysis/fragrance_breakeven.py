"""Rough estimate: by how much could the Dutch fragrance market be overstated before Ireland overtakes?

The Dutch customs figure is an upper bound (Rotterdam transit). This script lowers the Dutch fragrance market size and
per-head figures by the same percentage (growth unchanged), re-runs the "Fragrance focus" scoring with scoring.rank and
looks for the point where both countries get the same total score (bisection).

    python -m beauty_expansion.analysis.fragrance_breakeven      # needs the pipeline to have run once
"""

import pandas as pd

from beauty_expansion import config
from beauty_expansion.analysis import scoring

LEVEL_KPIS = ["fragrance_market_meur", "fragrance_per_capita_eur"]    # scaled together; fragrance_cagr is kept


def totals(kpis: pd.DataFrame, factor: float, country: str = "NL") -> pd.Series:
    """Total scores of the Fragrance focus scenario when `country`'s fragrance level is multiplied by `factor`."""
    scaled = kpis.copy()
    scaled.loc[country, LEVEL_KPIS] = scaled.loc[country, LEVEL_KPIS] * factor
    return scoring.rank(scaled, config.FRAGRANCE_FOCUS_WEIGHTS)["total_score"]


def breakeven(kpis: pd.DataFrame, country: str = "NL", rival: str = "IE") -> float:
    """Factor (0-1) where `country` and `rival` have the same score; nan if `country` doesn't lead at factor 1."""
    def gap(f):
        t = totals(kpis, f, country)
        return t[country] - t[rival]

    lo, hi = 0.01, 1.0
    if gap(hi) <= 0 or gap(lo) >= 0:
        return float("nan")
    for _ in range(50):
        mid = (lo + hi) / 2
        lo, hi = (lo, mid) if gap(mid) > 0 else (mid, hi)
    return hi


if __name__ == "__main__":
    k = pd.read_csv(config.PROCESSED / "kpis_by_country.csv", index_col=0)
    f = breakeven(k)
    if pd.isna(f):
        raise SystemExit("NL does not lead the Fragrance focus scenario (or never loses first place): nothing to estimate.")
    table = pd.DataFrame({"Start (customs figure)": totals(k, 1.0), "Break-even": totals(k, f)}).loc[["NL", "IE"]]
    print(table.round(2).to_string())
    nl = k.loc["NL"]
    print(f"\nBreak-even: Dutch fragrance level {(1 - f) * 100:.1f} % lower "
          f"({nl['fragrance_market_meur'] * f:.0f} M€ instead of {nl['fragrance_market_meur']:.0f} M€, "
          f"{nl['fragrance_per_capita_eur'] * f:.1f} instead of {nl['fragrance_per_capita_eur']:.1f} €/inhabitant). "
          "Rough estimate: growth is kept unchanged.")
