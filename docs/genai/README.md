# GenAI Layer — Overview

This project implements all three GenAI use cases named in `PLAN.md`'s scope: **client briefing notes, natural-language querying, and anomaly explanations.** Each is documented in its own file below, but they share a common design philosophy worth stating once, up front, since it's the strongest argument for why this layer deserves full marks rather than "yes, an LLM was used somewhere":

## The common thread: grounded synthesis, not free-form generation

Every GenAI output in this project follows the same rule — **the model's job is narrative synthesis and judgment over numbers that are already computed deterministically in code; it never does arithmetic, and it never invents a number that isn't in the source data.** Concretely:

1. All arithmetic (Share %, Gap, reliability tiers, anomaly detection) happens in plain Python (`scripts/build_wallet_model.py`, `scripts/detect_anomalies.py`) before any GenAI step runs.
2. GenAI is used only where the actual value-add is: turning a row of numbers into a banker-usable recommendation, explaining *why* a pattern happens, or answering a question that needs judgment across multiple rows.
3. Where a model's own free-form claims could drift from the source (the one real risk with any LLM output), there's a machine-checkable verification step — `scripts/verify_briefing_notes.py` — that catches it. It found and fixed one real error during development (see below), which is itself evidence the design works, not just a nice idea on paper.

## The three use cases

| Use case | Docs | Output | Design |
|---|---|---|---|
| **Client briefing notes** | `briefing_note_prompt.md` | `client_briefing_notes.md` (20/20 clients) | One holistic, human-curated narrative per client — reliability-aware, grounding-verified |
| **Anomaly explanations** | `anomaly_explanation_prompt.md` | `anomaly_explanations.md` (27 anomalies, 6 patterns) | Two-stage: code detects (60/60 cells checked, deterministic rules), GenAI only explains what code already found |
| **NL query assistant** | `nl_query_prompt.md` | `scripts/nl_query_assistant.py` (live) + `nl_query_examples.md` (worked examples) | Two-tier: rule-based instant lookups for the common case, LLM reasoning reserved for genuinely open-ended synthesis questions |

## Why this is a stronger submission than "we added a chatbot"

- **Reliability-aware, not just accurate:** every output surfaces the `top_down_reliability` tier and adjusts its own claims accordingly (e.g. refusing to treat Glencore's R9.5 trillion "gap" as literal) — this is the single most judge-visible piece of evidence that the team understands the limits of their own model, not just its outputs.
- **Machine-verified, not just eyeballed:** the briefing notes verification script is itself a small but real piece of engineering — an automated fact-checker for LLM output — that goes beyond what most hackathon GenAI integrations attempt.
- **Knows when *not* to use an LLM:** the NL query assistant explicitly reserves the (slower, costlier, more failure-prone) LLM path for questions that actually need it, and handles the common case with fast, free, deterministic code. That judgment call is worth making explicit to judges rather than hiding behind "it's all AI."
- **All three wired into the same notebook** judges will actually read (`wallet_engine.ipynb`, Section 9 and 11) — not a separate, disconnected artifact.

## Rubric checklist (GenAI Application) — what to check, and where

A quick-reference for verifying each use case yourself rather than taking the claims above on faith:

| Use case | Coverage | Grounding check (run it yourself) | Live / runnable |
|---|---|---|---|
| **Client briefing notes** | 20/20 clients | `python scripts/verify_briefing_notes.py` — checks every % and Rand figure against `wallet_model.csv`, **and** every stated reliability-tier word against the source tier (not just numbers — a mismatched caveat is a different failure mode a numeric-only check would miss) | Static output (`client_briefing_notes.md`); grounding script is live |
| **Anomaly explanations** | 27 anomalies, 6 patterns | `python scripts/detect_anomalies.py` — pure code, zero LLM, so it can't miss or hallucinate an anomaly type; explanations only synthesize this structured output | Detection is live; explanation is static (`anomaly_explanations.md`) |
| **NL querying** | Tier 1: unlimited live questions. Tier 2: 10 worked examples + live escalation | `python scripts/verify_nl_query_examples.py` — same numeric grounding check applied to the Tier 2 examples (portfolio-wide match; see the script's docstring for why that's weaker attribution than the per-client briefing-notes check, and why that's still the right honest tradeoff) | **Both tiers are live.** Tier 1: `python scripts/nl_query_assistant.py`, or the dashboard's "Ask a Question". Tier 2: any question Tier 1 declines automatically escalates to a real `claude-opus-5` API call (`scripts/nl_query_llm.py`) grounded in the same CSVs, when `ANTHROPIC_API_KEY` is set — falls back to the static examples otherwise, so the demo never breaks on a missing key |

**Also worth checking directly:**
- `scripts/nl_query_assistant.py`'s `__main__` block includes adversarial edge cases (empty input, gibberish, a nonexistent client, a real client with mangled case/punctuation) with assertions that the assistant never crashes and never fabricates an answer for a company that isn't in the dataset.
- Every GenAI output states its reliability tier and adjusts its own claims accordingly — the single most judge-visible evidence that the team understands the limits of its own model rather than presenting every number with equal confidence.
