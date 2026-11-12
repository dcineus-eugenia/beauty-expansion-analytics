"""Web scraper: shelf prices of the same beauty products in France vs candidate countries.

Source: LOOKFANTASTIC country websites, a pan-European beauty e-retailer whose product IDs are
shared across its country sites. That lets us compare the *same* product.

Why not sephora.fr, notino or douglas? They answer scripts with 403 Forbidden (anti-bot).
We respect that and don't try to get around it.

Politeness rules applied:
  - robots.txt allows /c/brands/ and /p/ pages (checked 2026-11-12)
  - one request at a time, 1.5 s pause between requests
  - every page cached in data/raw/prices/: a re-run doesn't hit the site again
Coverage: FR, NL, AT, IE. Finland redirects to a generic EU site and Norway has no site, so those
two use the Eurostat price level index only (see analysis/kpis.py).
"""

import json
import re
import time

import pandas as pd
import requests
from bs4 import BeautifulSoup

from beauty_expansion import config

SITES = {
    "FR": "https://www.lookfantastic.fr",
    "NL": "https://www.lookfantastic.nl",
    "AT": "https://www.lookfantastic.at",
    "IE": "https://www.lookfantastic.ie",
}
# Brands chosen to cover Sephora's 4 main categories.
BRANDS = {
    "skincare": ["the-ordinary", "cerave", "la-roche-posay", "clinique", "drunk-elephant"],
    "makeup": ["benefit", "nars", "mac", "too-faced"],
    "haircare": ["olaplex", "kerastase", "moroccanoil"],
    "fragrance": ["yves-saint-laurent", "lancome", "paco-rabanne"],
}
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/130.0 Safari/537.36",
    "Accept-Language": "en;q=0.8",
}
CACHE_DIR = config.RAW / "prices"
PAUSE_S = 1.5
MAX_PRODUCTS_PER_BRAND = 6


def _get(url: str, cache_name: str) -> str | None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache = CACHE_DIR / cache_name
    if cache.exists():
        return cache.read_text()
    time.sleep(PAUSE_S)
    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
    except requests.RequestException:
        return None
    if response.status_code != 200:
        cache.write_text("")              # remember the miss, don't retry every run
        return None
    cache.write_text(response.text)
    return response.text


def product_ids(country: str, brand: str) -> set[str]:
    html = _get(f"{SITES[country]}/c/brands/{brand}/", f"brand_{country}_{brand}.html")
    if not html:
        return set()
    return set(re.findall(r'href="/p/(?:[^"]*/)?(\d{7,9})/"', html))


def product_price(country: str, product_id: str) -> dict | None:
    """Read name and price from the page's schema.org JSON-LD (the most stable part of a page)."""
    html = _get(f"{SITES[country]}/p/{product_id}/", f"p_{country}_{product_id}.html")
    if not html:
        return None
    soup = BeautifulSoup(html, "html.parser")
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
        except json.JSONDecodeError:
            continue
        if data.get("@type") == "ProductGroup":
            variant = (data.get("hasVariant") or [None])[0]
        elif data.get("@type") == "Product":
            variant = data
        else:
            continue
        if not variant:
            continue
        offers = variant.get("offers")
        offers = offers[0] if isinstance(offers, list) else offers
        if not offers or offers.get("price") is None:
            continue
        brand = variant.get("brand") or data.get("brand")
        return {
            "product_id": product_id,
            "sku": variant.get("sku"),
            "name": variant.get("name"),
            "brand": brand.get("name") if isinstance(brand, dict) else brand,
            "price_eur": float(offers["price"]),
            "currency": offers.get("priceCurrency"),
        }
    return None


def extract_all() -> pd.DataFrame:
    """Prices of products sold on every country site, one row per (product, country)."""
    # 1. product IDs listed on each brand page, in every country
    common_by_brand = {}
    for category, brands in BRANDS.items():
        for brand in brands:
            ids_by_country = {c: product_ids(c, brand) for c in SITES}
            common_by_brand[(category, brand)] = (
                set.intersection(*ids_by_country.values()) if all(ids_by_country.values()) else set())

    # 2. Promotions (beauty boxes, advent calendars) are linked from EVERY brand page's menu.
    #    A real product belongs to one brand, so drop IDs seen under 2+ brands.
    seen = {}
    for ids in common_by_brand.values():
        for pid in ids:
            seen[pid] = seen.get(pid, 0) + 1
    promos = {pid for pid, n in seen.items() if n > 1}

    rows = []
    for (category, brand), common in common_by_brand.items():
        common = common - promos
        for pid in sorted(common)[:MAX_PRODUCTS_PER_BRAND]:
            for country in SITES:
                p = product_price(country, pid)
                if p and p["currency"] == "EUR":
                    rows.append({**p, "brand": brand, "country_code": country, "category": category})
        print(f"  prices {brand:<20} common products: {len(common):>3}")
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    # keep products priced in ALL countries, so every country is compared on the same basket
    complete = df.groupby("product_id")["country_code"].nunique() == len(SITES)
    return df[df["product_id"].isin(complete[complete].index)].reset_index(drop=True)
