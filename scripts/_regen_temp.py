"""Temporary: regenerate outputs to _v2-suffixed files while originals are locked open in Excel."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import merge_extraction
import split_by_category

merge_extraction.EXTRACTED_DIR
orig_open_name = "financials_extracted.csv"
new_name = "financials_extracted_v2.csv"

# Monkeypatch the output filename for this run only.
_original_main = merge_extraction.main


def patched_merge_main():
    import csv
    import json

    EXTRACTED_DIR = merge_extraction.EXTRACTED_DIR
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
        fiscal_year = merge_extraction.CONTENT_FISCAL_YEAR.get(folder)

        row = {
            "entity_name": merge_extraction.ENTITY_NAMES.get(folder, folder),
            "source_file": audit.get("chosen_file", ""),
            "fiscal_year": fiscal_year,
            "fiscal_year_detected": audit.get("year_detected", ""),
            "data_vintage_flag": merge_extraction.vintage_flag(fiscal_year),
            "file_selection_flag": audit.get("flag", ""),
            "currency": currency,
            "fx_rate_to_zar": rate,
            "fx_rate_date": fx["date"] if currency != "ZAR" else "",
        }
        for key in merge_extraction.NUMERIC_FIELDS:
            value = figures.get(key)
            row[f"{key}_m"] = value
            row[f"{key}_zar_m"] = merge_extraction.round_or_none(value, rate) if rate is not None else None

        for key in merge_extraction.FIELD_ORDER:
            if key in rec:
                row[key] = rec[key]
        out_rows.append(row)

    out_rows.sort(key=lambda r: r["entity_name"])

    out_path = EXTRACTED_DIR / new_name
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=merge_extraction.FIELD_ORDER)
        writer.writeheader()
        writer.writerows(out_rows)

    print(f"Wrote {len(out_rows)} rows to {out_path}")
    return out_path


merged_path = patched_merge_main()

# Now split, reading from the v2 merged file, writing v2 category files.
import csv as csv_mod

with open(merged_path, encoding="utf-8") as f:
    rows = list(csv_mod.DictReader(f))

for filename, fields in split_by_category.CATEGORIES:
    out_name = filename.replace(".csv", "_v2.csv")
    out_path = merge_extraction.EXTRACTED_DIR / out_name
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv_mod.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fields})
    print(f"Wrote {out_path}")
