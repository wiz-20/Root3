"""
Multi-year wallet model - ML training table for "predict Share of Wallet %" from a client's
financial profile.

Same top-down Total Wallet proxy and reliability tiering as scripts/build_wallet_model.py, but
computed per (entity_name, fiscal_year) instead of once per client, using the fiscal-year-
aligned internal pillar spend from scripts/build_pillar_spend_multiyear.py. This gives up to
43 real training rows (one per company-year) instead of 20, since both internal capture and
external financials genuinely vary year to year here - unlike pairing 43 financial years
against a single trailing-12-month internal snapshot, which would just repeat the same 20
internal numbers 2-3x with no new information.

Inputs:
  hackathon-finreports/_extracted/pillar_spend_multiyear_wide.csv   (internal, per company-year)
  hackathon-finreports/_extracted/financials_multiyear_ml.csv       (external features, per company-year)

Output:
  hackathon-finreports/_extracted/wallet_model_multiyear.csv        (ML-ready: features + share % targets)
"""

import numpy as np
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXTRACTED_DIR = ROOT / "hackathon-finreports" / "_extracted"


def main():
    internal = pd.read_csv(EXTRACTED_DIR / "pillar_spend_multiyear_wide.csv")
    internal = internal.rename(columns={
        "Transactional Banking": "internal_pillar1_zar_m",
        "Trade & Working Capital": "internal_pillar2_zar_m",
        "Foreign / Cross-Border": "internal_pillar3_zar_m",
    })
    for col in ["internal_pillar1_zar_m", "internal_pillar2_zar_m", "internal_pillar3_zar_m"]:
        internal[col] = internal[col] / 1e6

    fin = pd.read_csv(EXTRACTED_DIR / "financials_multiyear_ml.csv")

    df = fin.merge(internal, on=["entity_name", "fiscal_year"], how="inner")
    print(f"Merged {len(df)} company-year rows (financials: {len(fin)}, internal: {len(internal)})")

    df["pillar1_proxy_note"] = np.where(
        df["cost_of_sales_zar_m"].isna(),
        "revenue only - no disclosed cost_of_sales line for this sector/year",
        "revenue + cost_of_sales",
    )
    df["total_wallet_pillar1_zar_m"] = df["revenue_zar_m"].fillna(0) + df["cost_of_sales_zar_m"].fillna(0)
    df.loc[df["revenue_zar_m"].isna(), "total_wallet_pillar1_zar_m"] = np.nan

    wc_cols = ["inventory_zar_m", "trade_receivables_zar_m", "trade_payables_zar_m"]
    df["total_wallet_pillar2_zar_m"] = df[wc_cols].sum(axis=1, min_count=1)

    df["total_wallet_pillar3_zar_m"] = np.where(
        df["foreign_revenue_pct"].notna(),
        df["revenue_zar_m"] * (df["foreign_revenue_pct"] / 100),
        np.nan,
    )
    df["pillar3_estimated"] = df["foreign_revenue_pct"].notna()

    for i, internal_col in zip([1, 2, 3], ["internal_pillar1_zar_m", "internal_pillar2_zar_m", "internal_pillar3_zar_m"]):
        wallet_col = f"total_wallet_pillar{i}_zar_m"
        # A disclosed 0% foreign-revenue split (Shaftesbury: "0" is a real disclosed value, not
        # missing) makes the wallet proxy exactly 0 while real internal cross-border activity
        # still exists (intercompany/treasury flows despite no foreign trading revenue) -
        # dividing by that zero would silently produce inf, which breaks any ML pipeline reading
        # this CSV. NaN it out and flag explicitly instead of leaving an infinite "share".
        zero_wallet = df[wallet_col] == 0
        share = df[internal_col] / df[wallet_col] * 100
        df[f"share_pct_pillar{i}"] = share.where(~zero_wallet, np.nan).round(2)
        df[f"gap_zar_m_pillar{i}"] = (df[wallet_col] - df[internal_col]).round(1)
        df[f"zero_wallet_flag_pillar{i}"] = zero_wallet

    df["top_down_reliability"] = np.where(
        df["total_wallet_pillar1_zar_m"].isna(),
        "insufficient - revenue not disclosed this year",
        np.where(
            df["currency"] != "ZAR",
            "low - foreign reporting currency, group figures may include material non-SA operations",
            "moderate - ZAR reporter, financials are for the SA-listed entity itself",
        ),
    )

    out_cols = [
        "entity_name", "canonical", "fiscal_year", "sector" if "sector" in df.columns else None,
        "currency", "top_down_reliability", "partial_window",
        "revenue_zar_m", "cost_of_sales_zar_m", "operating_expenses_zar_m",
        "trade_receivables_zar_m", "trade_payables_zar_m", "inventory_zar_m",
        "foreign_revenue_pct", "fx_gains_losses_zar_m",
        "internal_pillar1_zar_m", "total_wallet_pillar1_zar_m", "share_pct_pillar1", "gap_zar_m_pillar1", "pillar1_proxy_note",
        "internal_pillar2_zar_m", "total_wallet_pillar2_zar_m", "share_pct_pillar2", "gap_zar_m_pillar2",
        "internal_pillar3_zar_m", "total_wallet_pillar3_zar_m", "share_pct_pillar3", "gap_zar_m_pillar3", "pillar3_estimated", "zero_wallet_flag_pillar3",
    ]
    out_cols = [c for c in out_cols if c and c in df.columns]
    out = df[out_cols].sort_values(["entity_name", "fiscal_year"])

    out_path = EXTRACTED_DIR / "wallet_model_multiyear.csv"
    out.to_csv(out_path, index=False)
    print(f"Wrote {len(out)} rows to {out_path}")

    print("\n--- Label coverage (for ML target selection) ---")
    print(f"share_pct_pillar1 (Transactional): {out['share_pct_pillar1'].notna().sum()}/{len(out)}")
    print(f"share_pct_pillar2 (Trade & WC):     {out['share_pct_pillar2'].notna().sum()}/{len(out)}")
    print(f"share_pct_pillar3 (Cross-Border):   {out['share_pct_pillar3'].notna().sum()}/{len(out)} - thin, foreign_revenue_pct rarely disclosed")

    print("\n--- Reliability tier counts ---")
    print(out["top_down_reliability"].value_counts().to_string())


if __name__ == "__main__":
    main()
