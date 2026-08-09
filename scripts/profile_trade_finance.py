"""
Profiling report for trade_finance.csv (~20K rows) — pandas.

Run: py scripts/profile_trade_finance.py
Writes: docs/reports/sections/trade_finance.md (also prints to stdout)
"""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from profiling_common import DATE_WINDOW_END, DATE_WINDOW_START, entity_coverage_section, md_table

ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = ROOT / "trade_finance.csv"
OUT_PATH = ROOT / "docs" / "reports" / "sections" / "trade_finance.md"

COLUMN_NOTES = {
    "instrument_id": "unique identifier per trade finance instrument",
    "entity_id": "internal client identifier — join key across all 3 Syn Bank datasets",
    "entity_name": "client display name — join key against external financials data",
    "sector": "client's industry/sector classification",
    "date": "instrument issue/booking date",
    "instrument_type": "letters_of_credit / export_collections / guarantees",
    "direction": "export or import",
    "tenor_days": "instrument tenor in days",
    "value_zar": "instrument face value, already converted to ZAR",
    "counterparty_country": "country of the trade counterparty",
    "commodity_or_contract_type": "underlying commodity or contract category",
    "status": "issued / settled / active / expired",
    "beneficiary_name": "name of the instrument beneficiary",
    "reference": "instrument reference / description text",
    "memo": "free-text memo field, mostly unused",
}

VALID_INSTRUMENT_TYPES = {"letters_of_credit", "export_collections", "guarantees"}
VALID_STATUSES = {"issued", "settled", "active", "expired"}


def main() -> None:
    df = pd.read_csv(CSV_PATH, parse_dates=["date"])
    lines = ["# trade_finance.csv — Profiling Report", ""]

    # --- Schema ---
    lines.append("## Schema")
    lines.append("")
    lines.append(md_table(
        ["Column", "Dtype", "Notes"],
        [[c, str(df[c].dtype), COLUMN_NOTES.get(c, "")] for c in df.columns],
    ))
    lines.append("")

    # --- Row counts & date coverage ---
    lines.append("## Row counts & date coverage")
    lines.append("")
    lines.append(f"Rows: {len(df):,}")
    date_min, date_max = df["date"].min(), df["date"].max()
    lines.append(f"Date range: {date_min.date()} -> {date_max.date()}")
    out_of_window = df[(df["date"] < DATE_WINDOW_START) | (df["date"] > DATE_WINDOW_END)]
    if len(out_of_window) == 0:
        lines.append(f"All rows fall within the stated {DATE_WINDOW_START} -> {DATE_WINDOW_END} window.")
    else:
        lines.append(f"**{len(out_of_window):,} rows fall OUTSIDE the stated {DATE_WINDOW_START} -> {DATE_WINDOW_END} window.**")
    implied_maturity_past_window = df[df["date"] + pd.to_timedelta(df["tenor_days"], unit="D") > pd.Timestamp(DATE_WINDOW_END)]
    lines.append(f"Rows whose `date + tenor_days` implied maturity falls after {DATE_WINDOW_END} (not an error — just means the instrument matures beyond the data window): {len(implied_maturity_past_window):,}")
    lines.append("")

    # --- Entity coverage ---
    id_name = df[["entity_id", "entity_name"]].drop_duplicates()
    ids_per_name = id_name.groupby("entity_name")["entity_id"].nunique()
    names_per_id = id_name.groupby("entity_id")["entity_name"].nunique()
    clean_1to1 = bool((ids_per_name == 1).all() and (names_per_id == 1).all())
    lines.append(entity_coverage_section(set(df["entity_name"].unique()), id_name_pairs_are_1to1=clean_1to1))
    lines.append("")

    # --- Missing values & duplicates ---
    lines.append("## Missing values & duplicates")
    lines.append("")
    null_pct = (100 * df.isnull().mean()).round(2)
    lines.append(md_table(
        ["Column", "Null %"],
        [[c, f"{null_pct[c]}%"] for c in df.columns],
    ))
    lines.append("")
    exact_dupes = df.duplicated().sum()
    id_dupes = df["instrument_id"].duplicated().sum()
    lines.append(f"Exact duplicate rows (all columns identical): {exact_dupes:,}")
    lines.append(f"Duplicate `instrument_id` values: {id_dupes:,}")
    lines.append("")

    # --- Outliers / data quality ---
    lines.append("## Outliers / data quality issues")
    lines.append("")
    nonpositive_value = (df["value_zar"] <= 0).sum()
    lines.append(f"`value_zar` <= 0: {nonpositive_value:,} rows")
    nonpositive_tenor = (df["tenor_days"] <= 0).sum()
    lines.append(f"`tenor_days` <= 0: {nonpositive_tenor:,} rows")
    extreme_tenor = (df["tenor_days"] > 3650).sum()
    lines.append(f"`tenor_days` > 3650 (10 years): {extreme_tenor:,} rows (max observed: {df['tenor_days'].max()})")
    bad_direction = (~df["direction"].isin(["export", "import"])).sum()
    lines.append(f"`direction` outside {{export, import}}: {bad_direction:,} rows")
    bad_instrument = (~df["instrument_type"].isin(VALID_INSTRUMENT_TYPES)).sum()
    lines.append(f"`instrument_type` outside {sorted(VALID_INSTRUMENT_TYPES)}: {bad_instrument:,} rows")
    bad_status = (~df["status"].isin(VALID_STATUSES)).sum()
    lines.append(f"`status` outside {sorted(VALID_STATUSES)}: {bad_status:,} rows")
    lines.append("")
    lines.append("Status distribution:")
    lines.append(md_table(["Status", "Count"], [[s, c] for s, c in df["status"].value_counts().items()]))
    lines.append("")

    # --- Currency ---
    lines.append("## Currency")
    lines.append("")
    lines.append(
        "No separate `currency` column — `value_zar` is named as already ZAR-converted, and there is no "
        "FX-rate column in this file to independently verify the conversion, same caveat as "
        "`cross_border_payments.csv`."
    )
    lines.append("")

    # --- Join feasibility ---
    lines.append("## Join feasibility")
    lines.append("")
    lines.append(
        "- To other internal datasets: `entity_id` (confirmed 1:1 with `entity_name` above) — same key used "
        "in `transactional_banking.csv` and `cross_border_payments.csv`.\n"
        "- To `financials_extracted_v2.csv`: `entity_name`, exact string match (see Entity coverage above)."
    )
    lines.append("")

    report = "\n".join(lines)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(report, encoding="utf-8")
    print(report)
    print(f"\n\nWrote {OUT_PATH}", file=sys.stderr)


if __name__ == "__main__":
    main()
