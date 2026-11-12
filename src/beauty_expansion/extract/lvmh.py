"""LVMH public data: ESG Data Book (Excel) and Selective Retailing financials (manual CSV).

The cleaning logic is the one built step by step in lessons/02_excel_financials.py.
"""

import urllib.request

import pandas as pd

from beauty_expansion import config

EXCEL_URL = "https://lvmh-com.cdn.prismic.io/lvmh-com/M5IFwnlvtIkq-QHG_LVMHESGDatabook-2025-.xlsx"
EXCEL_PATH = config.RAW / "lvmh" / "lvmh_esg_databook_2025.xlsx"
FINANCIALS_PATH = config.MANUAL / "lvmh_selective_retailing_financials.csv"
LABEL_COL = 1


def to_number(value):
    """0.18 -> 0.18, '19.1%' -> 0.191, '14 852' -> 14852.0, 'NA'/empty -> None."""
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


def extract_block(sheet: pd.DataFrame, title: str) -> pd.DataFrame:
    labels = sheet[LABEL_COL].astype(str).str.strip()
    start = sheet.index[labels == title][0]
    header = sheet.loc[start]
    rows = []
    for i in range(start + 1, len(sheet)):
        row = sheet.loc[i]
        if row.isna().all():
            if rows:
                break
            continue
        rows.append(row)
    block = pd.DataFrame(rows)
    block.columns = header.values
    block = block.rename(columns={title: "label"}).dropna(axis="columns", how="all")
    block["label"] = block["label"].str.strip()
    return block.reset_index(drop=True)


def headcount_by_group() -> pd.DataFrame:
    if not EXCEL_PATH.exists():
        EXCEL_PATH.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(EXCEL_URL, EXCEL_PATH)
    raw = pd.read_excel(EXCEL_PATH, sheet_name="EN - Social", header=None)
    block = extract_block(raw, "Headcount by business group (number)")
    block = block[block["label"] != "Total"]
    long = block.melt(id_vars="label", var_name="year", value_name="headcount")
    long = long.rename(columns={"label": "business_group"})
    long["year"] = long["year"].astype(int)
    long["headcount"] = long["headcount"].map(to_number).astype(int)
    return long


def selective_retailing() -> pd.DataFrame:
    """Revenue, recurring profit and headcount of LVMH Selective Retailing by year."""
    fin = pd.read_csv(FINANCIALS_PATH, sep=";").rename(columns={
        "Year": "year",
        "Revenue (M€)": "revenue_meur",
        "Profit from recurring operations (M€)": "recurring_profit_meur",
        "Source": "source",
    })
    for col in ["revenue_meur", "recurring_profit_meur"]:
        fin[col] = fin[col].map(to_number)
    hc = headcount_by_group()
    hc = hc[hc["business_group"] == "Selective Retailing"][["year", "headcount"]]
    out = fin.merge(hc, on="year", how="left")
    out["operating_margin"] = out["recurring_profit_meur"] / out["revenue_meur"]
    print(f"  lvmh selective retailing: {len(out)} years, headcount for {out['headcount'].notna().sum()}")
    return out
