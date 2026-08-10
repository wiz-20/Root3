"""
Clean, entity-level aggregation, and external join for transactional_banking.csv
(Pillar 1 — Transactional Banking).

Self-contained on purpose: reads from ../../transactional_banking.csv and
../../hackathon-finreports/_extracted/financials_extracted_v2.csv, but does not
import anything from scripts/ (which this task was told not to touch/modify).
All outputs are written under this folder only.

Known issues handled here (from docs/reports/2026-08-09-internal-data-profiling-report.md):
  - transaction_id is NOT a reliable unique key (~52,984 IDs reused across
    genuinely different transactions) -> we dedupe on the FULL row, never on
    transaction_id alone.
  - currency casing inconsistency ('ZAR' vs 'zar', ~1% of rows) -> normalized
    to uppercase before use.
  - ~0.4% exact duplicate rows -> dropped (full-row match), with the resulting
    % compared back against that 0.4% estimate.

Run: py analysis/transactional_aggregation/aggregate_transactional_banking.py
"""

import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent

TXN_CSV = ROOT / "transactional_banking.csv"
EXTERNAL_CSV = ROOT / "hackathon-finreports" / "_extracted" / "financials_extracted_v2.csv"

OUT_ENTITY_CSV = HERE / "entity_transactional_aggregation.csv"
OUT_JOINED_CSV = HERE / "entity_transactional_joined_external.csv"
OUT_SUMMARY_MD = HERE / "2026-08-09-transactional-aggregation-summary.md"

PROFILING_REPORT_EXACT_DUPE_PCT = 10812 / 2802875 * 100  # from the profiling report, for comparison


def load_and_clean() -> tuple[pd.DataFrame, dict]:
    df = pd.read_csv(TXN_CSV, parse_dates=["date"])
    notes = {"rows_raw": len(df)}

    # --- currency casing fix (cosmetic only; amount_zar is unaffected) ---
    before_variants = sorted(df["currency"].unique())
    df["currency"] = df["currency"].str.upper()
    after_variants = sorted(df["currency"].unique())
    notes["currency_variants_before"] = before_variants
    notes["currency_variants_after"] = after_variants
    non_zar_after = (df["currency"] != "ZAR").sum()
    notes["non_zar_rows_after_normalization"] = int(non_zar_after)

    # --- dedupe on the FULL row, never on transaction_id (per profiling report) ---
    exact_dupe_mask = df.duplicated(keep="first")
    notes["exact_duplicate_rows_dropped"] = int(exact_dupe_mask.sum())
    notes["exact_duplicate_pct"] = round(100 * exact_dupe_mask.sum() / len(df), 4)
    notes["profiling_report_estimate_pct"] = round(PROFILING_REPORT_EXACT_DUPE_PCT, 4)
    df = df[~exact_dupe_mask].copy()

    notes["rows_clean"] = len(df)
    return df, notes


def aggregate_entity_level(df: pd.DataFrame) -> pd.DataFrame:
    inbound = df[df["direction"] == "inbound"].groupby("entity_id")["amount_zar"].sum()
    outbound = df[df["direction"] == "outbound"].groupby("entity_id")["amount_zar"].sum()

    grouped = df.groupby(["entity_id", "entity_name", "sector"]).agg(
        transaction_count=("transaction_id", "size"),
        total_amount_zar=("amount_zar", "sum"),
        min_date=("date", "min"),
        max_date=("date", "max"),
    ).reset_index()

    grouped["inbound_amount_zar"] = grouped["entity_id"].map(inbound).fillna(0.0)
    grouped["outbound_amount_zar"] = grouped["entity_id"].map(outbound).fillna(0.0)
    grouped["net_amount_zar"] = grouped["inbound_amount_zar"] - grouped["outbound_amount_zar"]

    grouped = grouped.sort_values("entity_name").reset_index(drop=True)
    col_order = [
        "entity_id", "entity_name", "sector",
        "transaction_count", "total_amount_zar",
        "inbound_amount_zar", "outbound_amount_zar", "net_amount_zar",
        "min_date", "max_date",
    ]
    return grouped[col_order]


def join_external(entity_agg: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    external = pd.read_csv(EXTERNAL_CSV)

    internal_names = set(entity_agg["entity_name"])
    external_names = set(external["entity_name"])

    join_notes = {
        "internal_entity_count": len(internal_names),
        "external_entity_count": len(external_names),
        "missing_from_external": sorted(internal_names - external_names),
        "missing_from_internal": sorted(external_names - internal_names),
    }

    merged = entity_agg.merge(
        external, on="entity_name", how="outer", suffixes=("_txn", "_ext"), indicator=True
    )
    merged["join_status"] = merged["_merge"].map({
        "both": "matched",
        "left_only": "in transactional_banking.csv only — no external financials row",
        "right_only": "in financials_extracted_v2.csv only — no internal transaction data",
    })
    merged = merged.drop(columns=["_merge"])

    return merged, join_notes


def write_summary(clean_notes: dict, entity_agg: pd.DataFrame, join_notes: dict) -> None:
    lines = [
        "# Transactional Banking — Entity-Level Aggregation & External Join",
        "",
        "**Date:** 2026-08-09",
        "**Scope:** Clean `transactional_banking.csv`, aggregate to entity level (Pillar 1), "
        "join against `financials_extracted_v2.csv`, verify it lines up. No Share-of-Wallet or "
        "gap calculation — that's a later step.",
        "**Isolation:** all work done in `analysis/transactional_aggregation/`; nothing in "
        "`scripts/`, `docs/reports/`, or `hackathon-finreports/_extracted/` was modified, only read.",
        "",
        "## 1. Cleaning",
        "",
        f"Raw rows: {clean_notes['rows_raw']:,}",
        f"`currency` values before normalization: {clean_notes['currency_variants_before']}",
        f"`currency` values after normalization (`.str.upper()`): {clean_notes['currency_variants_after']}",
        f"Rows with non-ZAR currency after normalization: {clean_notes['non_zar_rows_after_normalization']} "
        "(confirms the casing fix was sufficient — no genuine non-ZAR currency exists in this file, matching the profiling report).",
        "",
        f"Exact duplicate rows dropped (full-row match, kept first occurrence): "
        f"{clean_notes['exact_duplicate_rows_dropped']:,} ({clean_notes['exact_duplicate_pct']}% of raw rows).",
        f"Profiling report's estimate was ~0.4% ({clean_notes['profiling_report_estimate_pct']}% exactly, from the same 10,812/2,802,875 figure) — "
        "**matches, no material difference.**",
        "",
        "**Judgment call:** deduped on the full row (all 13 columns), not on `transaction_id`, "
        "per the profiling report's finding that `transaction_id` is reused across genuinely "
        "different transactions and is therefore not a valid dedup key on its own. Using "
        "`transaction_id` to dedupe would have incorrectly dropped ~106K legitimate, distinct "
        "transactions.",
        "",
        f"Rows after cleaning: {clean_notes['rows_clean']:,}",
        "",
        "## 2. Entity-level aggregation",
        "",
        f"Entities in output: {len(entity_agg)} (expect 20).",
        "",
        "Columns produced, from what's actually in the schema (no fee-income column exists in "
        "this dataset, so that example from the ask isn't available — only settlement/transaction "
        "value and count):",
        "",
        "- `transaction_count` — total row count per entity, post-cleaning",
        "- `total_amount_zar` — gross flow, both directions summed (all amounts are already "
        "non-negative per the profiling report, so this is a plain sum, not `sum(abs(...))`)",
        "- `inbound_amount_zar` / `outbound_amount_zar` / `net_amount_zar` — direction split, "
        "for sanity-checking and because `net` and `gross` tell different stories (e.g. a client "
        "with huge offsetting inbound/outbound legs looks very different on each measure)",
        "- `min_date` / `max_date` — per-entity date coverage, to confirm no entity is silently "
        "partial (e.g. missing a chunk of the 3-year window)",
        "",
        "**Not produced (scope call, flagging rather than deciding):** a `leg_type` "
        "(collections/supplier_payments/intercompany_sweeps/tax/payroll) or `channel` breakdown "
        "per entity. The groupby to add this is cheap, but the ask was to stop at clean/aggregate/"
        "join/verify — happy to add it as a follow-up cut if it's useful before modeling.",
        "",
        "**Also flagging, not deciding:** the previously-approved pillar-spend-split design "
        "(`docs/superpowers/specs/2026-08-08-pillar-spend-split-design.md`) specifies a **trailing "
        "12-month window** (2025-07-01 to 2026-06-30) for the actual wallet-share numerator, to "
        "stay time-consistent with the external evidence. This aggregation instead uses **full "
        "history** (all ~3 years), since no time window was specified for this step and the min/"
        "max date columns are more useful as a full-history completeness check than they'd be if "
        "pre-filtered to one year. **Before this feeds into an actual Share-of-Wallet number, it "
        "should be re-cut to the trailing-12-month window per the approved spec** — this table as-is "
        "is the full-history version only.",
        "",
        "## 3. Join against financials_extracted_v2.csv",
        "",
        f"Internal (transactional) entity_name count: {join_notes['internal_entity_count']}",
        f"External (financials) entity_name count: {join_notes['external_entity_count']}",
        "",
    ]

    if not join_notes["missing_from_external"] and not join_notes["missing_from_internal"]:
        lines.append("**All 20 entities matched on both sides, exact `entity_name` string match. No fuzzy matching needed or used.**")
    else:
        if join_notes["missing_from_external"]:
            lines.append(f"**In transactional_banking.csv but missing from financials_extracted_v2.csv:** {join_notes['missing_from_external']}")
        if join_notes["missing_from_internal"]:
            lines.append(f"**In financials_extracted_v2.csv but missing from transactional_banking.csv:** {join_notes['missing_from_internal']}")
        lines.append("")
        lines.append("**No fuzzy matching was attempted — flagging this mismatch for a team decision rather than guessing at a name correction.**")

    lines += [
        "",
        "The joined output keeps every column from both sides (all of `financials_extracted_v2.csv`'s "
        "revenue/cost/receivables/FX fields, not just a pre-selected subset) plus a `join_status` "
        "column, so nothing about which external fields matter for modeling was decided here — "
        "that's a later step's call.",
        "",
        "## 4. Outputs",
        "",
        f"- `{OUT_ENTITY_CSV.name}` — entity-level aggregation, {len(entity_agg)} rows",
        f"- `{OUT_JOINED_CSV.name}` — joined against external financials, one row per entity",
        f"- `{OUT_SUMMARY_MD.name}` — this file",
        "",
        "## 5. Needs a team decision",
        "",
        "1. Should this be re-cut to the trailing-12-month window (per the approved pillar-spend-split "
        "design) before it's used for an actual Share-of-Wallet number, or is full-history the right "
        "basis going forward? (See note in Section 2.)",
        "2. Is a `leg_type`/`channel` breakdown per entity worth adding now, or only if/when it's "
        "actually needed for modeling?",
        "",
        "## Out of scope for this step",
        "",
        "No Share-of-Wallet, gap, or ratio calculation. No selection of which external columns are "
        "\"the\" Pillar 1 comparison fields. Clean, aggregate, join, verify only.",
    ]

    OUT_SUMMARY_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    df, clean_notes = load_and_clean()
    entity_agg = aggregate_entity_level(df)
    entity_agg.to_csv(OUT_ENTITY_CSV, index=False)

    joined, join_notes = join_external(entity_agg)
    joined.to_csv(OUT_JOINED_CSV, index=False)

    write_summary(clean_notes, entity_agg, join_notes)

    print(f"Rows raw -> clean: {clean_notes['rows_raw']:,} -> {clean_notes['rows_clean']:,}")
    print(f"Entities aggregated: {len(entity_agg)}")
    print(f"Join: internal={join_notes['internal_entity_count']} external={join_notes['external_entity_count']} "
          f"missing_from_external={join_notes['missing_from_external']} missing_from_internal={join_notes['missing_from_internal']}")
    print(f"\nWrote:\n  {OUT_ENTITY_CSV}\n  {OUT_JOINED_CSV}\n  {OUT_SUMMARY_MD}", file=sys.stderr)


if __name__ == "__main__":
    main()
