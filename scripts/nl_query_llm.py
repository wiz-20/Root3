"""
Live LLM path for GenAI use case #3 (NL querying) - Tier 2, open-ended synthesis.

The CURRENT operational portfolio is the ElasticNet prediction set produced from the
latest Syn Bank Gold-layer internal data. The external financials-based top-down model
is included only as an independent benchmark for clients that exist in those files.

Requires ANTHROPIC_API_KEY. Callers should check is_available() first.
"""

import os
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
EXTRACTED_DIR = ROOT / "hackathon-finreports" / "_extracted"

MODEL = "claude-opus-5"

SYSTEM_PROMPT = """You are a data analyst answering an open-ended question from a relationship banking team about Syn Bank's current Share-of-Wallet client portfolio.

You may receive two different estimation sources:

1. ml_predictions.csv
   - The CURRENT operational portfolio.
   - Produced by trained ElasticNet models from Syn Bank's latest internal activity.
   - This is the primary source for the clients currently being analysed.

2. wallet_model.csv / opportunity_ranking.csv
   - An external-financials-based TOP-DOWN benchmark.
   - This benchmark may only exist for a subset of clients.
   - Do not assume a client appears in the top-down data merely because it appears in the ML data.

anomalies_detected.csv contains rule-based checks associated with the top-down benchmark.

Answer in 100-200 words. Requirements:
1. Answer the actual question asked.
2. Never invent a number.
3. Clearly label every cited figure as either "ML model" or "top-down model".
4. Use the ML model as the primary source for the CURRENT client portfolio.
5. Only use the top-down model for a client when that client actually appears in the top-down tables.
6. If both estimates exist and materially disagree, state that explicitly.
7. If only the ML estimate exists, say that no external top-down benchmark is available.
8. If reliability tiering is relevant to a top-down figure, state the caveat explicitly.
9. If the available data cannot support a firm conclusion, say so plainly rather than guessing.
"""


def is_available() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def _build_ml_predictions_csv() -> str:
    """
    Build live ElasticNet predictions directly from the clients currently present
    in the medallion Gold layer.
    """
    try:
        ml_dir = str(ROOT / "machine_learning")
        if ml_dir not in sys.path:
            sys.path.insert(0, ml_dir)

        from predict_wallet import MLWalletPredictor

        predictor = MLWalletPredictor()
        predictions = predictor.predict_all_clients()

        if predictions.empty:
            return ""

        return predictions.to_csv(index=False)

    except Exception:
        return ""


def _read_optional_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path) if path.exists() else pd.DataFrame()


def _load_context() -> str:
    ml_predictions = _build_ml_predictions_csv()

    context_parts = []

    if ml_predictions:
        context_parts.append(
            "CURRENT ml_predictions.csv "
            "(ElasticNet predictions from latest internal Syn Bank data):\n"
            + ml_predictions
        )

    wallet_model = _read_optional_csv(
        EXTRACTED_DIR / "wallet_model.csv"
    )
    ranking = _read_optional_csv(
        EXTRACTED_DIR / "opportunity_ranking.csv"
    )
    anomalies = _read_optional_csv(
        EXTRACTED_DIR / "anomalies_detected.csv"
    )

    context_parts.append(
        "OPTIONAL EXTERNAL TOP-DOWN BENCHMARK:\n"
        f"wallet_model.csv:\n{wallet_model.to_csv(index=False)}\n\n"
        f"opportunity_ranking.csv:\n{ranking.to_csv(index=False)}\n\n"
        f"anomalies_detected.csv:\n{anomalies.to_csv(index=False)}"
    )

    return "\n\n".join(context_parts)


def answer_open_ended(question: str) -> str:
    """Tier 2: answer an open-ended question via a live Claude call."""
    import anthropic

    client = anthropic.Anthropic()
    context = _load_context()

    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": (
                    f"INPUT DATA:\n{context}\n\n"
                    f"QUESTION: {question}"
                ),
            }
        ],
    )

    return next(
        (
            block.text
            for block in response.content
            if block.type == "text"
        ),
        "",
    ).strip()


if __name__ == "__main__":
    if not is_available():
        print(
            "ANTHROPIC_API_KEY not set - Tier 2 live querying is disabled."
        )
    else:
        demo_questions = [
            "Which clients currently have the largest predicted wallet gaps?",
            "Which client should the sales team prioritize first, and why?",
        ]

        for question in demo_questions:
            print(f"\nQ: {question}")
            print(answer_open_ended(question))