"""
Module 02: Reading messy Excel and cleaning financials
======================================================

Goal: turn real, messy company files into clean tables you can trust.
Run it:  python lessons/02_excel_financials.py

Two real sources:
  1. LVMH ESG Data Book 2025 (Excel, published on lvmh.com/en/investors/key-figures)
     -> Selective Retailing headcount
  2. LVMH annual results press releases (copied by hand into data/manual/)
     -> Selective Retailing revenue and profit, in French number format ("14 852")

At the end we combine them into a KPI: revenue per employee.

Real files are never clean. In a data analyst's job, about 80 % of the time goes into this step.
"""

from pathlib import Path
import urllib.request

import pandas as pd

pd.set_option("display.width", 140)
pd.set_option("display.max_columns", None)

EXCEL_URL = "https://lvmh-com.cdn.prismic.io/lvmh-com/M5IFwnlvtIkq-QHG_LVMHESGDatabook-2025-.xlsx"
EXCEL_PATH = Path("data/raw/lvmh/lvmh_esg_databook_2025.xlsx")
FINANCIALS_PATH = Path("data/manual/lvmh_selective_retailing_financials.csv")

# ---------------------------------------------------------------------------
# 1. Get the file and look at what's inside
# ---------------------------------------------------------------------------
# Download only if we don't have it yet (a "cache"). Module 03 goes deeper on downloading.
if not EXCEL_PATH.exists():
    EXCEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    print("Downloading the LVMH ESG Data Book...")
    urllib.request.urlretrieve(EXCEL_URL, EXCEL_PATH)

excel = pd.ExcelFile(EXCEL_PATH)
print("=== 1. Sheets in the workbook ===")
print(excel.sheet_names)

# EXERCISE 1.1: the workbook has every sheet twice (FR and EN). Build a list with only the
# English sheets: the ones whose name starts with "EN". Use a loop, or a "list comprehension":
#   [name for name in excel.sheet_names if ...]
# Tip: strings have a .startswith("...") method.

# ---------------------------------------------------------------------------
# 2. Read a sheet "raw" and see the mess
# ---------------------------------------------------------------------------
# header=None: don't guess a header row, give me everything as-is.
raw = pd.read_excel(EXCEL_PATH, sheet_name="EN - Social", header=None)

print("\n=== 2. Raw sheet: first 30 rows ===")
print(raw.head(30))
# What you should notice:
#   - column 0 is empty (the designers left a margin column)
#   - the sheet holds MANY small tables stacked vertically, separated by empty rows
#   - each table starts with a title row like "Headcount by gender | 2023 | 2024 | 2025"
#   - some percentages are numbers (0.18), others are text ("19.1%"), even in the same table!
#   - pandas numbers rows from 0, Excel numbers them from 1: pandas row 57 = Excel row 58

# ---------------------------------------------------------------------------
# 3. Extract one table from the sheet
# ---------------------------------------------------------------------------
LABEL_COL = 1   # the column holding row labels


def extract_block(sheet: pd.DataFrame, title: str) -> pd.DataFrame:
    """Return the small table whose title row contains `title`.

    The title row gives the column headers (the years). The table ends at the first empty
    row after its data.
    """
    labels = sheet[LABEL_COL].astype(str).str.strip()
    matches = sheet.index[labels == title]
    if len(matches) == 0:
        raise ValueError(f"Table {title!r} not found")
    start = matches[0]

    header = sheet.loc[start]                    # e.g. [NaN, 'Headcount by...', 2023, 2024, 2025]
    rows = []
    for i in range(start + 1, len(sheet)):
        row = sheet.loc[i]
        if row.isna().all():                     # empty row
            if rows:                             # data already started -> end of table
                break
            continue                             # empty row right after the title -> skip it
        rows.append(row)

    block = pd.DataFrame(rows)
    block.columns = header.values
    block = block.rename(columns={title: "label"})
    block = block.dropna(axis="columns", how="all")      # drop empty columns (margin, "Cible")
    block["label"] = block["label"].str.strip()          # "Other Activities " -> "Other Activities"
    return block.reset_index(drop=True)


headcount = extract_block(raw, "Headcount by business group (number)")
print("\n=== 3. Headcount by business group ===")
print(headcount)

# EXERCISE 3.1: use extract_block to get "Headcount by occupational category (number)" and print it.
# Look at the 2023 Total. Does it equal the 2023 total headcount (213268, row 11 of the sheet)?
# Write one sentence in a comment: what could explain the difference? (Hint: scope/definitions.)

# ---------------------------------------------------------------------------
# 4. Validate, then reshape from "wide" to "long"
# ---------------------------------------------------------------------------
# Never trust a file blindly: check that the parts add up to the published total.
print("\n=== 4. Validation ===")
total_row = headcount[headcount["label"] == "Total"]
detail = headcount[headcount["label"] != "Total"]
for year in [2023, 2024, 2025]:
    computed = detail[year].sum()
    published = total_row[year].iloc[0]
    status = "OK" if computed == published else "MISMATCH"
    print(f"{year}: sum of groups = {computed:,}  published total = {published:,}  -> {status}")

# 2025 shows a MISMATCH of 1 employee in LVMH's own published file. That's a real finding!
# A gap this small is usually rounding or a late correction in one cell. The right reaction:
#   1. don't "fix" the source silently,
#   2. decide a business rule ("we use the detailed group figures, the gap is < 0.001 %"),
#   3. write that rule in the README's data dictionary ("Business rules" section).

# "Wide" = one column per year (nice for humans). "Long" = one row per (group, year)
# (what databases, charts and joins want). melt() converts wide -> long.
headcount_long = detail.melt(id_vars="label", var_name="year", value_name="headcount")
headcount_long = headcount_long.rename(columns={"label": "business_group"})
headcount_long["year"] = headcount_long["year"].astype(int)
headcount_long["headcount"] = headcount_long["headcount"].astype(int)
print("\nLong format:")
print(headcount_long.head(8))

# ---------------------------------------------------------------------------
# 5. Cleaning mixed number formats
# ---------------------------------------------------------------------------
geo = extract_block(raw, "Headcount by geographical area")
print("\n=== 5. Mixed formats ===")
print(geo)
print("Python types in the 2025 column:", geo[2025].map(type).value_counts().to_dict())


def to_number(value):
    """Convert messy cells to a float: 0.18 -> 0.18, '19.1%' -> 0.191, '14 852' -> 14852.0,
    'NA' / empty -> None."""
    if pd.isna(value):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(" ", "").replace("\xa0", "").replace(" ", "")
    if text.upper() in {"NA", "N/A", "-", ""}:
        return None
    if text.endswith("%"):
        return float(text.rstrip("%").replace(",", ".")) / 100
    return float(text.replace(",", "."))


for year in [2023, 2024, 2025]:
    geo[year] = geo[year].map(to_number)
print("\nCleaned:")
print(geo)
print("Each year should sum to ~1.0:", geo[[2023, 2024, 2025]].sum().round(2).to_dict())

# EXERCISE 5.1: extract "Headcount by age", clean the year columns with to_number, and print it.
# One year has no data at all. Which one? What does to_number return for it?

# ---------------------------------------------------------------------------
# 6. Financials from a press release (French number format)
# ---------------------------------------------------------------------------
print("\n=== 6. LVMH Selective Retailing financials ===")
fin = pd.read_csv(FINANCIALS_PATH, sep=";")
print(fin.dtypes)        # Revenue is text ('str'), not a number, because of the space in "14 852"

fin = fin.rename(columns={
    "Year": "year",
    "Revenue (M€)": "revenue_m_eur",
    "Profit from recurring operations (M€)": "recurring_profit_m_eur",
})
for col in ["revenue_m_eur", "recurring_profit_m_eur"]:
    fin[col] = fin[col].map(to_number)

fin["operating_margin"] = fin["recurring_profit_m_eur"] / fin["revenue_m_eur"]
fin["revenue_growth"] = fin["revenue_m_eur"].pct_change()       # vs previous row = previous year
print(fin.drop(columns="Source").to_string(formatters={
    "operating_margin": "{:.1%}".format,
    "revenue_growth": "{:+.1%}".format,
}))

# EXERCISE 6.1: compute the compound annual growth rate (CAGR) of revenue from 2021 to 2025:
#   CAGR = (revenue_2025 / revenue_2021) ** (1 / 4) - 1
# Tip: fin.loc[fin["year"] == 2025, "revenue_m_eur"].iloc[0] gets one value.
# This is a real KPI from the brief ("annual growth rate").

# ---------------------------------------------------------------------------
# 7. Combine both sources: revenue per employee
# ---------------------------------------------------------------------------
print("\n=== 7. Revenue per employee (Selective Retailing) ===")
sr_headcount = headcount_long[headcount_long["business_group"] == "Selective Retailing"]
combined = fin.merge(sr_headcount[["year", "headcount"]], on="year", how="inner")
combined["revenue_per_employee_k_eur"] = combined["revenue_m_eur"] * 1000 / combined["headcount"]
print(combined[["year", "revenue_m_eur", "headcount", "revenue_per_employee_k_eur"]].round(1))
# how="inner" keeps only years present in BOTH tables: 2021-2022 have no headcount in this file.
# Try how="left" to see the difference.

# ⚠️ Business caveat for the README: "Selective Retailing" = Sephora + DFS (duty free) + Le Bon Marché.
# LVMH does not publish Sephora alone. We use it as the best public proxy, and we SAY SO.

# EXERCISE 7.1: add `profit_per_employee_k_eur` (recurring profit per employee, in k€).
# Which year was the most productive per employee?

out = Path("data/processed/lvmh_selective_retailing.csv")
combined.drop(columns="Source").to_csv(out, index=False)
print(f"\nSaved {out}")

print("\n✅ Module 02 done. Next: module 03, Eurostat API (real country data).")
