"""
Splits financials_extracted.csv into 3 separate files matching the exact
3-category structure the team is using (per Fatan's original request):

  1. Income statement basics: revenue, cost of sales, operating expenses,
     trade receivables, trade payables
  2. Trade & working capital: inventory, trade receivables, imports/exports,
     working capital
  3. Foreign / FX exposure: foreign revenue %, geographic revenue split,
     FX gains/losses, disclosed FX exposure

Run after merge_extraction.py.

Outputs:
  hackathon-finreports/_extracted/category1_income_statement.csv
  hackathon-finreports/_extracted/category2_trade_working_capital.csv
  hackathon-finreports/_extracted/category3_fx_exposure.csv
"""

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXTRACTED_DIR = ROOT / "hackathon-finreports" / "_extracted"
MASTER = EXTRACTED_DIR / "financials_extracted.csv"

COMMON = [
    "entity_name", "source_file", "fiscal_year", "fiscal_year_detected", "data_vintage_flag",
    "currency", "fx_rate_to_zar", "page_ref", "file_selection_flag",
]

CATEGORY_1 = COMMON + [
    "revenue_zar_m", "revenue_m", "revenue",
    "cost_of_sales_zar_m", "cost_of_sales_m", "cost_of_sales",
    "operating_expenses",
    "trade_receivables_zar_m", "trade_receivables_m", "trade_receivables",
    "trade_payables_zar_m", "trade_payables_m", "trade_payables",
    "notes",
]

CATEGORY_2 = COMMON + [
    "inventory_zar_m", "inventory_m", "inventory",
    "trade_receivables_zar_m", "trade_receivables_m", "trade_receivables",
    "imports_exports",
    "working_capital_notes",
    "notes",
]

CATEGORY_3 = COMMON + [
    "foreign_revenue_pct",
    "geographic_revenue_split",
    "fx_gains_losses",
    "fx_exposure_notes",
    "notes",
]

CATEGORIES = [
    ("category1_income_statement.csv", CATEGORY_1),
    ("category2_trade_working_capital.csv", CATEGORY_2),
    ("category3_fx_exposure.csv", CATEGORY_3),
]


def main():
    with open(MASTER, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    for filename, fields in CATEGORIES:
        out_path = EXTRACTED_DIR / filename
        with open(out_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            for row in rows:
                writer.writerow({k: row.get(k, "") for k in fields})
        print(f"Wrote {len(rows)} rows to {out_path}")


if __name__ == "__main__":
    main()
