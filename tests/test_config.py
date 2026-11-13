"""Assumptions in config.py stay consistent with each other and with the data contracts."""

import pytest

from beauty_expansion import config, contracts
from beauty_expansion.analysis import kpis, scoring


def test_weights_sum_to_one():
    assert sum(config.KPI_WEIGHTS.values()) == pytest.approx(1.0)


def test_every_weighted_kpi_has_a_direction_an_axis_and_a_contract():
    kpi_columns = contracts.CONTRACTS["kpis_by_country.csv"].names
    assert set(config.KPI_WEIGHTS) == set(config.KPI_DIRECTION)
    for kpi in config.KPI_WEIGHTS:
        assert config.KPI_DIRECTION[kpi] in (1, -1)
        assert kpi in kpis.AXIS, f"{kpi} has no axis in analysis/kpis.py"
        assert kpi in kpi_columns, f"{kpi} is not in the kpis_by_country.csv contract"


@pytest.mark.parametrize("name", scoring.SCENARIOS)
def test_scenarios_use_known_kpis(name):
    weights = scoring.SCENARIOS[name]
    # every scenario weights the base KPIs (some at 0) and may add the fragrance KPIs
    assert set(config.KPI_WEIGHTS) <= set(weights) <= set(config.KPI_WEIGHTS) | set(config.FRAGRANCE_KPI_DIRECTION)
    assert all(w >= 0 for w in weights.values())


def test_countries():
    assert config.BASELINE not in config.CANDIDATES
    assert all(len(cc) == 2 and cc.isupper() for cc in config.COUNTRIES)


def test_store_plan():
    years = sorted(config.PLAN_STORES)
    assert years == list(range(years[0], years[-1] + 1)), "plan years must be consecutive"
    assert len(config.RAMP_UP) >= 1 and all(0 < r <= 1 for r in config.RAMP_UP)
