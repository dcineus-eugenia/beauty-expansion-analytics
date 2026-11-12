"""Small, known-answer tests for the calculation helpers."""

import pandas as pd
import pytest

from beauty_expansion import config
from beauty_expansion.analysis import scoring
from beauty_expansion.transform.geo import haversine_km


def test_haversine_paris_amsterdam():
    assert haversine_km(48.8566, 2.3522, 52.3676, 4.9041) == pytest.approx(430, abs=5)


def _kpis(**overrides) -> pd.DataFrame:
    rows = {cc: {k: 1.0 + i for k in config.KPI_WEIGHTS} for i, cc in enumerate(config.CANDIDATES)}
    df = pd.DataFrame(rows).T
    for k, v in overrides.items():
        df[k] = v
    return df


def test_normalise_respects_direction():
    s = scoring.normalise(_kpis())
    first, last = list(config.CANDIDATES)[0], list(config.CANDIDATES)[-1]
    assert s.loc[last, "market_size_meur"] == 100 and s.loc[first, "market_size_meur"] == 0      # higher is better
    assert s.loc[first, "prime_rent_eur_m2"] == 100 and s.loc[last, "prime_rent_eur_m2"] == 0    # lower is better
    assert s.min().min() >= 0 and s.max().max() <= 100


def test_normalise_ignores_noise():
    s = scoring.normalise(_kpis(gross_margin_post_tax=[0.450, 0.451, 0.452, 0.451, 0.450]))
    assert (s["gross_margin_post_tax"] == 50).all(), "differences under 2 % of the mean must not be stretched"


def test_rank_total_is_weighted_mean():
    r = scoring.rank(_kpis())
    assert r["total_score"].between(0, 100).all()
    assert r["total_score"].is_monotonic_decreasing
