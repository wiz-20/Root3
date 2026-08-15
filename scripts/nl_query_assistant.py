"""
Natural-language query assistant - GenAI use case #3 (PLAN.md: "client briefing notes, NL
querying, anomaly explanations").

Honest framing (stated here, not glossed over in the demo): this module is a lightweight,
**rule-based intent classifier + templated synthesis** layer, not a live LLM call - it needs
no API key, costs nothing to run, and is fully deterministic, which makes it safe to demo
live to judges without worrying about hallucination or an API outage. It handles the
~80% case of questions a relationship banker actually asks in practice (lookups,
comparisons, rankings, reliability checks) by retrieving the exact row(s) needed from the
already-computed, human-checked CSVs and filling them into a template.

**Tied to the ML model, not parallel to it:** every per-client answer folds in
`machine_learning/predict_wallet.py`'s ElasticNet prediction alongside the top-down number
(see `_client_summary`), and "what does the ML model predict" questions route to a
dedicated ML-only answer (`_ml_prediction`). The ML model's job is the numbers; this
module's job (same GenAI layer) is turning those numbers into an answer a banker can read -
that synthesis step is the actual "querying" deliverable, and it was pointless to build it
against only one of the two models the project produces.

For genuinely open-ended questions that need cross-row reasoning or judgment (e.g. "which 3
clients should the sales team prioritize this quarter and why"), this module is
deliberately NOT used - those escalate to a live LLM call (nl_query_llm.py) when an API key
is configured, or fall back to the documented worked examples in
hackathon-finreports/_extracted/nl_query_examples.md otherwise.

Usage (from a notebook cell or the CLI):
    from nl_query_assistant import QueryAssistant
    qa = QueryAssistant()
    print(qa.answer("What is Pepkor's share of the transactional wallet?"))
    print(qa.answer("What are the top 3 opportunities?"))
    print(qa.answer("Why is Glencore's gap so large?"))
"""

import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
EXTRACTED_DIR = ROOT / "hackathon-finreports" / "_extracted"

PILLAR_NAMES = {1: "Transactional Banking", 2: "Trade & Working Capital", 3: "Foreign/Cross-Border"}


def _load_ml_predictor():
    """Lazy, best-effort load so this module still works standalone (CLI, notebook cell 29)
    without machine_learning/ on sys.path - if it's unavailable for any reason, ML-aware
    answers just fall back to top-down-only rather than crashing the whole assistant."""
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
    elif abs(v) >= 1000:
        return f"R{v / 1000:.1f}bn"
    return f"R{v:.1f}m"


class QueryAssistant:
    def __init__(self, extracted_dir: Path = EXTRACTED_DIR, ml_predictor=None):
        self.wallet_model = pd.read_csv(extracted_dir / "wallet_model.csv")
        self.ranking = pd.read_csv(extracted_dir / "opportunity_ranking.csv")
        anomalies_path = extracted_dir / "anomalies_detected.csv"
        self.anomalies = pd.read_csv(anomalies_path) if anomalies_path.exists() else pd.DataFrame()
        self.entity_names = self.wallet_model["entity_name"].tolist()
        # Callers that already have one cached (e.g. the dashboard) should pass it in to avoid
        # loading the .pkl bundles twice; otherwise this lazily loads its own.
        self.ml_predictor = ml_predictor if ml_predictor is not None else _load_ml_predictor()

    _GENERIC_WORDS = {"the", "group", "holdings", "plc", "capital", "corporation", "banking", "pharmacare"}

    def _match_entity(self, question: str) -> str | None:
        q = question.lower()
        q_words = set(re.findall(r"[a-z]+", q))

        def is_match(name: str) -> bool:
            if name.lower() in q:
                return True
            meaningful = [w for w in name.split() if w.lower() not in self._GENERIC_WORDS]
            return any(w.lower() in q_words for w in meaningful)

        matches = [name for name in self.entity_names if is_match(name)]
        if not matches:
            return None
        # Prefer the longest matching name (avoids "Anglo American" matching inside
        # "AngloGold Ashanti" style substring collisions).
        return max(matches, key=len)

    def _row(self, entity_name: str) -> pd.Series:
        return self.wallet_model[self.wallet_model["entity_name"] == entity_name].iloc[0]

    def answer(self, question: str) -> str:
        q = question.lower().strip()
        entity = self._match_entity(question)

        # No entity mentioned + a generic help-seeking phrase -> list capabilities instead of
        # falling through to the decline message. Gated on "not entity" so a real question that
        # happens to include the word "help" (e.g. "can you help me understand Pepkor's gap?")
        # still routes to its actual intent below, not this generic response.
        if not entity and re.search(
            r"^help$|help me|what can (you|i)|what (should|could) i ask|"
            r"how do(es)? (this|you) work|what (questions|things) can (you|i)|capabilit",
            q,
        ):
            return self._help()

        if ("top" in q and re.search(r"opportunit|gap|priorit", q)) or "biggest gap" in q or "largest gap" in q:
            return self._top_opportunities(q)

        if entity and re.search(r"\bml\b|machine learning|elastic ?net|model predict|predict.*wallet|predict.*share|predict.*gap", q):
            return self._ml_prediction(entity)

        if entity and re.search(r"reliab|trust|confiden|literal", q):
            return self._reliability(entity)

        if entity and re.search(r"why.*(so large|so big|so high|large gap|huge)", q):
            return self._explain_gap(entity)

        if entity and re.search(r"anomal|issue|flag|weird|wrong", q):
            return self._anomalies_for(entity)

        if entity and re.search(r"lead with|pitch|recommend|prioriti[sz]e|which pillar", q):
            return self._recommend_pillar(entity)

        if entity and re.search(r"share|wallet|gap|penetrat", q):
            return self._client_summary(entity)

        if entity:
            return self._client_summary(entity)

        return (
            "I couldn't confidently match this question to a specific client or a supported "
            "query type (top opportunities / reliability / gap explanation / anomalies / pillar "
            "recommendation / client summary) using the rule-based layer. Ask \"what can you help "
            "me with?\" for a list of supported questions. This particular question is open-ended "
            "and best answered with full reasoning - see "
            "docs/genai/nl_query_prompt.md and hackathon-finreports/_extracted/nl_query_examples.md "
            "for how these are handled via the Cursor-agent LLM layer instead."
        )

    def _help(self) -> str:
        lines = [
            "I can answer questions about any of the 20 clients in the portfolio, using both the "
            "top-down model and the ML (ElasticNet) model together. Try things like:",
            "",
            "  - \"What is Pepkor's share of the transactional wallet?\" - full client summary (both models)",
            "  - \"What are the top 5 opportunities?\" / \"top 3 actionable opportunities\" - ranked by gap",
            "  - \"Can we trust Sanlam's numbers?\" - reliability tier for a client",
            "  - \"Why is Glencore's gap so large?\" - explains a large or foreign-currency-driven gap",
            "  - \"Which pillar should we lead with for MTN?\" - pillar recommendation",
            "  - \"Are there any anomalies for Bidvest?\" - anomaly detection results",
            "  - \"What does the ML model predict for Sanlam?\" - ML-only estimate",
            "",
            "Name a client and what you want to know, and the question routes automatically. "
            "Open-ended questions that need judgment across multiple clients (e.g. \"which 3 "
            "clients should sales prioritize this quarter?\") escalate to a live LLM call when "
            "one is available, or point to worked examples otherwise.",
        ]
        return "\n".join(lines)

    def _top_opportunities(self, q: str) -> str:
        n_match = re.search(r"top\s*(\d+)", q)
        n = int(n_match.group(1)) if n_match else 5
        actionable_only = "actionable" in q or "reliable" in q or "literal" in q
        df = self.ranking.copy()
        if actionable_only:
            df = df[df["top_down_reliability"].str.startswith("moderate")]
        df = df.dropna(subset=["total_gap_zar_m"]).sort_values("total_gap_zar_m", ascending=False).head(n)
        lines = [f"Top {len(df)} opportunities by total Rand gap" + (" (actionable/moderate-reliability tier only):" if actionable_only else " (all reliability tiers):")]
        for i, (_, r) in enumerate(df.iterrows(), start=1):
            tier = "moderate" if r["top_down_reliability"].startswith("moderate") else ("low" if r["top_down_reliability"].startswith("low") else "insufficient")
            rank_note = f" (portfolio rank #{int(r['rank'])})" if actionable_only else ""
            lines.append(f"  {i}. {r['entity_name']} ({r['sector']}) - {_fmt_rand(r['total_gap_zar_m'])} gap, {r['blended_share_pct']}% share [{tier} reliability]{rank_note}")
        if not actionable_only:
            lines.append("\nNote: several of the largest gaps above (foreign-currency reporters) are directional only, not literal Rand figures - ask for 'top actionable opportunities' to filter to ZAR reporters only.")
        return "\n".join(lines)

    def _reliability(self, entity: str) -> str:
        row = self._row(entity)
        return f"{entity}: top_down_reliability = \"{row['top_down_reliability']}\". Currency: {row['currency']}. Fiscal year: {int(row['fiscal_year'])} ({row['data_vintage_flag']})."

    def _explain_gap(self, entity: str) -> str:
        row = self._row(entity)
        parts = [f"{entity}'s total gap is {_fmt_rand(row['total_gap_zar_m'])} (blended share {row['blended_share_pct']}%)."]
        if row["top_down_reliability"].startswith("low"):
            parts.append(
                f"IMPORTANT CAVEAT: {entity} reports in {row['currency']}, a foreign currency - this gap is a "
                "consolidated GLOBAL group figure, not an SA-specific wallet. Read the % share as directional "
                "evidence of low penetration, but do NOT treat the Rand figure as literal or sum it into a "
                "portfolio total."
            )
        elif row["top_down_reliability"].startswith("insufficient"):
            parts.append(
                f"IMPORTANT CAVEAT: {entity}'s blended total could not be computed at all - Group-level "
                "financials were not disclosed in the source filing, so this figure is based on partial data only."
            )
        else:
            parts.append(f"{entity} reports in ZAR (the SA-listed entity itself) - this gap is a literal, usable figure.")
        for i in [1, 2, 3]:
            share, gap = row[f"share_pct_pillar{i}"], row[f"gap_zar_m_pillar{i}"]
            if pd.notna(share):
                parts.append(f"  Pillar {i} ({PILLAR_NAMES[i]}): {share}% share, {_fmt_rand(gap)} gap")
            else:
                parts.append(f"  Pillar {i} ({PILLAR_NAMES[i]}): external wallet not estimated for this company")
        return "\n".join(parts)

    def _anomalies_for(self, entity: str) -> str:
        if self.anomalies.empty:
            return "Anomaly data not loaded - run scripts/detect_anomalies.py first."
        rows = self.anomalies[self.anomalies["entity_name"] == entity]
        if rows.empty:
            return f"No anomalies flagged for {entity} by the rule-based detector (scripts/detect_anomalies.py)."
        lines = [f"{len(rows)} anomaly(ies) flagged for {entity}:"]
        for _, r in rows.iterrows():
            lines.append(f"  [{r['rule']}] pillar {r['pillar']}: {r['detail']}")
        lines.append("\nSee hackathon-finreports/_extracted/anomaly_explanations.md for the full explanation of each rule type.")
        return "\n".join(lines)

    def _recommend_pillar(self, entity: str) -> str:
        row = self._row(entity)
        candidates = []
        for i in [1, 2, 3]:
            share, gap = row[f"share_pct_pillar{i}"], row[f"gap_zar_m_pillar{i}"]
            if pd.notna(share) and pd.notna(gap):
                candidates.append((i, share, gap))
        if not candidates:
            return f"No pillar has a usable external wallet estimate for {entity} - cannot make a data-driven pillar recommendation."
        # Lead with the pillar that has the lowest current share (most relative headroom),
        # among pillars where the gap is not proxy-broken (share <= 100%).
        valid = [c for c in candidates if c[1] <= 100]
        pool = valid if valid else candidates
        best = min(pool, key=lambda c: c[1])
        i, share, gap = best
        reliability_note = "" if row["top_down_reliability"].startswith("moderate") else " (caveat: reliability is not 'moderate' for this client - see reliability query)"
        return f"For {entity}, lead with {PILLAR_NAMES[i]}: only {share}% share captured, {_fmt_rand(gap)} gap - the largest relative headroom among pillars with a usable external benchmark.{reliability_note}"

    def _client_summary(self, entity: str) -> str:
        row = self._row(entity)
        lines = [f"{entity} ({row['sector']}, {row['currency']} reporter, FY{int(row['fiscal_year'])}, reliability: {row['top_down_reliability'].split(' - ')[0]})"]
        for i in [1, 2, 3]:
            share, gap = row[f"share_pct_pillar{i}"], row[f"gap_zar_m_pillar{i}"]
            if pd.notna(share):
                lines.append(f"  {PILLAR_NAMES[i]}: {share}% share, {_fmt_rand(gap)} gap")
            else:
                lines.append(f"  {PILLAR_NAMES[i]}: external wallet not estimated")
        if pd.notna(row["blended_share_pct"]):
            lines.append(f"  Blended: {row['blended_share_pct']}% share, {_fmt_rand(row['total_gap_zar_m'])} gap")
        else:
            lines.append("  Blended: not computed (insufficient data)")
        if self.ml_predictor is not None:
            lines.append(f"\nML cross-check (ElasticNet, internal-activity-only): {self.ml_predictor.describe(entity)}")
        return "\n".join(lines)

    def _ml_prediction(self, entity: str) -> str:
        if self.ml_predictor is None:
            return (
                f"The ML cross-check isn't available in this session (machine_learning/ models "
                f"failed to load). Falling back to the top-down summary for {entity}:\n\n"
                + self._client_summary(entity)
            )
        return self.ml_predictor.describe(entity)


if __name__ == "__main__":
    qa = QueryAssistant()
    demo_questions = [
        "What is Pepkor's share of the transactional wallet?",
        "What are the top 5 opportunities?",
        "What are the top 3 actionable opportunities?",
        "Why is Glencore's gap so large?",
        "Which pillar should we lead with for MTN?",
        "Can we trust Sanlam's numbers?",
        "Are there any anomalies for Bidvest?",
        "What is the meaning of life?",
    ]
    for question in demo_questions:
        print(f"\nQ: {question}")
        print(qa.answer(question))

    # Adversarial / edge-case questions - not "AI safety" in the LLM-jailbreak sense, but the
    # inputs most likely to break a rule-based NLU layer: no entity, a fake entity, gibberish,
    # empty input, and case/whitespace variation on a real entity. Each must return a graceful
    # string (the decline message or a sensible answer) - never raise, and never fabricate a
    # per-client answer for a company that isn't in the dataset.
    print("\n\n--- Edge cases (must not crash; must not hallucinate a fake client) ---")
    edge_case_questions = [
        "",
        "asdkjfh qwoeiu zxcv nothing here matches anything",
        "What is Fake Company Inc's share of the transactional wallet?",
        "what is pepkor's SHARE??",  # case/whitespace/punctuation variation on a real entity
        "Why is Enron's gap so large?",  # real-sounding but not-in-portfolio entity
    ]
    for question in edge_case_questions:
        print(f"\nQ: {question!r}")
        try:
            answer = qa.answer(question)
        except Exception as e:  # noqa: BLE001 - this loop's whole point is "did anything raise"
            print(f"  FAIL: raised {type(e).__name__}: {e}")
            continue
        assert isinstance(answer, str) and answer, "answer() must always return a non-empty string"
        if "Fake Company" in question or "Enron" in question:
            # No entity by this name exists in wallet_model.csv - the assistant must not
            # invent a per-client summary for it; it should fall through to the decline message.
            assert answer.startswith("I couldn't confidently match"), (
                f"expected the decline message for a nonexistent entity, got: {answer[:80]!r}"
            )
        print(f"  OK: {answer[:120]}{'...' if len(answer) > 120 else ''}")
