# Syn Bank Product Pillar Spend Split — Design

**Date:** 2026-08-08
**Status:** Approved
**Context:** Syn Bank Share of Wallet Intelligence Engine (see `PLAN.md`). This is the first piece of PLAN.md Section 5 Step 4, "Internal wallet share build" — it defines how Syn Bank's three internal datasets get mapped into the product-pillar taxonomy that the wallet model will later compare against externally-estimated Total Wallet, pillar by pillar.

## Problem

We have three internal datasets (`transactional_banking.csv`, `cross_border_payments.csv`, `trade_finance.csv`) but no existing logic that splits a client's total captured spend into the product categories a coverage banker actually thinks in. Without this split, "Syn Bank Share" can only be compared to "Total Wallet" as a single blended number, which hides *where* the gap is (e.g. a client might be fully captured on transactional banking but invisible on trade finance).

## Pillar Taxonomy

Five pillars, chosen to mirror Syn Bank's own product pillars so internal capture and external wallet estimates line up 1:1 later:

| Pillar | Internal source | External signal (used in a later step) |
|---|---|---|
| Transactional Banking / Cash Management | `transactional_banking.csv` | revenue size |
| Trade Finance | `trade_finance.csv` | inventory + cost of sales |
| FX / Global Markets | `cross_border_payments.csv` | foreign revenue % |
| Lending / Debt Capital Markets | none | debt schedules + SENS bond issuances |
| Investment Banking / Advisory | none | SENS announcements (rights issues, M&A, capital raising) |

Lending/DCM and IB/Advisory have **no internal data by construction** — Syn Bank's transaction data structurally cannot see these product lines for competitor-held facilities. Rather than omit them, every client gets a row for all 5 pillars, with the two data-free pillars carrying `internal_spend_zar = 0` and `has_internal_signal = False`. This makes the gap explicit and keeps the pillar set consistent for later joins against the external wallet estimate (which *will* have signal for all 5).

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
    grouped["has_internal_signal"] = True
    return grouped
```

Called once per source dataset with the right `pillar_name` and `amount_col`, then concatenated. Two placeholder rows per client (Lending/DCM, IB/Advisory) are unioned in afterward with `internal_spend_zar = 0.0` and `has_internal_signal = False`, using the same `entity_id, entity_name, sector` keys pulled from the entity list already validated in notebook Section 4.

**Result — `pillar_spend_long`:**

| Column | Type | Notes |
|---|---|---|
| `entity_id` | str | |
| `entity_name` | str | |
| `sector` | str | |
| `pillar` | str | one of the 5 pillar names above |
| `internal_spend_zar` | float | gross flow, trailing 12 months |
| `has_internal_signal` | bool | False only for Lending/DCM and IB/Advisory |

This is the single source of truth. All downstream views (wide table, charts) derive from it rather than recomputing.

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

`pillar_spend_wide` is one row per client, one column per pillar, plus a total and a per-pillar `pct_of_total` (the client's captured-wallet mix — e.g. "82% transactional, 12% trade finance, 6% FX, 0% lending, 0% IB"). This is the table that later joins against the external Total Wallet estimate, pillar-for-pillar, to compute the gap.

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
- Lending/DCM and IB/Advisory pillars have zero internal signal by construction — Syn Bank's data cannot see competitor-held facilities in these product lines. This is a structural gap in the numerator, not a data quality issue, and should be called out explicitly wherever the pillar mix is presented (dashboard, briefing notes) so a 0% share in these two pillars isn't misread as "no lending/IB need" rather than "no internal visibility."
