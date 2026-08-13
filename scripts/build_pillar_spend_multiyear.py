"""
Fiscal-year-aligned internal pillar split - multi-year extension for ML training.

scripts/build_pillar_spend.py computes ONE trailing-12-month internal snapshot per client
(2025-07-01 -> 2026-06-30), per the approved spec. That's correct for "current Syn Bank
share", but it means pairing it with the 43-row financials_multiyear_ml.csv panel doesn't
actually buy any extra independent samples for a "predict Share %" ML target - internal
spend would be the same 20 numbers repeated across each company's 2-3 financial years.

This script instead computes internal pillar spend separately for EACH of the 43
company-years in financials_multiyear.csv, using a trailing-12-month window ending at
THAT year's actual disclosed fiscal_year_end - so both internal (numerator) and external
(denominator) genuinely vary year to year, giving up to 43 real training rows instead of 20.

Inputs:
  transactional_banking.csv, cross_border_payments.csv, trade_finance.csv (repo root, raw)
  hackathon-finreports/_extracted/financials_multiyear.csv (for entity_name, fiscal_year, fiscal_year_end)

Outputs:
  hackathon-finreports/_extracted/pillar_spend_multiyear_long.csv
  hackathon-finreports/_extracted/pillar_spend_multiyear_wide.csv

Known limitation: raw internal data only covers 2023-07-01 -> 2026-06-30. 3 of 43
company-years (Naspers/Prosus/Vodacom FY2024, all 31-March fiscal year end) need a window
starting 2023-04-01, before the data begins - clipped to the available range and flagged
`partial_window=True` (9 months of coverage instead of 12) rather than silently treated as
a full year.
"""

import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXTRACTED_DIR = ROOT / "hackathon-finreports" / "_extracted"

DATA_START = pd.Timestamp("2023-07-01")
DATA_END = pd.Timestamp("2026-06-30")

PILLAR_NAMES = {
    "transactional_banking": "Transactional Banking",
    "trade_working_capital": "Trade & Working Capital",
    "foreign_cross_border": "Foreign / Cross-Border",
}


def main():
    print("Loading raw internal datasets...")
    txn = pd.read_csv(ROOT / "transactional_banking.csv", parse_dates=["date"])
    xborder = pd.read_csv(ROOT / "cross_border_payments.csv", parse_dates=["date"])
    trade = pd.read_csv(ROOT / "trade_finance.csv", parse_dates=["date"])

    txn["currency"] = txn["currency"].str.upper()
    txn = txn.drop_duplicates()
    xborder = xborder.drop_duplicates()
    trade = trade.drop_duplicates()

    datasets = {
        "transactional_banking": (txn, "amount_zar"),
        "trade_working_capital": (trade, "value_zar"),
        "foreign_cross_border": (xborder, "value_zar"),
    }

    fin = pd.read_csv(EXTRACTED_DIR / "financials_multiyear.csv")
    fin = fin.dropna(subset=["fiscal_year_end"]).copy()
    fin["fye"] = pd.to_datetime(fin["fiscal_year_end"], format="%d %B %Y")
    fin["window_start_raw"] = fin["fye"] - pd.DateOffset(years=1) + pd.Timedelta(days=1)
    fin["window_start"] = fin["window_start_raw"].clip(lower=DATA_START)
    fin["window_end"] = fin["fye"].clip(upper=DATA_END)
    fin["partial_window"] = (fin["window_start_raw"] < DATA_START) | (fin["fye"] > DATA_END)
    fin["window_days"] = (fin["window_end"] - fin["window_start"]).dt.days + 1

    long_rows = []
    for _, r in fin.iterrows():
        entity_name = r["entity_name"]
        for pillar_key, (df, amount_col) in datasets.items():
            windowed = df[
                (df["entity_name"] == entity_name)
                & (df["date"] >= r["window_start"])
                & (df["date"] <= r["window_end"])
            ]
            long_rows.append({
                "entity_name": entity_name,
                "fiscal_year": r["fiscal_year"],
                "pillar": PILLAR_NAMES[pillar_key],
                "pillar_key": pillar_key,
                "internal_spend_zar": windowed[amount_col].sum(),
                "transaction_count": len(windowed),
                "window_start": r["window_start"].date().isoformat(),
                "window_end": r["window_end"].date().isoformat(),
                "window_days": r["window_days"],
                "partial_window": r["partial_window"],
            })

    long_df = pd.DataFrame(long_rows).sort_values(["entity_name", "fiscal_year", "pillar"])
    long_path = EXTRACTED_DIR / "pillar_spend_multiyear_long.csv"
    long_df.to_csv(long_path, index=False)
    print(f"Wrote {len(long_df)} rows to {long_path}")

    pillar_cols = list(PILLAR_NAMES.values())
    wide_df = long_df.pivot_table(
        index=["entity_name", "fiscal_year", "window_start", "window_end", "partial_window"],
        columns="pillar",
        values="internal_spend_zar",
    ).reset_index()
    wide_df["total_internal_spend_zar"] = wide_df[pillar_cols].sum(axis=1)

    wide_path = EXTRACTED_DIR / "pillar_spend_multiyear_wide.csv"
    wide_df.to_csv(wide_path, index=False)
    print(f"Wrote {len(wide_df)} rows to {wide_path}")

    n_partial = wide_df["partial_window"].sum()
    print(f"\n{n_partial}/{len(wide_df)} rows have a partial (<12mo) window - see column `partial_window`.")
    print(wide_df[wide_df["partial_window"]][["entity_name", "fiscal_year", "window_start", "window_end"]].to_string(index=False))


if __name__ == "__main__":
    main()
