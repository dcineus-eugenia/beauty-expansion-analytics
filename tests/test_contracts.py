"""The data contracts are consistent, enforced, and documented."""

import pandas as pd
import pytest

from beauty_expansion import config, contracts

FRACTION_SUFFIXES = ("_rate", "_share", "_margin", "_cagr")


@pytest.mark.parametrize("contract", contracts.CONTRACTS.values(), ids=lambda c: c.file)
def test_column_names_say_their_unit(contract):
    for col in contract.columns:
        if col.name.endswith("_eur") or col.name.endswith("_meur"):
            assert col.unit in ("EUR", "M EUR"), f"{contract.file}.{col.name}: euro column needs an EUR unit"
            assert (col.unit == "M EUR") == col.name.endswith("_meur"), f"{contract.file}.{col.name}: _meur = millions"
        if col.name.endswith("_pct"):
            assert (col.min, col.max) == (0, 100), f"{contract.file}.{col.name}: _pct columns are 0-100"
        if col.name.endswith(FRACTION_SUFFIXES):
            assert col.max is not None and col.max <= 1, f"{contract.file}.{col.name}: fractions are 0-1"
        if col.name.endswith("_km"):
            assert col.unit == "km"


@pytest.mark.parametrize("contract", contracts.CONTRACTS.values(), ids=lambda c: c.file)
def test_keys_are_columns(contract):
    assert set(contract.key) <= set(contract.names)
    assert len(contract.names) == len(set(contract.names)), "duplicate column in contract"


def _valid_competition() -> pd.DataFrame:
    return pd.DataFrame({
        "country_code": sorted(config.COUNTRIES),
        "perfumeries": [10, 20, 30, 40, 50, 60],
        "perfumeries_per_100k": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
        "top3_share": [0.5] * 6,
        "leader": ["Douglas"] * 6,
        "fragrance_skus_eligible_pct": [100, 90, 95, 98, 80, 60],
        "perfumeries_per_100k_top5_cities": [2.0] * 6,
        "independent_share": [0.3] * 6,
        "small_sample": [False] * 6,
        "fragrance_skus_source": ["simulated internal catalogue"] * 6,
    })


def test_valid_frame_passes():
    contracts.validate("fragrance_competition.csv", _valid_competition())


@pytest.mark.parametrize("breakage, message", [
    (lambda df: df.drop(columns="leader"), "missing columns"),
    (lambda df: df.assign(extra=1), "not in the contract"),
    (lambda df: df.assign(top3_share=37.0), "above 1"),                 # percent written as a fraction column
    (lambda df: df.assign(country_code=["FR", "NL", "AT", "IE", "FI", "Norway"]), "unexpected values"),
    (lambda df: df.assign(perfumeries=df["perfumeries"].astype(str)), "expected int"),
    (lambda df: pd.concat([df, df.head(1)]), "duplicate keys"),
    (lambda df: df.assign(fragrance_skus_source=[None] + ["simulated internal catalogue"] * 5), "empty values"),
])
def test_broken_frames_are_rejected(breakage, message):
    with pytest.raises(contracts.ContractError, match=message):
        contracts.validate("fragrance_competition.csv", breakage(_valid_competition()))


def test_unknown_file_is_rejected():
    with pytest.raises(contracts.ContractError, match="no contract"):
        contracts.validate("my_new_file.csv", pd.DataFrame({"a": [1]}))


def test_docs_match_contracts():
    doc = (config.ROOT / "docs" / "DATA_CONTRACTS.md").read_text()
    assert doc.strip() == contracts.to_markdown().strip(), (
        "docs/DATA_CONTRACTS.md is out of date: run "
        "`python -m beauty_expansion.contracts --markdown > docs/DATA_CONTRACTS.md`")


def test_pipeline_outputs_pass(has_outputs):
    errors = contracts.validate_outputs()
    assert not errors, "\n".join(errors)
