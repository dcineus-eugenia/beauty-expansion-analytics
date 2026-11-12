"""Hand-collected files in data/manual/: every country covered, every figure sourced."""

import pandas as pd
import pytest

from beauty_expansion import config

FACTS = pd.read_csv(config.MANUAL / "country_facts.csv")
HUBS = pd.read_csv(config.MANUAL / "logistics_hubs.csv")
PRESENCE = pd.read_csv(config.MANUAL / "sephora_presence.csv")


def test_country_facts_cover_every_country_once():
    assert sorted(FACTS["country_code"]) == sorted(config.COUNTRIES)


@pytest.mark.parametrize("column, low, high", [
    ("vat_standard_rate", 0.0, 0.3),
    ("corporate_tax_rate", 0.0, 0.5),
    ("customs_duty_cosmetics", 0.0, 0.2),
    ("prime_rent_eur_m2_year", 100, 50_000),
])
def test_country_facts_ranges(column, low, high):
    assert FACTS[column].between(low, high).all(), f"{column} outside [{low}, {high}]: rates are fractions"


@pytest.mark.parametrize("frame, columns", [
    (FACTS, ["source_vat", "source_corporate_tax", "source_rent"]),
    (HUBS, ["source"]),
    (PRESENCE, ["evidence"]),
])
def test_every_figure_has_a_source(frame, columns):
    for col in columns:
        assert frame[col].astype(str).str.startswith("http").all(), f"{col}: every row needs a source URL"


def test_hubs_are_in_europe_with_a_customs_flag():
    lat_min, lat_max, lon_min, lon_max = config.EUROPE_BBOX
    assert HUBS["lat"].between(lat_min, lat_max).all() and HUBS["lon"].between(lon_min, lon_max).all()
    assert HUBS["in_eu_customs_union"].isin([True, False]).all()
    assert HUBS["in_eu_customs_union"].any(), "at least one EU hub is needed"


def test_candidates_have_no_sephora_store():
    rows = PRESENCE.set_index("country_code").reindex(list(config.CANDIDATES))
    assert rows["sephora_physical_stores"].eq("no").all(), "a candidate is marked as already having Sephora"
