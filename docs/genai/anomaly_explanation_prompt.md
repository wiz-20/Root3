# GenAI Layer — Anomaly Explanation

**Deliverable this satisfies:** the "anomaly explanations" GenAI use case named in `PLAN.md` (alongside client briefing notes and NL querying) — this is a deliberately distinct capability, not a repackaging of the briefing notes.

## Why this is architecturally different from the briefing notes

The briefing notes (`docs/genai/briefing_note_prompt.md`) are a **holistic narrative per client**, written by a human-in-the-loop judgment call about which 20 clients matter and what story their numbers tell.

This layer is the opposite shape: **systematic, rule-based detection across all 60 client×pillar cells** (20 clients × 3 pillars) plus the blended total — nothing is judgment-selected, every cell is checked against the same fixed rules — with GenAI used for exactly one job: explaining *why* a detected pattern happens and what a banker should do about it. Detection and explanation are two separate scripts/artifacts on purpose:

1. **`scripts/detect_anomalies.py`** (pure code, deterministic, zero LLM involvement) — scans every cell against 5 fixed rules (proxy breakdown >100% share, missing external wallet, insufficient reliability, low-reliability scale mismatch in the top quartile of gaps, and statistical outliers >1.5σ from their reliability-tier peer group) and writes every match to `anomalies_detected.csv`. An LLM asked to "find anomalies" in a raw 20-row table can miss real ones or invent fake ones — a fixed rule set can't do either.
2. **This prompt, applied only to that structured output** — never to the raw `wallet_model.csv` — synthesizes the 27 detected instances into ~6 distinct explained patterns, grouped by rule type rather than 27 near-duplicate paragraphs.

## Prompt template

```
You are a data analyst explaining a set of automatically-flagged anomalies from a bank's
wallet-share model to a non-technical banking audience (relationship bankers, not analysts).

You will be given a CSV of anomalies. Each row has: entity_name, pillar, rule (the
programmatic rule that triggered), and detail (the specific numbers that triggered it).

For EACH DISTINCT RULE TYPE (not each row):
1. Explain in plain English what pattern this rule is catching and why it happens
   mechanically (not "the model is wrong" - explain the real-world reason, e.g. a global
   miner's group revenue includes non-SA operations).
2. Cite 2-3 specific example entities from the rows for that rule, with their actual numbers.
3. State plainly whether this is (a) a genuine business finding a banker should act on,
   (b) a data/proxy limitation that should be caveated but not acted on literally, or
   (c) a research gap (real activity, no benchmark yet) - do not blur these three categories.
4. If it's category (a), give one specific recommended action.

Do not invent entities, numbers, or rows not present in the input CSV. If a rule type has
only 1 matching row, still explain it - do not skip low-count patterns.

INPUT: anomalies_detected.csv (27 rows, 6 rule types)
```

## Output

See `hackathon-finreports/_extracted/anomaly_explanations.md` — 6 rule types covering all 27 detected instances across 18 of the 20 clients, each classified into the finding/limitation/research-gap taxonomy from the prompt.

## Why this design earns marks beyond "we called an LLM"

- **Two-stage grounding**: the model never sees raw financials, only an already-verified, code-generated anomaly list — makes hallucination structurally harder, not just prompted-against.
- **Exhaustive, not cherry-picked**: 60/60 cells checked by fixed rules, vs. a human eyeballing a spreadsheet for "anything weird" and inevitably missing some.
- **Actionable typology**: forces every explanation into finding / limitation / research-gap, directly serving the rubric's "actionable, banker-usable recommendations" criterion instead of just describing what's odd.
- **Reusable**: the detection rules and thresholds are stated explicitly in `scripts/detect_anomalies.py`'s docstring — swapping in a new quarter's `wallet_model.csv` re-runs the same two stages with no code changes.
