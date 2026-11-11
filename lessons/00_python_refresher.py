"""
Module 00: Python refresher
===========================

Goal: get back into Python basics using the project's own data.
Run it:  python lessons/00_python_refresher.py

How to work:
  1. Read a section, run the script, check the output matches what you expect.
  2. Do the EXERCISE blocks (replace the `...` and uncomment the lines).
  3. Re-run. If something breaks, read the error message from the BOTTOM up:
     the last line says what went wrong, the lines above say where.

The numbers below are rough placeholders for practice. Real data arrives in module 03.
"""

# ---------------------------------------------------------------------------
# 1. Variables and types
# ---------------------------------------------------------------------------
# A variable is a name pointing to a value. Python guesses the type for you.

company_name = "Maison Éclat"   # str  (text). Rename it to your team's company!
store_count_france = 180        # int  (whole number)
avg_basket_eur = 42.5           # float (decimal number)
is_listed = True                # bool (True / False)

print("=== 1. Variables ===")
print(company_name, type(company_name))
print(store_count_france, type(store_count_france))

# f-strings: put variables inside text with {}. `:,` adds thousands separators,
# `:.1f` keeps 1 decimal.
print(f"{company_name} runs {store_count_france} stores, average basket {avg_basket_eur:.1f} €")

# ---------------------------------------------------------------------------
# 2. Lists: ordered collections
# ---------------------------------------------------------------------------
candidate_countries = ["Spain", "Italy", "Germany", "Belgium", "Netherlands"]

print("\n=== 2. Lists ===")
print("First candidate:", candidate_countries[0])     # indexes start at 0
print("Last candidate:", candidate_countries[-1])     # -1 = last item
print("How many:", len(candidate_countries))

# EXERCISE 2.1: add "Portugal" to the list with .append(), then print the list.
# candidate_countries.append(...)
# print(...)

# ---------------------------------------------------------------------------
# 3. Dictionaries: key -> value lookups
# ---------------------------------------------------------------------------
# One dict = one record. This is how JSON from APIs will look in module 03.

spain = {
    "country": "Spain",
    "code": "ES",
    "population_m": 48.6,       # millions
    "vat_rate": 0.21,
    "beauty_market_bn_eur": 9.5,
}

print("\n=== 3. Dicts ===")
print("Spain VAT:", spain["vat_rate"])
print("Keys:", list(spain.keys()))

# A list of dicts = a table. Each dict is a row. pandas (module 01) turns this into a DataFrame.
countries = [
    {"country": "Spain",       "code": "ES", "population_m": 48.6, "vat_rate": 0.21, "beauty_market_bn_eur": 9.5},
    {"country": "Italy",       "code": "IT", "population_m": 59.0, "vat_rate": 0.22, "beauty_market_bn_eur": 12.0},
    {"country": "Germany",     "code": "DE", "population_m": 84.5, "vat_rate": 0.19, "beauty_market_bn_eur": 15.5},
    {"country": "Belgium",     "code": "BE", "population_m": 11.8, "vat_rate": 0.21, "beauty_market_bn_eur": 2.6},
    {"country": "Netherlands", "code": "NL", "population_m": 17.9, "vat_rate": 0.21, "beauty_market_bn_eur": 3.6},
]

# EXERCISE 3.1: print Germany's population using the `countries` list.
# Hint: Germany is at index 2, and each item is a dict.
# print(countries[...][...])

# ---------------------------------------------------------------------------
# 4. Loops and conditions
# ---------------------------------------------------------------------------
print("\n=== 4. Loops ===")
for c in countries:
    # Market size per inhabitant: a first KPI!
    spend_per_capita = c["beauty_market_bn_eur"] * 1e9 / (c["population_m"] * 1e6)
    flag = "🔥" if spend_per_capita > 200 else ""
    print(f"{c['country']:<12} {spend_per_capita:>6.0f} €/inhabitant/year {flag}")

# EXERCISE 4.1: print only the countries whose VAT rate is below 0.21.
# for c in countries:
#     if ...:
#         print(...)

# ---------------------------------------------------------------------------
# 5. Functions: reusable logic
# ---------------------------------------------------------------------------
# Every KPI in this project will be a function. Write it once, apply it to every country.

def price_ex_vat(price_incl_vat: float, vat_rate: float) -> float:
    """Remove VAT from a shelf price. 24.00 € at 20 % VAT -> 20.00 € ex VAT."""
    return price_incl_vat / (1 + vat_rate)


def gross_margin_pct(price_incl_vat: float, vat_rate: float, unit_cost: float) -> float:
    """Gross margin after tax as a % of the ex-VAT price."""
    net_price = price_ex_vat(price_incl_vat, vat_rate)
    return (net_price - unit_cost) / net_price


print("\n=== 5. Functions ===")
# Same lipstick, same 9 € purchase cost, sold 25 € VAT-included everywhere:
for c in countries:
    m = gross_margin_pct(25.0, c["vat_rate"], unit_cost=9.0)
    print(f"{c['country']:<12} margin {m:.1%}")

# EXERCISE 5.1: write a function `relative_price_index(price_target, price_france)`
# that returns price_target / price_france * 100 (France = 100).
# Test it: relative_price_index(23.0, 25.0) should give 92.0
# def relative_price_index(...):
#     ...
# print(relative_price_index(23.0, 25.0))

# ---------------------------------------------------------------------------
# 6. Putting it together: a first (naive) ranking
# ---------------------------------------------------------------------------
print("\n=== 6. First ranking ===")
ranked = sorted(countries, key=lambda c: c["beauty_market_bn_eur"], reverse=True)
for rank, c in enumerate(ranked, start=1):
    print(f"#{rank} {c['country']} ({c['beauty_market_bn_eur']} bn €)")

# This ranking only uses market size, which is too naive. Germany wins on size but it's
# also the most competitive market. Module 07 combines 10 KPIs into a weighted score.

# EXERCISE 6.1 (challenge): rank countries by spend per capita instead of market size.
# Tip: define a small function first, then pass it as `key=`.

print("\n✅ Module 00 done. Next: lessons/01_pandas_basics.py")
