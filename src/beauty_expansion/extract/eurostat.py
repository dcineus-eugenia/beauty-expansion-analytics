"""Eurostat open-data API (JSON-stat 2.0).

Docs: https://wikis.ec.europa.eu/display/EUROSTATHELP/API+Statistics+-+data+query
Each call returns a cube; `to_long()` flattens it into a tidy table (geo, time, value).
Responses are cached in data/raw/eurostat/ so re-runs are fast and work offline.
"""

import json

import pandas as pd
import requests

from beauty_expansion import config

BASE_URL = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data"
CACHE_DIR = config.RAW / "eurostat"

# name -> (dataset code, filters). Every series the project uses, in one place.
SERIES = {
    "population": ("demo_pjan", {"sex": "T", "age": "TOTAL", "unit": "NR"}),
    "gdp_per_capita_pps": ("nama_10_pc", {"unit": "CP_PPS_EU27_2020_HAB", "na_item": "B1GQ"}),
    "personal_care_spend_meur": ("nama_10_cp18", {"unit": "CP_MEUR", "coicop18": "CP131"}),
    "personal_care_spend_eur_hab": ("nama_10_cp18", {"unit": "CP_EUR_HAB", "coicop18": "CP131"}),
    "personal_care_share_pct": ("nama_10_cp18", {"unit": "PC_TOT", "coicop18": "CP131"}),
    "hicp_personal_care": ("prc_hicp_aind", {"unit": "INX_A_AVG", "coicop": "CP1213"}),
    "price_level_index_misc": ("prc_ppp_ind_1", {"indic_ppp": "PLI_EU27_2020", "ppp_cat18": "A0112"}),
    "labour_cost_retail_eur_h": ("lc_lci_lev", {"lcstruct": "D1_D4_MD5", "nace_r2": "G", "unit": "EUR"}),
}


def fetch(dataset: str, filters: dict, geos: list[str], since: int = 2019, refresh: bool = False) -> dict:
    """Call the API (or read the cache) and return the raw JSON-stat dict."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    key = "_".join([dataset, *[f"{k}-{v}" for k, v in sorted(filters.items())], *sorted(geos), str(since)])
    cache = CACHE_DIR / f"{key}.json"
    if cache.exists() and not refresh:
        return json.loads(cache.read_text())

    params = [(k, v) for k, v in filters.items()] + [("geo", g) for g in geos]
    params.append(("sinceTimePeriod", str(since)))
    response = requests.get(f"{BASE_URL}/{dataset}", params=params, timeout=180)
    response.raise_for_status()
    data = response.json()
    if "error" in data:
        raise RuntimeError(f"Eurostat error for {dataset}: {data['error']}")
    cache.write_text(json.dumps(data))
    return data


def to_long(data: dict) -> pd.DataFrame:
    """Flatten a JSON-stat cube filtered down to geo x time into columns geo, time, value."""
    geo_index = data["dimension"]["geo"]["category"]["index"]
    time_index = data["dimension"]["time"]["category"]["index"]
    geo_by_pos = {pos: code for code, pos in geo_index.items()}
    time_by_pos = {pos: code for code, pos in time_index.items()}
    n_time = len(time_index)

    rows = []
    for flat_pos, value in data["value"].items():
        flat_pos = int(flat_pos)
        rows.append({
            "geo": geo_by_pos[flat_pos // n_time],
            "year": int(time_by_pos[flat_pos % n_time]),
            "value": float(value),
        })
    return pd.DataFrame(rows)


def extract_all(geos: list[str], refresh: bool = False) -> pd.DataFrame:
    """Return every series in SERIES as one long table: indicator, geo, year, value, dataset."""
    frames = []
    for name, (dataset, filters) in SERIES.items():
        df = to_long(fetch(dataset, filters, geos, refresh=refresh))
        df["indicator"] = name
        df["dataset"] = dataset
        frames.append(df)
        print(f"  eurostat {name:<30} {len(df):>4} rows ({dataset})")
    return pd.concat(frames, ignore_index=True)[["indicator", "geo", "year", "value", "dataset"]]
