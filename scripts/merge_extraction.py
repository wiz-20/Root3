"""
Financial report extraction pipeline - Step 3 (merge).

Combines:
  hackathon-finreports/_extracted/file_selection_audit.csv   (Step 1 output)
  hackathon-finreports/_extracted/extracted_fields.json      (Step 3 output - agent-read fields)

into the final:
  hackathon-finreports/_extracted/financials_extracted.csv
"""

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXTRACTED_DIR = ROOT / "hackathon-finreports" / "_extracted"

ENTITY_NAMES = {
    "angloamerican": "Anglo American",
    "angloashanti": "AngloGold Ashanti",
    "aspen": "Aspen Pharmacare",
    "bhp": "BHP Group",
    "bid": "Bid Corporation",
    "bidvest group": "The Bidvest Group",
    "clicks": "Clicks Group",
    "glencore": "Glencore",
    "gold fields": "Gold Fields",
    "mtn": "MTN Group",
    "naspe": "Naspers",
    "nepi": "NEPI Rockcastle",
    "out": "OUTsurance Group",
    "pepkor": "Pepkor Holdings",
    "prosus": "Prosus",
    "sanlam": "Sanlam",
    "shaftesbury": "Shaftesbury Capital plc",
    "shoprite": "Shoprite Holdings",
    "valterra": "Valterra Platinum",
    "vodacom": "Vodacom Group",
}

NUMERIC_FIELDS = ["revenue", "cost_of_sales", "trade_receivables", "trade_payables", "inventory"]

# The fiscal year actually covered by the report content, as stated in each company's
# extraction notes - NOT the year in the filename (those can mismatch: e.g. MTN's AFS
# filename is dated March 2025 but the statements are for FY2024; Gold Fields/AngloGold/
# Valterra have no year in their filename at all, so fiscal_year_detected is blank there).
# This is the trustworthy column to filter/group on.
CONTENT_FISCAL_YEAR = {
    "angloamerican": 2025,
    "angloashanti": 2025,
    "aspen": 2025,
    "bhp": 2025,
    "bid": 2025,
    "bidvest group": 2025,
    "clicks": 2025,
    "glencore": 2025,
    "gold fields": 2025,
    "mtn": 2024,
    "naspe": 2026,
    "nepi": 2025,
    "out": 2025,
    "pepkor": 2025,
    "prosus": 2026,
    "sanlam": 2023,
    "shaftesbury": 2025,
    "shoprite": 2025,
    "valterra": 2024,
    "vodacom": 2026,
}

# Most companies in this set report FY2025 or FY2026; anything older is flagged so it
# can't be silently used at full confidence in a gap ranking alongside current peers.
CURRENT_FY_THRESHOLD = 2025


def vintage_flag(fiscal_year):
    if fiscal_year is None:
        return "unknown - verify fiscal year before use"
    if fiscal_year >= CURRENT_FY_THRESHOLD:
        return "current"
    return f"STALE (FY{fiscal_year} vs. most peers FY2025/2026) - needs team decision on confidence weighting"


FIELD_ORDER = [
    "entity_name",
    "source_file",
    "fiscal_year",
    "fiscal_year_detected",
    "data_vintage_flag",
    "currency",
    "fx_rate_to_zar",
    "fx_rate_date",
    "revenue_m",
    "revenue_zar_m",
    "cost_of_sales_m",
    "cost_of_sales_zar_m",
    "trade_receivables_m",
    "trade_receivables_zar_m",
    "trade_payables_m",
    "trade_payables_zar_m",
    "inventory_m",
    "inventory_zar_m",
    "revenue",
    "cost_of_sales",
    "operating_expenses",
    "trade_receivables",
    "trade_payables",
    "inventory",
    "imports_exports",
    "working_capital_notes",
    "foreign_revenue_pct",
    "geographic_revenue_split",
    "fx_gains_losses",
    "fx_exposure_notes",
    "page_ref",
    "file_selection_flag",
    "notes",
]


def round_or_none(value, rate):
    if value is None:
        return None
    return round(value * rate, 1)


def main():
    audit_rows = {row["folder"]: row for row in csv.DictReader(open(EXTRACTED_DIR / "file_selection_audit.csv", encoding="utf-8"))}
    extracted = json.load(open(EXTRACTED_DIR / "extracted_fields.json", encoding="utf-8"))
    primary_figures = json.load(open(EXTRACTED_DIR / "primary_figures.json", encoding="utf-8"))
    fx = json.load(open(EXTRACTED_DIR / "fx_rates_zar.json", encoding="utf-8"))
    rates = fx["rates_to_zar"]

    out_rows = []
    for rec in extracted:
        folder = rec["folder"]
        audit = audit_rows.get(folder, {})
        figures = primary_figures.get(folder, {})
        currency = figures.get("currency", "")
        rate = rates.get(currency)

        fiscal_year = CONTENT_FISCAL_YEAR.get(folder)
        row = {
            "entity_name": ENTITY_NAMES.get(folder, folder),
            "source_file": audit.get("chosen_file", ""),
            "fiscal_year": fiscal_year,
            "fiscal_year_detected": audit.get("year_detected", ""),
            "data_vintage_flag": vintage_flag(fiscal_year),
            "file_selection_flag": audit.get("flag", ""),
            "currency": currency,
            "fx_rate_to_zar": rate,
            "fx_rate_date": fx["date"] if currency != "ZAR" else "",
        }
        for key in NUMERIC_FIELDS:
            value = figures.get(key)
            row[f"{key}_m"] = value
            row[f"{key}_zar_m"] = round_or_none(value, rate) if rate is not None else None

        for key in FIELD_ORDER:
            if key in rec:
                row[key] = rec[key]
        out_rows.append(row)

    out_rows.sort(key=lambda r: r["entity_name"])

    out_path = EXTRACTED_DIR / "financials_extracted.csv"
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELD_ORDER)
        writer.writeheader()
        writer.writerows(out_rows)

    print(f"Wrote {len(out_rows)} rows to {out_path}")
    print(f"FX source: {fx['source']} ({fx['date']}) - rates: {rates}")


if __name__ == "__main__":
    main()
