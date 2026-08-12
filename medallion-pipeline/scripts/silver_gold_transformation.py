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

dates = [["2025-01-01", "2025-12-31"], ["2025-01-01", "2025-12-31"], ["2024-07-01", "2025-06-30"], ["2024-07-01", "2025-06-30"], ["2024-07-01", "2025-06-30"], ["2024-07-01", "2025-06-30"], ["2024-09-01", "2025-08-31"], ["2025-01-01", "2025-12-31"],
         ["2025-01-01", "2025-12-31"], ["2025-01-01", "2025-12-31"], ["2024-04-01", "2025-03-31"], ["2025-01-01", "2025-12-31"], ["2024-07-01", "2025-06-30"], ["2024-10-01", "2025-09-30"], ["2024-04-01", "2025-03-31"], ["2025-01-01", "2025-12-31"], ["2025-01-01", "2025-12-31"],
         ["2024-07-01", "2025-06-30"], ["2025-01-01", "2025-12-31"], ["2024-04-01", "2025-03-31"]]


cross_border = cross_border.sort_values(by="entity_name", ascending=True).reset_index(drop=True)
cross_border["date"] = pd.to_datetime(cross_border["date"])

entities = cross_border["entity_name"].drop_duplicates().tolist()

date_ranges = {
    entity: (pd.Timestamp(dates[i][0]), pd.Timestamp(dates[i][1]))
    for i, entity in enumerate(entities)
}

cross_border["start_date"] = cross_border["entity_name"].map(
    lambda x: date_ranges[x][0]
)

cross_border["end_date"] = cross_border["entity_name"].map(
    lambda x: date_ranges[x][1]
)

cross_border = cross_border[
    (cross_border["date"] >= cross_border["start_date"]) &
    (cross_border["date"] <= cross_border["end_date"])
]

revenue_df = (
    cross_border[cross_border["direction"] == "inbound"]
    .loc[:, ["entity_name", "value_zar"]]
    .groupby("entity_name")["value_zar"]
    .sum()
    .reset_index()
)

expense_df = (
    cross_border[cross_border["direction"] == "outbound"]
    .loc[:, ["entity_name", "value_zar"]]
    .groupby("entity_name")["value_zar"]
    .sum()
    .reset_index()
)

cross_border_summary = pd.DataFrame(
    revenue_df.merge(expense_df, on="entity_name")
)

cross_border_summary.columns = [
    "entity_name",
    "foreign_revenue",
    "foreign_expenses"
]


#Write the analysis data to the gold layer (as .csv files)
GOLD_DIR = ROOT / "gold"
GOLD_DIR.mkdir(parents=True, exist_ok=True)
cross_border_summary.to_csv(GOLD_DIR / "cross_border_gold.csv", index=False)