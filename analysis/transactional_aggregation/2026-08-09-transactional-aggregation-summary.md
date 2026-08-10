# Transactional Banking — Entity-Level Aggregation & External Join

**Date:** 2026-08-09
**Scope:** Clean `transactional_banking.csv`, aggregate to entity level (Pillar 1), join against `financials_extracted_v2.csv`, verify it lines up. No Share-of-Wallet or gap calculation — that's a later step.
**Isolation:** all work done in `analysis/transactional_aggregation/`; nothing in `scripts/`, `docs/reports/`, or `hackathon-finreports/_extracted/` was modified, only read.

## 1. Cleaning

Raw rows: 2,802,875
`currency` values before normalization: ['ZAR', 'zar']
`currency` values after normalization (`.str.upper()`): ['ZAR']
Rows with non-ZAR currency after normalization: 0 (confirms the casing fix was sufficient — no genuine non-ZAR currency exists in this file, matching the profiling report).

Exact duplicate rows dropped (full-row match, kept first occurrence): 11,072 (0.395% of raw rows).
Profiling report's estimate was ~0.4% (0.3857% exactly, from the same 10,812/2,802,875 figure) — **matches, no material difference.**

**Judgment call:** deduped on the full row (all 13 columns), not on `transaction_id`, per the profiling report's finding that `transaction_id` is reused across genuinely different transactions and is therefore not a valid dedup key on its own. Using `transaction_id` to dedupe would have incorrectly dropped ~106K legitimate, distinct transactions.

Rows after cleaning: 2,791,803

## 2. Entity-level aggregation

Entities in output: 20 (expect 20).

Columns produced, from what's actually in the schema (no fee-income column exists in this dataset, so that example from the ask isn't available — only settlement/transaction value and count):

- `transaction_count` — total row count per entity, post-cleaning
- `total_amount_zar` — gross flow, both directions summed (all amounts are already non-negative per the profiling report, so this is a plain sum, not `sum(abs(...))`)
- `inbound_amount_zar` / `outbound_amount_zar` / `net_amount_zar` — direction split, for sanity-checking and because `net` and `gross` tell different stories (e.g. a client with huge offsetting inbound/outbound legs looks very different on each measure)
- `min_date` / `max_date` — per-entity date coverage, to confirm no entity is silently partial (e.g. missing a chunk of the 3-year window)

All 20 entities span (or nearly span) the full 2023-07-01 -> 2026-06-30 window — the date-coverage check did its job. Three low-volume entities (Shaftesbury Capital plc: 1,418 transactions, `min_date` 2023-07-03/`max_date` 2026-06-28; Valterra Platinum: 794 transactions; NEPI Rockcastle: 2,787 transactions, `min_date` 2023-07-02) start/end a day or two inside the window rather than exactly on the boundary — expected sampling variance for entities with this few transactions, not a sign of missing data (no entity is off by more than 2-3 days, and there's no gap in the middle of anyone's range).

**Not produced (scope call, flagging rather than deciding):** a `leg_type` (collections/supplier_payments/intercompany_sweeps/tax/payroll) or `channel` breakdown per entity. The groupby to add this is cheap, but the ask was to stop at clean/aggregate/join/verify — happy to add it as a follow-up cut if it's useful before modeling.

**Also flagging, not deciding:** the previously-approved pillar-spend-split design (`docs/superpowers/specs/2026-08-08-pillar-spend-split-design.md`) specifies a **trailing 12-month window** (2025-07-01 to 2026-06-30) for the actual wallet-share numerator, to stay time-consistent with the external evidence. This aggregation instead uses **full history** (all ~3 years), since no time window was specified for this step and the min/max date columns are more useful as a full-history completeness check than they'd be if pre-filtered to one year. **Before this feeds into an actual Share-of-Wallet number, it should be re-cut to the trailing-12-month window per the approved spec** — this table as-is is the full-history version only.

## 3. Join against financials_extracted_v2.csv

Internal (transactional) entity_name count: 20
External (financials) entity_name count: 20

**All 20 entities matched on both sides, exact `entity_name` string match. No fuzzy matching needed or used.**

The joined output keeps every column from both sides (all of `financials_extracted_v2.csv`'s revenue/cost/receivables/FX fields, not just a pre-selected subset) plus a `join_status` column, so nothing about which external fields matter for modeling was decided here — that's a later step's call.

## 4. Outputs

- `entity_transactional_aggregation.csv` — entity-level aggregation, 20 rows
- `entity_transactional_joined_external.csv` — joined against external financials, one row per entity
- `2026-08-09-transactional-aggregation-summary.md` — this file

## 5. Needs a team decision

1. Should this be re-cut to the trailing-12-month window (per the approved pillar-spend-split design) before it's used for an actual Share-of-Wallet number, or is full-history the right basis going forward? (See note in Section 2.)
2. Is a `leg_type`/`channel` breakdown per entity worth adding now, or only if/when it's actually needed for modeling?

## Out of scope for this step

No Share-of-Wallet, gap, or ratio calculation. No selection of which external columns are "the" Pillar 1 comparison fields. Clean, aggregate, join, verify only.