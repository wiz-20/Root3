import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# Raw Syn Bank datasets live at the repo root (see .gitignore comment) - every teammate
# keeps their own local copy there, not under a data/ subfolder.
CROSS_BORDER_DIR = ROOT / "cross_border_payments.csv"
TRADE_DIR = ROOT / "trade_finance.csv"
TRANSACTIONAL_DIR = ROOT / "transactional_banking.csv"

cross_border = pd.read_csv(CROSS_BORDER_DIR)
trade_finance = pd.read_csv(TRADE_DIR)
transactional_banking = pd.read_csv(TRANSACTIONAL_DIR)

#Removes duplicated transactions
cross_border_deduped = cross_border.drop_duplicates()
trade_finance_deduped = trade_finance.drop_duplicates()
transactional_banking_deduped = transactional_banking.drop_duplicates()

#Removes the memo row (provides no value and just adds unnecessary computational overhead)
cross_border_deduped = cross_border_deduped.drop(columns=["memo"])
trade_finance_deduped = trade_finance_deduped.drop(columns=["memo"])
transactional_banking_deduped = transactional_banking_deduped.drop(columns=["memo"])

#Good data practice: keep the currency column consistent despite not being used downstream
transactional_banking_casing_fixed = transactional_banking_deduped.copy()
transactional_banking_casing_fixed["currency"] = transactional_banking_casing_fixed["currency"].str.upper()

#Write the transformed data to the silver layer (as .csv files)
SILVER_DIR = ROOT / "medallion-pipeline" / "silver"
SILVER_DIR.mkdir(parents=True, exist_ok=True)

cross_border_deduped.to_csv(SILVER_DIR / "cross_border_silver.csv", index=False)
trade_finance_deduped.to_csv(SILVER_DIR / "trade_finance_silver.csv", index=False)
transactional_banking_casing_fixed.to_csv(SILVER_DIR / "transactional_banking_silver.csv", index=False)