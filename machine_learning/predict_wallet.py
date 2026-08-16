"""
ElasticNet-based Share-of-Wallet inference - turns the trained per-pillar models
(machine_learning/elastic_net.py) into a callable "predict for one client" API,
returning share, total wallet, and gap (not just share) via derive_wallet_and_gap().

Complements the top-down deterministic model (scripts/build_wallet_model.py): the
top-down model needs the client's external total wallet, which is missing or
low-reliability for many clients (see wallet_model.csv's reliability tiers). This
model needs only Syn Bank's own internal activity - always known internally in
production - which makes it a useful cross-check everywhere, and the only usable
quantitative estimate where the top-down benchmark is weak.

Loads the already-trained .pkl bundles from machine_learning/models/ (built by
elastic_net.py) - does not retrain anything.

Two ways to get a prediction:
    predict_for_client(entity_name)   - looks up internal activity from the medallion
                                         gold CSVs for one of the clients already in the
                                         pipeline.
    predict_from_inputs(...)          - takes internal-activity figures directly, for a
                                         client not yet run through the medallion pipeline
                                         (e.g. a live "what if" demo). No CSV lookup, no
                                         gold-layer rebuild required.

Usage:
    from predict_wallet import MLWalletPredictor
    predictor = MLWalletPredictor()
    predictor.predict_for_client("Pepkor Holdings")
    predictor.predict_from_inputs(collections=5_000_000, supplier_payments=2_000_000)
"""

from pathlib import Path

import joblib
import numpy as np
import pandas as pd

# Allow synbank_wallet_engine to easily visualise output
try:
    from machine_learning.wallet_math import derive_wallet_and_gap
except ModuleNotFoundError:
    from wallet_math import derive_wallet_and_gap


ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = ROOT / "machine_learning" / "models"
GOLD_DIR = ROOT / "medallion-pipeline" / "gold"


def _latest_row(df: pd.DataFrame, entity_name: str):
    rows = df[df["entity_name"] == entity_name]
    if rows.empty:
        return None
    return rows.sort_values("year").iloc[-1]


def _fmt_rand_m(zar_m: float) -> str:
    if pd.isna(zar_m):
        return "not available"
    v = float(zar_m)
    if abs(v) >= 1000:
        return f"R{v / 1000:.1f}bn"
    return f"R{v:.1f}m"


def _target_result_from_value(label: str, internal: float, predicted_share: float) -> dict:
    wallet, gap = derive_wallet_and_gap(internal, predicted_share)
    return {
        "target": label,
        "internal_zar": internal,
        "predicted_share_pct": predicted_share * 100,
        "predicted_total_wallet_zar_m": wallet / 1_000_000 if np.isfinite(wallet) else float("nan"),
        "predicted_gap_zar_m": gap / 1_000_000 if np.isfinite(gap) else float("nan"),
    }


class MLWalletPredictor:
    """Loads the trained bundles once; predicts share/total-wallet/gap per pillar."""

    def __init__(self, models_dir: Path = MODELS_DIR, gold_dir: Path = GOLD_DIR):
        self.trade_bundle = joblib.load(models_dir / "trade_model.pkl")
        self.trade_scaler = joblib.load(models_dir / "trade_scaler.pkl")
        self.transactional_bundle = joblib.load(models_dir / "transactional_model.pkl")
        self.transactional_scaler = joblib.load(models_dir / "transactional_scaler.pkl")
        self.fx_model = joblib.load(models_dir / "fx_model.pkl")
        self.fx_scaler = joblib.load(models_dir / "fx_scaler.pkl")

        self.trade_internal = pd.read_csv(gold_dir / "trade_finance_gold.csv")
        self.transactional_internal = pd.read_csv(gold_dir / "transactional_banking_gold.csv")
        self.fx_internal = pd.read_csv(gold_dir / "cross_border_gold.csv")

    # ---- shared prediction logic (both pillars need both of their features together) ----

    def _predict_trade(self, trade_receivables: float, trade_payables: float) -> list[dict]:
        X = pd.DataFrame([[trade_receivables, trade_payables]], columns=self.trade_bundle["feature_columns"])
        X_scaled = self.trade_scaler.transform(X)
        receivables_share = float(self.trade_bundle["receivables_model"].predict(X_scaled)[0])
        payables_share = float(self.trade_bundle["payables_model"].predict(X_scaled)[0])
        return [
            _target_result_from_value("Trade receivables", trade_receivables, receivables_share),
            _target_result_from_value("Trade payables", trade_payables, payables_share),
        ]

    def _predict_transactional(self, collections: float, supplier_payments: float) -> list[dict]:
        X = pd.DataFrame([[collections, supplier_payments]], columns=self.transactional_bundle["feature_columns"])
        X_scaled = self.transactional_scaler.transform(X)
        revenue_share = float(self.transactional_bundle["revenue_model"].predict(X_scaled)[0])
        cost_share = float(self.transactional_bundle["cost_model"].predict(X_scaled)[0])
        return [
            _target_result_from_value("Revenue (collections)", collections, revenue_share),
            _target_result_from_value("Cost of sales (supplier payments)", supplier_payments, cost_share),
        ]

    def _predict_fx(self, cross_border_inflows: float) -> list[dict]:
        X = pd.DataFrame([[cross_border_inflows]], columns=["cross_border_inflows"])
        X_scaled = self.fx_scaler.transform(X)
        fx_share = float(self.fx_model.predict(X_scaled)[0])
        return [_target_result_from_value("Foreign revenue (cross-border inflows)", cross_border_inflows, fx_share)]

    # ---- public entry points ----

    def predict_for_client(self, entity_name: str) -> dict:
        """
        Returns {pillar_name: [{target, internal_zar, predicted_share_pct,
        predicted_total_wallet_zar_m, predicted_gap_zar_m}, ...]}.

        Looks up internal activity from the medallion gold CSVs. A pillar's list is empty
        when this client has no row for it there (this hackathon dataset is a fixed
        extract; in production Syn Bank's own activity is always known). For a client not
        yet in the gold tables, use predict_from_inputs() instead.
        """
        result: dict[str, list[dict]] = {}

        trade_row = _latest_row(self.trade_internal, entity_name)
        result["Trade & Working Capital"] = (
            self._predict_trade(float(trade_row["synbank_trade_receivables"]), float(trade_row["synbank_trade_payables"]))
            if trade_row is not None else []
        )

        transactional_row = _latest_row(self.transactional_internal, entity_name)
        result["Transactional Banking"] = (
            self._predict_transactional(float(transactional_row["collections"]), float(transactional_row["supplier_payments"]))
            if transactional_row is not None else []
        )

        fx_row = _latest_row(self.fx_internal, entity_name)
        result["Foreign/Cross-Border"] = (
            self._predict_fx(float(fx_row["cross_border_inflows"]))
            if fx_row is not None else []
        )

        return result

    def predict_from_inputs(
        self,
        trade_receivables: float | None = None,
        trade_payables: float | None = None,
        collections: float | None = None,
        supplier_payments: float | None = None,
        cross_border_inflows: float | None = None,
    ) -> dict:
        """
        Same output shape as predict_for_client(), but takes internal-activity figures
        directly instead of looking them up from the medallion gold CSVs - for predicting
        on a client not (yet) run through the medallion pipeline. No CSV lookup, no
        pipeline rerun, no retraining - the already-trained model is applied immediately.

        Trade receivables/payables are both needed together to predict either trade target
        (the model was trained on both as joint features), and likewise for collections/
        supplier payments - so each pillar is only predicted when its full feature pair is
        supplied. FX needs only cross_border_inflows.
        """
        result: dict[str, list[dict]] = {"Trade & Working Capital": [], "Transactional Banking": [], "Foreign/Cross-Border": []}

        if trade_receivables is not None and trade_payables is not None:
            result["Trade & Working Capital"] = self._predict_trade(trade_receivables, trade_payables)

        if collections is not None and supplier_payments is not None:
            result["Transactional Banking"] = self._predict_transactional(collections, supplier_payments)

        if cross_border_inflows is not None:
            result["Foreign/Cross-Border"] = self._predict_fx(cross_border_inflows)

        return result


    def predict_all_clients(self) -> pd.DataFrame:
        """
        Run the trained models for every client present in the medallion gold layer
        and return the predictions as one tidy DataFrame.

        Each row represents one client/target prediction, making it easy to display,
        filter, rank, or export the complete portfolio output in a notebook.
        """
        clients = sorted(
            set(self.trade_internal["entity_name"].dropna())
            | set(self.transactional_internal["entity_name"].dropna())
            | set(self.fx_internal["entity_name"].dropna())
        )

        rows = []

        for entity_name in clients:
            predictions = self.predict_for_client(entity_name)

            for pillar, targets in predictions.items():
                for target in targets:
                    rows.append({
                        "entity_name": entity_name,
                        "pillar": pillar,
                        "target": target["target"],
                        "internal_zar": target["internal_zar"],
                        "predicted_share_pct": target["predicted_share_pct"],
                        "predicted_total_wallet_zar_m": target["predicted_total_wallet_zar_m"],
                        "predicted_gap_zar_m": target["predicted_gap_zar_m"],
                    })

        return pd.DataFrame(rows)

    def describe(self, entity_name: str) -> str:
        """
        Turns predict_for_client()'s numbers into a banker-readable narrative - this is the
        GenAI-facing half of the ML model: the ElasticNet predictions are the *input*, this
        sentence is the *synthesis* a relationship banker actually reads. No LLM call needed
        (the numbers are already known; this is templated synthesis, same "Tier 1" philosophy
        as scripts/nl_query_assistant.py), which keeps it free and always available.
        """
        return self.describe_predictions(self.predict_for_client(entity_name), entity_name)

    def describe_predictions(self, by_pillar: dict, label: str = "this client") -> str:
        """Same narrative synthesis as describe(), but over an already-computed predictions
        dict (from either predict_for_client() or predict_from_inputs()) - lets ad-hoc,
        not-yet-in-the-pipeline predictions get the same GenAI-facing summary."""
        all_targets = [(pillar, t) for pillar, targets in by_pillar.items() for t in targets]
        if not all_targets:
            return f"No internal-activity figures available for {label} - nothing for the ElasticNet models to predict from."

        computable = [(p, t) for p, t in all_targets if pd.notna(t["predicted_gap_zar_m"])]
        not_computable = [(p, t) for p, t in all_targets if pd.isna(t["predicted_gap_zar_m"])]

        if not computable:
            return (
                f"ElasticNet (internal-activity-only) has {len(all_targets)} target(s) for {label}, but "
                "predicted a non-positive share on all of them, so total wallet/gap aren't computable for any - "
                "see the reliability caveat in machine_learning/wallet_math.py."
            )

        pillar, headline = max(computable, key=lambda pt: pt[1]["predicted_gap_zar_m"])
        parts = [
            f"ElasticNet (internal-activity-only) estimates {label}'s {headline['target'].lower()} wallet "
            f"at {_fmt_rand_m(headline['predicted_total_wallet_zar_m'])}, with Syn Bank capturing "
            f"~{headline['predicted_share_pct']:.1f}% - a ~{_fmt_rand_m(headline['predicted_gap_zar_m'])} gap, "
            f"the largest of its {len(computable)} computable target(s) ({pillar})."
        ]

        others = [t for p, t in computable if t is not headline]
        if others:
            other_bits = [
                f"{t['target'].lower()} {_fmt_rand_m(t['predicted_gap_zar_m'])} gap ({t['predicted_share_pct']:.1f}% share)"
                for t in others
            ]
            parts.append("Other targets: " + "; ".join(other_bits) + ".")

        if not_computable:
            skipped = ", ".join(t["target"].lower() for _, t in not_computable)
            parts.append(
                f"Not computable for {skipped} - predicted share came out non-positive, so no fabricated wallet/gap figure is shown."
            )

        return " ".join(parts)


if __name__ == "__main__":
    predictor = MLWalletPredictor()

    # Predict across every client available in the medallion gold-layer inputs.
    predictions_df = predictor.predict_all_clients()

    # Keep the output judge-friendly when the script is run directly.
    display_df = predictions_df.copy()
    display_df["internal_zar"] = display_df["internal_zar"].round(2)
    display_df["predicted_share_pct"] = display_df["predicted_share_pct"].round(2)
    display_df["predicted_total_wallet_zar_m"] = display_df["predicted_total_wallet_zar_m"].round(2)
    display_df["predicted_gap_zar_m"] = display_df["predicted_gap_zar_m"].round(2)

    print("\nElasticNet predictions for all clients\n")
    print(display_df.to_string(index=False))