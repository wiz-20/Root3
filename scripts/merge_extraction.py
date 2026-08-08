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

FIELD_ORDER = [
    "entity_name",
    "source_file",
    "fiscal_year_detected",
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

        row = {
            "entity_name": ENTITY_NAMES.get(folder, folder),
            "source_file": audit.get("chosen_file", ""),
            "fiscal_year_detected": audit.get("year_detected", ""),
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
