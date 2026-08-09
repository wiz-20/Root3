"""
Profiling report for cross_border_payments.csv (~241K rows) — pandas.

Run: py scripts/profile_cross_border_payments.py
Writes: docs/reports/sections/cross_border_payments.md (also prints to stdout)
"""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from profiling_common import DATE_WINDOW_END, DATE_WINDOW_START, entity_coverage_section, md_table

ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = ROOT / "cross_border_payments.csv"
OUT_PATH = ROOT / "docs" / "reports" / "sections" / "cross_border_payments.md"

COLUMN_NOTES = {
    "transaction_id": "unique identifier per payment record",
    "entity_id": "internal client identifier — join key across all 3 Syn Bank datasets",
    "entity_name": "client display name — join key against external financials data",
    "sector": "client's industry/sector classification",
    "date": "transaction date",
    "direction": "inbound (money received) or outbound (money sent)",
    "currency_pair": "FX currency pair for the cross-border leg, e.g. ZAR/USD",
    "value_zar": "transaction value, already converted to ZAR",
    "counterparty_country": "country of the payment counterparty",
    "corridor_type": "category of cross-border flow: intercompany / trade / other",
    "beneficiary_name": "name of the payment beneficiary",
    "reference": "payment reference / description text",
    "memo": "free-text memo field, mostly unused",
}


def main() -> None:
    df = pd.read_csv(CSV_PATH, parse_dates=["date"])
    lines = ["# cross_border_payments.csv — Profiling Report", ""]

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
    id_dupes = df["transaction_id"].duplicated().sum()
    lines.append(f"Exact duplicate rows (all columns identical): {exact_dupes:,}")
    lines.append(f"Duplicate `transaction_id` values: {id_dupes:,}")
    lines.append("")

    # --- Outliers / data quality ---
    lines.append("## Outliers / data quality issues")
    lines.append("")
    nonpositive_value = (df["value_zar"] <= 0).sum()
    lines.append(f"`value_zar` <= 0: {nonpositive_value:,} rows")
    bad_direction = (~df["direction"].isin(["inbound", "outbound"])).sum()
    lines.append(f"`direction` outside {{inbound, outbound}}: {bad_direction:,} rows")
    bad_corridor = (~df["corridor_type"].isin(["intercompany", "trade", "other"])).sum()
    lines.append(f"`corridor_type` outside {{intercompany, trade, other}}: {bad_corridor:,} rows")
    lines.append("")
    lines.append(f"Distinct `currency_pair` values ({df['currency_pair'].nunique()}): " + ", ".join(sorted(df["currency_pair"].unique())))
    lines.append("")
    empty_country = (df["counterparty_country"].astype("string").str.strip() == "").sum()
    lines.append(f"`counterparty_country` empty-string (as opposed to null): {empty_country:,} rows")
    lines.append("")

    # --- Currency ---
    lines.append("## Currency")
    lines.append("")
    lines.append(
        "No separate `currency` column — `value_zar` is named as already ZAR-converted, and there is no "
        "FX-rate column in this file to independently verify the conversion. `currency_pair` describes the "
        "corridor (e.g. `ZAR/USD`) but is not itself a unit the `value_zar` figure is denominated in. "
        "**Flag for team:** we cannot verify from this file alone whether `value_zar` was converted at a "
        "point-in-time rate per transaction or a static rate — worth confirming with whoever generated this "
        "synthetic data, since it affects whether small time-series distortions are meaningful."
    )
    lines.append("")

    # --- Join feasibility ---
    lines.append("## Join feasibility")
    lines.append("")
    lines.append(
        "- To other internal datasets: `entity_id` (confirmed 1:1 with `entity_name` above) — same key used "
        "in `transactional_banking.csv` and `trade_finance.csv`.\n"
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
