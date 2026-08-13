"""
Financial report extraction pipeline - multi-year merge.

Combines:
  hackathon-finreports/_extracted/multi_year_audit.csv        (which file/pages fed each company-year)
  hackathon-finreports/_extracted/multi_year_figures.json     (agent-extracted numeric fields per company-year)
  hackathon-finreports/_extracted/financials_extracted.csv    (existing FY2025 rows, reused for companies
                                                                 whose FY2025 source file didn't change)
  hackathon-finreports/_extracted/fx_rates_zar.json

into a long-format, numeric-only ML training set:
  hackathon-finreports/_extracted/financials_multiyear.csv

One row per (company, fiscal_year) - up to 3 rows per company (2024/2025/2026), vs. the single-year
financials_extracted.csv which has exactly one row per company. Free-text fields (geographic split,
fx exposure narrative, working capital notes, imports/exports) are intentionally dropped here per the
ML use case - only currency-normalizable numeric fields + a short `notes` caveat are kept.
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

# Companies where the FY2025 source file in hackathon-finreports-2025 is unchanged from the
# single-year pipeline's pick - reuse financials_extracted.csv for these instead of re-extracting.
FY2025_UNCHANGED = {
    "angloamerican", "angloashanti", "aspen", "bhp", "bid", "bidvest group",
    "clicks", "glencore", "gold fields", "nepi", "out", "pepkor", "shaftesbury", "shoprite",
}

NUMERIC_FIELDS = [
    "revenue", "cost_of_sales", "operating_expenses",
    "trade_receivables", "trade_payables", "inventory", "fx_gains_losses",
]

FIELD_ORDER = [
    "entity_name",
    "canonical",
    "fiscal_year",
    "source_file",
    "currency",
    "fx_rate_to_zar",
    "fx_rate_date",
    "revenue_m", "revenue_zar_m",
    "cost_of_sales_m", "cost_of_sales_zar_m",
    "operating_expenses_m", "operating_expenses_zar_m",
    "trade_receivables_m", "trade_receivables_zar_m",
    "trade_payables_m", "trade_payables_zar_m",
    "inventory_m", "inventory_zar_m",
    "foreign_revenue_pct",
    "fx_gains_losses_m", "fx_gains_losses_zar_m",
    "fiscal_year_end",
    "page_ref",
    "notes",
]


def round_or_none(value, rate):
    if value is None or rate is None:
        return None
    return round(value * rate, 1)


def main():
    fx = json.load(open(EXTRACTED_DIR / "fx_rates_zar.json", encoding="utf-8"))
    rates = fx["rates_to_zar"]

    multi_year_path = EXTRACTED_DIR / "multi_year_figures.json"
    multi_year_records = json.load(open(multi_year_path, encoding="utf-8")) if multi_year_path.exists() else []

    out_rows = []
    seen = set()  # (canonical, year)

    for rec in multi_year_records:
        canonical = rec["canonical"]
        year = rec["fiscal_year"]
        currency = rec.get("currency", "")
        rate = rates.get(currency)
        row = {
            "entity_name": ENTITY_NAMES.get(canonical, canonical),
            "canonical": canonical,
            "fiscal_year": year,
            "source_file": rec.get("source_file", ""),
            "currency": currency,
            "fx_rate_to_zar": rate,
            "fx_rate_date": fx["date"] if currency != "ZAR" else "",
            "foreign_revenue_pct": rec.get("foreign_revenue_pct"),
            "fiscal_year_end": rec.get("fiscal_year_end", ""),
            "page_ref": rec.get("page_ref", ""),
            "notes": rec.get("notes", ""),
        }
        for key in NUMERIC_FIELDS:
            value = rec.get(key)
            row[f"{key}_m"] = value
            row[f"{key}_zar_m"] = round_or_none(value, rate)
        out_rows.append(row)
        seen.add((canonical, year))

    # Reuse existing FY2025 rows for companies whose FY2025 source file didn't change.
    existing_path = EXTRACTED_DIR / "financials_extracted.csv"
    if existing_path.exists():
        with open(existing_path, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                canonical = None
                for key, name in ENTITY_NAMES.items():
                    if name == r["entity_name"]:
                        canonical = key
                        break
                if canonical is None or canonical not in FY2025_UNCHANGED:
                    continue
                if (canonical, 2025) in seen:
                    continue
                row = {
                    "entity_name": r["entity_name"],
                    "canonical": canonical,
                    "fiscal_year": 2025,
                    "source_file": r.get("source_file", ""),
                    "currency": r.get("currency", ""),
                    "fx_rate_to_zar": r.get("fx_rate_to_zar"),
                    "fx_rate_date": r.get("fx_rate_date", ""),
                    "foreign_revenue_pct": None,  # was free-text in the single-year pipeline, not reused
                    "fiscal_year_end": "",
                    "page_ref": r.get("page_ref", ""),
                    "notes": "Reused from financials_extracted.csv (FY2025 source file unchanged); foreign_revenue_pct/fx_gains_losses not carried over since those were free-text there.",
                }
                for key in ["revenue", "cost_of_sales", "trade_receivables", "trade_payables", "inventory"]:
                    row[f"{key}_m"] = r.get(f"{key}_m") or None
                    row[f"{key}_zar_m"] = r.get(f"{key}_zar_m") or None
                row["operating_expenses_m"] = None
                row["operating_expenses_zar_m"] = None
                row["fx_gains_losses_m"] = None
                row["fx_gains_losses_zar_m"] = None
                out_rows.append(row)
                seen.add((canonical, 2025))

    out_rows.sort(key=lambda r: (r["entity_name"], r["fiscal_year"]))

    out_path = EXTRACTED_DIR / "financials_multiyear.csv"
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELD_ORDER)
        writer.writeheader()
        for row in out_rows:
            writer.writerow({k: row.get(k, "") for k in FIELD_ORDER})

    print(f"Wrote {len(out_rows)} company-year rows to {out_path}")

    # Also emit a pure-numeric, ML-ready version (no notes/page_ref/source_file text columns).
    ml_fields = [f for f in FIELD_ORDER if f not in ("source_file", "page_ref", "notes", "fiscal_year_end")]
    ml_path = EXTRACTED_DIR / "financials_multiyear_ml.csv"
    with open(ml_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=ml_fields)
        writer.writeheader()
        for row in out_rows:
            writer.writerow({k: row.get(k, "") for k in ml_fields})
    print(f"Wrote ML-ready (numeric-only) version to {ml_path}")


if __name__ == "__main__":
    main()
