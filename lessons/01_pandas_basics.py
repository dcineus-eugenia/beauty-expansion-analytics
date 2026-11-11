"""
Module 01: pandas basics
========================

Goal: work with tables (DataFrames), the core skill of every data analyst.
Run it:  python lessons/01_pandas_basics.py

A DataFrame is like an Excel sheet in Python: rows, named columns, one type per column.
Everything you did with loops in module 00 becomes one line here.
"""

import pandas as pd

# Show all columns when printing (default hides some)
pd.set_option("display.width", 120)

# ---------------------------------------------------------------------------
# 1. Create a DataFrame from a list of dicts (same data as module 00)
# ---------------------------------------------------------------------------
countries = pd.DataFrame([
    {"country": "Germany",     "code": "DE", "population_m": 84.5, "vat_rate": 0.19, "beauty_market_bn_eur": 15.5, "competitor_stores": 980},
    {"country": "Netherlands", "code": "NL", "population_m": 17.9, "vat_rate": 0.21, "beauty_market_bn_eur": 3.6,  "competitor_stores": 260},
    {"country": "Austria",     "code": "AT", "population_m": 9.2,  "vat_rate": 0.20, "beauty_market_bn_eur": 1.9,  "competitor_stores": 140},
    {"country": "Belgium",     "code": "BE", "population_m": 11.8, "vat_rate": 0.21, "beauty_market_bn_eur": 2.6,  "competitor_stores": 150},
    {"country": "Ireland",     "code": "IE", "population_m": 5.3,  "vat_rate": 0.23, "beauty_market_bn_eur": 1.0,  "competitor_stores": 70},
])

print("=== 1. The DataFrame ===")
print(countries)
print("\nShape (rows, columns):", countries.shape)
print("\nColumn types:\n", countries.dtypes)

# ---------------------------------------------------------------------------
# 2. Select columns and rows
# ---------------------------------------------------------------------------
print("\n=== 2. Selecting ===")
print(countries["country"])                         # one column -> a Series
print(countries[["country", "vat_rate"]])           # several columns -> a DataFrame
print(countries[countries["vat_rate"] < 0.21])      # filter rows with a condition

# EXERCISE 2.1: show countries with a beauty market above 2 bn €.
# print(countries[...])

# EXERCISE 2.2: combine two conditions with & (and), each wrapped in parentheses:
# market above 2 bn AND VAT at or below 0.21.

# ---------------------------------------------------------------------------
# 3. New columns = new KPIs (vectorised: no loop needed)
# ---------------------------------------------------------------------------
print("\n=== 3. Computed columns ===")
countries["spend_per_capita_eur"] = countries["beauty_market_bn_eur"] * 1e9 / (countries["population_m"] * 1e6)

# Competitive density: competitor stores per million inhabitants (a KPI from the brief!)
countries["stores_per_m_inhab"] = countries["competitor_stores"] / countries["population_m"]

print(countries[["country", "spend_per_capita_eur", "stores_per_m_inhab"]].round(1))

# EXERCISE 3.1: add a column `market_per_store_m_eur`: beauty market (in M€) divided by
# competitor stores. It's a rough estimate of revenue per existing store. Which country looks
# the least crowded?

# ---------------------------------------------------------------------------
# 4. Sort and rank
# ---------------------------------------------------------------------------
print("\n=== 4. Sorting ===")
print(countries.sort_values("spend_per_capita_eur", ascending=False)[["country", "spend_per_capita_eur"]])

# rank(): 1 = best. Low density is good for us, so ascending=True.
countries["rank_density"] = countries["stores_per_m_inhab"].rank(ascending=True)
countries["rank_spend"] = countries["spend_per_capita_eur"].rank(ascending=False)
countries["naive_score"] = countries["rank_density"] + countries["rank_spend"]   # lower = better
print(countries.sort_values("naive_score")[["country", "rank_spend", "rank_density", "naive_score"]])

# ---------------------------------------------------------------------------
# 5. groupby: aggregate by a category
# ---------------------------------------------------------------------------
print("\n=== 5. groupby ===")
countries["region"] = ["DACH", "Benelux", "DACH", "Benelux", "Anglo"]
summary = countries.groupby("region").agg(
    countries=("country", "count"),
    total_market_bn=("beauty_market_bn_eur", "sum"),
    avg_vat=("vat_rate", "mean"),
)
print(summary)

# ---------------------------------------------------------------------------
# 6. Save and reload: the pipeline's handoff between steps
# ---------------------------------------------------------------------------
out = "data/interim/countries_practice.csv"
countries.to_csv(out, index=False)
reloaded = pd.read_csv(out)
print(f"\n=== 6. Saved to {out}, reloaded {len(reloaded)} rows ===")

# EXERCISE 6.1: also save it as Excel with .to_excel("data/interim/countries_practice.xlsx", index=False)
# and open it in Excel/Numbers to check.

print("\n✅ Module 01 done. Next: module 02, reading messy Excel financials.")
