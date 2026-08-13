"""
Internal wallet share build - Step 4 (PLAN.md Section 5).

Implements docs/superpowers/specs/2026-08-08-pillar-spend-split-design.md exactly:
  - trailing 12 months only (2025-07-01 -> 2026-06-30)
  - gross flow (both directions summed, not net)
  - 3 pillars: Transactional Banking, Trade & Working Capital, Foreign / Cross-Border

Inputs (repo root, gitignored - not committed, must exist locally):
  transactional_banking.csv
  cross_border_payments.csv
  trade_finance.csv

Outputs:
  hackathon-finreports/_extracted/pillar_spend_long.csv   (long form - source of truth)
  hackathon-finreports/_extracted/pillar_spend_wide.csv   (wide form - one row per client)
"""

import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "hackathon-finreports" / "_extracted"

WINDOW_START = "2025-07-01"
WINDOW_END = "2026-06-30"

PILLAR_NAMES = {
    "transactional_banking": "Transactional Banking",
    "trade_working_capital": "Trade & Working Capital",
    "foreign_cross_border": "Foreign / Cross-Border",
}


def build_pillar_rows(df: pd.DataFrame, pillar_key: str, amount_col: str) -> pd.DataFrame:
    windowed = df[(df["date"] >= WINDOW_START) & (df["date"] <= WINDOW_END)]
    grouped = (
        windowed.groupby(["entity_id", "entity_name", "sector"])[amount_col]
        .sum()
        .reset_index()
        .rename(columns={amount_col: "internal_spend_zar"})
    )
    grouped["pillar"] = PILLAR_NAMES[pillar_key]
    grouped["pillar_key"] = pillar_key
    grouped["transaction_count"] = (
        windowed.groupby(["entity_id", "entity_name", "sector"]).size().values
    )
    return grouped


def main():
    print("Loading raw internal datasets (this may take a minute for transactional_banking.csv)...")
    txn = pd.read_csv(ROOT / "transactional_banking.csv", parse_dates=["date"])
    xborder = pd.read_csv(ROOT / "cross_border_payments.csv", parse_dates=["date"])
    trade = pd.read_csv(ROOT / "trade_finance.csv", parse_dates=["date"])

    # Cleaning per the profiling report's findings, before aggregation.
    txn["currency"] = txn["currency"].str.upper()
    txn = txn.drop_duplicates()
    xborder = xborder.drop_duplicates()
    trade = trade.drop_duplicates()

    pillar_1 = build_pillar_rows(txn, "transactional_banking", "amount_zar")
    pillar_2 = build_pillar_rows(trade, "trade_working_capital", "value_zar")
    pillar_3 = build_pillar_rows(xborder, "foreign_cross_border", "value_zar")

    pillar_spend_long = pd.concat([pillar_1, pillar_2, pillar_3], ignore_index=True)
    pillar_spend_long = pillar_spend_long.sort_values(["entity_name", "pillar"]).reset_index(drop=True)

    long_path = OUT_DIR / "pillar_spend_long.csv"
    pillar_spend_long.to_csv(long_path, index=False)
    print(f"Wrote {len(pillar_spend_long)} rows to {long_path}")

    pillar_spend_wide = pillar_spend_long.pivot(
        index=["entity_id", "entity_name", "sector"],
        columns="pillar",
        values="internal_spend_zar",
    ).reset_index()

    pillar_cols = list(PILLAR_NAMES.values())
    # Any entity with zero activity in a pillar during the trailing-12-month window
    # would show up as NaN from the pivot (no group at all), not a real gap - flag rather
    # than silently zero-fill.
    missing = pillar_spend_wide[pillar_cols].isna().sum().sum()
    if missing:
        print(f"WARNING: {missing} entity-pillar combinations have no rows in the trailing-12-month window - filling 0 but verify this isn't a data gap.")
    pillar_spend_wide[pillar_cols] = pillar_spend_wide[pillar_cols].fillna(0)

    pillar_spend_wide["total_internal_spend_zar"] = pillar_spend_wide[pillar_cols].sum(axis=1)
    for col in pillar_cols:
        pillar_spend_wide[f"{col} % of total"] = (
            pillar_spend_wide[col] / pillar_spend_wide["total_internal_spend_zar"]
        ).round(4)

    wide_path = OUT_DIR / "pillar_spend_wide.csv"
    pillar_spend_wide.to_csv(wide_path, index=False)
    print(f"Wrote {len(pillar_spend_wide)} rows to {wide_path}")
    print(f"\nWindow: {WINDOW_START} -> {WINDOW_END} (trailing 12 months, per approved spec)")
    print(f"Total internal spend across all clients/pillars: R{pillar_spend_wide['total_internal_spend_zar'].sum():,.0f}")


if __name__ == "__main__":
    main()
