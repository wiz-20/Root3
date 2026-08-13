# Wallet Model — Top-Down Build & Opportunity Ranking

**Date:** 2026-08-13
**Scope:** PLAN.md Section 5, steps 4–7 (internal wallet share build, external wallet estimation, wallet model, opportunity ranking). First end-to-end pass — closes the loop from raw data to a ranked, Rand-denominated gap for the first time.
**Scope decision (solo/time-constrained):** top-down financials-based Total Wallet estimate only. Bottom-up competitor evidence (SARB BA900, JSE SENS, borrowing notes) was cut from this pass — see `DATA_SOURCES.md` for what that would add if time allows later.

## How it was built

1. `scripts/build_pillar_spend.py` — internal side. Reuses the approved 3-pillar taxonomy (`docs/superpowers/specs/2026-08-08-pillar-spend-split-design.md`): Transactional Banking, Trade & Working Capital, Foreign/Cross-Border. Trailing 12 months only (2025-07-01 → 2026-06-30), gross flow (both directions summed). Output: `pillar_spend_long.csv` / `pillar_spend_wide.csv`.
2. `scripts/build_wallet_model.py` — external side + combination. Builds a Total Wallet **proxy** per pillar from each company's own most-current disclosed financials (`financials_extracted.csv`):
   - **Pillar 1 (Transactional Banking):** revenue + cost_of_sales (revenue-only for the 8 companies where cost_of_sales structurally doesn't exist — insurers, REITs, telcos, holding companies).
   - **Pillar 2 (Trade & Working Capital):** inventory + trade receivables + trade payables — the working-capital base trade-finance instruments could finance.
   - **Pillar 3 (Foreign/Cross-Border):** revenue × disclosed foreign-revenue %, only for the 4/20 companies (MTN, Naspers, Sanlam, Vodacom) where that split was actually disclosed as a number — left as "not estimated" for the other 16 rather than guessing.

   Then: Share % = internal / wallet proxy, Gap = wallet proxy − internal, per pillar and blended.

## The one modeling problem worth knowing about before you read any Rand figure

The naive version of this (proxy = consolidated group revenue) produced a **R9.5 trillion "gap" for Glencore** and other global miners/traders — obviously not real. Consolidated group revenue for a multinational commodity trader reflects *worldwide* operations, not the slice of banking activity addressable by an SA bank. Rather than hide this, the model now tags every row with a `top_down_reliability` column:

- **`moderate`** (11 companies, ZAR reporters) — the disclosed financials are for the SA-listed entity itself. Rand gap figures are reasonably literal.
- **`low`** (8 companies — Anglo American, AngloGold Ashanti, BHP, Glencore, Gold Fields, Naspers, Prosus, NEPI Rockcastle, Shaftesbury) — foreign-currency reporters. The % share is still informative (very low, genuinely) but the absolute Rand gap should be read as directional only, not summed into a portfolio total.
- **`insufficient`** (Bidvest) — only company-level (not Group) financials were ever found in the source AFS, so Pillar 1's external wallet is unknown; blended total is correctly left blank rather than computed from 2 of 3 pillars.

**This is the single most important limitation to state up front in the deck** — it's also a legitimate "business insight" finding in its own right (a naive model would have told a banker to chase a fictional multi-trillion-Rand Glencore opportunity).

## Top opportunities — actionable tier only (ZAR reporters, Rand gap is literal)

| Client | Pillar | Share % | Gap (R millions) | Read |
|---|---|---|---|---|
| Shoprite Holdings | Transactional Banking | 2.4% | 437,348 | Large domestic retailer, very low captured transactional share |
| Bid Corporation | Transactional Banking | 3.1% | 400,581 | Same pattern — global foodservice group, SA entity mostly untapped |
| MTN Group | Transactional Banking | 4.6% | 216,271 | Largest telco gap; also #1 on Cross-Border (see below) |
| **Valterra Platinum** | Transactional **and** Trade & WC | **0.0–0.2%** | 204,050 / 58,834 | Flag this one specifically — near-zero share across *every* pillar despite being a domestic ZAR reporter (not a scale-mismatch artifact like the multinationals above). Genuinely the sharpest single-client story in the dataset. |
| Vodacom Group | Foreign/Cross-Border | 4.7% | 58,970 | Best pillar-level cross-border find (only 4 companies have this pillar estimated at all) |

## What doesn't fit the pattern — worth a sentence in the deck, not a fix

- **Sanlam & OUTsurance, Pillar 2/3:** internal captured flow *exceeds* the top-down proxy (flagged `internal flow exceeds top-down proxy`). Plausible explanation: insurers run large treasury/float activity that a simple receivables+payables+inventory proxy doesn't capture — not a data error, but the proxy underestimates insurers specifically.
- **Pillar 3 coverage is thin (4/20).** Foreign-revenue % is disclosed as a clean number for MTN, Naspers, Sanlam, Vodacom only. The other 16 companies have real internal cross-border transaction activity (see `pillar_spend_wide.csv`) with no external wallet to compare it to yet — this is exactly where the cut bottom-up SENS/JSE segment-data work would help most, if there's time on Saturday.

## Files produced

- `hackathon-finreports/_extracted/pillar_spend_long.csv`, `pillar_spend_wide.csv` — internal side
- `hackathon-finreports/_extracted/wallet_model.csv` — full per-client, per-pillar model with all caveat columns
- `hackathon-finreports/_extracted/opportunity_ranking.csv` — clients ranked by total Rand gap, reliability tier included

## Assumptions & limitations (for the methodology appendix)

1. Top-down only — no bottom-up competitor evidence in this pass; stated as a limitation, not a precision claim.
2. Pillar 3 wallet estimated for only 4/20 companies (numeric foreign-revenue disclosure required); the rest are "external estimate unavailable", not zero.
3. Internal = trailing-12-month gross flow (both directions); external = single-fiscal-year P&L/balance-sheet snapshot. A negative gap (internal > proxy) is flagged per-row as a plausible real signal, not clipped to zero.
4. `cost_of_sales` is structurally absent for insurers/REITs/telcos/holding companies — Pillar 1 falls back to revenue-only for those 8 rather than fabricating a cost figure.
5. Foreign-currency reporters' Rand gap figures are directional only (see reliability tiering above) — do not sum low-reliability rows into a portfolio-level Rand total.
