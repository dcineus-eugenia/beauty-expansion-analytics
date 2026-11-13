"""Fragrance market size from customs data (issue #2).

Product: HS 3303 "Perfumes and toilet waters" (eau de parfum, eau de toilette, cologne).

Sources
-------
- EU countries: Eurostat Comext, dataset DS-045409 (EU trade since 1988 by HS2-4-6), partner = WORLD.
  API docs: https://wikis.ec.europa.eu/display/EUROSTATHELP/API+-+Getting+started+with+statistics+API
- Norway is not in Comext: Statistics Norway (SSB) table 08801, HS 3303 = the sum of its 8-digit
  national codes 33030010 (2025-), 33030011 + 33030012 (until 2024) and 33030090. Values are in NOK,
  converted to EUR with the Eurostat annual average rate (ert_bil_eur_a).
Every answer is cached in data/raw/comext/, so re-runs are fast and work offline.

Method: apparent consumption ~ imports - exports
-----------------------------------------------
- The full formula is production + imports - exports. We tested PRODCOM (DS-059367, codes
  20421150 + 20421170) on 2026-11-12: candidates produce almost no fragrance (FI 0, AT 0 for toilet
  waters; NL and IE confidential), so imports - exports is a fair proxy for them.
- France is a large net exporter (2025: exports EUR 8.1bn vs imports EUR 0.8bn). Even with production,
  PRODCOM gives -EUR 2.9bn, because production is valued at factory price and exports at border
  price, brand value included. So a trade balance that is <= 0 is not a consumption measure: we set it
  to missing (NaN) instead of showing a negative market.
- The Netherlands re-exports a lot through Rotterdam and its European distribution centres. Raw
  imports overstate its market (2024: EUR 1.6bn imported, EUR 1.2bn re-exported). imports - exports
  removes most of this effect, but some of the remaining flow may still be transit, not consumption.
- Values are customs values (imports CIF, exports FOB), not retail prices: they compare countries
  with each other, they are not the retail market size.
"""

import json
from datetime import date

import pandas as pd
import requests

from beauty_expansion import config

COMEXT_URL = "https://ec.europa.eu/eurostat/api/comext/dissemination/statistics/1.0/data/DS-045409"
SSB_URL = "https://data.ssb.no/api/v0/en/table/08801"
FX_URL = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/ert_bil_eur_a"
CACHE_DIR = config.RAW / "comext"

HS_CODE = "3303"
SSB_CODES = ["33030010_2025", "33030011_1988", "33030012_1988", "33030090_1988"]
FLOWS = {"1": "imports_eur", "2": "exports_eur"}      # Comext and SSB use the same codes
SINCE = 2019
SOURCE_COMEXT = "Eurostat Comext DS-045409, HS 3303, partner WORLD"
SOURCE_SSB = "Statistics Norway table 08801, HS 3303 (NOK converted at Eurostat ert_bil_eur_a annual average)"
COLUMNS = ["country_code", "year", "imports_eur", "exports_eur", "apparent_consumption_eur", "per_capita_eur", "source"]


def _get_json(url: str, cache_name: str, *, params=None, body=None, refresh: bool = False) -> dict:
    """GET (or POST when `body` is given) a JSON answer, cached in data/raw/comext/."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache = CACHE_DIR / f"{cache_name}.json"
    if cache.exists() and not refresh:
        return json.loads(cache.read_text(encoding="utf-8"))
    if body is None:
        response = requests.get(url, params=params, timeout=180)
    else:
        response = requests.post(url, json=body, timeout=180)
    response.raise_for_status()
    data = response.json()
    if "error" in data:
        raise RuntimeError(f"API error for {url}: {data['error']}")
    cache.write_text(json.dumps(data), encoding="utf-8")
    return data


def jsonstat_to_long(data: dict) -> pd.DataFrame:
    """Flatten any JSON-stat 2.0 cube into one row per cell: one column per dimension + `value`.

    The cube is stored as one flat list; the position of a cell is read like a number written
    with one "digit" per dimension, the last dimension changing fastest.
    """
    dims, sizes = data["id"], data["size"]
    code_at = {d: {pos: code for code, pos in data["dimension"][d]["category"]["index"].items()} for d in dims}
    values = data["value"]
    cells = values.items() if isinstance(values, dict) else enumerate(values)   # sparse dict or dense list
    rows = []
    for flat, value in cells:
        if value is None:
            continue
        flat, row = int(flat), {}
        for d, n in zip(reversed(dims), reversed(sizes)):
            row[d] = code_at[d][flat % n]
            flat //= n
        row["value"] = float(value)
        rows.append(row)
    return pd.DataFrame(rows, columns=[*dims, "value"])


def _last_complete_year() -> int:
    return date.today().year - 1


def comext_trade(countries: list[str], refresh: bool = False) -> pd.DataFrame:
    """Imports and exports of HS 3303 in EUR for EU countries: country_code, year, imports_eur, exports_eur."""
    frames = []
    for cc in countries:
        params = [("reporter", cc), ("partner", "WORLD"), ("product", HS_CODE), ("flow", "1"), ("flow", "2"),
                  ("indicators", "VALUE_IN_EUROS"), ("freq", "A"), ("sinceTimePeriod", str(SINCE))]
        frames.append(jsonstat_to_long(_get_json(COMEXT_URL, f"comext_{HS_CODE}_{cc}_{SINCE}", params=params,
                                                 refresh=refresh)))
    df = pd.concat(frames, ignore_index=True).rename(columns={"reporter": "country_code", "time": "year"})
    df["year"] = df["year"].astype(int)
    wide = df.pivot_table(index=["country_code", "year"], columns="flow", values="value", aggfunc="sum")
    wide = wide.rename(columns=FLOWS).reset_index()
    wide.columns.name = None
    wide["source"] = SOURCE_COMEXT
    return wide


def eur_nok_rate(refresh: bool = False) -> pd.Series:
    """Annual average NOK per 1 EUR (Eurostat ert_bil_eur_a), indexed by year."""
    params = [("currency", "NOK"), ("statinfo", "AVG"), ("unit", "NAC"), ("sinceTimePeriod", str(SINCE))]
    fx = jsonstat_to_long(_get_json(FX_URL, f"fx_eur_nok_{SINCE}", params=params, refresh=refresh))
    return fx.assign(year=fx["time"].astype(int)).set_index("year")["value"]


def norway_trade(refresh: bool = False) -> pd.DataFrame:
    """Imports and exports of HS 3303 for Norway (SSB 08801), summed over all partner countries, in EUR."""
    body = {
        "query": [
            {"code": "Varekoder", "selection": {"filter": "item", "values": SSB_CODES}},
            {"code": "ImpEks", "selection": {"filter": "item", "values": list(FLOWS)}},
            {"code": "Land", "selection": {"filter": "all", "values": ["*"]}},   # every partner country
            {"code": "ContentsCode", "selection": {"filter": "item", "values": ["Verdi"]}},   # value in NOK
            {"code": "Tid", "selection": {"filter": "all", "values": ["*"]}},
        ],
        "response": {"format": "json-stat2"},
    }
    df = jsonstat_to_long(_get_json(SSB_URL, f"ssb_08801_{HS_CODE}", body=body, refresh=refresh))
    df["year"] = df["Tid"].astype(int)
    df = df[df["year"] >= SINCE]
    nok = df.groupby(["year", "ImpEks"])["value"].sum().unstack("ImpEks").rename(columns=FLOWS)
    eur = nok.div(eur_nok_rate(refresh), axis=0)           # NOK / (NOK per EUR) = EUR
    eur = eur.reset_index().assign(country_code="NO", source=SOURCE_SSB)
    eur.columns.name = None
    return eur


def extract_all(countries: list[str], refresh: bool = False) -> pd.DataFrame:
    """Imports and exports of HS 3303 for every country, complete years only."""
    eu = [c for c in countries if c != "NO"]
    frames = [comext_trade(eu, refresh)]
    if "NO" in countries:
        frames.append(norway_trade(refresh))
    trade = pd.concat(frames, ignore_index=True)
    trade = trade[trade["year"] <= _last_complete_year()]
    print(f"  comext HS {HS_CODE}: {trade['country_code'].nunique()} countries, "
          f"{trade['year'].min()}-{trade['year'].max()}, {len(trade)} rows")
    return trade.sort_values(["country_code", "year"]).reset_index(drop=True)


def fragrance_market(trade: pd.DataFrame, macro: pd.DataFrame) -> pd.DataFrame:
    """Add apparent consumption and per-capita values.

    `macro` is the long Eurostat table from eurostat.extract_all() (columns indicator, geo, year, value):
    its `population` rows give the denominator. When the latest year has no population yet, the last
    known year is used.
    """
    pop = macro[macro["indicator"] == "population"].rename(columns={"geo": "country_code", "value": "population"})
    out = trade.merge(pop[["country_code", "year", "population"]], on=["country_code", "year"], how="left")
    out["population"] = out.groupby("country_code")["population"].ffill()

    balance = out["imports_eur"] - out["exports_eur"]
    # A net exporter (balance <= 0) has a real market, but trade data can't measure it: leave it missing.
    out["apparent_consumption_eur"] = balance.where(balance > 0)
    out["per_capita_eur"] = out["apparent_consumption_eur"] / out["population"]
    return out[COLUMNS]


def cagr(market: pd.DataFrame, column: str = "apparent_consumption_eur") -> pd.Series:
    """Compound annual growth rate from the first to the last year, per country (NaN if a bound is missing)."""
    def one(g: pd.DataFrame) -> float:
        g = g.dropna(subset=[column]).sort_values("year")
        if len(g) < 2:
            return float("nan")
        first, last = g.iloc[0], g.iloc[-1]
        return (last[column] / first[column]) ** (1 / (last["year"] - first["year"])) - 1
    return market.groupby("country_code")[[column, "year"]].apply(one).rename(f"{column}_cagr")


def summary(market: pd.DataFrame) -> pd.DataFrame:
    """Latest year per country: market (M EUR), per capita (EUR) and CAGR since the first year (%)."""
    latest = market.sort_values("year").groupby("country_code").tail(1).set_index("country_code")
    out = pd.DataFrame({
        "year": latest["year"],
        "market_meur": latest["apparent_consumption_eur"] / 1e6,
        "per_capita_eur": latest["per_capita_eur"],
        "cagr_pct": cagr(market) * 100,
    })
    return out.sort_values("per_capita_eur", ascending=False)


if __name__ == "__main__":
    # Standalone run: python -m beauty_expansion.extract.comext
    from beauty_expansion.extract import eurostat

    countries = list(config.COUNTRIES)
    trade = extract_all(countries)
    population = eurostat.to_long(eurostat.fetch(*eurostat.SERIES["population"], countries))
    population["indicator"] = "population"
    market = fragrance_market(trade, population)
    config.PROCESSED.mkdir(parents=True, exist_ok=True)
    market.to_csv(config.PROCESSED / "fragrance_market.csv", index=False)

    view = market.assign(imports_meur=market["imports_eur"] / 1e6, exports_meur=market["exports_eur"] / 1e6,
                         apparent_meur=market["apparent_consumption_eur"] / 1e6)
    print(view[["country_code", "year", "imports_meur", "exports_meur", "apparent_meur", "per_capita_eur"]]
          .round(1).to_string(index=False))
    print("\nLatest year (NaN = net exporter, not measurable with trade data):")
    print(summary(market).round(1).to_string())
