"""
The Silver -> Gold step of the medallion pipeline: cleaned and deduplicated data is used to
extract useful insights into the SynBank data (to be used alongside external data)

Inputs:
1. medallion-pipeline/silver/cross_border_silver.csv
2. medallion-pipeline/silver/trade_finance_silver.csv
3. medallion-pipeline/silver/transactional_banking_silver.csv

Outputs:
1. medallion-pipeline/gold/cross_border_gold.csv
2. medallion-pipeline/gold/trade_finance_gold.csv
3. medallion-pipeline/gold/transactional_banking_silver.csv
"""

import pandas as pd
from pathlib import Path
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[2]

CROSS_BORDER_DIR = ROOT / "silver" / "cross_border_silver.csv"
TRADE_DIR = ROOT / "silver" / "trade_finance_silver.csv"
TRANSACTIONAL_DIR = ROOT / "silver" / "transactional_banking_silver.csv"

GOLD_DIR = ROOT / "gold"
GOLD_DIR.mkdir(parents=True, exist_ok=True)

cross_border = pd.read_csv(CROSS_BORDER_DIR)
trade_finance = pd.read_csv(TRADE_DIR)
transactional_banking = pd.read_csv(TRANSACTIONAL_DIR)

# Silver-layer CSVs round-trip dates as strings - cross_border and trade_finance are each
# converted back to datetime further down, but transactional_banking wasn't, which crashed
# every date-range comparison below with "Invalid comparison between dtype=str and DatetimeArray".
transactional_banking["date"] = pd.to_datetime(transactional_banking["date"])

cross_border = (
    cross_border
    .sort_values(by="entity_name", ascending=True)
    .reset_index(drop=True)
)

cross_border["date"] = pd.to_datetime(cross_border["date"])

# Per-entity fiscal-year windows are derived directly from each company's disclosed
# fiscal_year_end (hackathon-finreports/_extracted/financials_multiyear.csv) rather than a
# hand-typed, position-indexed list - a hardcoded list keyed by list position silently breaks
# the moment its order doesn't exactly match the alphabetically-sorted entity list it's zipped
# against (7/20 entities - Clicks, Glencore, OUTsurance, Pepkor, Prosus, Sanlam, Shoprite - were
# getting another company's fiscal-year window under the old hardcoded lists, contaminating the
# internal/external pairing used for ML training).
_financials = pd.read_csv(
    REPO_ROOT / "hackathon-finreports" / "_extracted" / "financials_multiyear.csv"
)
_financials["fye"] = pd.to_datetime(_financials["fiscal_year_end"], format="%d %B %Y")
_financials["window_start"] = _financials["fye"] - pd.DateOffset(years=1) + pd.Timedelta(days=1)


def _date_ranges_for_year(fiscal_year: int) -> dict:
    subset = _financials[_financials["fiscal_year"] == fiscal_year]
    return {
        row["entity_name"]: (row["window_start"], row["fye"])
        for _, row in subset.iterrows()
    }


date_ranges_2024 = _date_ranges_for_year(2024)
date_ranges_2025 = _date_ranges_for_year(2025)
date_ranges_2026 = _date_ranges_for_year(2026)


############################################
# 1. Extract Features from Cross-Border Data
############################################

cross_border_2024 = cross_border
cross_border_2025 = cross_border
cross_border_2026 = cross_border


# 2024 financial year data
cross_border_2024["start_date"] = cross_border["entity_name"].map(
    lambda x: date_ranges_2024[x][0]
)

cross_border_2024["end_date"] = cross_border["entity_name"].map(
    lambda x: date_ranges_2024[x][1]
)

cross_border_2024 = cross_border[
    (cross_border["date"] >= cross_border_2024["start_date"]) &
    (cross_border["date"] <= cross_border_2024["end_date"])
].copy()

cross_border_2024["year"] = "2024"


# 2025 financial year data
cross_border_2025["start_date"] = cross_border["entity_name"].map(
    lambda x: date_ranges_2025[x][0]
)

cross_border_2025["end_date"] = cross_border["entity_name"].map(
    lambda x: date_ranges_2025[x][1]
)

cross_border_2025 = cross_border[
    (cross_border["date"] >= cross_border_2025["start_date"]) &
    (cross_border["date"] <= cross_border_2025["end_date"])
].copy()

cross_border_2025["year"] = "2025"


# 2026 financial year data
cross_border_2026 = cross_border[
    cross_border["entity_name"].isin(date_ranges_2026.keys())
].copy()

cross_border_2026["start_date"] = cross_border_2026["entity_name"].map(
    lambda x: date_ranges_2026[x][0]
)

cross_border_2026["end_date"] = cross_border_2026["entity_name"].map(
    lambda x: date_ranges_2026[x][1]
)

cross_border_2026 = cross_border_2026[
    (cross_border_2026["date"] >= cross_border_2026["start_date"]) &
    (cross_border_2026["date"] <= cross_border_2026["end_date"])
].copy()

cross_border_2026["year"] = "2026"


cross_border = pd.concat(
    [
        cross_border_2024,
        cross_border_2025,
        cross_border_2026
    ],
    ignore_index=True
)


revenue_df = (
    cross_border[cross_border["direction"] == "inbound"]
    .loc[:, ["entity_name", "year", "value_zar"]]
    .groupby(["entity_name", "year"], as_index=False)["value_zar"]
    .sum()
    .rename(columns={"value_zar": "foreign_revenue"})
)


expense_df = (
    cross_border[cross_border["direction"] == "outbound"]
    .loc[:, ["entity_name", "year", "value_zar"]]
    .groupby(["entity_name", "year"], as_index=False)["value_zar"]
    .sum()
    .rename(columns={"value_zar": "foreign_expenses"})
)



cross_border_base = (
    cross_border[["entity_name", "year"]]
    .drop_duplicates()
)

cross_border_summary = (
    cross_border_base
    .merge(
        revenue_df,
        on=["entity_name", "year"],
        how="left"
    )
    .merge(
        expense_df,
        on=["entity_name", "year"],
        how="left"
    )
)

cross_border_summary.columns = [
    "entity_name",
    "year",
    "cross_border_inflows",
    "cross_border_outflows"
]

cross_border_summary[
    ["cross_border_inflows", "cross_border_outflows"]
] = cross_border_summary[
    ["cross_border_inflows", "cross_border_outflows"]
].fillna(0)


# Write the analysis data to the gold layer
cross_border_summary.to_csv(
    GOLD_DIR / "cross_border_gold.csv",
    index=False
)


############################################
# 2. Extract Features from Transactional Data
############################################

transactional_banking_2024 = transactional_banking
transactional_banking_2025 = transactional_banking
transactional_banking_2026 = transactional_banking


# 2024 financial year data
transactional_banking_2024["start_date"] = (
    transactional_banking["entity_name"].map(
        lambda x: date_ranges_2024[x][0]
    )
)

transactional_banking_2024["end_date"] = (
    transactional_banking["entity_name"].map(
        lambda x: date_ranges_2024[x][1]
    )
)

transactional_banking_2024 = transactional_banking[
    (
        transactional_banking["date"]
        >= transactional_banking_2024["start_date"]
    ) &
    (
        transactional_banking["date"]
        <= transactional_banking_2024["end_date"]
    )
].copy()

transactional_banking_2024["year"] = "2024"


# 2025 financial year data
transactional_banking_2025["start_date"] = (
    transactional_banking["entity_name"].map(
        lambda x: date_ranges_2025[x][0]
    )
)

transactional_banking_2025["end_date"] = (
    transactional_banking["entity_name"].map(
        lambda x: date_ranges_2025[x][1]
    )
)

transactional_banking_2025 = transactional_banking[
    (
        transactional_banking["date"]
        >= transactional_banking_2025["start_date"]
    ) &
    (
        transactional_banking["date"]
        <= transactional_banking_2025["end_date"]
    )
].copy()

transactional_banking_2025["year"] = "2025"


# 2026 financial year data
transactional_banking_2026 = transactional_banking[
    transactional_banking["entity_name"].isin(
        date_ranges_2026.keys()
    )
].copy()

transactional_banking_2026["start_date"] = (
    transactional_banking_2026["entity_name"].map(
        lambda x: date_ranges_2026[x][0]
    )
)

transactional_banking_2026["end_date"] = (
    transactional_banking_2026["entity_name"].map(
        lambda x: date_ranges_2026[x][1]
    )
)

transactional_banking_2026 = transactional_banking_2026[
    (
        transactional_banking_2026["date"]
        >= transactional_banking_2026["start_date"]
    ) &
    (
        transactional_banking_2026["date"]
        <= transactional_banking_2026["end_date"]
    )
].copy()

transactional_banking_2026["year"] = "2026"


transactional_banking = pd.concat(
    [
        transactional_banking_2024,
        transactional_banking_2025,
        transactional_banking_2026
    ],
    ignore_index=True
)


collections = (
    transactional_banking[
        transactional_banking["leg_type"] == "collections"
    ]
    .loc[:, ["entity_name", "year", "amount_zar"]]
    .groupby(["entity_name", "year"], as_index=False)["amount_zar"]
    .sum()
)


supplier_payments = (
    transactional_banking[
        transactional_banking["leg_type"] == "supplier_payments"
    ]
    .loc[:, ["entity_name", "year", "amount_zar"]]
    .groupby(["entity_name", "year"], as_index=False)["amount_zar"]
    .sum()
)



transactional_base = (
    transactional_banking[["entity_name", "year"]]
    .drop_duplicates()
)

transactional_banking_summary = (
    transactional_base
    .merge(
        collections,
        on=["entity_name", "year"],
        how="left"
    )
    .merge(
        supplier_payments,
        on=["entity_name", "year"],
        how="left"
    )
)

transactional_banking_summary.columns = [
    "entity_name",
    "year",
    "collections",
    "supplier_payments"
]

transactional_banking_summary[
    ["collections", "supplier_payments"]
] = transactional_banking_summary[
    ["collections", "supplier_payments"]
].fillna(0)


# Write the analysis data to the gold layer
transactional_banking_summary.to_csv(
    GOLD_DIR / "transactional_banking_gold.csv",
    index=False
)


############################################
# 3. Extract Features from Trade Finance Data
############################################

trade_finance["date"] = pd.to_datetime(
    trade_finance["date"]
)


# 2024 financial year
trade_finance_2024 = trade_finance.copy()

trade_finance_2024["start_date"] = (
    trade_finance_2024["entity_name"].map(
        lambda x: date_ranges_2024[x][0]
    )
)

trade_finance_2024["end_date"] = (
    trade_finance_2024["entity_name"].map(
        lambda x: date_ranges_2024[x][1]
    )
)

trade_finance_2024 = trade_finance_2024[
    (
        trade_finance_2024["date"]
        >= trade_finance_2024["start_date"]
    ) &
    (
        trade_finance_2024["date"]
        <= trade_finance_2024["end_date"]
    )
].copy()

trade_finance_2024["year"] = "2024"


# 2025 financial year
trade_finance_2025 = trade_finance.copy()

trade_finance_2025["start_date"] = (
    trade_finance_2025["entity_name"].map(
        lambda x: date_ranges_2025[x][0]
    )
)

trade_finance_2025["end_date"] = (
    trade_finance_2025["entity_name"].map(
        lambda x: date_ranges_2025[x][1]
    )
)

trade_finance_2025 = trade_finance_2025[
    (
        trade_finance_2025["date"]
        >= trade_finance_2025["start_date"]
    ) &
    (
        trade_finance_2025["date"]
        <= trade_finance_2025["end_date"]
    )
].copy()

trade_finance_2025["year"] = "2025"


# 2026 financial year
trade_finance_2026 = trade_finance[
    trade_finance["entity_name"].isin(
        date_ranges_2026.keys()
    )
].copy()

trade_finance_2026["start_date"] = (
    trade_finance_2026["entity_name"].map(
        lambda x: date_ranges_2026[x][0]
    )
)

trade_finance_2026["end_date"] = (
    trade_finance_2026["entity_name"].map(
        lambda x: date_ranges_2026[x][1]
    )
)

trade_finance_2026 = trade_finance_2026[
    (
        trade_finance_2026["date"]
        >= trade_finance_2026["start_date"]
    ) &
    (
        trade_finance_2026["date"]
        <= trade_finance_2026["end_date"]
    )
].copy()

trade_finance_2026["year"] = "2026"


# Combine all financial years
trade_finance = pd.concat(
    [
        trade_finance_2024,
        trade_finance_2025,
        trade_finance_2026
    ],
    ignore_index=True
)


trade_payables = (
    trade_finance[
        (trade_finance["status"].isin(["active", "issued"])) &
        (trade_finance["direction"] == "import") &
        (
            trade_finance["instrument_type"]
            == "letters_of_credit"
        )
    ]
    .loc[:, ["entity_name", "year", "value_zar"]]
    .groupby(
        ["entity_name", "year"],
        as_index=False
    )["value_zar"]
    .sum()
    .rename(
        columns={
            "value_zar": "synbank_trade_payables"
        }
    )
)


trade_receivables = (
    trade_finance[
        (trade_finance["status"].isin(["active", "issued"])) &
        (trade_finance["direction"] == "export") &
        (
            (
                trade_finance["instrument_type"]
                == "letters_of_credit"
            ) |
            (
                trade_finance["instrument_type"]
                == "export_collections"
            )
        )
    ]
    .loc[:, ["entity_name", "year", "value_zar"]]
    .groupby(
        ["entity_name", "year"],
        as_index=False
    )["value_zar"]
    .sum()
    .rename(
        columns={
            "value_zar": "synbank_trade_receivables"
        }
    )
)




trade_finance_base = (
    trade_finance[["entity_name", "year"]]
    .drop_duplicates()
)

trade_finance_summary = (
    trade_finance_base
    .merge(
        trade_payables,
        on=["entity_name", "year"],
        how="left"
    )
    .merge(
        trade_receivables,
        on=["entity_name", "year"],
        how="left"
    )
)

trade_finance_summary[
    [
        "synbank_trade_payables",
        "synbank_trade_receivables"
    ]
] = trade_finance_summary[
    [
        "synbank_trade_payables",
        "synbank_trade_receivables"
    ]
].fillna(0)


trade_finance_summary.to_csv(
    GOLD_DIR / "trade_finance_gold.csv",
    index=False
)