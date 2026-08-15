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

Usage:
    from predict_wallet import MLWalletPredictor
    predictor = MLWalletPredictor()
    predictor.predict_for_client("Pepkor Holdings")
"""

from pathlib import Path

import joblib
import numpy as np
import pandas as pd

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


def _target_result(label: str, internal_col: str, row: pd.Series, predicted_share: float) -> dict:
    internal = float(row[internal_col])
    wallet, gap = derive_wallet_and_gap(internal, predicted_share)
    return {
        "target": label,
        "internal_zar": internal,
        "predicted_share_pct": predicted_share * 100,
        "predicted_total_wallet_zar_m": wallet / 1_000_000 if np.isfinite(wallet) else float("nan"),
        "predicted_gap_zar_m": gap / 1_000_000 if np.isfinite(gap) else float("nan"),
    }


class MLWalletPredictor:
    """Loads the trained bundles once; predicts share/total-wallet/gap per pillar for a client."""

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

    def predict_for_client(self, entity_name: str) -> dict:
        """
        Returns {pillar_name: [{target, internal_zar, predicted_share_pct,
        predicted_total_wallet_zar_m, predicted_gap_zar_m}, ...]}.

        A pillar's list is empty when this client has no internal-activity row for it in the
        gold tables (this hackathon dataset is a fixed extract; in production Syn Bank's own
        activity is always known).
        """
        result: dict[str, list[dict]] = {}

        trade_row = _latest_row(self.trade_internal, entity_name)
        trade_targets = []
        if trade_row is not None:
            X = pd.DataFrame(
                [[trade_row["synbank_trade_receivables"], trade_row["synbank_trade_payables"]]],
                columns=self.trade_bundle["feature_columns"],
            )
            X_scaled = self.trade_scaler.transform(X)
            receivables_share = float(self.trade_bundle["receivables_model"].predict(X_scaled)[0])
            payables_share = float(self.trade_bundle["payables_model"].predict(X_scaled)[0])
            trade_targets.append(_target_result("Trade receivables", "synbank_trade_receivables", trade_row, receivables_share))
            trade_targets.append(_target_result("Trade payables", "synbank_trade_payables", trade_row, payables_share))
        result["Trade & Working Capital"] = trade_targets

        transactional_row = _latest_row(self.transactional_internal, entity_name)
        transactional_targets = []
        if transactional_row is not None:
            X = pd.DataFrame(
                [[transactional_row["collections"], transactional_row["supplier_payments"]]],
                columns=self.transactional_bundle["feature_columns"],
            )
            X_scaled = self.transactional_scaler.transform(X)
            revenue_share = float(self.transactional_bundle["revenue_model"].predict(X_scaled)[0])
            cost_share = float(self.transactional_bundle["cost_model"].predict(X_scaled)[0])
            transactional_targets.append(_target_result("Revenue (collections)", "collections", transactional_row, revenue_share))
            transactional_targets.append(_target_result("Cost of sales (supplier payments)", "supplier_payments", transactional_row, cost_share))
        result["Transactional Banking"] = transactional_targets

        fx_row = _latest_row(self.fx_internal, entity_name)
        fx_targets = []
        if fx_row is not None:
            X = pd.DataFrame([[fx_row["cross_border_inflows"]]], columns=["cross_border_inflows"])
            X_scaled = self.fx_scaler.transform(X)
            fx_share = float(self.fx_model.predict(X_scaled)[0])
            fx_targets.append(_target_result("Foreign revenue (cross-border inflows)", "cross_border_inflows", fx_row, fx_share))
        result["Foreign/Cross-Border"] = fx_targets

        return result

    def describe(self, entity_name: str) -> str:
        """
        Turns predict_for_client()'s numbers into a banker-readable narrative - this is the
        GenAI-facing half of the ML model: the ElasticNet predictions are the *input*, this
        sentence is the *synthesis* a relationship banker actually reads. No LLM call needed
        (the numbers are already known; this is templated synthesis, same "Tier 1" philosophy
        as scripts/nl_query_assistant.py), which keeps it free and always available.
        """
        by_pillar = self.predict_for_client(entity_name)
        all_targets = [(pillar, t) for pillar, targets in by_pillar.items() for t in targets]
        if not all_targets:
            return f"No internal-activity data available for {entity_name} in the ML training set - the ElasticNet models have nothing to predict from."

        computable = [(p, t) for p, t in all_targets if pd.notna(t["predicted_gap_zar_m"])]
        not_computable = [(p, t) for p, t in all_targets if pd.isna(t["predicted_gap_zar_m"])]

        if not computable:
            return (
                f"ElasticNet (internal-activity-only) has {len(all_targets)} target(s) for {entity_name}, but "
                "predicted a non-positive share on all of them, so total wallet/gap aren't computable for any - "
                "see the reliability caveat in machine_learning/wallet_math.py."
            )

        pillar, headline = max(computable, key=lambda pt: pt[1]["predicted_gap_zar_m"])
        parts = [
            f"ElasticNet (internal-activity-only) estimates {entity_name}'s {headline['target'].lower()} wallet "
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
    for client in ["Pepkor Holdings", "Glencore", "Valterra Platinum"]:
        print(f"\n{client}:")
        for pillar, targets in predictor.predict_for_client(client).items():
            if not targets:
                print(f"  {pillar}: no internal activity data available")
                continue
            print(f"  {pillar}:")
            for t in targets:
                if t["predicted_total_wallet_zar_m"] == t["predicted_total_wallet_zar_m"]:  # not NaN
                    wallet_str = f"R{t['predicted_total_wallet_zar_m']:.1f}m"
                    gap_str = f"R{t['predicted_gap_zar_m']:.1f}m"
                else:
                    wallet_str = "not computable (predicted share <= 0)"
                    gap_str = "n/a"
                print(f"    {t['target']}: predicted share={t['predicted_share_pct']:.1f}%, total wallet={wallet_str}, gap={gap_str}")
