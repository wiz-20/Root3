"""
Anomaly detection - GenAI use case #2 (PLAN.md: "client briefing notes, NL querying, anomaly
explanations"). Deliberately split into two separate, auditable stages rather than one LLM
call over raw numbers:

  Stage 1 (this script, pure code): scans every client x pillar cell in wallet_model.csv
  (60 cells: 20 clients x 3 pillars, plus the blended total) against a fixed set of
  deterministic rules and writes every match to anomalies_detected.csv. Nothing here is
  probabilistic or model-generated - it's the same kind of rule a human analyst would apply
  by eye, just applied exhaustively and consistently across all 60 cells instead of
  eyeballing a spreadsheet and hoping nothing gets missed.

  Stage 2 (docs/genai/anomaly_explanations.md, GenAI-written): takes ONLY the structured
  output of stage 1 - never the raw wallet_model.csv - and writes the natural-language
  "why does this happen and what should a banker do about it" synthesis, grouped by anomaly
  type rather than one paragraph per cell (60 near-duplicate paragraphs would bury the 5-6
  actually distinct patterns in the data).

This split matters for grounding: an LLM asked to "find anomalies" in a raw table can miss
real ones or invent fake ones. An LLM asked to "explain already-detected anomalies" from a
fixed, code-generated list can't do either - its only job is narrative synthesis over facts
that already exist.

Rules (all thresholds and definitions stated here, not inferred by the model):
  1. proxy_breakdown       - pillar share % > 100 (internal capture exceeds the top-down
                              wallet proxy) - pulled directly from the gap_flag_pillarN
                              columns already produced by scripts/build_wallet_model.py.
  2. wallet_unavailable    - a pillar's external wallet proxy could not be computed at all
                              (NaN) - real internal activity may still exist for that pillar.
  3. reliability_insufficient - top_down_reliability == "insufficient" (Group financials not
                              disclosed in the source AFS at all).
  4. scale_mismatch_low_reliability - top_down_reliability == "low" (foreign-currency,
                              consolidated group reporter) AND total_gap_zar_m is in the top
                              quartile of all rows - the "naive-model trap" pattern (Glencore-
                              style trillion-Rand gaps that are consolidation artifacts, not
                              real findings).
  5. statistical_outlier  - blended_share_pct is >1.5 standard deviations from the mean of
                              its own reliability peer group (moderate-reliability ZAR
                              reporters vs. low-reliability foreign reporters kept separate,
                              since they're not comparable distributions) - flags both
                              unusually high (str_outlier_high) and unusually low
                              (str_outlier_low) share, in either direction.

Output: hackathon-finreports/_extracted/anomalies_detected.csv
"""

import numpy as np
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXTRACTED_DIR = ROOT / "hackathon-finreports" / "_extracted"

GAP_TOP_QUARTILE_THRESHOLD = None  # computed at runtime
Z_SCORE_THRESHOLD = 1.5


def main():
    df = pd.read_csv(EXTRACTED_DIR / "wallet_model.csv")
    anomalies = []

    # --- Rule 1: proxy breakdown (share % > 100, i.e. internal exceeds top-down proxy) ---
    for pillar in [1, 2, 3]:
        flag_col = f"gap_flag_pillar{pillar}"
        share_col = f"share_pct_pillar{pillar}"
        for _, row in df[df[flag_col].astype(str).str.contains("exceeds top-down proxy", na=False)].iterrows():
            anomalies.append({
                "entity_name": row["entity_name"], "pillar": pillar, "rule": "proxy_breakdown",
                "detail": f"share={row[share_col]}%, internal=R{row[f'internal_pillar{pillar}_zar_m']:.1f}m, "
                          f"wallet=R{row[f'total_wallet_pillar{pillar}_zar_m']:.1f}m",
            })

    # --- Rule 2: wallet unavailable for a pillar ---
    for pillar in [1, 2, 3]:
        wallet_col = f"total_wallet_pillar{pillar}_zar_m"
        internal_col = f"internal_pillar{pillar}_zar_m"
        for _, row in df[df[wallet_col].isna()].iterrows():
            anomalies.append({
                "entity_name": row["entity_name"], "pillar": pillar, "rule": "wallet_unavailable",
                "detail": f"internal activity=R{row[internal_col]:.1f}m exists but no external wallet estimate available",
            })

    # --- Rule 3: insufficient reliability ---
    for _, row in df[df["top_down_reliability"].str.startswith("insufficient")].iterrows():
        anomalies.append({
            "entity_name": row["entity_name"], "pillar": "blended", "rule": "reliability_insufficient",
            "detail": "Group-level financials not disclosed in source AFS - blended total not computed",
        })

    # --- Rule 4: scale mismatch for low-reliability (foreign currency) rows ---
    q75 = df["total_gap_zar_m"].quantile(0.75)
    low_rel = df[df["top_down_reliability"].str.startswith("low") & (df["total_gap_zar_m"] >= q75)]
    for _, row in low_rel.iterrows():
        anomalies.append({
            "entity_name": row["entity_name"], "pillar": "blended", "rule": "scale_mismatch_low_reliability",
            "detail": f"total_gap=R{row['total_gap_zar_m']/1000:.1f}bn on a foreign-currency consolidated group report "
                      f"(top quartile of all 20 clients, threshold=R{q75/1000:.1f}bn)",
        })

    # --- Rule 5: statistical outliers within reliability peer group ---
    for tier_prefix in ["moderate", "low"]:
        peer_group = df[df["top_down_reliability"].str.startswith(tier_prefix)].copy()
        mu, sigma = peer_group["blended_share_pct"].mean(), peer_group["blended_share_pct"].std()
        peer_group["z"] = (peer_group["blended_share_pct"] - mu) / sigma
        for _, row in peer_group[peer_group["z"].abs() > Z_SCORE_THRESHOLD].iterrows():
            direction = "high" if row["z"] > 0 else "low"
            anomalies.append({
                "entity_name": row["entity_name"], "pillar": "blended", "rule": f"statistical_outlier_{direction}",
                "detail": f"blended_share={row['blended_share_pct']}% vs peer-group ({tier_prefix}-reliability, n={len(peer_group)}) "
                          f"mean={mu:.1f}%, std={sigma:.1f}%, z={row['z']:.2f}",
            })

    out = pd.DataFrame(anomalies)
    out_path = EXTRACTED_DIR / "anomalies_detected.csv"
    out.to_csv(out_path, index=False)

    print(f"Detected {len(out)} anomalies across {out['entity_name'].nunique()} clients, {out['rule'].nunique()} rule types")
    print(out["rule"].value_counts().to_string())
    print(f"\nWritten to {out_path}")


if __name__ == "__main__":
    main()
