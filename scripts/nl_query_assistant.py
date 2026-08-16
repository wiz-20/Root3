"""
Natural-language query assistant - GenAI use case #3.

Tier 1 is a deterministic, zero-cost intent classifier + templated synthesis layer.
The CURRENT operational portfolio is taken from machine_learning/predict_wallet.py,
which reads the latest medallion Gold data and applies the already-trained ElasticNet
models.

The external financials-based top-down model remains available as an OPTIONAL benchmark
for clients that exist in wallet_model.csv. New clients can therefore be queried from
their live ML predictions even when no external benchmark has yet been created.

Open-ended cross-client questions can escalate to nl_query_llm.py when an API key is
configured.
"""

import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
EXTRACTED_DIR = ROOT / "hackathon-finreports" / "_extracted"

PILLAR_NAMES = {
    1: "Transactional Banking",
    2: "Trade & Working Capital",
    3: "Foreign/Cross-Border",
}


def _load_ml_predictor():
    """Best-effort model load so the assistant still fails gracefully."""
    try:
        ml_dir = str(ROOT / "machine_learning")
        if ml_dir not in sys.path:
            sys.path.insert(0, ml_dir)

        from predict_wallet import MLWalletPredictor

        return MLWalletPredictor()
    except Exception:
        return None


def _fmt_rand(zar_millions: float) -> str:
    if pd.isna(zar_millions):
        return "not available"

    v = float(zar_millions)

    if abs(v) >= 1_000_000:
        return f"R{v / 1_000_000:.2f} trillion"
    if abs(v) >= 1000:
        return f"R{v / 1000:.1f}bn"

    return f"R{v:.1f}m"


class QueryAssistant:
    """
    Tier 1 query assistant.

    Source priority:
    1. Current ElasticNet predictions from the latest Gold-layer internal data.
    2. Top-down benchmark only when the selected client exists in wallet_model.csv.
    """

    def __init__(self, extracted_dir: Path = EXTRACTED_DIR, ml_predictor=None):
        wallet_path = extracted_dir / "wallet_model.csv"
        ranking_path = extracted_dir / "opportunity_ranking.csv"
        anomalies_path = extracted_dir / "anomalies_detected.csv"

        self.wallet_model = (
            pd.read_csv(wallet_path)
            if wallet_path.exists()
            else pd.DataFrame()
        )
        self.ranking = (
            pd.read_csv(ranking_path)
            if ranking_path.exists()
            else pd.DataFrame()
        )
        self.anomalies = (
            pd.read_csv(anomalies_path)
            if anomalies_path.exists()
            else pd.DataFrame()
        )

        self.ml_predictor = (
            ml_predictor
            if ml_predictor is not None
            else _load_ml_predictor()
        )

        if self.ml_predictor is not None:
            try:
                self.ml_predictions = self.ml_predictor.predict_all_clients()
            except Exception:
                self.ml_predictions = pd.DataFrame()
        else:
            self.ml_predictions = pd.DataFrame()

        if not self.ml_predictions.empty:
            self.entity_names = sorted(
                self.ml_predictions["entity_name"]
                .dropna()
                .astype(str)
                .unique()
                .tolist()
            )
        elif not self.wallet_model.empty:
            self.entity_names = sorted(
                self.wallet_model["entity_name"]
                .dropna()
                .astype(str)
                .unique()
                .tolist()
            )
        else:
            self.entity_names = []

    _GENERIC_WORDS = {
        "the",
        "group",
        "holdings",
        "plc",
        "capital",
        "corporation",
        "banking",
        "pharmacare",
        "ltd",
        "limited",
    }

    def _match_entity(self, question: str) -> str | None:
        q = question.lower()
        q_words = set(re.findall(r"[a-z]+", q))

        def is_match(name: str) -> bool:
            if name.lower() in q:
                return True

            meaningful = [
                w
                for w in name.split()
                if w.lower() not in self._GENERIC_WORDS
            ]
            return any(w.lower() in q_words for w in meaningful)

        matches = [name for name in self.entity_names if is_match(name)]

        if not matches:
            return None

        return max(matches, key=len)

    def _top_down_row(self, entity_name: str):
        if self.wallet_model.empty:
            return None

        rows = self.wallet_model[
            self.wallet_model["entity_name"] == entity_name
        ]

        if rows.empty:
            return None

        return rows.iloc[0]

    def _entity_ml_rows(self, entity_name: str) -> pd.DataFrame:
        if self.ml_predictions.empty:
            return pd.DataFrame()

        return self.ml_predictions[
            self.ml_predictions["entity_name"] == entity_name
        ].copy()

    def _ml_opportunity_table(self) -> pd.DataFrame:
        if self.ml_predictions.empty:
            return pd.DataFrame()

        df = self.ml_predictions[
            self.ml_predictions["predicted_gap_zar_m"].notna()
            & self.ml_predictions["predicted_total_wallet_zar_m"].notna()
        ].copy()

        if df.empty:
            return pd.DataFrame()

        df["internal_zar_m"] = df["internal_zar"] / 1_000_000

        result = (
            df.groupby("entity_name", as_index=False)
            .agg(
                internal_zar_m=("internal_zar_m", "sum"),
                predicted_total_wallet_zar_m=(
                    "predicted_total_wallet_zar_m",
                    "sum",
                ),
                total_gap_zar_m=("predicted_gap_zar_m", "sum"),
            )
        )

        result["predicted_share_pct"] = (
            result["internal_zar_m"]
            / result["predicted_total_wallet_zar_m"]
            * 100
        )

        return result

    def answer(self, question: str) -> str:
        q = question.lower().strip()
        entity = self._match_entity(question)

        if not entity and re.search(
            r"^help$|help me|what can (you|i)|what (should|could) i ask|"
            r"how do(es)? (this|you) work|what (questions|things) can (you|i)|capabilit",
            q,
        ):
            return self._help()

        if (
            ("top" in q and re.search(r"opportunit|gap|priorit", q))
            or "biggest gap" in q
            or "largest gap" in q
        ):
            return self._top_opportunities(q)

        if entity and re.search(
            r"\bml\b|machine learning|elastic ?net|model predict|"
            r"predict.*wallet|predict.*share|predict.*gap",
            q,
        ):
            return self._ml_prediction(entity)

        if entity and re.search(r"reliab|trust|confiden|literal|benchmark", q):
            return self._reliability(entity)

        if entity and re.search(
            r"why.*(so large|so big|so high|large gap|huge)",
            q,
        ):
            return self._explain_gap(entity)

        if entity and re.search(r"anomal|issue|flag|weird|wrong", q):
            return self._anomalies_for(entity)

        if entity and re.search(
            r"lead with|pitch|recommend|prioriti[sz]e|which pillar",
            q,
        ):
            return self._recommend_pillar(entity)

        if entity and re.search(r"share|wallet|gap|penetrat", q):
            return self._client_summary(entity)

        if entity:
            return self._client_summary(entity)

        return (
            "I couldn't confidently match this question to a current client or a "
            "supported Tier 1 query type. Ask about a client summary, the ML prediction, "
            "top opportunities, pillar recommendation, top-down benchmark reliability, "
            "or anomalies. Open-ended portfolio questions can be escalated to Tier 2 "
            "when the live LLM path is configured."
        )

    def _help(self) -> str:
        if self.entity_names:
            example_client = self.entity_names[0]
            examples = (
                f'  - "What is {example_client}\'s wallet?"\n'
                f'  - "What does the ML model predict for {example_client}?"\n'
                f'  - "Which pillar should we lead with for {example_client}?"\n'
                f'  - "Is there a top-down benchmark for {example_client}?"\n'
            )
        else:
            examples = ""

        return (
            "I can query the current Syn Bank portfolio using the live ElasticNet "
            "predictions generated from the latest Gold-layer data.\n\n"
            f"{examples}"
            '  - "What are the top 5 opportunities?"\n'
            "\nWhere an external top-down benchmark exists for the same client, I can "
            "also compare or explain that benchmark."
        )

    def _top_opportunities(self, q: str) -> str:
        n_match = re.search(r"top\s*(\d+)", q)
        n = int(n_match.group(1)) if n_match else 5

        df = self._ml_opportunity_table()

        if df.empty:
            return "No current ML wallet predictions are available."

        df = (
            df.sort_values(
                "total_gap_zar_m",
                ascending=False,
            )
            .head(n)
        )

        lines = [
            f"Top {len(df)} current opportunities by ElasticNet-predicted wallet gap:"
        ]

        for i, (_, r) in enumerate(df.iterrows(), start=1):
            lines.append(
                f"  {i}. {r['entity_name']} - "
                f"{_fmt_rand(r['total_gap_zar_m'])} predicted gap, "
                f"{r['predicted_share_pct']:.1f}% predicted Syn Bank share"
            )

        lines.append(
            "\nSource: current ElasticNet predictions from the latest internal Syn Bank data."
        )

        return "\n".join(lines)

    def _reliability(self, entity: str) -> str:
        row = self._top_down_row(entity)

        if row is None:
            return (
                f"{entity} is available in the current ML portfolio, but no external "
                "top-down benchmark is available for this client. The live estimate is "
                "therefore based on the ElasticNet model."
            )

        return (
            f"{entity}: external top-down benchmark reliability = "
            f"\"{row['top_down_reliability']}\". "
            f"Currency: {row['currency']}. "
            f"Fiscal year: FY{int(row['fiscal_year'])}."
        )

    def _explain_gap(self, entity: str) -> str:
        ml_rows = self._entity_ml_rows(entity)

        if ml_rows.empty:
            return f"No current ML prediction is available for {entity}."

        computable = ml_rows[
            ml_rows["predicted_gap_zar_m"].notna()
        ]

        if computable.empty:
            return (
                f"The ElasticNet model has current activity for {entity}, but none of "
                "the predicted shares produced a computable wallet/gap."
            )

        total_gap = computable["predicted_gap_zar_m"].sum()
        largest = computable.sort_values(
            "predicted_gap_zar_m",
            ascending=False,
        ).iloc[0]

        parts = [
            f"{entity}'s current ElasticNet-predicted total computable gap is "
            f"{_fmt_rand(total_gap)}.",
            f"The largest target-level gap is {largest['target']} "
            f"({_fmt_rand(largest['predicted_gap_zar_m'])}), with a predicted "
            f"Syn Bank share of {largest['predicted_share_pct']:.1f}%.",
        ]

        benchmark = self._top_down_row(entity)
        if benchmark is not None:
            parts.append(
                "An external top-down benchmark also exists for this client; ask for "
                "the client summary or reliability if you want the independent comparison."
            )
        else:
            parts.append(
                "No external top-down benchmark is currently available for this client."
            )

        return " ".join(parts)

    def _anomalies_for(self, entity: str) -> str:
        if self.anomalies.empty:
            return (
                "No top-down anomaly table is currently loaded. "
                "This does not affect the live ML prediction."
            )

        rows = self.anomalies[
            self.anomalies["entity_name"] == entity
        ]

        if rows.empty:
            return (
                f"No top-down anomalies are recorded for {entity}. "
                "For a new ML-only client this usually means no external benchmark/anomaly "
                "analysis has been generated yet."
            )

        lines = [f"{len(rows)} top-down anomaly(ies) flagged for {entity}:"]

        for _, r in rows.iterrows():
            lines.append(
                f"  [{r['rule']}] pillar {r['pillar']}: {r['detail']}"
            )

        return "\n".join(lines)

    def _recommend_pillar(self, entity: str) -> str:
        rows = self._entity_ml_rows(entity)

        if rows.empty:
            return f"No current ML prediction is available for {entity}."

        valid = rows[
            rows["predicted_gap_zar_m"].notna()
        ].copy()

        if valid.empty:
            return (
                f"No computable ML wallet gap is available for {entity}, "
                "so I cannot make a data-driven pillar recommendation."
            )

        pillar_summary = (
            valid.groupby("pillar", as_index=False)
            .agg(
                predicted_gap_zar_m=("predicted_gap_zar_m", "sum"),
                internal_zar=("internal_zar", "sum"),
                predicted_total_wallet_zar_m=(
                    "predicted_total_wallet_zar_m",
                    "sum",
                ),
            )
        )

        pillar_summary["predicted_share_pct"] = (
            (pillar_summary["internal_zar"] / 1_000_000)
            / pillar_summary["predicted_total_wallet_zar_m"]
            * 100
        )

        best = pillar_summary.sort_values(
            "predicted_gap_zar_m",
            ascending=False,
        ).iloc[0]

        return (
            f"For {entity}, the current ElasticNet results suggest leading with "
            f"{best['pillar']}: {_fmt_rand(best['predicted_gap_zar_m'])} predicted gap "
            f"and {best['predicted_share_pct']:.1f}% predicted Syn Bank share."
        )

    def _client_summary(self, entity: str) -> str:
        lines = [entity]

        if self.ml_predictor is not None:
            lines.append(
                "\nCurrent ElasticNet estimate (latest internal Syn Bank activity):"
            )
            lines.append(self.ml_predictor.describe(entity))
        else:
            lines.append("\nCurrent ElasticNet estimate is unavailable in this session.")

        row = self._top_down_row(entity)

        if row is not None:
            lines.append("\nExternal top-down benchmark:")

            for i in [1, 2, 3]:
                share = row[f"share_pct_pillar{i}"]
                gap = row[f"gap_zar_m_pillar{i}"]

                if pd.notna(share):
                    lines.append(
                        f"  {PILLAR_NAMES[i]}: "
                        f"{share}% share, {_fmt_rand(gap)} gap"
                    )

            if pd.notna(row["blended_share_pct"]):
                lines.append(
                    f"  Blended: {row['blended_share_pct']}% share, "
                    f"{_fmt_rand(row['total_gap_zar_m'])} gap"
                )

            lines.append(
                "  Reliability: "
                f"{row['top_down_reliability'].split(' - ')[0]}"
            )
        else:
            lines.append(
                "\nNo external top-down benchmark is currently available for this client."
            )

        return "\n".join(lines)

    def _ml_prediction(self, entity: str) -> str:
        if self.ml_predictor is None:
            return (
                "The current ElasticNet model could not be loaded in this session."
            )

        return self.ml_predictor.describe(entity)


if __name__ == "__main__":
    qa = QueryAssistant()

    print("Current clients:")
    for name in qa.entity_names:
        print(f"  - {name}")

    if qa.entity_names:
        demo_client = qa.entity_names[0]
        demo_questions = [
            f"What is {demo_client}'s wallet?",
            f"Which pillar should we lead with for {demo_client}?",
            "What are the top 5 opportunities?",
        ]

        for question in demo_questions:
            print(f"\nQ: {question}")
            print(qa.answer(question))