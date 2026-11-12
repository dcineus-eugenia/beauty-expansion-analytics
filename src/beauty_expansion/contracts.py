"""Data contracts: the single definition of every shared data file.

A contract says, for one file: its grain (what one row is), its key, and for each column its type,
unit and allowed values. The pipeline refuses to write a file that breaks its contract, so a change
made by one teammate can't silently break another teammate's chart.

    python -m beauty_expansion.contracts               # check every file in data/processed/
    python -m beauty_expansion.contracts --markdown    # print docs/DATA_CONTRACTS.md

Naming rule (checked by tests/test_contracts.py), so units are readable from the column name:
    *_eur   euros              *_meur  millions of euros     *_km    kilometres
    *_pct   percent, 0-100     *_rate / *_share / *_margin / *_cagr   fraction, 0-1 (0.2 = 20 %)
    *_per_100k  per 100,000 inhabitants                       country_code  ISO 3166-1 alpha-2
To add or change a column: edit its contract here in the same pull request, then regenerate the docs.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field

import pandas as pd

from beauty_expansion import config

ALL = sorted(config.COUNTRIES)
CANDIDATES = sorted(config.CANDIDATES)
SCRAPED = ["AT", "FR", "IE", "NL"]  # countries with a LOOKFANTASTIC site
LAT_MIN, LAT_MAX, LON_MIN, LON_MAX = config.EUROPE_BBOX


@dataclass(frozen=True)
class Col:
    name: str
    dtype: str                      # "str" | "int" | "float" | "bool" | "id" (int or str)
    unit: str = ""
    description: str = ""
    nullable: bool = False
    min: float | None = None
    max: float | None = None
    allowed: tuple | None = None


@dataclass(frozen=True)
class Contract:
    file: str
    grain: str
    key: tuple[str, ...]
    columns: tuple[Col, ...]
    produced_by: str
    required: bool = True           # False = planned file (fragrance issues), checked once it exists
    countries: tuple[str, ...] = tuple(ALL)
    notes: str = ""

    @property
    def names(self) -> list[str]:
        return [c.name for c in self.columns]


def country(allowed=ALL) -> Col:
    return Col("country_code", "str", "ISO 3166-1", "country", allowed=tuple(allowed))


def eur(name, description, nullable=False, min=None) -> Col:
    return Col(name, "float", "EUR", description, nullable, min)


CONTRACTS: dict[str, Contract] = {c.file: c for c in [
    Contract(
        "kpis_by_country.csv", "one country", ("country_code",), produced_by="analysis/kpis.py",
        columns=(
            country(),
            Col("market_size_meur", "float", "M EUR", "household personal-care spending (Eurostat CP131)", min=0),
            Col("spend_per_capita_eur", "float", "EUR", "personal-care spending per inhabitant", min=0),
            Col("market_cagr", "float", "fraction", "growth of market size, 2019 to latest year", min=-0.5, max=0.5),
            Col("personal_care_share_pct", "float", "%", "personal care as a share of household spending", min=0, max=100),
            Col("sephora_fr_market_share", "float", "fraction", "Sephora revenue / market (France only)", True, 0, 1),
            Col("leader_store_share", "float", "fraction", "leading chain's share of selective stores", min=0, max=1),
            Col("leader_brand", "str", "", "leading selective chain by store count"),
            Col("relative_price_index", "float", "FR=100", "Eurostat price level index, personal care", min=20, max=500),
            Col("scraped_price_index", "float", "FR=100", "median online price vs France", True, 20, 500),
            Col("scraped_products", "float", "count", "products matched in every scraped country", True, 0),
            Col("price_passthrough", "float", "fraction", "share of the price level gap passed to prices", min=0, max=1),
            Col("effective_price_index", "float", "FR=100", "price index used in the margin", min=20, max=500),
            Col("vat_standard_rate", "float", "fraction", "standard VAT rate", min=0, max=0.3),
            Col("hub_distance_km", "float", "km", "mean road distance from selective stores to nearest EU hub", min=0, max=3000),
            Col("trade_friction", "float", "points", "customs + currency friction (0 = none)", min=0, max=10),
            Col("catalogue_eligible_pct", "float", "%", "share of French SKUs sellable in the country", min=0, max=100),
            Col("gross_margin_post_tax", "float", "fraction", "gross margin after VAT, logistics and customs", min=0, max=1),
            Col("catchment_density_per_100k", "float", "per 100k", "selective stores within 10 km of top-5 cities", min=0),
            Col("selective_stores_per_100k_national", "float", "per 100k", "selective stores per inhabitant, whole country", min=0),
            Col("prime_rent_eur_m2", "float", "EUR/m²/year", "prime high-street rent (Cushman & Wakefield)", min=0),
            Col("labour_cost_retail_eur_h", "float", "EUR/hour", "hourly labour cost, retail (Eurostat)", min=0),
            Col("corporate_tax_rate", "float", "fraction", "headline corporate income tax", min=0, max=0.5),
            Col("population", "float", "people", "population on 1 January (Eurostat)", min=0),
        )),
    Contract(
        "country_ranking.csv", "one candidate country", ("country_code",), produced_by="analysis/scoring.py",
        countries=tuple(CANDIDATES),
        columns=(
            country(CANDIDATES),
            Col("total_score", "float", "0-100", "weighted attractiveness score", min=0, max=100),
            Col("Market & potential", "float", "0-100", "axis score", min=0, max=100),
            Col("Price & margin", "float", "0-100", "axis score", min=0, max=100),
            Col("Network & footprint", "float", "0-100", "axis score", min=0, max=100),
            Col("Operations & logistics", "float", "0-100", "axis score", min=0, max=100),
            Col("Assortment", "float", "0-100", "axis score", min=0, max=100),
            Col("country", "str", "", "country name", allowed=tuple(config.CANDIDATES.values())),
        )),
    Contract(
        "sensitivity.csv", "one weighting scenario", ("scenario",), produced_by="analysis/scoring.py", countries=(),
        columns=(
            Col("scenario", "str", "", "weighting scenario name"),
            Col("winner", "str", "ISO 3166-1", "first country", allowed=tuple(CANDIDATES)),
            Col("runner_up", "str", "ISO 3166-1", "second country", allowed=tuple(CANDIDATES)),
            Col("winner_score", "float", "0-100", "winner's total score", min=0, max=100),
            Col("gap_to_runner_up", "float", "points", "winner minus runner-up", min=0, max=100),
        )),
    Contract(
        "business_case_summary.csv", "one candidate × scenario", ("country_code", "scenario"),
        produced_by="analysis/business_case.py", countries=tuple(CANDIDATES),
        columns=(
            country(CANDIDATES),
            Col("scenario", "str", "", "sales scenario", allowed=("pessimistic", "base", "optimistic")),
            Col("store_revenue_meur", "float", "M EUR", "revenue of one mature store", min=0),
            Col("store_ebitda_margin", "float", "fraction", "EBITDA / revenue of one mature store", min=-1, max=1),
            Col("payback_years", "float", "years", "store payback; empty = never within 10 years", True, 0, 10),
            Col("plan_revenue_2029_meur", "float", "M EUR", "network revenue in 2029", min=0),
            Col("plan_capex_meur", "float", "M EUR", "fit-out + opening costs + opening inventory", min=0),
            Col("plan_npv_meur", "float", "M EUR", "NPV of the 15-store plan at the WACC"),
            Col("demand_factor", "float", "ratio", "local demand vs France (after elasticity)", min=0, max=3),
            Col("assortment_factor", "float", "ratio", "share of the catalogue sellable", min=0, max=1),
            Col("competition_factor", "float", "ratio", "competition adjustment", min=0, max=3),
            Col("go", "bool", "", "passes all three decision checks"),
        )),
    Contract(
        "business_case_plan.csv", "one candidate × year (base scenario)", ("country_code", "year"),
        produced_by="analysis/business_case.py", countries=tuple(CANDIDATES),
        columns=(
            country(CANDIDATES),
            Col("year", "int", "year", "plan year", min=2027, max=2031),
            Col("stores_open", "int", "count", "stores open at year end", min=0, max=sum(config.PLAN_STORES.values())),
            eur("revenue_eur", "network revenue", min=0),
            eur("gross_margin_eur", "revenue minus cost of goods, VAT excluded"),
            eur("rent_eur", "rent", min=0),
            eur("staff_cost_eur", "staff cost", min=0),
            eur("other_costs_eur", "other operating costs + central costs", min=0),
            eur("ebitda_eur", "EBITDA"),
            eur("ebit_eur", "EBIT"),
            eur("capex_eur", "capital expenditure incl. opening inventory", min=0),
            eur("free_cash_flow_eur", "after-tax free cash flow"),
        )),
    Contract(
        "catchment_density.csv", "one city (top 5 per country)", ("country_code", "city"), produced_by="transform/geo.py",
        columns=(
            country(),
            Col("city", "str", "", "city name (OpenStreetMap)"),
            Col("population", "int", "people", "city population (OpenStreetMap)", min=0),
            Col("selective_stores_10km", "int", "count", "selective stores within 10 km", min=0),
            Col("stores_per_100k", "float", "per 100k", "selective stores per 100,000 city inhabitants", min=0),
        )),
    Contract(
        "stores.csv", "one competitor store (OpenStreetMap feature)", ("osm_id",), produced_by="extract/osm.py",
        notes="Continental Europe only: overseas territories are removed (config.EUROPE_BBOX).",
        columns=(
            Col("osm_id", "str", "", "OpenStreetMap type/id"),
            country(),
            Col("brand", "str", "", "chain", allowed=tuple(config.SELECTIVE_BRANDS + config.DRUGSTORE_BRANDS)),
            Col("segment", "str", "", "competitor type", allowed=("selective", "drugstore")),
            Col("city", "str", "", "addr:city tag", nullable=True),
            Col("lat", "float", "degrees", "latitude", min=LAT_MIN, max=LAT_MAX),
            Col("lon", "float", "degrees", "longitude", min=LON_MIN, max=LON_MAX),
            Col("km_to_nearest_hub", "float", "km", "road distance to nearest EU hub", min=0, max=3000),
            Col("nearest_hub", "str", "", "hub name (data/manual/logistics_hubs.csv)"),
        )),
    Contract(
        "prices.csv", "one product × country (online price)", ("product_id", "country_code"),
        produced_by="extract/prices.py", countries=tuple(SCRAPED),
        columns=(
            Col("product_id", "id", "", "LOOKFANTASTIC product id"),
            Col("sku", "id", "", "variant SKU"),
            Col("name", "str", "", "product name as shown on the country site"),
            Col("brand", "str", "", "brand slug"),
            Col("price_eur", "float", "EUR", "shelf price incl. VAT", min=0.01),
            Col("currency", "str", "", "currency", allowed=("EUR",)),
            country(SCRAPED),
            Col("category", "str", "", "category", allowed=("fragrance", "makeup", "skincare", "haircare", "bath_body")),
        )),
    Contract(
        "lvmh_selective_retailing.csv", "one year", ("year",), produced_by="extract/lvmh.py", countries=(),
        columns=(
            Col("year", "int", "year", "fiscal year", min=2015, max=2030),
            Col("revenue_meur", "float", "M EUR", "Selective Retailing revenue", min=0),
            Col("recurring_profit_meur", "float", "M EUR", "profit from recurring operations"),
            Col("source", "str", "", "LVMH publication URL"),
            Col("headcount", "float", "people", "employees (LVMH Excel)", True, 0),
            Col("operating_margin", "float", "fraction", "recurring profit / revenue", min=-1, max=1),
        )),
    Contract(
        "internal_stores_fr.csv", "one French store (SIMULATED)", ("store_id",), produced_by="extract/internal.py",
        countries=(), notes="Simulated data, calibrated on Sephora France totals. Always label it as simulated.",
        columns=(
            Col("store_id", "str", "", "simulated store id"),
            Col("region", "str", "", "French region"),
            Col("format", "str", "", "store format", allowed=("flagship", "city", "mall")),
            Col("size_m2", "float", "m²", "sales area", min=0),
            Col("opening_year", "int", "year", "opening year", min=1970, max=2030),
            eur("revenue_eur", "annual revenue", min=0),
            eur("cogs_eur", "cost of goods sold", min=0),
            eur("rent_eur", "annual rent", min=0),
            Col("staff_fte", "float", "FTE", "full-time equivalents", min=0),
            eur("staff_cost_eur", "staff cost", min=0),
            eur("other_opex_eur", "other operating costs", min=0),
            eur("store_ebitda_eur", "store EBITDA"),
        )),

    # ---- Fragrance deep-dive (GitHub issues #2-#5): planned files, checked as soon as they exist ----
    Contract(
        "fragrance_market.csv", "one country × year", ("country_code", "year"), required=False,
        produced_by="extract/comext.py (issue #2)",
        notes="Eurostat Comext HS 3303. Apparent consumption = imports - exports (corrects NL re-exports). "
              "Norway may be missing (not in Comext): leave it out rather than invent it.",
        columns=(
            country(),
            Col("year", "int", "year", "calendar year", min=2015, max=2030),
            eur("imports_eur", "imports of HS 3303 from the world", min=0),
            eur("exports_eur", "exports of HS 3303 to the world", min=0),
            eur("apparent_consumption_eur", "imports minus exports (can be negative for a re-export hub)"),
            eur("per_capita_eur", "apparent consumption per inhabitant"),
            Col("source", "str", "", "dataset id or URL"),
        )),
    Contract(
        "fragrance_prices.csv", "one fragrance product × country", ("country_code", "product_id"), required=False,
        produced_by="extract/prices.py (issue #3)", countries=tuple(SCRAPED),
        columns=(
            country(SCRAPED),
            Col("product_id", "id", "", "LOOKFANTASTIC product id"),
            Col("brand", "str", "", "brand slug"),
            Col("name", "str", "", "product name"),
            Col("volume_ml", "float", "ml", "bottle size parsed from the name", min=1, max=1000),
            Col("price_eur", "float", "EUR", "shelf price incl. VAT", min=0.01),
            Col("price_excl_vat_eur", "float", "EUR", "price / (1 + VAT rate)", min=0.01),
            Col("price_per_ml", "float", "EUR/ml", "price incl. VAT per ml", min=0.001, max=50),
            Col("index_vs_fr", "float", "FR=100", "price vs the same product in France", min=20, max=500),
        )),
    Contract(
        "fragrance_competition.csv", "one country", ("country_code",), required=False,
        produced_by="extract/osm.py + analysis (issue #4)",
        notes="fragrance_skus_eligible_pct comes from the SIMULATED catalogue.",
        columns=(
            country(),
            Col("perfumeries", "int", "count", "OpenStreetMap shop=perfumery + tracked perfumery chains", min=0),
            Col("perfumeries_per_100k", "float", "per 100k", "perfumeries per 100,000 inhabitants", min=0),
            Col("top3_share", "float", "fraction", "share of perfumeries held by the 3 largest chains", min=0, max=1),
            Col("leader", "str", "", "largest perfumery chain"),
            Col("fragrance_skus_eligible_pct", "float", "%", "share of French fragrance SKUs sellable (simulated)", min=0, max=100),
        )),
]}

DECISION_KEYS = {"target", "target_name", "recommendation", "selection_rule", "checks",
                 "base_npv_meur", "pessimistic_npv_meur", "payback_years"}


class ContractError(ValueError):
    pass


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------
def _dtype_ok(s: pd.Series, dtype: str) -> bool:
    s = s.dropna()
    if s.empty:
        return True
    if dtype == "str":
        return s.map(lambda v: isinstance(v, str)).all()
    if dtype == "bool":
        return pd.api.types.is_bool_dtype(s) or set(s.unique()) <= {True, False}
    if dtype == "int":
        return pd.api.types.is_numeric_dtype(s) and not pd.api.types.is_bool_dtype(s) and (s % 1 == 0).all()
    if dtype == "float":
        return pd.api.types.is_numeric_dtype(s) and not pd.api.types.is_bool_dtype(s)
    if dtype == "id":
        return pd.api.types.is_integer_dtype(s) or s.map(lambda v: isinstance(v, (str, int))).all()
    raise ValueError(f"unknown dtype {dtype!r}")


def check(contract: Contract, df: pd.DataFrame) -> list[str]:
    """Return every way `df` breaks `contract` (empty list = valid)."""
    errors = []
    missing = [c for c in contract.names if c not in df.columns]
    extra = [c for c in df.columns if c not in contract.names]
    if missing:
        errors.append(f"missing columns {missing}")
    if extra:
        errors.append(f"columns not in the contract {extra} (add them to contracts.py first)")
    if df.empty:
        errors.append("no rows")
    for col in contract.columns:
        if col.name not in df.columns:
            continue
        s = df[col.name]
        if not col.nullable and s.isna().any():
            errors.append(f"{col.name}: {int(s.isna().sum())} empty values")
        if not _dtype_ok(s, col.dtype):
            errors.append(f"{col.name}: expected {col.dtype}, got {s.dtype}")
            continue
        values = s.dropna()
        if col.allowed is not None:
            bad = sorted(set(values) - set(col.allowed), key=str)
            if bad:
                errors.append(f"{col.name}: unexpected values {bad[:5]}")
        if col.dtype in ("int", "float") and not values.empty:
            if col.min is not None and values.min() < col.min:
                errors.append(f"{col.name}: min {values.min():.4g} is below {col.min} {col.unit}")
            if col.max is not None and values.max() > col.max:
                errors.append(f"{col.name}: max {values.max():.4g} is above {col.max} {col.unit}")
    key = [k for k in contract.key if k in df.columns]
    if len(key) == len(contract.key) and df.duplicated(key).any():
        dupes = df[df.duplicated(key, keep=False)][key].drop_duplicates().head(3).to_dict("records")
        errors.append(f"duplicate keys {list(contract.key)}, e.g. {dupes}")
    if contract.countries and "country_code" in df.columns:
        absent = sorted(set(contract.countries) - set(df["country_code"]))
        if absent and contract.required:
            errors.append(f"countries missing: {absent}")
    return errors


def validate(file: str, df: pd.DataFrame) -> pd.DataFrame:
    """Raise ContractError if `df` breaks the contract of `file`; return df unchanged otherwise."""
    if file not in CONTRACTS:
        raise ContractError(f"{file}: no contract. Add one to src/beauty_expansion/contracts.py")
    errors = check(CONTRACTS[file], df)
    if errors:
        raise ContractError(f"{file} breaks its data contract:\n  - " + "\n  - ".join(errors))
    return df


def read(file: str, directory=None) -> pd.DataFrame:
    """Read a processed CSV with the key columns restored (the way the contracts describe it)."""
    df = pd.read_csv((directory or config.PROCESSED) / file)
    return df.rename(columns={"Unnamed: 0": "country_code"})


def cross_checks(frames: dict[str, pd.DataFrame], decision: dict | None) -> list[str]:
    """Coherence between files: the same countries, years and winner everywhere."""
    errors = []
    if "country_ranking.csv" in frames:
        ranking = frames["country_ranking.csv"].sort_values("total_score", ascending=False)
        top = ranking["country_code"].iloc[0]
        if "sensitivity.csv" in frames:
            base = frames["sensitivity.csv"].iloc[0]
            if base["winner"] != top:
                errors.append(f"sensitivity base winner {base['winner']} != ranking winner {top}")
        if decision is not None and decision.get("target") not in ranking["country_code"].head(2).tolist():
            errors.append(f"decision target {decision.get('target')} is not in the ranking's top 2")
    if "business_case_plan.csv" in frames:
        years = sorted(frames["business_case_plan.csv"]["year"].unique())
        if years[:len(config.PLAN_STORES)] != sorted(config.PLAN_STORES):
            errors.append(f"business plan years {years} don't start with config.PLAN_STORES {sorted(config.PLAN_STORES)}")
    if decision is not None:
        missing = DECISION_KEYS - set(decision)
        if missing:
            errors.append(f"decision.json: missing keys {sorted(missing)}")
        if decision.get("recommendation") not in ("GO", "CONDITIONAL GO", "NO-GO"):
            errors.append(f"decision.json: unknown recommendation {decision.get('recommendation')!r}")
        if decision.get("target") not in config.CANDIDATES:
            errors.append(f"decision.json: target {decision.get('target')!r} is not a candidate")
    return errors


def validate_outputs(directory=None) -> list[str]:
    """Check every processed file that exists (and that required ones exist). Returns all errors."""
    directory = directory or config.PROCESSED
    errors, frames = [], {}
    for file, contract in CONTRACTS.items():
        path = directory / file
        if not path.exists():
            if contract.required:
                errors.append(f"{file}: missing (run the pipeline)")
            continue
        df = read(file, directory)
        errors += [f"{file}: {e}" for e in check(contract, df)]
        frames[file] = df
    known = set(CONTRACTS) | {"ai_summary.json", "decision.json", "warehouse.duckdb"}
    for path in sorted(directory.glob("*")):
        if (path.is_file() and not path.name.startswith((".", "warehouse.duckdb"))
                and path.name not in known):
            errors.append(f"{path.name}: file without a contract (add one to contracts.py)")
    decision_path = directory / "decision.json"
    decision = json.loads(decision_path.read_text()) if decision_path.exists() else None
    errors += cross_checks(frames, decision)
    return errors


# ---------------------------------------------------------------------------
# Documentation
# ---------------------------------------------------------------------------
def to_markdown() -> str:
    lines = [
        "# Data contracts",
        "",
        "<!-- Generated by `python -m beauty_expansion.contracts --markdown > docs/DATA_CONTRACTS.md`."
        " Do not edit by hand: edit src/beauty_expansion/contracts.py. -->",
        "",
        "Every file in `data/processed/` has a contract: its grain, key and columns. The pipeline refuses",
        "to write a file that breaks it, and CI checks that this page matches the code.",
        "",
        "**Units from names:** `_eur` euros · `_meur` millions of euros · `_km` kilometres · "
        "`_pct` percent 0–100 · `_rate`, `_share`, `_margin`, `_cagr` fraction 0–1 · `_per_100k` per 100,000 inhabitants.",
        "",
    ]
    for c in CONTRACTS.values():
        status = "" if c.required else " *(planned)*"
        lines += [f"## `{c.file}`{status}", "",
                  f"- **Grain:** {c.grain}",
                  f"- **Key:** {', '.join(f'`{k}`' for k in c.key)}",
                  f"- **Produced by:** `{c.produced_by}`"]
        if c.countries:
            lines.append(f"- **Countries:** {', '.join(c.countries)}")
        if c.notes:
            lines.append(f"- **Note:** {c.notes}")
        lines += ["", "| Column | Type | Unit | Range / values | Empty allowed | Description |",
                  "|---|---|---|---|---|---|"]
        for col in c.columns:
            if col.allowed:
                rng = ", ".join(map(str, col.allowed)) if len(col.allowed) <= 6 else f"{len(col.allowed)} listed values"
            elif col.min is not None or col.max is not None:
                rng = f"{'' if col.min is None else col.min} – {'' if col.max is None else col.max}"
            else:
                rng = ""
            lines.append(f"| `{col.name}` | {col.dtype} | {col.unit} | {rng} | {'yes' if col.nullable else ''} | {col.description} |")
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Check data/processed against the data contracts.")
    parser.add_argument("--markdown", action="store_true", help="print the contracts as Markdown")
    args = parser.parse_args()
    if args.markdown:
        print(to_markdown())
        return 0
    errors = validate_outputs()
    if errors:
        print("Data contract errors:\n  - " + "\n  - ".join(errors))
        return 1
    print(f"All data contracts pass ({len(CONTRACTS)} contracts).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
