# GenAI Layer — Natural Language Query Assistant

**Deliverable this satisfies:** the "NL querying" GenAI use case named in `PLAN.md` (alongside client briefing notes and anomaly explanations).

## Two-tier design (stated honestly, not oversold)

Real natural-language querying over structured data splits cleanly into two very different problems, and this project deliberately solves them two different ways rather than pretending one hammer fits both:

### Tier 1 — Lookups, comparisons, rankings (~80% of realistic banker questions)
**`scripts/nl_query_assistant.py`** — a rule-based intent classifier + templated synthesis engine. No LLM call, no API key, $0 cost, fully deterministic. It retrieves the exact row(s) needed from `wallet_model.csv` / `opportunity_ranking.csv` / `anomalies_detected.csv` and fills a template. This is **not** dressed up as "AI" in the code itself — it's an honest, lightweight NLU layer that handles the questions a banker actually asks in a coverage meeting instantly and safely:
- "What is Pepkor's share of the transactional wallet?"
- "What are the top 3 actionable opportunities?"
- "Why is Glencore's gap so large?"
- "Which pillar should we lead with for MTN?"
- "Can we trust Sanlam's numbers?"
- "Are there any anomalies for Bidvest?"

This is safe to demo live to judges — no risk of hallucination, no risk of an API being down mid-demo, and it can be extended to a real Streamlit/notebook widget in minutes if there's time.

### Tier 2 — Open-ended synthesis questions (need judgment, not just lookup)
Questions like *"which 3 clients should the sales team prioritize this quarter?"* or *"is there a sector-level pattern across mining companies?"* need genuine reasoning across multiple rows, not a single lookup. These are answered using the same approach as the briefing notes and anomaly explanations — the prompt below, applied via the Cursor agent (Claude) as the LLM, grounded strictly in the already-computed CSVs.

## Prompt template (Tier 2)

```
You are a data analyst answering an open-ended question from a relationship banking team
about a top-down Share-of-Wallet model covering 20 corporate clients across 3 banking
pillars (Transactional, Trade & Working Capital, Foreign/Cross-Border).

You will be given: the question, and the full wallet_model.csv / opportunity_ranking.csv /
anomalies_detected.csv tables as context.

Answer in 100-200 words. Requirements:
1. Answer the actual question asked - do not pad with unrelated context.
2. Cite specific entities and numbers from the provided tables - do not use any number not
   present in the input data.
3. If reliability tiering is relevant to the answer (i.e. the question touches a
   low-reliability or insufficient-reliability row), state that caveat explicitly.
4. If the question cannot be confidently answered from the available data, say so plainly
   rather than guessing - a wrong confident answer is worse than an honest "the data
   doesn't support a firm conclusion here."

INPUT DATA: <wallet_model.csv, opportunity_ranking.csv, anomalies_detected.csv>
QUESTION: <question>
```

## Output

Tier 1 is fully functional code — run `python scripts/nl_query_assistant.py` for a live demo with 8 example questions. Tier 2 worked examples (6 open-ended questions requiring real cross-row synthesis) are in `hackathon-finreports/_extracted/nl_query_examples.md`.

## Why this two-tier split is the right call, not a shortcut

A single LLM call over a big CSV context for *every* question (including "what's Pepkor's share") would be slower, cost more (on a real API), and introduce hallucination risk on questions that have one unambiguous correct answer sitting right there in a lookup table. Reserving the LLM for genuinely open-ended synthesis — where a lookup table alone can't produce the answer — is the more defensible engineering decision, and is exactly the kind of "know when *not* to use an LLM" judgment that separates a thoughtful GenAI integration from a wrapper around an API call.
