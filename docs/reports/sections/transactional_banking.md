# transactional_banking.csv — Profiling Report

_Profiled with PySpark 4.2.0, local mode._

## Schema

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

## Row counts & date coverage

Rows: 2,802,875
Date range: 2023-07-01 -> 2026-06-30
All rows fall within the stated 2023-07-01 -> 2026-06-30 window.

### Entity coverage

Confirmed entities (from `financials_extracted_v2.csv`): 20 | Distinct entities in this dataset: 20 | Exact-string matches: 20

**MATCH** — entity_name set is identical to the confirmed 20. No join-blocking name issues.

`entity_id` <-> `entity_name` is a clean 1:1 mapping (no entity_id maps to >1 name or vice versa).

## Missing values & duplicates

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

## Outliers / data quality issues

`amount_zar` <= 0: 0 rows
`direction` outside {inbound, outbound}: 0 rows
`leg_type` outside ['collections', 'intercompany_sweeps', 'payroll', 'supplier_payments', 'tax']: 0 rows
`channel` outside ['Debit Order', 'EFT', 'Internal Transfer', 'RTC', 'SWIFT']: 0 rows

Distinct `currency` values (2): 'ZAR' (2,774,594), 'zar' (28,281)

## Currency

`amount_zar` is named as already ZAR-converted, and case-insensitively every row's `currency` is 'ZAR' — but the literal string varies by case ('ZAR', 'zar'). This is a **data-quality/formatting bug, not a currency-conversion issue**: no non-ZAR currency actually appears in this file, so there is nothing to convert. Flag for whoever consumes `currency` downstream (e.g. a groupby or filter on the literal string 'ZAR' would silently drop the lowercase rows) — worth normalizing case before use.

## Join feasibility

- To other internal datasets: `entity_id` (confirmed 1:1 with `entity_name` above) — same key used in `cross_border_payments.csv` and `trade_finance.csv`.
- To `financials_extracted_v2.csv`: `entity_name`, exact string match (see Entity coverage above).
