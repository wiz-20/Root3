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

cross_border = pd.read_csv(CROSS_BORDER_DIR)
trade_finance = pd.read_csv(TRADE_DIR)
transactional_banking = pd.read_csv(TRANSACTIONAL_DIR)

dates_2024 = [["2024-01-01", "2024-12-31"], ["2024-01-01", "2024-12-31"], ["2023-07-01", "2024-06-30"], ["2023-07-01", "2024-06-30"], ["2023-07-01", "2024-06-30"], ["2023-07-01", "2024-06-30"], ["2023-09-01", "2024-08-31"], ["2024-01-01", "2024-12-31"],
         ["2024-01-01", "2024-12-31"], ["2024-01-01", "2024-12-31"], ["2023-04-01", "2024-03-31"], ["2024-01-01", "2024-12-31"], ["2023-07-01", "2024-06-30"], ["2023-10-01", "2024-09-30"], ["2023-04-01", "2024-03-31"], ["2024-01-01", "2024-12-31"], ["2024-01-01", "2024-12-31"],
         ["2023-07-01", "2024-06-30"], ["2024-01-01", "2024-12-31"], ["2023-04-01", "2024-03-31"]]


dates_2025 = [["2025-01-01", "2025-12-31"], ["2025-01-01", "2025-12-31"], ["2024-07-01", "2025-06-30"], ["2024-07-01", "2025-06-30"], ["2024-07-01", "2025-06-30"], ["2024-07-01", "2025-06-30"], ["2024-09-01", "2025-08-31"], ["2025-01-01", "2025-12-31"],
         ["2025-01-01", "2025-12-31"], ["2025-01-01", "2025-12-31"], ["2024-04-01", "2025-03-31"], ["2025-01-01", "2025-12-31"], ["2024-07-01", "2025-06-30"], ["2024-10-01", "2025-09-30"], ["2024-04-01", "2025-03-31"], ["2025-01-01", "2025-12-31"], ["2025-01-01", "2025-12-31"],
         ["2024-07-01", "2025-06-30"], ["2025-01-01", "2025-12-31"], ["2024-04-01", "2025-03-31"]]


cross_border = cross_border.sort_values(by="entity_name", ascending=True).reset_index(drop=True)
cross_border["date"] = pd.to_datetime(cross_border["date"])

entities = cross_border["entity_name"].drop_duplicates().tolist()

date_ranges_2024 = {
    entity: (pd.Timestamp(dates_2024[i][0]), pd.Timestamp(dates_2024[i][1]))
    for i, entity in enumerate(entities)
}

date_ranges_2025 = {
    entity: (pd.Timestamp(dates_2025[i][0]), pd.Timestamp(dates_2025[i][1]))
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

cross_border_2024 = cross_border
cross_border_2025 = cross_border
cross_border_2026 = cross_border

#2024 financial year data
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


cross_border = pd.concat([cross_border_2024, cross_border_2025, cross_border_2026], ignore_index=True)





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


cross_border_summary = pd.DataFrame(
    revenue_df.merge(expense_df, on=["entity_name", "year"])
)

cross_border_summary.columns = [
    "entity_name",
    "year",
    "foreign_revenue",
    "foreign_expenses"
]


#Write the analysis data to the gold layer (as .csv files)
GOLD_DIR = ROOT / "gold"
GOLD_DIR.mkdir(parents=True, exist_ok=True)
cross_border_summary.to_csv(GOLD_DIR / "cross_border_gold.csv", index=False)