# Internal Dataset Profiling Report

**Date:** 2026-08-09
**Scope:** Pre-modeling sanity check of the three internal Syn Bank datasets, per PLAN.md Section 5 Step 3 ("Cleaning & profiling"), before any Share-of-Wallet calculation logic is written. Same principle as the external financials extraction work: sanity-check first, document gaps honestly, don't force conclusions.
**Datasets profiled:** `transactional_banking.csv` (2,802,875 rows), `cross_border_payments.csv` (241,117 rows), `trade_finance.csv` (20,303 rows).
**Cross-checked against:** `hackathon-finreports/_extracted/financials_extracted_v2.csv` (`entity_name`, the 20 confirmed clients) and each other.

## How this was produced

- `scripts/profile_transactional_banking.py` — PySpark, local mode (this file is large enough that the team asked for Spark specifically).
- `scripts/profile_cross_border_payments.py`, `scripts/profile_trade_finance.py` — pandas.
- `scripts/check_cross_dataset_consistency.py` — checks the three internal datasets against **each other** (entity_id/entity_name/sector agreement), which none of the per-dataset scripts can do alone.
- `scripts/profiling_common.py` — shared entity cross-check + markdown helpers, imported by all four.

**Environment note:** PySpark needs a JVM, and this machine had neither Java nor PySpark installed. `pip install pyspark` was straightforward; Java was not — the standard `winget install` path hung indefinitely on a UAC elevation prompt that can't be answered in a non-interactive shell. Worked around by downloading the portable Microsoft OpenJDK 17 zip (no install/admin rights needed) to `.tools/jdk-17.0.20+8` (gitignored — ~500MB, not something to commit) and pointing `JAVA_HOME` at it; `setx JAVA_HOME` was also run so it persists for this Windows user account, and each Spark script falls back to the local copy automatically if `JAVA_HOME` isn't already set. **Anyone else re-running `profile_transactional_banking.py` needs a JVM available one way or another** — either their own Java install or by re-running the same portable-zip steps. `pyspark==4.2.0` has been added to `requirements.txt`; the JDK itself is a system dependency `pip` can't install, so it isn't in there.

---

## 1. transactional_banking.csv

_Profiled with PySpark 4.2.0, local mode._

### Schema

| Column | Dtype | Notes |
|---|---|---|
| transaction_id | string | unique identifier per transaction record |
| entity_id | string | internal client identifier — join key across all 3 Syn Bank datasets |
| entity_name | string | client display name — join key against external financials data |
| sector | string | client's industry/sector classification |
| date | date | transaction date |
| leg_type | string | collections / supplier_payments / intercompany_sweeps / tax / payroll |
| direction | string | inbound (money received) or outbound (money sent) |
| amount_zar | double | transaction amount, already in ZAR |
| currency | string | currency code recorded on the transaction |
| channel | string | payment rail: EFT / SWIFT / Internal Transfer / RTC / Debit Order |
| beneficiary_name | string | name of the payment beneficiary |
| reference | string | payment reference / description text |
| memo | string | free-text memo field, mostly unused |

### Row counts & date coverage

Rows: 2,802,875
Date range: 2023-07-01 -> 2026-06-30
All rows fall within the stated 2023-07-01 -> 2026-06-30 window.

#### Entity coverage

Confirmed entities (from `financials_extracted_v2.csv`): 20 | Distinct entities in this dataset: 20 | Exact-string matches: 20

**MATCH** — entity_name set is identical to the confirmed 20. No join-blocking name issues.

`entity_id` <-> `entity_name` is a clean 1:1 mapping (no entity_id maps to >1 name or vice versa).

### Missing values & duplicates

| Column | Null % |
|---|---|
| transaction_id | 0.0% |
| entity_id | 0.0% |
| entity_name | 0.0% |
| sector | 0.0% |
| date | 0.0% |
| leg_type | 0.0% |
| direction | 0.0% |
| amount_zar | 0.0% |
| currency | 0.0% |
| channel | 0.0% |
| beneficiary_name | 0.0% |
| reference | 0.0% |
| memo | 99.87% |

Exact duplicate rows (all columns identical): 10,812
Distinct `transaction_id` values that appear more than once: 52,984 (106,777 rows involved).
**This is not the same as exact duplicate rows** — spot-checking confirms `transaction_id` is being reused across genuinely different transactions (different entities, dates, amounts, beneficiaries), not just re-inserted copies of the same record. `transaction_id` is therefore **not a reliable unique key** and cannot be used for row-level dedup or as a join key on its own. This does not corrupt entity/pillar-level sums (aggregation groups by `entity_id`, not `transaction_id`), but flag it before anyone builds transaction-level logic (e.g. de-duplication, audit trail lookups) on top of this ID.

### Outliers / data quality issues

`amount_zar` <= 0: 0 rows
`direction` outside {inbound, outbound}: 0 rows
`leg_type` outside ['collections', 'intercompany_sweeps', 'payroll', 'supplier_payments', 'tax']: 0 rows
`channel` outside ['Debit Order', 'EFT', 'Internal Transfer', 'RTC', 'SWIFT']: 0 rows

Distinct `currency` values (2): 'ZAR' (2,774,594), 'zar' (28,281)

### Currency

`amount_zar` is named as already ZAR-converted, and case-insensitively every row's `currency` is 'ZAR' — but the literal string varies by case ('ZAR', 'zar'). This is a **data-quality/formatting bug, not a currency-conversion issue**: no non-ZAR currency actually appears in this file, so there is nothing to convert. Flag for whoever consumes `currency` downstream (e.g. a groupby or filter on the literal string 'ZAR' would silently drop the lowercase rows) — worth normalizing case before use.

### Join feasibility

- To other internal datasets: `entity_id` (confirmed 1:1 with `entity_name` above) — same key used in `cross_border_payments.csv` and `trade_finance.csv`.
- To `financials_extracted_v2.csv`: `entity_name`, exact string match (see Entity coverage above).

---

## 2. cross_border_payments.csv

### Schema

| Column | Dtype | Notes |
|---|---|---|
| transaction_id | str | unique identifier per payment record |
| entity_id | str | internal client identifier — join key across all 3 Syn Bank datasets |
| entity_name | str | client display name — join key against external financials data |
| sector | str | client's industry/sector classification |
| date | datetime64[us] | transaction date |
| direction | str | inbound (money received) or outbound (money sent) |
| currency_pair | str | FX currency pair for the cross-border leg, e.g. ZAR/USD |
| value_zar | float64 | transaction value, already converted to ZAR |
| counterparty_country | str | country of the payment counterparty |
| corridor_type | str | category of cross-border flow: intercompany / trade / other |
| beneficiary_name | str | name of the payment beneficiary |
| reference | str | payment reference / description text |
| memo | str | free-text memo field, mostly unused |

### Row counts & date coverage

Rows: 241,117
Date range: 2023-07-01 -> 2026-06-30
All rows fall within the stated 2023-07-01 -> 2026-06-30 window.

#### Entity coverage

Confirmed entities (from `financials_extracted_v2.csv`): 20 | Distinct entities in this dataset: 20 | Exact-string matches: 20

**MATCH** — entity_name set is identical to the confirmed 20. No join-blocking name issues.

`entity_id` <-> `entity_name` is a clean 1:1 mapping (no entity_id maps to >1 name or vice versa).

### Missing values & duplicates

| Column | Null % |
|---|---|
| transaction_id | 0.0% |
| entity_id | 0.0% |
| entity_name | 0.0% |
| sector | 0.0% |
| date | 0.0% |
| direction | 0.0% |
| currency_pair | 0.0% |
| value_zar | 0.0% |
| counterparty_country | 1.52% |
| corridor_type | 0.0% |
| beneficiary_name | 0.0% |
| reference | 0.0% |
| memo | 99.81% |

Exact duplicate rows (all columns identical): 926
Duplicate `transaction_id` values: 1,223

### Outliers / data quality issues

`value_zar` <= 0: 0 rows
`direction` outside {inbound, outbound}: 0 rows
`corridor_type` outside {intercompany, trade, other}: 0 rows

Distinct `currency_pair` values (5): AED/ZAR, CNY/ZAR, EUR/ZAR, GBP/ZAR, USD/ZAR

`counterparty_country` empty-string (as opposed to null): 0 rows

### Currency

No separate `currency` column — `value_zar` is named as already ZAR-converted, and there is no FX-rate column in this file to independently verify the conversion. `currency_pair` describes the corridor (e.g. `ZAR/USD`) but is not itself a unit the `value_zar` figure is denominated in. **Flag for team:** we cannot verify from this file alone whether `value_zar` was converted at a point-in-time rate per transaction or a static rate — worth confirming with whoever generated this synthetic data, since it affects whether small time-series distortions are meaningful.

### Join feasibility

- To other internal datasets: `entity_id` (confirmed 1:1 with `entity_name` above) — same key used in `transactional_banking.csv` and `trade_finance.csv`.
- To `financials_extracted_v2.csv`: `entity_name`, exact string match (see Entity coverage above).

---

## 3. trade_finance.csv

### Schema

| Column | Dtype | Notes |
|---|---|---|
| instrument_id | str | unique identifier per trade finance instrument |
| entity_id | str | internal client identifier — join key across all 3 Syn Bank datasets |
| entity_name | str | client display name — join key against external financials data |
| sector | str | client's industry/sector classification |
| date | datetime64[us] | instrument issue/booking date |
| instrument_type | str | letters_of_credit / export_collections / guarantees |
| direction | str | export or import |
| tenor_days | int64 | instrument tenor in days |
| value_zar | float64 | instrument face value, already converted to ZAR |
| counterparty_country | str | country of the trade counterparty |
| commodity_or_contract_type | str | underlying commodity or contract category |
| status | str | issued / settled / active / expired |
| beneficiary_name | str | name of the instrument beneficiary |
| reference | str | instrument reference / description text |
| memo | str | free-text memo field, mostly unused |

### Row counts & date coverage

Rows: 20,303
Date range: 2023-07-01 -> 2026-06-30
All rows fall within the stated 2023-07-01 -> 2026-06-30 window.
Rows whose `date + tenor_days` implied maturity falls after 2026-06-30 (not an error — just means the instrument matures beyond the data window): 2,164

#### Entity coverage

Confirmed entities (from `financials_extracted_v2.csv`): 20 | Distinct entities in this dataset: 20 | Exact-string matches: 20

**MATCH** — entity_name set is identical to the confirmed 20. No join-blocking name issues.

`entity_id` <-> `entity_name` is a clean 1:1 mapping (no entity_id maps to >1 name or vice versa).

### Missing values & duplicates

| Column | Null % |
|---|---|
| instrument_id | 0.0% |
| entity_id | 0.0% |
| entity_name | 0.0% |
| sector | 0.0% |
| date | 0.0% |
| instrument_type | 0.0% |
| direction | 0.0% |
| tenor_days | 0.0% |
| value_zar | 0.0% |
| counterparty_country | 1.57% |
| commodity_or_contract_type | 0.0% |
| status | 0.0% |
| beneficiary_name | 0.0% |
| reference | 0.0% |
| memo | 99.54% |

Exact duplicate rows (all columns identical): 88
Duplicate `instrument_id` values: 91

### Outliers / data quality issues

`value_zar` <= 0: 0 rows
`tenor_days` <= 0: 0 rows
`tenor_days` > 3650 (10 years): 0 rows (max observed: 365)
`direction` outside {export, import}: 0 rows
`instrument_type` outside ['export_collections', 'guarantees', 'letters_of_credit']: 0 rows
`status` outside ['active', 'expired', 'issued', 'settled']: 0 rows

Status distribution:

| Status | Count |
|---|---|
| settled | 8632 |
| active | 7066 |
| issued | 2995 |
| expired | 1610 |

### Currency

No separate `currency` column — `value_zar` is named as already ZAR-converted, and there is no FX-rate column in this file to independently verify the conversion, same caveat as `cross_border_payments.csv`.

### Join feasibility

- To other internal datasets: `entity_id` (confirmed 1:1 with `entity_name` above) — same key used in `transactional_banking.csv` and `cross_border_payments.csv`.
- To `financials_extracted_v2.csv`: `entity_name`, exact string match (see Entity coverage above).

---

## 4. Cross-dataset consistency (all 3 internal datasets against each other)

One row per (entity_id, entity_name, sector) triple found in each dataset. All three should agree exactly per entity_id.

Distinct `entity_id` values across all 3 datasets combined: 20

**MATCH** — every `entity_id` maps to the identical `(entity_name, sector)` pair in all 3 internal datasets. Safe to join on `entity_id` alone across all 3.

---

## 5. Summary — what's usable, what's broken, what needs a team decision

### Usable as-is

- **Entity coverage is clean across the board.** All three internal datasets contain exactly the confirmed 20 entities, with exact-string `entity_name` matches against `financials_extracted_v2.csv` and a clean 1:1 `entity_id` <-> `entity_name` mapping *within* each dataset. The cross-dataset check confirms all three also agree with **each other** on `entity_id` -> `(entity_name, sector)` — no entity is missing from any of the three, and none has conflicting name/sector data across files. **`entity_id` is a safe join key across all three internal datasets and `entity_name` is a safe join key against the external financials table.**
- **Date coverage is clean.** All three datasets fall entirely within the stated 2023-07-01 -> 2026-06-30 window — zero out-of-range rows anywhere.
- **Categorical fields are clean.** Every `direction`, `leg_type`, `channel`, `corridor_type`, `instrument_type`, and `status` value across all three files falls within its expected value set — zero unexpected categories.
- **Value/amount fields are sane.** Zero non-positive `amount_zar` / `value_zar` rows anywhere, and `trade_finance.tenor_days` is always positive and reasonable (max observed 365 days).
- **`memo` is universally near-empty** (99.5-99.9% null across all three) — safe to ignore/drop, not a data-quality problem, just an unused field.

### Broken / needs cleanup before modeling

- **`transaction_id` in `transactional_banking.csv` is not a reliable unique key.** 52,984 distinct IDs (106,777 rows, ~3.8% of the file) are reused across genuinely different transactions — different entities, dates, amounts, beneficiaries — confirmed by spot-checking actual rows, not just a count mismatch. The same pattern shows up at much smaller scale in `cross_border_payments.csv` (1,223 duplicate `transaction_id` occurrences out of 241K rows, ~0.5%) and `trade_finance.csv` (91 duplicate `instrument_id` occurrences out of 20K rows, ~0.45%) — same underlying data-generation artifact, proportionally minor there. **This does not corrupt entity/pillar-level aggregation** (grouping by `entity_id`, not by transaction ID, per the approved pillar-spend-split design), but blocks any transaction-level dedup or audit-trail logic that assumes ID uniqueness.
- **`transactional_banking.csv`'s `currency` column has a casing bug**, not a currency problem: values are `'ZAR'` (2,774,594 rows) and `'zar'` (28,281 rows) — same currency, inconsistent case. Every row actually is ZAR (confirmed case-insensitively), so there's nothing to FX-convert, but a naive `currency == "ZAR"` filter downstream would silently drop 1% of rows. Trivial fix (`.str.upper()`) before this column is used for any filter/groupby.
- **Exact duplicate rows exist in all three files**: 10,812 in transactional (0.4%), 926 in cross-border (0.4%), 88 in trade finance (0.4%) — consistent ~0.4% rate across all three, another likely data-generation artifact rather than three independent bugs. Not yet deduplicated by these profiling scripts (profiling only, per scope) — **whoever writes the aggregation step needs to decide whether to `.drop_duplicates()` first**, since summing raw amounts would double-count these rows.

### Needs a team decision (flagging, not deciding unilaterally — same approach as the cost_of_sales proxy call)

1. **Should exact duplicate rows be dropped before aggregation, and on what key?** Options: drop full-row duplicates (`.drop_duplicates()` with no subset — safest, only removes rows that are byte-for-byte identical across every column including reference/beneficiary/memo), or something narrower. Recommend the safest option (full-row) since it can't accidentally remove two genuinely-identical-looking-but-different transactions that merely share the same amount/date/entity.
2. **Is the reused `transaction_id` / `instrument_id` pattern expected synthetic-data behavior, or a generation bug worth flagging back to whoever produced the datasets?** It doesn't block the wallet-share pillar aggregation (keyed on `entity_id`), but it would surprise anyone who assumes these IDs are unique primary keys, and it's worth knowing which before it's cited as "transaction count" anywhere in the deck.
3. **Can `value_zar` / `amount_zar` conversion accuracy be verified at all?** None of the three files carries an FX-rate or original-currency-amount column, so there's no way to independently check the ZAR conversion the way the external financials extraction did (with a documented spot rate + source + date). If this matters for the write-up's rigor claims, it needs to be either accepted as a synthetic-data given or clarified with whoever generated the hackathon data.

### Out of scope for this step (per instructions — profiling only)

No cleaning, deduplication, or Share-of-Wallet calculation logic was written. The three flags above are handoffs to whoever builds the aggregation step next (the pillar-spend-split build already spec'd in `docs/superpowers/specs/2026-08-08-pillar-spend-split-design.md`), not resolved here.
