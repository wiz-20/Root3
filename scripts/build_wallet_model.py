"""
Wallet model - PLAN.md Section 5 steps 5-7 ("External wallet estimation", "Wallet model",
"Opportunity ranking").

Combines:
  - pillar_spend_wide.csv        (internal, Syn Bank captured gross flow, trailing 12mo, ZAR)
  - financials_extracted.csv     (external, most-current-FY financials per company, ZAR millions)
  - financials_multiyear_ml.csv  (external, numeric foreign_revenue_pct where disclosed)

into a top-down Total Wallet estimate per pillar, then Syn Bank Share % and Gap.

**Scope decision (documented limitation):** bottom-up competitor evidence (SARB BA900,
JSE SENS, borrowing notes) was cut from this pass given the solo/time-constrained build -
this is a top-down financials-based proxy only. See the "Assumptions & Limitations" printout
at the end of this script and carry it into the methodology appendix verbatim.

Top-down Total Wallet proxy per pillar (ZAR millions, all from the company's own most current
disclosed financials):
  Pillar 1 - Transactional Banking:  revenue + cost_of_sales (revenue only where cost_of_sales
             is structurally absent for the sector - insurers/REITs/telcos/holding cos - not
             re-guessed; this mirrors the P&L-driven cash-in/cash-out that flows through a
             transactional banking relationship).
  Pillar 2 - Trade & Working Capital: inventory + trade_receivables + trade_payables (the
             working-capital base that trade-finance instruments could finance).
  Pillar 3 - Foreign / Cross-Border: revenue x foreign_revenue_pct, only for the 4/20 companies
             where a numeric foreign-revenue split was actually disclosed in the source
             document (MTN, Naspers, Sanlam, Vodacom) - left as "not estimated" for the other
             16 rather than fabricating a split. This is the single biggest gap in this pass;
             flagged explicitly rather than silently zero-filled.

Outputs:
  hackathon-finreports/_extracted/wallet_model.csv        (one row per client, all 3 pillars + total)
  hackathon-finreports/_extracted/opportunity_ranking.csv (clients ranked by total Rand gap)
"""

import numpy as np
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXTRACTED_DIR = ROOT / "hackathon-finreports" / "_extracted"


def main():
    pillar_wide = pd.read_csv(EXTRACTED_DIR / "pillar_spend_wide.csv")
    financials = pd.read_csv(EXTRACTED_DIR / "financials_extracted.csv")
    multiyear_ml = pd.read_csv(EXTRACTED_DIR / "financials_multiyear_ml.csv")

    # Internal pillar columns are in raw ZAR (trailing 12mo gross flow) - convert to ZAR
    # millions so every number in this model is in the same unit as the financials data.
    pillar_wide = pillar_wide.rename(columns={
        "Transactional Banking": "internal_pillar1_zar_m",
        "Trade & Working Capital": "internal_pillar2_zar_m",
        "Foreign / Cross-Border": "internal_pillar3_zar_m",
    })
    for col in ["internal_pillar1_zar_m", "internal_pillar2_zar_m", "internal_pillar3_zar_m"]:
        pillar_wide[col] = pillar_wide[col] / 1e6

    foreign_pct = (
        multiyear_ml[multiyear_ml["fiscal_year"] == 2025][["entity_name", "foreign_revenue_pct"]]
        .dropna(subset=["foreign_revenue_pct"])
        .drop_duplicates(subset="entity_name")
    )

    fin = financials[[
        "entity_name", "fiscal_year", "data_vintage_flag", "currency",
        "revenue_zar_millions", "cost_of_sales_zar_millions",
        "trade_receivables_zar_millions", "trade_payables_zar_millions", "inventory_zar_millions",
    ]].merge(foreign_pct, on="entity_name", how="left")

    df = pillar_wide.merge(fin, on="entity_name", how="left")

    # --- Pillar 1: Transactional Banking wallet proxy ---
    df["pillar1_cost_component"] = df["cost_of_sales_zar_millions"]
    df["pillar1_proxy_note"] = np.where(
        df["cost_of_sales_zar_millions"].isna(),
        "revenue only - no disclosed cost_of_sales line for this sector (insurer/REIT/telco/holding co)",
        "revenue + cost_of_sales",
    )
    df["total_wallet_pillar1_zar_m"] = df["revenue_zar_millions"].fillna(0) + df["cost_of_sales_zar_millions"].fillna(0)
    df.loc[df["revenue_zar_millions"].isna(), "total_wallet_pillar1_zar_m"] = np.nan

    # --- Pillar 2: Trade & Working Capital wallet proxy ---
    wc_cols = ["inventory_zar_millions", "trade_receivables_zar_millions", "trade_payables_zar_millions"]
    df["total_wallet_pillar2_zar_m"] = df[wc_cols].sum(axis=1, min_count=1)

    # --- Pillar 3: Foreign / Cross-Border wallet proxy ---
    df["total_wallet_pillar3_zar_m"] = np.where(
        df["foreign_revenue_pct"].notna(),
        df["revenue_zar_millions"] * (df["foreign_revenue_pct"] / 100),
        np.nan,
    )
    df["pillar3_estimated"] = df["foreign_revenue_pct"].notna()

    # --- Share % and Gap per pillar ---
    for i, internal_col in zip([1, 2, 3], ["internal_pillar1_zar_m", "internal_pillar2_zar_m", "internal_pillar3_zar_m"]):
        wallet_col = f"total_wallet_pillar{i}_zar_m"
        df[f"share_pct_pillar{i}"] = (df[internal_col] / df[wallet_col] * 100).round(1)
        df[f"gap_zar_m_pillar{i}"] = (df[wallet_col] - df[internal_col]).round(1)
        # Internal (gross, both directions) exceeding a net P&L-based proxy is a real,
        # explainable signal (e.g. high treasury/FX turnover) - flag it, don't hide it.
        df[f"gap_flag_pillar{i}"] = np.where(
            df[wallet_col].isna(), "external estimate unavailable",
            np.where(df[f"gap_zar_m_pillar{i}"] < 0, "internal flow exceeds top-down proxy - see notes", ""),
        )

    df["total_wallet_zar_m"] = df[["total_wallet_pillar1_zar_m", "total_wallet_pillar2_zar_m", "total_wallet_pillar3_zar_m"]].sum(axis=1, min_count=1)
    df["total_internal_zar_m"] = df["internal_pillar1_zar_m"] + df["internal_pillar2_zar_m"] + df["internal_pillar3_zar_m"]
    df["blended_share_pct"] = (df["total_internal_zar_m"] / df["total_wallet_zar_m"] * 100).round(1)
    df["total_gap_zar_m"] = (df["total_wallet_zar_m"] - df["total_internal_zar_m"]).round(1)

    # --- Reliability tiering (the part that matters before anyone reads a Rand figure) ---
    # Two known ways this top-down proxy misleads, both flagged explicitly rather than hidden:
    #   (a) Pillar 1 external wallet missing entirely (Bidvest: only company-level AFS found,
    #       not Group) - a partial blended total here would be dramatically understated, so
    #       the blended total is voided (NaN) rather than computed from 2 of 3 pillars.
    #   (b) Foreign-currency reporters (9/20) are consolidated GLOBAL group figures - for a
    #       multinational miner/trader, group revenue reflects worldwide operations, not the
    #       SA-specific banking relationship Syn Bank could plausibly capture. The resulting
    #       Rand gap for these rows is directional (very low % share is real) but the absolute
    #       Rand figure should not be read literally or summed into a portfolio total.
    df.loc[df["total_wallet_pillar1_zar_m"].isna(), ["total_wallet_zar_m", "blended_share_pct", "total_gap_zar_m"]] = np.nan

    df["top_down_reliability"] = np.where(
        df["total_wallet_pillar1_zar_m"].isna(),
        "insufficient - Group revenue not disclosed in source AFS; blended total not computed",
        np.where(
            df["currency"] != "ZAR",
            "low - foreign reporting currency; consolidated GROUP figures likely include material non-SA operations, treat Rand gap as directional/% only, not literal",
            "moderate - ZAR reporter, financials are for the SA-listed entity itself",
        ),
    )

    out_cols = [
        "entity_id", "entity_name", "sector", "fiscal_year", "data_vintage_flag", "currency", "top_down_reliability",
        "internal_pillar1_zar_m", "total_wallet_pillar1_zar_m", "share_pct_pillar1", "gap_zar_m_pillar1", "pillar1_proxy_note", "gap_flag_pillar1",
        "internal_pillar2_zar_m", "total_wallet_pillar2_zar_m", "share_pct_pillar2", "gap_zar_m_pillar2", "gap_flag_pillar2",
        "internal_pillar3_zar_m", "total_wallet_pillar3_zar_m", "share_pct_pillar3", "gap_zar_m_pillar3", "pillar3_estimated", "gap_flag_pillar3",
        "total_internal_zar_m", "total_wallet_zar_m", "blended_share_pct", "total_gap_zar_m",
    ]
    model = df[out_cols].sort_values("total_gap_zar_m", ascending=False, na_position="last")
    model_path = EXTRACTED_DIR / "wallet_model.csv"
    model.to_csv(model_path, index=False)
    print(f"Wrote {len(model)} rows to {model_path}")

    ranking = model[[
        "entity_name", "sector", "data_vintage_flag", "top_down_reliability",
        "total_internal_zar_m", "total_wallet_zar_m", "blended_share_pct", "total_gap_zar_m",
    ]].copy()
    ranking.insert(0, "rank", range(1, len(ranking) + 1))
    ranking_path = EXTRACTED_DIR / "opportunity_ranking.csv"
    ranking.to_csv(ranking_path, index=False)
    print(f"Wrote {len(ranking)} rows to {ranking_path}")

    actionable = ranking[ranking["top_down_reliability"].str.startswith("moderate")]
    print("\n--- Top 5 opportunities, ACTIONABLE tier only (ZAR reporters - Rand gap is literal, not just directional) ---")
    print(actionable.head(5).to_string(index=False))
    print("\n--- Full ranking (includes low-reliability multinational rows - % share is real, Rand gap is directional only) ---")
    print(ranking.head(5).to_string(index=False))

    print("\n--- Coverage ---")
    print(f"Pillar 1 (transactional) wallet estimated for: {df['total_wallet_pillar1_zar_m'].notna().sum()}/20")
    print(f"Pillar 2 (trade/WC) wallet estimated for:       {df['total_wallet_pillar2_zar_m'].notna().sum()}/20")
    print(f"Pillar 3 (cross-border) wallet estimated for:   {df['total_wallet_pillar3_zar_m'].notna().sum()}/20 (only where foreign revenue % was disclosed)")

    print("\n--- Assumptions & Limitations (carry into methodology appendix) ---")
    print("1. Top-down only - no bottom-up competitor evidence (SARB BA900, JSE SENS, borrowing")
    print("   notes) in this pass. Total Wallet is a financials-based proxy, not a directly")
    print("   observed competitor-inclusive figure. This likely under- or over-states the true")
    print("   wallet in either direction and should be stated as a limitation, not a precision claim.")
    print("2. Pillar 3 (Foreign/Cross-Border) wallet is only estimated for the 4/20 companies")
    print("   with a disclosed numeric foreign-revenue split (MTN, Naspers, Sanlam, Vodacom).")
    print("   The other 16 have real internal cross-border activity but no external wallet")
    print("   estimate to compare it against yet - flagged 'external estimate unavailable',")
    print("   not silently zero.")
    print("3. Internal figures are trailing-12-month gross flow (both directions); external")
    print("   proxies are single-fiscal-year P&L/balance-sheet figures - a negative gap (internal")
    print("   > proxy) is a plausible real signal (e.g. treasury/FX turnover) rather than an error,")
    print("   flagged per-row rather than clipped to zero.")
    print("4. cost_of_sales is structurally absent for insurers/REITs/telcos/holding companies -")
    print("   Pillar 1 proxy falls back to revenue-only for those 8 rows rather than fabricating a cost figure.")


if __name__ == "__main__":
    main()
