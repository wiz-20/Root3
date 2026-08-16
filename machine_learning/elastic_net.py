from sklearn.linear_model import ElasticNet
from sklearn.model_selection import LeaveOneGroupOut
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error, r2_score
import pandas as pd
from pathlib import Path
import numpy as np
import joblib

from wallet_math import derive_wallet_and_gap  # noqa: F401 - re-exported for notebook cells


# ============================================================
# MODEL HYPERPARAMETERS
# ============================================================

alphas = [
    0.00001,
    0.0001,
    0.001,
    0.01,
    0.1,
]

l1_ratios = [
    0.1,
    0.25,
    0.5,
    0.75,
    0.9,
]


# ============================================================
# PATHS
# ============================================================

ROOT = Path(__file__).resolve().parents[1]

external_data = pd.read_csv(
    ROOT / "hackathon-finreports/_extracted/financials_multiyear.csv"
)

CROSS_BORDER_DIR = (
    ROOT / "medallion-pipeline" / "gold" / "cross_border_gold.csv"
)

TRADE_DIR = (
    ROOT / "medallion-pipeline" / "gold" / "trade_finance_gold.csv"
)

TRANSACTIONAL_DIR = (
    ROOT / "medallion-pipeline" / "gold" / "transactional_banking_gold.csv"
)

MODELS_DIR = ROOT / "machine_learning" / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)


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
        "trade_payables_zar_m",
    ]
].copy()

trade_external_data["trade_receivables_zar_m"] *= 1000000.0
trade_external_data["trade_payables_zar_m"] *= 1000000.0

trade_external_data.columns = [
    "entity_name",
    "year",
    "trade_receivables",
    "trade_payables",
]

trade_external_data = trade_external_data.dropna()

print(
    "External trade data has",
    trade_external_data["trade_payables"].count(),
    "total records",
)


# ============================================================
# PREPARE EXTERNAL TRANSACTIONAL DATA
# ============================================================

transactional_external_data = external_data[
    [
        "entity_name",
        "fiscal_year",
        "revenue_zar_m",
        "cost_of_sales_zar_m",
    ]
].copy()

transactional_external_data = transactional_external_data.dropna()

transactional_external_data["revenue_zar_m"] *= 1000000.0
transactional_external_data["cost_of_sales_zar_m"] *= 1000000.0

transactional_external_data.columns = [
    "entity_name",
    "year",
    "revenue",
    "cost_of_sales",
]

print(
    "External transactional data has",
    transactional_external_data["revenue"].count(),
    "total records",
)


# ============================================================
# PREPARE EXTERNAL FX DATA
# ============================================================

fx_external_data = external_data[
    [
        "entity_name",
        "fiscal_year",
        "revenue_zar_m",
        "foreign_revenue_pct",
    ]
].copy()
fx_external_data = fx_external_data.dropna()

print(
    "External FX data has",
    fx_external_data["revenue_zar_m"].count(),
    "total records",
)

fx_external_data["foreign_revenue"] = (
    fx_external_data["revenue_zar_m"]
    * 1000000.0
    * (fx_external_data["foreign_revenue_pct"] / 100.0)
)

fx_external_data = fx_external_data.drop(
    columns=["revenue_zar_m", "foreign_revenue_pct"]
)

fx_external_data.columns = [
    "entity_name",
    "year",
    "foreign_revenue",
]


# ============================================================
# BUILD ML DATASETS
# ============================================================

# -------------------------- TRADE ----------------------------

trade = pd.merge(
    trade_external_data,
    trade_internal,
    on=("year", "entity_name"),
)

trade["share_of_trade_receivables"] = (
    trade["synbank_trade_receivables"] / trade["trade_receivables"]
)

trade["share_of_trade_payables"] = (
    trade["synbank_trade_payables"] / trade["trade_payables"]
)

trade = trade.replace([np.inf, -np.inf], np.nan)
trade = trade.dropna(
    subset=["share_of_trade_receivables", "share_of_trade_payables"]
)

X_trade = trade[
    ["synbank_trade_receivables", "synbank_trade_payables"]
]
y_trade_receivables = trade["share_of_trade_receivables"]
y_trade_payables = trade["share_of_trade_payables"]
groups_trade = trade["entity_name"]

print("\n--------------------------- TRADE FINANCE ---------------------------")
print("Trade observations:", len(trade))
print("Trade companies:", groups_trade.nunique())


# ---------------------- TRANSACTIONAL ------------------------

transactional = pd.merge(
    transactional_external_data,
    transactional_internal,
    on=("year", "entity_name"),
)

transactional["share_of_revenue"] = (
    transactional["collections"] / transactional["revenue"]
)

transactional["share_of_cost_of_sales"] = (
    transactional["supplier_payments"] / transactional["cost_of_sales"]
)

transactional = transactional.replace([np.inf, -np.inf], np.nan)
transactional = transactional.dropna(
    subset=["share_of_revenue", "share_of_cost_of_sales"]
)

transactional = transactional.rename(
    columns={
        "collections": "synbank_collections",
        "supplier_payments": "synbank_supplier_payments",
    }
)

X_transactional = transactional[
    ["synbank_collections", "synbank_supplier_payments"]
]
y_revenue = transactional["share_of_revenue"]
y_cost = transactional["share_of_cost_of_sales"]
groups_transactional = transactional["entity_name"]

print("\n-------------------------- TRANSACTIONAL ----------------------------")
print("Transactional observations:", len(transactional))
print("Transactional companies:", groups_transactional.nunique())


# ---------------------------- FX -----------------------------

fx = pd.merge(
    fx_external_data,
    fx_internal,
    on=("year", "entity_name"),
)


fx["share_of_foreign_revenue"] = (
    fx["cross_border_inflows"] / fx["foreign_revenue"]
)

fx = fx.replace([np.inf, -np.inf], np.nan)
fx = fx.dropna(subset=["share_of_foreign_revenue"])

X_fx = fx[["cross_border_inflows"]]
y_fx = fx["share_of_foreign_revenue"]
groups_fx = fx["entity_name"]

print(fx[fx["entity_name"] == "Sanlam"].head(10))

print("\n------------------------------ FX ----------------------------------")
print("FX observations:", len(fx))
print("FX companies:", groups_fx.nunique())


# ============================================================
# HELPER: LEAVE-ONE-COMPANY-OUT FOR ONE ELASTIC NET TARGET
# ============================================================

def logo_elastic_net_predictions(X, y, groups, alpha, l1_ratio):
    """
    Generate out-of-fold predictions using Leave-One-Group-Out CV.

    Each company is held out completely once. The scaler is fitted only
    on the training companies inside each fold, preventing data leakage.
    """
    logo = LeaveOneGroupOut()
    predictions = np.zeros(len(y), dtype=float)

    for train_idx, test_idx in logo.split(X, y, groups=groups):
        X_train = X.iloc[train_idx]
        X_test = X.iloc[test_idx]
        y_train = y.iloc[train_idx]

        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)

        model = ElasticNet(
            alpha=alpha,
            l1_ratio=l1_ratio,
            max_iter=10000,
        )

        model.fit(X_train_scaled, y_train)
        predictions[test_idx] = model.predict(X_test_scaled)

    return predictions


# ============================================================
# HYPERPARAMETER SEARCH — EACH TARGET OPTIMISED SEPARATELY
# ============================================================

best = {
    "trade_receivables": {
        "r2": -np.inf,
        "mse": np.inf,
        "alpha": None,
        "l1_ratio": None,
    },
    "trade_payables": {
        "r2": -np.inf,
        "mse": np.inf,
        "alpha": None,
        "l1_ratio": None,
    },
    "transactional_revenue": {
        "r2": -np.inf,
        "mse": np.inf,
        "alpha": None,
        "l1_ratio": None,
    },
    "transactional_cost": {
        "r2": -np.inf,
        "mse": np.inf,
        "alpha": None,
        "l1_ratio": None,
    },
    "fx_foreign_revenue": {
        "r2": -np.inf,
        "mse": np.inf,
        "alpha": None,
        "l1_ratio": None,
    },
}

for alpha in alphas:
    for l1 in l1_ratios:

        # ----------------------- TRADE -----------------------
        receivables_predictions = logo_elastic_net_predictions(
            X_trade,
            y_trade_receivables,
            groups_trade,
            alpha,
            l1,
        )

        payables_predictions = logo_elastic_net_predictions(
            X_trade,
            y_trade_payables,
            groups_trade,
            alpha,
            l1,
        )

        receivables_r2 = r2_score(
            y_trade_receivables,
            receivables_predictions,
        )
        receivables_mse = mean_squared_error(
            y_trade_receivables,
            receivables_predictions,
        )

        payables_r2 = r2_score(
            y_trade_payables,
            payables_predictions,
        )
        payables_mse = mean_squared_error(
            y_trade_payables,
            payables_predictions,
        )

        if receivables_r2 > best["trade_receivables"]["r2"]:
            best["trade_receivables"] = {
                "r2": receivables_r2,
                "mse": receivables_mse,
                "alpha": alpha,
                "l1_ratio": l1,
            }

        if payables_r2 > best["trade_payables"]["r2"]:
            best["trade_payables"] = {
                "r2": payables_r2,
                "mse": payables_mse,
                "alpha": alpha,
                "l1_ratio": l1,
            }


        # ------------------- TRANSACTIONAL -------------------
        revenue_predictions = logo_elastic_net_predictions(
            X_transactional,
            y_revenue,
            groups_transactional,
            alpha,
            l1,
        )

        cost_predictions = logo_elastic_net_predictions(
            X_transactional,
            y_cost,
            groups_transactional,
            alpha,
            l1,
        )

        revenue_r2 = r2_score(y_revenue, revenue_predictions)
        revenue_mse = mean_squared_error(y_revenue, revenue_predictions)

        cost_r2 = r2_score(y_cost, cost_predictions)
        cost_mse = mean_squared_error(y_cost, cost_predictions)

        if revenue_r2 > best["transactional_revenue"]["r2"]:
            best["transactional_revenue"] = {
                "r2": revenue_r2,
                "mse": revenue_mse,
                "alpha": alpha,
                "l1_ratio": l1,
            }

        if cost_r2 > best["transactional_cost"]["r2"]:
            best["transactional_cost"] = {
                "r2": cost_r2,
                "mse": cost_mse,
                "alpha": alpha,
                "l1_ratio": l1,
            }


        # ------------------------- FX ------------------------
        fx_predictions = logo_elastic_net_predictions(
            X_fx,
            y_fx,
            groups_fx,
            alpha,
            l1,
        )

        fx_r2 = r2_score(y_fx, fx_predictions)
        fx_mse = mean_squared_error(y_fx, fx_predictions)


        if fx_r2 > best["fx_foreign_revenue"]["r2"]:
            best["fx_foreign_revenue"] = {
                "r2": fx_r2,
                "mse": fx_mse,
                "alpha": alpha,
                "l1_ratio": l1,
            }



# ============================================================
# REPORT BEST TARGET-SPECIFIC PARAMETERS
# ============================================================

print("\n\n==================== BEST HYPERPARAMETERS ====================")

for target_name, result in best.items():
    print(
        f"{target_name}: "
        f"alpha={result['alpha']}, "
        f"l1_ratio={result['l1_ratio']}, "
        f"R²={result['r2']}, "
        f"MSE={result['mse']}"
    )

print("==============================================================\n")


# ============================================================
# REFIT FINAL TARGET-SPECIFIC MODELS ON ALL AVAILABLE DATA
# ============================================================
# CV above is used for model/hyperparameter selection. The final models
# below are fitted on all available observations for future inference.

# -------------------------- TRADE -----------------------------

trade_scaler = StandardScaler()
X_trade_scaled = trade_scaler.fit_transform(X_trade)

trade_receivables_model = ElasticNet(
    alpha=best["trade_receivables"]["alpha"],
    l1_ratio=best["trade_receivables"]["l1_ratio"],
    max_iter=10000,
)
trade_receivables_model.fit(X_trade_scaled, y_trade_receivables)

trade_payables_model = ElasticNet(
    alpha=best["trade_payables"]["alpha"],
    l1_ratio=best["trade_payables"]["l1_ratio"],
    max_iter=10000,
)
trade_payables_model.fit(X_trade_scaled, y_trade_payables)

# One business pillar, two independently tuned estimators.
trade_model_bundle = {
    "receivables_model": trade_receivables_model,
    "payables_model": trade_payables_model,
    "feature_columns": list(X_trade.columns),
    "hyperparameters": {
        "receivables": {
            "alpha": best["trade_receivables"]["alpha"],
            "l1_ratio": best["trade_receivables"]["l1_ratio"],
        },
        "payables": {
            "alpha": best["trade_payables"]["alpha"],
            "l1_ratio": best["trade_payables"]["l1_ratio"],
        },
    },
}


# ---------------------- TRANSACTIONAL -------------------------

transactional_scaler = StandardScaler()
X_transactional_scaled = transactional_scaler.fit_transform(X_transactional)

transactional_revenue_model = ElasticNet(
    alpha=best["transactional_revenue"]["alpha"],
    l1_ratio=best["transactional_revenue"]["l1_ratio"],
    max_iter=10000,
)
transactional_revenue_model.fit(
    X_transactional_scaled,
    y_revenue,
)

transactional_cost_model = ElasticNet(
    alpha=best["transactional_cost"]["alpha"],
    l1_ratio=best["transactional_cost"]["l1_ratio"],
    max_iter=10000,
)
transactional_cost_model.fit(
    X_transactional_scaled,
    y_cost,
)

# One business pillar, two independently tuned estimators.
transactional_model_bundle = {
    "revenue_model": transactional_revenue_model,
    "cost_model": transactional_cost_model,
    "feature_columns": list(X_transactional.columns),
    "hyperparameters": {
        "revenue": {
            "alpha": best["transactional_revenue"]["alpha"],
            "l1_ratio": best["transactional_revenue"]["l1_ratio"],
        },
        "cost": {
            "alpha": best["transactional_cost"]["alpha"],
            "l1_ratio": best["transactional_cost"]["l1_ratio"],
        },
    },
}


# ----------------------------- FX -----------------------------

fx_scaler = StandardScaler()
X_fx_scaled = fx_scaler.fit_transform(X_fx)

fx_model = ElasticNet(
    alpha=best["fx_foreign_revenue"]["alpha"],
    l1_ratio=best["fx_foreign_revenue"]["l1_ratio"],
    max_iter=10000,
)
fx_model.fit(X_fx_scaled, y_fx)


# ============================================================
# SAVE THREE BUSINESS-PILLAR MODEL FILES + THEIR SCALERS
# ============================================================

joblib.dump(
    trade_model_bundle,
    MODELS_DIR / "trade_model.pkl",
)
joblib.dump(
    trade_scaler,
    MODELS_DIR / "trade_scaler.pkl",
)

joblib.dump(
    transactional_model_bundle,
    MODELS_DIR / "transactional_model.pkl",
)
joblib.dump(
    transactional_scaler,
    MODELS_DIR / "transactional_scaler.pkl",
)

joblib.dump(
    fx_model,
    MODELS_DIR / "fx_model.pkl",
)
joblib.dump(
    fx_scaler,
    MODELS_DIR / "fx_scaler.pkl",
)

print(f"Models and scalers saved to: {MODELS_DIR}")