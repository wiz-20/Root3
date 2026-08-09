# cross_border_payments.csv — Profiling Report

## Schema

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

## Row counts & date coverage

Rows: 241,117
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

## Outliers / data quality issues

`value_zar` <= 0: 0 rows
`direction` outside {inbound, outbound}: 0 rows
`corridor_type` outside {intercompany, trade, other}: 0 rows

Distinct `currency_pair` values (5): AED/ZAR, CNY/ZAR, EUR/ZAR, GBP/ZAR, USD/ZAR

`counterparty_country` empty-string (as opposed to null): 0 rows

## Currency

No separate `currency` column — `value_zar` is named as already ZAR-converted, and there is no FX-rate column in this file to independently verify the conversion. `currency_pair` describes the corridor (e.g. `ZAR/USD`) but is not itself a unit the `value_zar` figure is denominated in. **Flag for team:** we cannot verify from this file alone whether `value_zar` was converted at a point-in-time rate per transaction or a static rate — worth confirming with whoever generated this synthetic data, since it affects whether small time-series distortions are meaningful.

## Join feasibility

- To other internal datasets: `entity_id` (confirmed 1:1 with `entity_name` above) — same key used in `transactional_banking.csv` and `trade_finance.csv`.
- To `financials_extracted_v2.csv`: `entity_name`, exact string match (see Entity coverage above).
