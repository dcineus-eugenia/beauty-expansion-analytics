"""Tests for the fragrance competition step (issue #4). No network: synthetic data only.

Run from the project root: python -m pytest -q
"""

import pandas as pd
import pytest

from beauty_expansion import config
from beauty_expansion.extract import internal, osm
from beauty_expansion.transform import fragrance_competition as fc

PERF_COLS = ["osm_id", "country_code", "name", "chain", "segment", "lat", "lon"]
STORE_COLS = ["osm_id", "country_code", "brand", "segment", "city", "lat", "lon"]


def shop(osm_id, cc, chain, lat=52.0, lon=5.0):
    return {"osm_id": osm_id, "country_code": cc, "name": chain, "chain": chain,
            "segment": "perfumery", "lat": lat, "lon": lon}


def store(osm_id, cc, brand, lat=52.0, lon=5.0):
    return {"osm_id": osm_id, "country_code": cc, "brand": brand, "segment": "selective",
            "city": None, "lat": lat, "lon": lon}


@pytest.fixture
def canonical():
    return {b.lower(): b for b in config.SELECTIVE_BRANDS + config.DRUGSTORE_BRANDS + config.PERFUMERY_CHAINS}


# ---------------------------------------------------------------- chain detection
@pytest.mark.parametrize("tags, expected", [
    ({"brand": "ICI Paris XL"}, "ICI PARIS XL"),            # known chain, other spelling
    ({"name": "douglas"}, "Douglas"),                       # no brand tag, matched by name
    ({"name": "The Perfume shop"}, "The Perfume Shop"),     # Ireland: no brand tag
    ({"name": "Parfumerie Dupont"}, "independent"),
    ({"brand": "Pour Vous"}, "Pour Vous"),                  # unknown brand kept, combine() decides
])
def test_chain(tags, expected, canonical):
    assert osm._chain(tags, canonical) == expected


# ---------------------------------------------------------------- combine
def test_combine_adds_chain_stores_without_double_counting():
    perf = pd.DataFrame([shop("n/1", "NL", "Douglas"), shop("n/2", "FI", "independent")], columns=PERF_COLS)
    stores = pd.DataFrame([
        store("n/1", "NL", "Douglas"),   # same OSM object as a shop=perfumery row
        store("w/9", "FI", "KICKS"),     # chain tagged shop=cosmetics: must be added
        store("w/8", "FI", "Lush"),      # selective but not a perfumery chain: must be ignored
    ], columns=STORE_COLS)
    shops = fc.combine(perf, stores)
    assert sorted(shops["osm_id"]) == ["n/1", "n/2", "w/9"]


def test_combine_unknown_brand_seen_once_is_independent():
    perf = pd.DataFrame([
        shop("n/1", "NL", "JANZEN;Il Bucato di Adele"),   # brands carried by an independent
        shop("n/2", "NL", "Pour Vous"), shop("n/3", "NL", "Pour Vous"),   # small real chain
    ], columns=PERF_COLS)
    chains = fc.combine(perf, pd.DataFrame(columns=STORE_COLS)).set_index("osm_id")["chain"]
    assert chains["n/1"] == "independent"
    assert chains["n/2"] == "Pour Vous"


# ---------------------------------------------------------------- competition
def test_competition_counts_density_top3_and_leader():
    chains = ["Douglas"] * 4 + ["ICI PARIS XL"] * 3 + ["Marionnaud", "Rituals", "independent"]
    perf = pd.DataFrame([shop(f"n/{cc}{i}", cc, c) for cc in config.COUNTRIES for i, c in enumerate(chains)],
                        columns=PERF_COLS)
    cities = pd.DataFrame([{"country_code": cc, "city": "C", "population": 100_000, "lat": 52.0, "lon": 5.0}
                           for cc in config.COUNTRIES])
    macro = pd.DataFrame([{"indicator": "population", "geo": cc, "year": y, "value": v}
                          for cc in config.COUNTRIES for y, v in ((2023, 9e6), (2024, 1e6))])
    out = fc.competition(perf, cities, fc.latest_population(macro)).set_index("country_code")
    assert (out["perfumeries"] == 10).all()
    assert (out["perfumeries_per_100k"] == 1.0).all()            # latest year (2024) used
    assert (out["top3_share"] == 0.8).all()                      # (4 + 3 + 1) / 10, independents in the base
    assert (out["leader"] == "Douglas").all()
    assert (out["perfumeries_per_100k_top5_cities"] == 10.0).all()
    assert out["small_sample"].all()                            # 10 shops < FRAGRANCE_MIN_SHOPS


def test_competition_country_without_shops():
    cities = pd.DataFrame([{"country_code": cc, "city": "C", "population": 100_000, "lat": 52.0, "lon": 5.0}
                           for cc in config.COUNTRIES])
    population = pd.Series({cc: 1e6 for cc in config.COUNTRIES})
    out = fc.competition(pd.DataFrame(columns=PERF_COLS), cities, population)
    assert (out["perfumeries"] == 0).all() and out["leader"].isna().all()


# ---------------------------------------------------------------- assortment (simulated catalogue)
def test_exclusion_reason_matches_eligibility():
    cat = internal.catalogue()
    for cc in internal.EXCLUSIVE_DISTRIBUTION_RATE:
        assert (cat[f"exclusion_{cc}"].isna() == cat[f"eligible_{cc}"]).all(), cc


def test_assortment_reasons_add_up_to_100():
    eligible_pct, reasons = fc.assortment(internal.catalogue())
    assert eligible_pct["FR"] == 100
    totals = reasons.groupby("country_code")["pct_of_fragrance_skus"].sum()
    assert ((totals - 100).abs() < 1e-9).all()
    assert (reasons["source"] == fc.CATALOGUE_SOURCE).all()


# ---------------------------------------------------------------- skipped step
def test_clear_outputs_removes_stale_files(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "PROCESSED", tmp_path)
    for name in fc.OUTPUTS:
        (tmp_path / name).write_text("old")
    fc.clear_outputs()
    fc.clear_outputs()     # nothing left to remove: must not fail
    assert not any((tmp_path / name).exists() for name in fc.OUTPUTS)


def test_small_sample_flag_threshold(monkeypatch):
    monkeypatch.setattr(config, "FRAGRANCE_MIN_SHOPS", 10)
    perf = pd.DataFrame([shop(f"n/NL{i}", "NL", "Douglas") for i in range(10)]
                        + [shop(f"n/IE{i}", "IE", "independent") for i in range(9)], columns=PERF_COLS)
    cities = pd.DataFrame([{"country_code": cc, "city": "C", "population": 100_000, "lat": 52.0, "lon": 5.0}
                           for cc in config.COUNTRIES])
    flags = fc.competition(perf, cities, pd.Series({cc: 1e6 for cc in config.COUNTRIES})).set_index("country_code")["small_sample"]
    assert not flags["NL"] and flags["IE"]                       # 10 shops: enough; 9: small sample
