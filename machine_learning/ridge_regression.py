from sklearn.linear_model import Ridge
import pandas as pd
from pathlib import Path
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import GroupShuffleSplit
import joblib


# ============================================================
# MODEL INITIALISATION
# ============================================================

transactional_model = Ridge(alpha=1.0)
trade_model = Ridge(alpha=1.0)
fx_model = Ridge(alpha=1.0)


# ============================================================
# PATHS
# ============================================================

ROOT = Path(__file__).resolve().parents[1]

external_data = pd.read_csv(
    ROOT / "hackathon-finreports/_extracted/financials_multiyear.csv"
)

CROSS_BORDER_DIR = (
    ROOT
    / "medallion-pipeline"
    / "gold"
    / "cross_border_gold.csv"
)

TRADE_DIR = (
    ROOT
    / "medallion-pipeline"
    / "gold"
    / "trade_finance_gold.csv"
)

TRANSACTIONAL_DIR = (
    ROOT
    / "medallion-pipeline"
    / "gold"
    / "transactional_banking_gold.csv"
)


# ============================================================
# IMPORT INTERNAL SYNBANK GOLD DATASETS
# ============================================================

fx_internal = pd.read_csv(CROSS_BORDER_DIR)
transactional_internal = pd.read_csv(TRANSACTIONAL_DIR)
trade_internal = pd.read_csv(TRADE_DIR)


# ============================================================
# PREPARE EXTERNAL TRADE DATA
# ============================================================

trade_external_data = external_data[
    [
        "entity_name",
        "fiscal_year",
        "trade_receivables_zar_m",
        "trade_payables_zar_m"
    ]
]

trade_external_data["trade_receivables_zar_m"] = (
    trade_external_data["trade_receivables_zar_m"]
    * 1000000.0
)

trade_external_data["trade_payables_zar_m"] = (
    trade_external_data["trade_payables_zar_m"]
    * 1000000.0
)

trade_external_data.columns = [
    "entity_name",
    "year",
    "trade_receivables",
    "trade_payables"
]

trade_external_data = trade_external_data.dropna()

print(
    "External trade data has",
    trade_external_data["trade_payables"].count(),
    "total records"
)


# ============================================================
# PREPARE EXTERNAL TRANSACTIONAL DATA
# ============================================================

transactional_external_data = external_data[
    [
        "entity_name",
        "fiscal_year",
        "revenue_zar_m",
        "cost_of_sales_zar_m"
    ]
]

transactional_external_data = (
    transactional_external_data.dropna()
)

transactional_external_data["revenue_zar_m"] = (
    transactional_external_data["revenue_zar_m"]
    * 1000000.0
)

transactional_external_data["cost_of_sales_zar_m"] = (
    transactional_external_data["cost_of_sales_zar_m"]
    * 1000000.0
)

transactional_external_data.columns = [
    "entity_name",
    "year",
    "revenue",
    "cost_of_sales"
]

print(
    "External transactional data has",
    transactional_external_data["revenue"].count(),
    "total records"
)


# ============================================================
# PREPARE EXTERNAL FX DATA
# ============================================================

fx_external_data = external_data[
    [
        "entity_name",
        "fiscal_year",
        "revenue_zar_m",
        "foreign_revenue_pct"
    ]
]

fx_external_data = fx_external_data.dropna()

print(
    "External FX data has",
    fx_external_data["revenue_zar_m"].count(),
    "total records"
)

fx_external_data["foreign_revenue"] = (
    (
        fx_external_data["revenue_zar_m"]
        * 1000000.0
    )
    * (
        fx_external_data["foreign_revenue_pct"]
        / 100.0
    )
)

fx_external_data = fx_external_data.drop(
    columns=[
        "revenue_zar_m",
        "foreign_revenue_pct"
    ]
)

fx_external_data.columns = [
    "entity_name",
    "year",
    "foreign_revenue"
]


# ============================================================
# TRADE FINANCE ML MODEL
# ============================================================

print("ML MODEL FOR THE TRADE FINANCE DATA BELOW:")

trade = pd.merge(
    trade_external_data,
    trade_internal,
    on=("year", "entity_name")
)

trade["share_of_trade_receivables"] = (
    trade["synbank_trade_receivables"]
    / trade["trade_receivables"]
)

trade["share_of_trade_payables"] = (
    trade["synbank_trade_payables"]
    / trade["trade_payables"]
)

trade = trade.drop(
    columns=[
        "trade_receivables",
        "trade_payables"
    ]
)

y_trade = trade[
    [
        "share_of_trade_receivables",
        "share_of_trade_payables"
    ]
]

X_trade = trade[
    [
        "synbank_trade_receivables",
        "synbank_trade_payables"
    ]
]

groups = trade["entity_name"]

group_split = GroupShuffleSplit(
    n_splits=1,
    test_size=0.2,
    random_state=42
)

train_idx, test_idx = next(
    group_split.split(
        X_trade,
        y_trade,
        groups=groups
    )
)

X_trade_train = X_trade.iloc[train_idx]
X_trade_test = X_trade.iloc[test_idx]

y_trade_train = y_trade.iloc[train_idx]
y_trade_test = y_trade.iloc[test_idx]

print("X_train shape:", X_trade_train.shape)
print("X_test shape:", X_trade_test.shape)
print("y_train shape:", y_trade_train.shape)
print("y_test shape:", y_trade_test.shape)

trade_scaler = StandardScaler()

X_trade_train_scaled = trade_scaler.fit_transform(
    X_trade_train
)

X_trade_test_scaled = trade_scaler.transform(
    X_trade_test
)

trade_model.fit(
    X_trade_train_scaled,
    y_trade_train
)

y_trade_pred = trade_model.predict(
    X_trade_test_scaled
)

print(
    "Receivables R²:",
    r2_score(
        y_trade_test[
            "share_of_trade_receivables"
        ],
        y_trade_pred[:, 0]
    )
)

print(
    "Payables R²:",
    r2_score(
        y_trade_test[
            "share_of_trade_payables"
        ],
        y_trade_pred[:, 1]
    )
)

print(
    "Receivables MSE:",
    mean_squared_error(
        y_trade_test[
            "share_of_trade_receivables"
        ],
        y_trade_pred[:, 0]
    )
)

print(
    "Payables MSE:",
    mean_squared_error(
        y_trade_test[
            "share_of_trade_payables"
        ],
        y_trade_pred[:, 1]
    )
)

results = y_trade_test.copy()

results["predicted_receivables"] = (
    y_trade_pred[:, 0]
)

results["predicted_payables"] = (
    y_trade_pred[:, 1]
)

print(results)


# ============================================================
# TRANSACTIONAL BANKING ML MODEL
# ============================================================

print("ML MODEL FOR THE TRANSACTIONAL DATA BELOW:")

transactional = pd.merge(
    transactional_external_data,
    transactional_internal,
    on=("year", "entity_name")
)

transactional["share_of_revenue"] = (
    transactional["collections"]
    / transactional["revenue"]
)

transactional["share_of_cost_of_sales"] = (
    transactional["supplier_payments"]
    / transactional["cost_of_sales"]
)

transactional = transactional.drop(
    columns=[
        "revenue",
        "cost_of_sales"
    ]
)

transactional.columns = [
    "entity_name",
    "year",
    "synbank_collections",
    "synbank_supplier_payments",
    "share_of_revenue",
    "share_of_cost_of_sales"
]

y_transactional = transactional[
    [
        "share_of_revenue",
        "share_of_cost_of_sales"
    ]
]

X_transactional = transactional[
    [
        "synbank_collections",
        "synbank_supplier_payments"
    ]
]

groups = transactional["entity_name"]

group_split = GroupShuffleSplit(
    n_splits=1,
    test_size=0.2,
    random_state=42
)

train_idx, test_idx = next(
    group_split.split(
        X_transactional,
        y_transactional,
        groups=groups
    )
)

X_transactional_train = (
    X_transactional.iloc[train_idx]
)

X_transactional_test = (
    X_transactional.iloc[test_idx]
)

y_transactional_train = (
    y_transactional.iloc[train_idx]
)

y_transactional_test = (
    y_transactional.iloc[test_idx]
)

print(
    "X_train shape:",
    X_transactional_train.shape
)

print(
    "X_test shape:",
    X_transactional_test.shape
)

print(
    "y_train shape:",
    y_transactional_train.shape
)

print(
    "y_test shape:",
    y_transactional_test.shape
)

transactional_scaler = StandardScaler()

X_transactional_train_scaled = (
    transactional_scaler.fit_transform(
        X_transactional_train
    )
)

X_transactional_test_scaled = (
    transactional_scaler.transform(
        X_transactional_test
    )
)

transactional_model.fit(
    X_transactional_train_scaled,
    y_transactional_train
)

y_transactional_pred = (
    transactional_model.predict(
        X_transactional_test_scaled
    )
)

print(
    "Revenue R²:",
    r2_score(
        y_transactional_test[
            "share_of_revenue"
        ],
        y_transactional_pred[:, 0]
    )
)

print(
    "Cost R²:",
    r2_score(
        y_transactional_test[
            "share_of_cost_of_sales"
        ],
        y_transactional_pred[:, 1]
    )
)

results = y_transactional_test.copy()

results["predicted_revenue"] = (
    y_transactional_pred[:, 0]
)

results["predicted_cost"] = (
    y_transactional_pred[:, 1]
)

print(results)


# ============================================================
# FX ML MODEL
# ============================================================

print("ML MODEL FOR THE FX DATA BELOW:")

fx = pd.merge(
    fx_external_data,
    fx_internal,
    on=("year", "entity_name")
)

fx["share_of_foreign_revenue"] = (
    fx["cross_border_inflows"]
    / fx["foreign_revenue"]
)

# Remove invalid shares caused by division by zero
fx = fx.replace([np.inf, -np.inf], np.nan)
fx = fx.dropna(subset=["share_of_foreign_revenue"])

fx = fx.drop(
    columns=[
        "foreign_revenue"
    ]
)

y_fx = fx[
    "share_of_foreign_revenue"
]

X_fx = fx[
    [
        "cross_border_inflows"
    ]
]

groups = fx["entity_name"]

group_split = GroupShuffleSplit(
    n_splits=1,
    test_size=0.2,
    random_state=42
)

train_idx, test_idx = next(
    group_split.split(
        X_fx,
        y_fx,
        groups=groups
    )
)

X_fx_train = X_fx.iloc[train_idx]
X_fx_test = X_fx.iloc[test_idx]

y_fx_train = y_fx.iloc[train_idx]
y_fx_test = y_fx.iloc[test_idx]

print("X_train shape:", X_fx_train.shape)
print("X_test shape:", X_fx_test.shape)
print("y_train shape:", y_fx_train.shape)
print("y_test shape:", y_fx_test.shape)

fx_scaler = StandardScaler()

X_fx_train_scaled = fx_scaler.fit_transform(
    X_fx_train
)

X_fx_test_scaled = fx_scaler.transform(
    X_fx_test
)

fx_model.fit(
    X_fx_train_scaled,
    y_fx_train
)

y_fx_pred = fx_model.predict(
    X_fx_test_scaled
)

print(
    "Foreign Revenue R²:",
    r2_score(
        y_fx_test,
        y_fx_pred
    )
)

print(
    "Foreign Revenue MSE:",
    mean_squared_error(
        y_fx_test,
        y_fx_pred
    )
)

results = y_fx_test.to_frame()

results["predicted_foreign_revenue"] = (
    y_fx_pred
)

print(results)



# ============================================================
# SAVE TRAINED MODELS AND SCALERS
# ============================================================

MODELS_DIR = ROOT / "machine_learning" / "models"

MODELS_DIR.mkdir(
    parents=True,
    exist_ok=True
)

joblib.dump(
    trade_model,
    MODELS_DIR / "trade_model.pkl"
)

joblib.dump(
    trade_scaler,
    MODELS_DIR / "trade_scaler.pkl"
)

joblib.dump(
    transactional_model,
    MODELS_DIR / "transactional_model.pkl"
)

joblib.dump(
    transactional_scaler,
    MODELS_DIR / "transactional_scaler.pkl"
)

joblib.dump(
    fx_model,
    MODELS_DIR / "fx_model.pkl"
)

joblib.dump(
    fx_scaler,
    MODELS_DIR / "fx_scaler.pkl"
)

print(f"Models and scalers saved to: {MODELS_DIR}")