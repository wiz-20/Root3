"""
Live LLM path for GenAI use case #3 (NL querying) - Tier 2, open-ended synthesis.

Tier 1 (nl_query_assistant.py) is deterministic and free; it handles ~80% of realistic
banker questions (lookups, comparisons, rankings) and explicitly declines anything that
needs judgment across multiple rows. Until now, those declined questions were answered
only as static worked examples (hackathon-finreports/_extracted/nl_query_examples.md),
generated once via the Cursor-agent-as-LLM workflow described in
docs/genai/nl_query_prompt.md. This module makes that same prompt contract live: a real
Claude API call, grounded strictly in the same CSVs Tier 1 reads from, so a judge can ask
their own open-ended question rather than only reading the worked examples.

**Two independent estimates, both in the grounding context:** alongside the top-down
financials-based proxy (wallet_model.csv / opportunity_ranking.csv), the context also
includes machine_learning/predict_wallet.py's ElasticNet predictions for all 20 clients -
an independent model built from Syn Bank's own internal activity alone. The system prompt
requires every cited figure to be labelled with which model it came from, so the model
can genuinely synthesize both (or flag disagreement) rather than the two silently blurring
into one narrative.

Requires ANTHROPIC_API_KEY. Callers should check is_available() first and fall back to the
Tier 1 decline message (which points at the static examples) when it's False - this keeps
the zero-cost, zero-dependency demo path fully intact when no key is configured.
"""

import os
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
EXTRACTED_DIR = ROOT / "hackathon-finreports" / "_extracted"

MODEL = "claude-opus-5"

SYSTEM_PROMPT = """You are a data analyst answering an open-ended question from a relationship banking team about Syn Bank's Share-of-Wallet model covering 20 corporate clients across 3 banking pillars (Transactional, Trade & Working Capital, Foreign/Cross-Border).

You will be given up to four tables as context:
- wallet_model.csv and opportunity_ranking.csv - a TOP-DOWN proxy built from each client's public financials.
- anomalies_detected.csv - rule-based anomaly detection on the top-down model.
- ml_predictions.csv - an independent ML MODEL (ElasticNet) that predicts share of wallet from Syn Bank's own internal activity alone, then derives total wallet and gap from that prediction. This is a genuinely different estimation approach from the top-down proxy, not a restatement of it - the two can and do disagree on some clients.

Answer in 100-200 words. Requirements:
1. Answer the actual question asked - do not pad with unrelated context.
2. Cite specific entities and numbers from the provided tables - do not use any number not present in the input data.
3. Label which source every figure comes from ("top-down model" or "ML model") - never blend a number from one table into a sentence that reads as if it came from the other.
4. If the two models materially disagree on a client central to your answer, say so explicitly rather than silently picking one.
5. If reliability tiering is relevant to the answer (i.e. the question touches a low-reliability or insufficient-reliability row), state that caveat explicitly.
6. If the question cannot be confidently answered from the available data, say so plainly rather than guessing - a wrong confident answer is worse than an honest "the data doesn't support a firm conclusion here."
"""


def is_available() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def _build_ml_predictions_csv() -> str:
    """All 20 clients' ElasticNet predictions flattened to a CSV table - the second grounding
    source. Best-effort: returns "" (silently omitted from context) if machine_learning/ can't
    be loaded, so a broken ML environment degrades to top-down-only rather than crashing Tier 2."""
    try:
        ml_dir = str(ROOT / "machine_learning")
        if ml_dir not in sys.path:
            sys.path.insert(0, ml_dir)
        from predict_wallet import MLWalletPredictor
    except Exception:
        return ""

    try:
        predictor = MLWalletPredictor()
        wallet_model = pd.read_csv(EXTRACTED_DIR / "wallet_model.csv")
        rows = []
        for entity_name in wallet_model["entity_name"]:
            for pillar, targets in predictor.predict_for_client(entity_name).items():
                for t in targets:
                    rows.append({"entity_name": entity_name, "pillar": pillar, **t})
        return pd.DataFrame(rows).to_csv(index=False) if rows else ""
    except Exception:
        return ""


def _load_context() -> str:
    wallet_model = pd.read_csv(EXTRACTED_DIR / "wallet_model.csv")
    ranking = pd.read_csv(EXTRACTED_DIR / "opportunity_ranking.csv")
    anomalies_path = EXTRACTED_DIR / "anomalies_detected.csv"
    anomalies = pd.read_csv(anomalies_path) if anomalies_path.exists() else pd.DataFrame()
    context = (
        f"wallet_model.csv:\n{wallet_model.to_csv(index=False)}\n\n"
        f"opportunity_ranking.csv:\n{ranking.to_csv(index=False)}\n\n"
        f"anomalies_detected.csv:\n{anomalies.to_csv(index=False)}"
    )
    ml_predictions = _build_ml_predictions_csv()
    if ml_predictions:
        context += (
            "\n\nml_predictions.csv (predicted_total_wallet_zar_m / predicted_gap_zar_m are blank "
            "where the model predicted a non-positive share and the figure isn't computable):\n"
            + ml_predictions
        )
    return context


def answer_open_ended(question: str) -> str:
    """Tier 2: answer a genuinely open-ended question via a live Claude call, grounded in the CSVs."""
    import anthropic

    client = anthropic.Anthropic()
    context = _load_context()
    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": f"INPUT DATA:\n{context}\n\nQUESTION: {question}"}],
    )
    return next((b.text for b in response.content if b.type == "text"), "").strip()


if __name__ == "__main__":
    if not is_available():
        print("ANTHROPIC_API_KEY not set - this Tier 2 live path is disabled. "
              "See hackathon-finreports/_extracted/nl_query_examples.md for static worked examples instead.")
    else:
        demo_questions = [
            "If you had to pick 3 clients for the sales team to prioritize this quarter, which would you pick, and why?",
            "Is there a client whose numbers we should double-check before presenting to the exec team?",
        ]
        for question in demo_questions:
            print(f"\nQ: {question}")
            print(answer_open_ended(question))
