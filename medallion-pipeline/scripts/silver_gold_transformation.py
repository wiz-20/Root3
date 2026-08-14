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

CROSS_BORDER_DIR = ROOT / "silver" / "cross_border_silver.csv"
TRADE_DIR = ROOT / "silver" / "trade_finance_silver.csv"
TRANSACTIONAL_DIR = ROOT / "silver" / "transactional_banking_silver.csv"

GOLD_DIR = ROOT / "gold"
GOLD_DIR.mkdir(parents=True, exist_ok=True)

cross_border = pd.read_csv(CROSS_BORDER_DIR)
trade_finance = pd.read_csv(TRADE_DIR)
transactional_banking = pd.read_csv(TRANSACTIONAL_DIR)


dates_2024 = [
    ["2024-01-01", "2024-12-31"],
    ["2024-01-01", "2024-12-31"],
    ["2023-07-01", "2024-06-30"],
    ["2023-07-01", "2024-06-30"],
    ["2023-07-01", "2024-06-30"],
    ["2023-07-01", "2024-06-30"],
    ["2023-09-01", "2024-08-31"],
    ["2024-01-01", "2024-12-31"],
    ["2024-01-01", "2024-12-31"],
    ["2024-01-01", "2024-12-31"],
    ["2023-04-01", "2024-03-31"],
    ["2024-01-01", "2024-12-31"],
    ["2023-07-01", "2024-06-30"],
    ["2023-10-01", "2024-09-30"],
    ["2023-04-01", "2024-03-31"],
    ["2024-01-01", "2024-12-31"],
    ["2024-01-01", "2024-12-31"],
    ["2023-07-01", "2024-06-30"],
    ["2024-01-01", "2024-12-31"],
    ["2023-04-01", "2024-03-31"]
]


dates_2025 = [
    ["2025-01-01", "2025-12-31"],
    ["2025-01-01", "2025-12-31"],
    ["2024-07-01", "2025-06-30"],
    ["2024-07-01", "2025-06-30"],
    ["2024-07-01", "2025-06-30"],
    ["2024-07-01", "2025-06-30"],
    ["2024-09-01", "2025-08-31"],
    ["2025-01-01", "2025-12-31"],
    ["2025-01-01", "2025-12-31"],
    ["2025-01-01", "2025-12-31"],
    ["2024-04-01", "2025-03-31"],
    ["2025-01-01", "2025-12-31"],
    ["2024-07-01", "2025-06-30"],
    ["2024-10-01", "2025-09-30"],
    ["2024-04-01", "2025-03-31"],
    ["2025-01-01", "2025-12-31"],
    ["2025-01-01", "2025-12-31"],
    ["2024-07-01", "2025-06-30"],
    ["2025-01-01", "2025-12-31"],
    ["2024-04-01", "2025-03-31"]
]


cross_border = (
    cross_border
    .sort_values(by="entity_name", ascending=True)
    .reset_index(drop=True)
)

cross_border["date"] = pd.to_datetime(cross_border["date"])

entities = cross_border["entity_name"].drop_duplicates().tolist()


date_ranges_2024 = {
    entity: (
        pd.Timestamp(dates_2024[i][0]),
        pd.Timestamp(dates_2024[i][1])
    )
    for i, entity in enumerate(entities)
}


date_ranges_2025 = {
    entity: (
        pd.Timestamp(dates_2025[i][0]),
        pd.Timestamp(dates_2025[i][1])
    )
    for i, entity in enumerate(entities)
}


date_ranges_2026 = {
    "Naspers": (
        pd.Timestamp("2025-04-01"),
        pd.Timestamp("2026-03-31")
    ),

    "Prosus": (
        pd.Timestamp("2025-04-01"),
        pd.Timestamp("2026-03-31")
    ),

    "Vodacom Group": (
        pd.Timestamp("2025-04-01"),
        pd.Timestamp("2026-03-31")
    )
}


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