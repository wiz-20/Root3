# Syn Bank Product Pillar Spend Split — Design

**Date:** 2026-08-08 (revised 2026-08-08 — narrowed from 5 to 3 pillars per team decision)
**Status:** Approved
**Context:** Syn Bank Share of Wallet Intelligence Engine (see `PLAN.md`). This is the first piece of PLAN.md Section 5 Step 4, "Internal wallet share build" — it defines how Syn Bank's three internal datasets get mapped into the product-pillar taxonomy that the wallet model will later compare against externally-estimated Total Wallet, pillar by pillar.

## Problem

We have three internal datasets (`transactional_banking.csv`, `cross_border_payments.csv`, `trade_finance.csv`) but no existing logic that splits a client's total captured spend into the product categories a coverage banker actually thinks in. Without this split, "Syn Bank Share" can only be compared to "Total Wallet" as a single blended number, which hides *where* the gap is (e.g. a client might be fully captured on transactional banking but invisible on trade finance).

## Pillar Taxonomy

Three pillars — scoped deliberately to only the parts of the wallet where Syn Bank has internal data to measure a share from. The project's core question is "what share does Syn Bank hold, and where's the gap," which only computes for pillars with a real internal numerator. (An earlier 5-pillar draft included Lending/DCM and IB/Advisory as zero-signal placeholders; the team cut them rather than model an internal share of zero.)

| Pillar | Syn Bank data to use | External/company financial data to look for | Purpose |
|---|---|---|---|
| 1. Transactional Banking | `transactional_banking.csv` — transaction values, payment/collection activity, transaction frequency, inbound/outbound flows | Revenue, cost of sales, operating expenses, cash flow from operations, trade receivables, trade payables | Estimate the scale of the client's day-to-day payment and collection activity |
| 2. Trade & Working Capital | `trade_finance.csv` — letters of credit, guarantees, export collections, trade values, tenor, import/export direction | Inventory, COGS, trade receivables, trade payables, imports/exports, working-capital movements, disclosed trade facilities/guarantees/LCs | Estimate the client's trade-finance and working-capital requirement |
| 3. Foreign / Cross-Border | `cross_border_payments.csv` — cross-border payment value, currency pair, direction, counterparty country, corridor, transaction frequency | Foreign revenue, foreign operating costs, geographic revenue, foreign-currency assets/liabilities, FX gains/losses, disclosed currency exposure, imports/exports | Estimate the client's international/foreign-currency banking activity |

Every pillar has real internal signal by construction — no placeholder rows, no zero-signal flag needed.

## Time Window

All three source datasets cover 2023-07-01 to 2026-06-30 (3 fiscal years). The pillar split uses only the **trailing 12 months**: `date >= 2025-07-01 and date <= 2026-06-30`.

Rationale: this is the most recently completed FY in the data, keeps the internal "Syn Bank Share" numerator time-consistent with external evidence (SENS filings, latest annual report), and avoids diluting current wallet share with 3-year-old activity.

## Metric Definition

Per client, per pillar: **gross flow** — `sum(abs(amount))` across both directions, not net.

- `transactional_banking.csv`: sum of `amount_zar` across `direction in {inbound, outbound}`
- `cross_border_payments.csv`: sum of `value_zar` across `direction in {inbound, outbound}`
- `trade_finance.csv`: sum of `value_zar` across `direction in {export, import}`

Rationale: banks earn fees on both legs of a flow (collections and payments, imports and exports), so gross turnover is the right proxy for wallet size — not net position, which can mask activity when flows roughly offset.

No filtering on `trade_finance.status` (`issued`/`settled`/`active`/`expired`) — all instrument rows within the trailing-12-month window count toward gross flow regardless of current status.

## Build — Long Form (source of truth)

A per-dataset function, e.g.:

```python
def build_pillar_rows(df: pd.DataFrame, pillar_name: str, amount_col: str) -> pd.DataFrame:
    windowed = df[(df["date"] >= "2025-07-01") & (df["date"] <= "2026-06-30")]
    grouped = (
        windowed.groupby(["entity_id", "entity_name", "sector"])[amount_col]
        .sum()
        .reset_index()
        .rename(columns={amount_col: "internal_spend_zar"})
    )
    grouped["pillar"] = pillar_name
    return grouped
```

Called once per source dataset with the right `pillar_name` and `amount_col`, then concatenated — no placeholder rows needed since all three pillars have real data.

**Result — `pillar_spend_long`:**

| Column | Type | Notes |
|---|---|---|
| `entity_id` | str | |
| `entity_name` | str | |
| `sector` | str | |
| `pillar` | str | one of the 3 pillar names above |
| `internal_spend_zar` | float | gross flow, trailing 12 months |

This is the single source of truth. All downstream views (wide form, charts) derive from it rather than recomputing.

## Pivot — Wide Form (display/export)

```python
pillar_spend_wide = pillar_spend_long.pivot(
    index=["entity_id", "entity_name", "sector"],
    columns="pillar",
    values="internal_spend_zar",
).reset_index()

pillar_spend_wide["total_internal_spend_zar"] = pillar_spend_wide[pillar_cols].sum(axis=1)

for col in pillar_cols:
    pillar_spend_wide[f"{col}_pct_of_total"] = (
        pillar_spend_wide[col] / pillar_spend_wide["total_internal_spend_zar"]
    )
```

`pillar_spend_wide` is one row per client, one column per pillar, plus a total and a per-pillar `pct_of_total` (the client's captured-wallet mix — e.g. "82% transactional, 12% trade & working capital, 6% foreign/cross-border"). This is the table that later joins against the external Total Wallet estimate, pillar-for-pillar, to compute the gap.

## Where This Lives

New notebook section inserted between the existing "4. Entity list sanity check" and where wallet-share modeling begins:

**"5. Internal wallet share by product pillar"**

This renumbers everything after it in `wallet_engine.ipynb` by one (the PLAN.md Section 5 notebook structure list stays conceptually the same — "4. Internal wallet share build" — just realized as notebook section 5 once the entity check occupies section 4).

## Out of Scope (for this step)

- External wallet estimation (top-down financials multiplier, bottom-up competitor evidence) — later step, consumes `pillar_spend_wide` as an input but is not built here.
- Gap ranking / opportunity scoring — depends on the external estimate, later step.
- Any handling of the `memo` column (>99% null across all three datasets) — not used by this split.
- Currency conversion — all three amount columns are already in ZAR (`amount_zar`, `value_zar`, `value_zar`), no FX conversion needed at this step.

## Assumptions & Limitations (for methodology appendix)

- Trailing-12-month window (2025-07 to 2026-06) is used as "current" wallet share; this discards 2 years of history that could show trend but keeps the snapshot time-consistent with external evidence.
- Gross flow (not net) is treated as the wallet-size proxy, consistent with how banks earn fees on both directions of a flow.
- **Scope decision:** the wallet-share comparison (internal capture vs. external Total Wallet) is limited to the three pillars where Syn Bank has internal data — Transactional Banking, Trade & Working Capital, Foreign/Cross-Border. Lending/Debt Capital Markets and Investment Banking/Advisory are explicitly out of scope for the *share* calculation: Syn Bank's transaction data has no visibility into competitor-held facilities in those product lines, so there is no internal numerator to compute a share from. Any lending or IB/advisory opportunity signal (debt schedules, SENS bond issuances, M&A announcements) should be surfaced separately in the external research / briefing-note layer, not folded into the 3-pillar gap ranking. This should be stated plainly in the methodology appendix so reviewers don't read the 3-pillar scope as "Syn Bank has no lending or IB exposure" rather than "the model doesn't attempt to measure it."
