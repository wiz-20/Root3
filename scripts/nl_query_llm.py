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

Requires ANTHROPIC_API_KEY. Callers should check is_available() first and fall back to the
Tier 1 decline message (which points at the static examples) when it's False - this keeps
the zero-cost, zero-dependency demo path fully intact when no key is configured.
"""

import os
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
EXTRACTED_DIR = ROOT / "hackathon-finreports" / "_extracted"

MODEL = "claude-opus-5"

SYSTEM_PROMPT = """You are a data analyst answering an open-ended question from a relationship banking team about a top-down Share-of-Wallet model covering 20 corporate clients across 3 banking pillars (Transactional, Trade & Working Capital, Foreign/Cross-Border).

You will be given the full wallet_model.csv, opportunity_ranking.csv, and anomalies_detected.csv tables as context, followed by a question.

Answer in 100-200 words. Requirements:
1. Answer the actual question asked - do not pad with unrelated context.
2. Cite specific entities and numbers from the provided tables - do not use any number not present in the input data.
3. If reliability tiering is relevant to the answer (i.e. the question touches a low-reliability or insufficient-reliability row), state that caveat explicitly.
4. If the question cannot be confidently answered from the available data, say so plainly rather than guessing - a wrong confident answer is worse than an honest "the data doesn't support a firm conclusion here."
"""


def is_available() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def _load_context() -> str:
    wallet_model = pd.read_csv(EXTRACTED_DIR / "wallet_model.csv")
    ranking = pd.read_csv(EXTRACTED_DIR / "opportunity_ranking.csv")
    anomalies_path = EXTRACTED_DIR / "anomalies_detected.csv"
    anomalies = pd.read_csv(anomalies_path) if anomalies_path.exists() else pd.DataFrame()
    return (
        f"wallet_model.csv:\n{wallet_model.to_csv(index=False)}\n\n"
        f"opportunity_ranking.csv:\n{ranking.to_csv(index=False)}\n\n"
        f"anomalies_detected.csv:\n{anomalies.to_csv(index=False)}"
    )


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
