"""
Grounding verification for GenAI-generated Tier 2 NL query examples
(hackathon-finreports/_extracted/nl_query_examples.md).

Same grounding concern as scripts/verify_briefing_notes.py: "how do we know the LLM didn't
invent a number?" Extracts every percentage and every Rand figure (bn/trillion/m) stated in
each Q&A pair and checks it against the source-of-truth numbers in wallet_model.csv and
opportunity_ranking.csv, within a small rounding tolerance.

Honest limitation, stated up front rather than glossed over: unlike the briefing notes (one
section per client, checked against that client's own row), each Tier 2 answer here often
synthesizes across MULTIPLE clients in one paragraph (e.g. "which 3 clients should we
prioritize"). There is no reliable way to parse which number belongs to which entity from
prose alone, so this check is portfolio-wide: every stated number must match SOME row in the
dataset, not necessarily the specific client it's attributed to. That is weaker attribution
than the per-client check, but it still catches the failure mode that matters most for a
grounding check - a number that was never in the data at all.

Output: prints a pass/fail summary per question, and a full audit trail to
hackathon-finreports/_extracted/nl_query_examples_verification.csv
"""

import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
EXTRACTED_DIR = ROOT / "hackathon-finreports" / "_extracted"

TOLERANCE = 0.015  # 1.5% relative tolerance for rounding in prose (e.g. "R448bn" for 447,941)

PCT_RE = re.compile(r"(-?\d+(?:\.\d+)?)\s*%")
RAND_RE = re.compile(r"R\s?(-?\d+(?:[.,]\d+)?)\s*(trillion|bn|billion|million|m)\b", re.IGNORECASE)

UNIT_TO_ZAR_MILLIONS = {
    "trillion": 1_000_000.0,
    "bn": 1_000.0,
    "billion": 1_000.0,
    "million": 1.0,
    "m": 1.0,
}


def close(a: float, b: float, tol: float = TOLERANCE) -> bool:
    if pd.isna(a) or pd.isna(b):
        return False
    if b == 0:
        return abs(a) < 1e-6
    return (abs(a - b) / abs(b) <= tol) or (abs(a - b) <= 0.5)


def extract_questions(md_text: str) -> dict:
    """Split the examples file into {question: answer_text} blocks."""
    sections = {}
    parts = re.split(r"^### Q: (.+)$", md_text, flags=re.MULTILINE)
    # parts[0] is the preamble before the first "### Q:"; then alternating [question, body, ...]
    for i in range(1, len(parts), 2):
        question = parts[i].strip()
        sections[question] = parts[i + 1]
    return sections


def numbers_in_text(text: str) -> tuple[list[float], list[float]]:
    pcts = [float(m.group(1)) for m in PCT_RE.finditer(text)]
    rands_zar_m = []
    for m in RAND_RE.finditer(text):
        value = float(m.group(1).replace(",", ""))
        unit = m.group(2).lower()
        rands_zar_m.append(value * UNIT_TO_ZAR_MILLIONS[unit])
    return pcts, rands_zar_m


def build_portfolio_number_pool() -> tuple[list[float], list[float]]:
    wallet_model = pd.read_csv(EXTRACTED_DIR / "wallet_model.csv")
    ranking = pd.read_csv(EXTRACTED_DIR / "opportunity_ranking.csv")
    multiyear_ml = pd.read_csv(EXTRACTED_DIR / "financials_multiyear_ml.csv")

    pct_cols = ["share_pct_pillar1", "share_pct_pillar2", "share_pct_pillar3", "blended_share_pct"]
    rand_cols = [
        "internal_pillar1_zar_m", "total_wallet_pillar1_zar_m", "gap_zar_m_pillar1",
        "internal_pillar2_zar_m", "total_wallet_pillar2_zar_m", "gap_zar_m_pillar2",
        "internal_pillar3_zar_m", "total_wallet_pillar3_zar_m", "gap_zar_m_pillar3",
        "total_internal_zar_m", "total_wallet_zar_m", "total_gap_zar_m",
    ]

    pcts = []
    rands = []
    for df in (wallet_model, ranking):
        for c in pct_cols:
            if c in df.columns:
                pcts.extend(df[c].dropna().tolist())
        for c in rand_cols:
            if c in df.columns:
                rands.extend(df[c].dropna().tolist())

    foreign_pct = (
        multiyear_ml[multiyear_ml["fiscal_year"] == 2025]
        .drop_duplicates(subset="entity_name")["foreign_revenue_pct"]
        .dropna()
        .tolist()
    )
    pcts.extend(foreign_pct)

    return pcts, rands


def main():
    examples_text = (EXTRACTED_DIR / "nl_query_examples.md").read_text(encoding="utf-8")
    portfolio_pcts, portfolio_rands = build_portfolio_number_pool()

    questions = extract_questions(examples_text)
    audit_rows = []

    for question, body in questions.items():
        stated_pcts, stated_rands = numbers_in_text(body)

        for pct in stated_pcts:
            matched = any(close(pct, p) for p in portfolio_pcts)
            audit_rows.append({
                "question": question, "type": "percent", "stated_value": pct, "verified": matched,
            })

        for rand in stated_rands:
            matched = any(close(rand, r) for r in portfolio_rands)
            audit_rows.append({
                "question": question, "type": "rand_zar_m", "stated_value": rand, "verified": matched,
            })

    audit = pd.DataFrame(audit_rows)
    audit_path = EXTRACTED_DIR / "nl_query_examples_verification.csv"
    audit.to_csv(audit_path, index=False)

    print(f"Checked {len(audit)} numeric claims across {audit['question'].nunique()} Tier 2 questions")
    print("(portfolio-wide match, not per-client attributed - see this script's docstring for why)\n")

    summary = audit.groupby("question")["verified"].agg(["sum", "count"])
    summary["pass"] = summary["sum"] == summary["count"]
    for question, r in summary.iterrows():
        status = "PASS" if r["pass"] else "REVIEW"
        short_q = question if len(question) <= 70 else question[:67] + "..."
        print(f"  [{status}] {short_q}: {int(r['sum'])}/{int(r['count'])} numeric claims verified")

    unverified = audit[~audit["verified"]]
    if len(unverified):
        print(f"\n{len(unverified)} UNVERIFIED claims (candidate hallucinations/rounding beyond tolerance):")
        print(unverified.to_string(index=False))
    else:
        print(f"\nAll {len(audit)} numeric claims across {audit['question'].nunique()} questions verified against wallet_model.csv / opportunity_ranking.csv (tolerance={TOLERANCE:.1%}).")

    print(f"\nFull audit trail written to {audit_path}")


if __name__ == "__main__":
    main()
