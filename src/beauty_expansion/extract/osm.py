"""OpenStreetMap via the Overpass API: beauty store locations and main cities.

Overpass is a free, shared service: we cache every answer in data/raw/osm/ and wait between
calls. Usage policy: https://wiki.openstreetmap.org/wiki/Overpass_API#Public_Overpass_API_instances
"""

import json
import time

import pandas as pd
import requests

from beauty_expansion import config

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
HEADERS = {"User-Agent": "beauty-expansion-student-project (Eugenia School data analytics case)"}
CACHE_DIR = config.RAW / "osm"


def _query(name: str, ql: str, refresh: bool = False) -> dict:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache = CACHE_DIR / f"{name}.json"
    if cache.exists() and not refresh:
        return json.loads(cache.read_text())
    for attempt in range(3):
        response = requests.post(OVERPASS_URL, data={"data": ql}, headers=HEADERS, timeout=300)
        if response.status_code == 200:
            break
        time.sleep(30 * (attempt + 1))      # server busy (429/504): back off and retry
    response.raise_for_status()
    data = response.json()
    if "runtime error" in data.get("remark", ""):      # Overpass answers 200 even when the query timed out
        raise RuntimeError(f"Overpass query {name} failed: {data['remark']}")
    cache.write_text(json.dumps(data))
    time.sleep(5)                           # be polite to the shared server
    return data


def _brand_regex() -> str:
    brands = config.SELECTIVE_BRANDS + config.DRUGSTORE_BRANDS
    return "^(" + "|".join(b.replace(".", r"\.") for b in brands) + ")$"


NAME_LOOKUP_COUNTRIES = {"NO", "FI"}
NORDIC_CHAINS = ["KICKS", "Lyko", "Sokos Emotion", "Fredrik & Louisa", "Parfymeriet", "Normal", "Vita", "Matas", "Life"]


def _name_lookups() -> str:
    """Exact-name lookups (indexed, fast), in the spellings found in OSM: 'KICKS', 'Kicks', 'kicks'."""
    names = set()
    for b in NORDIC_CHAINS:
        names |= {b, b.upper(), b.title(), b.lower()}
    return "\n      ".join(f'nwr["shop"]["name"="{n}"](area.a);' for n in sorted(names))


def stores(country_code: str, refresh: bool = False) -> pd.DataFrame:
    """All stores of the tracked brands in one country, with coordinates."""
    ql = f"""
    [out:json][timeout:240];
    area["ISO3166-1"="{country_code}"][admin_level=2]->.a;
    nwr["brand"~"{_brand_regex()}",i](area.a);
    out tags center;
    """
    data = _query(f"stores_{country_code}", ql, refresh)

    # Data-quality lesson: Nordic chains (KICKS, Normal, Vita...) are often tagged with their `name`
    # only, no `brand`. A second, exact-name query fills that gap where it matters.
    if country_code in NAME_LOOKUP_COUNTRIES:
        ql_names = f"""
        [out:json][timeout:240];
        area["ISO3166-1"="{country_code}"][admin_level=2]->.a;
        ({_name_lookups()});
        out tags center;
        """
        data["elements"] += _query(f"stores_by_name_{country_code}", ql_names, refresh)["elements"]

    canonical = {b.lower(): b for b in config.SELECTIVE_BRANDS + config.DRUGSTORE_BRANDS}
    rows = []
    for el in data["elements"]:
        tags = el.get("tags", {})
        point = el.get("center", el)
        brand = canonical.get(tags.get("brand", "").lower()) or canonical.get(tags.get("name", "").lower())
        if brand is None or "lat" not in point:
            continue
        rows.append({
            "osm_id": f"{el['type']}/{el['id']}",
            "country_code": country_code,
            "brand": brand,
            "segment": "selective" if brand in config.SELECTIVE_BRANDS else "drugstore",
            "city": tags.get("addr:city"),
            "lat": point["lat"],
            "lon": point["lon"],
        })
    df = pd.DataFrame(rows).drop_duplicates("osm_id")
    lat_min, lat_max, lon_min, lon_max = config.EUROPE_BBOX
    return df[df["lat"].between(lat_min, lat_max) & df["lon"].between(lon_min, lon_max)]


def cities(country_code: str, top: int = 5, refresh: bool = False) -> pd.DataFrame:
    """Largest cities of a country (OSM place=city with a population tag)."""
    ql = f"""
    [out:json][timeout:120];
    area["ISO3166-1"="{country_code}"][admin_level=2]->.a;
    node["place"="city"]["population"](area.a);
    out;
    """
    data = _query(f"cities_{country_code}", ql, refresh)
    rows = []
    for el in data["elements"]:
        tags = el["tags"]
        try:
            population = int(str(tags["population"]).replace(" ", "").replace(",", "").replace(".", ""))
        except ValueError:
            continue
        rows.append({
            "country_code": country_code,
            "city": tags.get("name:en") or tags.get("name"),
            "population": population,
            "lat": el["lat"],
            "lon": el["lon"],
        })
    df = pd.DataFrame(rows).sort_values("population", ascending=False)
    return df.drop_duplicates("city").head(top).reset_index(drop=True)


def extract_all(countries: list[str], refresh: bool = False) -> tuple[pd.DataFrame, pd.DataFrame]:
    store_frames, city_frames = [], []
    for cc in countries:
        s = stores(cc, refresh)
        c = cities(cc, refresh=refresh)
        print(f"  osm {cc}: {len(s):>5} stores, top cities: {', '.join(c['city'])}")
        store_frames.append(s)
        city_frames.append(c)
    return pd.concat(store_frames, ignore_index=True), pd.concat(city_frames, ignore_index=True)
