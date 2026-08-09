# trade_finance.csv — Profiling Report

## Schema

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

## Row counts & date coverage

Rows: 20,303
Date range: 2023-07-01 -> 2026-06-30
All rows fall within the stated 2023-07-01 -> 2026-06-30 window.
Rows whose `date + tenor_days` implied maturity falls after 2026-06-30 (not an error — just means the instrument matures beyond the data window): 2,164

### Entity coverage

Confirmed entities (from `financials_extracted_v2.csv`): 20 | Distinct entities in this dataset: 20 | Exact-string matches: 20

**MATCH** — entity_name set is identical to the confirmed 20. No join-blocking name issues.

`entity_id` <-> `entity_name` is a clean 1:1 mapping (no entity_id maps to >1 name or vice versa).

## Missing values & duplicates

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

## Outliers / data quality issues

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

## Currency

No separate `currency` column — `value_zar` is named as already ZAR-converted, and there is no FX-rate column in this file to independently verify the conversion, same caveat as `cross_border_payments.csv`.

## Join feasibility

- To other internal datasets: `entity_id` (confirmed 1:1 with `entity_name` above) — same key used in `transactional_banking.csv` and `cross_border_payments.csv`.
- To `financials_extracted_v2.csv`: `entity_name`, exact string match (see Entity coverage above).
