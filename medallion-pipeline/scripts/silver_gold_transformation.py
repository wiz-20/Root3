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


revenue_df = (
    cross_border[(cross_border["direction"] == "inbound") & (cross_border["date"] > "2025-06-30")]
    .loc[:, ["entity_name", "value_zar"]]
    .groupby("entity_name")["value_zar"]
    .sum()
    .reset_index()
)

expense_df = (
    cross_border[(cross_border["direction"] == "outbound") & (cross_border["date"] > "2025-06-30")]
    .loc[:, ["entity_name", "value_zar"]]
    .groupby("entity_name")["value_zar"]
    .sum()
    .reset_index()
)

cross_border_summary = pd.DataFrame(revenue_df.merge(expense_df, on="entity_name"))

cross_border_summary.columns = ["entity_name", "foreign_revenue", "foreign_expenses"]

print(cross_border_summary)