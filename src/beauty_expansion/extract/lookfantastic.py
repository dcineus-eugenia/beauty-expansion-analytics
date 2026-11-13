"""LOOKFANTASTIC perfume prices, scraped from brand pages (issue #3).

For each country site and each brand, the scraper:
1. finds the brand's "all products" listing page (its name changes by brand);
2. reads every product card on every page (?pageNumber=2, 3...);
3. keeps title, current price, recommended retail price (RRP) and the volume in ml.

Output: data/raw/lookfantastic_prices.csv (cache, not committed). Re-run with refresh=True to
scrape again. Prices are shelf prices, VAT included, in EUR.
"""

from __future__ import annotations

import re
import time
from datetime import date

import pandas as pd
import requests
from bs4 import BeautifulSoup

from beauty_expansion import config

CACHE = config.RAW / "lookfantastic_prices.csv"

_session = requests.Session()
_session.headers["User-Agent"] = config.SCRAPER_USER_AGENT


# ---------------------------------------------------------------------------
# Small parsing helpers
# ---------------------------------------------------------------------------
def parse_price(text: str | None) -> float | None:
    """'80,50 €', '€80,50', '€80.50' or '80.50€' -> 80.5."""
    if not text:
        return None
    s = re.sub(r"[^\d,.]", "", text)
    if not s:
        return None
    if "," in s and "." in s:            # both: the last one is the decimal separator
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    else:
        s = s.replace(",", ".")
    return float(s)


_ML = re.compile(r"(\d+(?:[.,]\d+)?)\s?ml\b", re.IGNORECASE)
_SET_WORDS = re.compile(
    r"\b(set|coffret|gift|geschenk|cadeau|kit|duo|trio|collection|discovery)\b|\+| x \d",
    re.IGNORECASE,
)
_TYPES = [  # order matters: most specific first
    ("eau de parfum", "EDP"),
    ("eau de toilette", "EDT"),
    ("cologne", "EDC"),
    ("extrait", "Parfum"),
    ("elixir", "Parfum"),
    ("parfum", "Parfum"),
]


def parse_volume_ml(title: str) -> float | None:
    """Volume of a single bottle; None when there is no volume or several (sets)."""
    found = _ML.findall(title)
    if len(found) != 1:
        return None
    return float(found[0].replace(",", "."))


def fragrance_type(title: str) -> str | None:
    t = title.lower()
    for word, label in _TYPES:
        if word in t:
            return label
    return None  # not a perfume (make-up, skincare, body lotion...)


def parse_card(card) -> dict:
    """One <product-card-wrapper> -> one row."""
    title_tag = card.select_one(".product-item-title")
    title = title_tag.get_text(" ", strip=True) if title_tag else ""

    rrp = current = None
    price_tag = card.select_one("p.price")
    if price_tag:
        spans = [s for s in price_tag.find_all("span") if "sr-only" not in (s.get("class") or [])]
        for s in spans:
            if "line-through" in (s.get("class") or []):
                rrp = parse_price(s.get_text())
            else:
                current = parse_price(s.get_text())

    return {
        "product_id": card.get("data-quicklook"),
        "title": title,
        "price_eur": current,
        "rrp_eur": rrp if rrp is not None else current,  # no discount -> RRP = price
        "volume_ml": parse_volume_ml(title),
        "fragrance_type": fragrance_type(title),
        "is_set": bool(_SET_WORDS.search(title)) or len(_ML.findall(title)) > 1,
        "is_refill": "refill" in title.lower(),
        "product_url": title_tag.get("href") if title_tag else None,
    }


# ---------------------------------------------------------------------------
# Network
# ---------------------------------------------------------------------------
def _get(url: str) -> requests.Response:
    time.sleep(config.SCRAPER_DELAY_S)
    response = _session.get(url, timeout=30)
    response.raise_for_status()
    return response


def _cards(soup: BeautifulSoup) -> list:
    return soup.select("product-card-wrapper")


def find_listing(base: str, slug: str, extra: list[str]) -> str | None:
    """Return the URL of the brand's paginated 'all products' page, or None if not sold."""
    for suffix in [*extra, "view-all", "all", ""]:
        url = f"{base}/c/brands/{slug}/" + (f"{suffix}/" if suffix else "")
        try:
            response = _get(url)
        except requests.HTTPError:
            continue
        if "brand-not-available" in response.url:
            return None
        soup = BeautifulSoup(response.text, "html.parser")
        has_pagination = soup.select_one("nav p[aria-label]") is not None
        if _cards(soup) and has_pagination:
            return response.url
    return None


def scrape_brand(country: str, brand: str, slug: str, extra: list[str]) -> list[dict]:
    base = config.LOOKFANTASTIC_SITES[country]
    url = find_listing(base, slug, extra)
    if url is None:
        print(f"  lookfantastic {country} {brand:<20} not found on this site")
        return []

    rows, page = [], 1
    while url and page <= config.SCRAPER_MAX_PAGES:
        soup = BeautifulSoup(_get(url).text, "html.parser")
        for card in _cards(soup):
            row = parse_card(card)
            row.update(country_code=country, brand=brand, page_url=url)
            rows.append(row)
        next_link = soup.select_one('a[data-e2e="pagination-next"]')
        url = next_link.get("href") if next_link else None
        page += 1
    print(f"  lookfantastic {country} {brand:<20} {len(rows):>4} products")
    return rows


def extract_all(refresh: bool = False) -> pd.DataFrame:
    """Scrape every brand on every site, or read the cache if it already exists."""
    if CACHE.exists() and not refresh:
        df = pd.read_csv(CACHE)
        print(f"  lookfantastic (cache) {len(df)} products")
        return df

    rows = []
    for country in config.LOOKFANTASTIC_SITES:
        for brand, (slug, extra) in config.FRAGRANCE_BRANDS.items():
            rows += scrape_brand(country, brand, slug, extra)

    df = pd.DataFrame(rows)
    df["scrape_date"] = date.today().isoformat()
    df["source"] = "LOOKFANTASTIC brand pages (scraped)"
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(CACHE, index=False)
    return df


if __name__ == "__main__":  # quick test: python -m beauty_expansion.extract.lookfantastic
    import sys

    data = extract_all(refresh="--refresh" in sys.argv)
    print(data.groupby(["country_code", "brand"]).size().unstack(0))
