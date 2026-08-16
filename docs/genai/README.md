# GenAI Layer — Syn Bank Share of Wallet Intelligence Engine

**Team ROOT3** — Standard Bank Data School Hackathon 2026

## Overview

The GenAI layer provides the natural-language interpretation and querying interface for
the Syn Bank Share-of-Wallet Intelligence Engine.

It sits on top of the analytical models and converts their outputs into accessible,
business-facing insights for relationship managers and decision-makers.

The GenAI layer does **not** calculate the underlying Share-of-Wallet estimates itself.
Numerical estimates are produced by two independent analytical approaches:

1. A **top-down model**, which estimates wallet size and opportunity gaps using Syn Bank
   activity together with publicly available financial disclosures.
2. An **ElasticNet machine-learning model**, which learns relationships between Syn Bank
   internal activity and externally derived wallet indicators. Once trained, it can
   perform inference using new Syn Bank internal activity without requiring a new
   financial-report extraction for every prediction.

The GenAI layer consumes these outputs to explain results, surface anomalies, compare
estimation approaches, and allow users to interrogate the portfolio through natural
language.

---

## GenAI Components

The solution implements three complementary GenAI use cases.

| Use Case | Purpose |
|---|---|
| **Client Briefing Notes** | Converts model outputs into concise client-level business insights |
| **Anomaly Explanation** | Explains unusual or potentially unreliable analytical results |
| **Natural-Language Querying** | Allows users to interrogate the Share-of-Wallet portfolio conversationally |

The natural-language querying component is further divided into two tiers:

| Tier | Implementation | Purpose |
|---|---|---|
| **Tier 1** | `scripts/nl_query_assistant.py` | Deterministic querying for common analytical questions |
| **Tier 2** | `scripts/nl_query_llm.py` | Live LLM synthesis for open-ended questions |

The dashboard in `dashboard/app.py` provides the business-facing interface through which
these capabilities are exposed.

---

## Architecture

```text
Top-Down Model ───────────────┐
                              │
ElasticNet ML Predictions ────┼──→ Grounded GenAI Layer
                              │          │
Anomaly Detection ────────────┘          ├── Client Briefings
                                         ├── Anomaly Explanations
                                         └── Natural-Language Queries
                                                   │
                                                   ↓
                                                Dashboard
```

The analytical models remain responsible for numerical estimation.

The GenAI layer is therefore an **interpretation and decision-support layer**, rather
than the source of the financial estimates themselves.

---

## 1. Client Briefing Notes

Client briefing notes translate Share-of-Wallet outputs into concise business-facing
summaries.

Rather than requiring a relationship manager to manually inspect multiple model outputs,
the briefing layer highlights the most relevant information for a client, including:

- Estimated Share of Wallet
- Addressable wallet gap
- Differences across banking pillars
- Potential opportunity areas
- Reliability considerations
- Relevant anomalies or limitations

These summaries provide a bridge between the analytical outputs and the business user.

Where both modelling approaches are available, the top-down and ML estimates remain
distinct rather than being silently combined into a single figure.

---

## 2. Anomaly Explanation

The top-down analytical pipeline includes rule-based anomaly detection to identify
results that may require additional scrutiny.

Examples include estimates affected by incomplete external disclosures or unusual
relationships between Syn Bank activity and the estimated external wallet.

The GenAI layer translates these analytical flags into human-readable explanations.

This allows a user to distinguish between:

```text
Large commercial opportunity
          vs.
Potentially unreliable estimate
```

The anomaly explanation layer therefore does not independently decide whether an
estimate is valid. It explains anomalies already identified by the analytical pipeline.

---

## 3. Natural-Language Querying

The natural-language querying capability allows users to interrogate the Share-of-Wallet
portfolio without manually searching through CSV files or model outputs.

A two-tier architecture is used.

```text
User Question
      ↓
Tier 1 — Deterministic Assistant
      │
      ├── Supported structured question
      │           ↓
      │    Deterministic Answer
      │
      └── Open-ended question
                  ↓
          Tier 2 — Live LLM
                  ↓
          Grounded Synthesis
                  ↓
               Answer
```

This design keeps common analytical queries deterministic while reserving the live LLM
for questions where broader synthesis is useful.

---

## Tier 1 — Deterministic Query Assistant

**Implementation:** `scripts/nl_query_assistant.py`

Tier 1 handles common analytical questions without requiring an external LLM call.

It uses the current ElasticNet predictions generated by:

```python
MLWalletPredictor.predict_all_clients()
```

The resulting prediction table determines the current client universe.

This is important because the assistant is **not restricted to the original top-down
portfolio**. A newly supplied client can therefore become queryable once its internal
activity has successfully passed through the medallion pipeline.

Tier 1 supports questions such as:

- "What is this client's wallet?"
- "What does the ML model predict for this client?"
- "What are the top 5 opportunities?"
- "Which pillar should we lead with for this client?"
- "Is there a top-down benchmark for this client?"
- "Are there anomalies associated with this client?"

Responses are generated directly from the underlying model outputs using deterministic
logic and templates.

No external LLM API is required for Tier 1.

---

## Tier 2 — Live LLM Synthesis

**Implementation:** `scripts/nl_query_llm.py`

Tier 2 handles more open-ended questions requiring synthesis across multiple clients,
pillars, or estimation approaches.

Examples include:

- "Which clients should the sales team prioritise this quarter and why?"
- "Which estimates should be double-checked before presenting them?"
- "Where do the ML and top-down models materially disagree?"
- "What are the most important opportunities across the current portfolio?"

For every Tier 2 request, the system builds a grounding context containing the latest
available analytical outputs.

### ML Grounding Data

`nl_query_llm.py` calls:

```python
MLWalletPredictor.predict_all_clients()
```

and converts the results into an in-memory CSV grounding table containing fields such as:

```text
entity_name
pillar
target
internal_zar
predicted_share_pct
predicted_total_wallet_zar_m
predicted_gap_zar_m
```

This represents the **current operational client portfolio**.

### Top-Down Grounding Data

The LLM also receives the available external benchmark information from:

```text
wallet_model.csv
opportunity_ranking.csv
anomalies_detected.csv
```

These files provide the independent top-down estimate and associated reliability
information.

The top-down portfolio may contain only a subset of the clients currently available to
the ML model.

---

## Grounding and Hallucination Controls

The Tier 2 LLM is not asked to independently calculate Share of Wallet.

Instead, the relevant analytical outputs are explicitly supplied as grounding context
with each request.

The system prompt instructs the LLM to:

1. Answer the actual question being asked.
2. Never introduce numerical values that are not contained in the supplied data.
3. Explicitly label figures as originating from either the **ML model** or the
   **top-down model**.
4. Treat the ML predictions as the primary source for the current operational portfolio.
5. Only use a top-down estimate when that client actually exists in the top-down data.
6. Surface material disagreement between the two estimation approaches.
7. Explicitly state when no external top-down benchmark is available.
8. Preserve relevant reliability caveats associated with top-down estimates.
9. State when the available evidence cannot support a confident conclusion rather than
   guessing.

The two estimation approaches therefore remain distinguishable throughout the GenAI
workflow:

```text
Top-Down Estimate ───────→ labelled "top-down model" ──┐
                                                       │
                                                       ├──→ LLM Synthesis
                                                       │
ElasticNet Estimate ─────→ labelled "ML model" ────────┘
```

This allows agreement between the models to provide additional context while ensuring
that disagreement is visible to the user rather than hidden.

---

## Handling New Clients

The GenAI layer is designed to work beyond the original modelling portfolio.

When new Syn Bank internal activity becomes available, the raw files at the repository
root are updated:

```text
cross_border_payments.csv
trade_finance.csv
transactional_banking.csv
```

For a completely new client whose fiscal-year information is not already available from
the extracted financial-report metadata, its reporting periods must also be supplied in:

```text
client_fiscal_years.csv
```

For example:

```csv
entity_name,fiscal_year,fiscal_year_end
New Client Ltd,2025,30 June 2025
New Client Ltd,2026,30 June 2026
```

The new data then follows the existing pipeline:

```text
Updated Syn Bank Internal Data
             ↓
       Bronze → Silver
             ↓
        Silver → Gold
             ↓
     Updated Gold Features
             ↓
       MLWalletPredictor
             ↓
     Trained ElasticNet Models
             ↓
        Predicted Share
             ↓
         Wallet + Gap
             ↓
       GenAI Grounding
             ↓
          Dashboard
```

The existing trained ElasticNet models can therefore score new internal activity without
requiring a new external financial-report extraction for every client.

---

## Existing vs New Clients

For an existing client where both estimation approaches are available:

```text
Current ML Prediction
          +
Top-Down Benchmark
          ↓
   GenAI Layer
          ↓
Comparison / Synthesis
```

For a completely new client:

```text
Current ML Prediction
          +
No Top-Down Benchmark
          ↓
   GenAI Layer
          ↓
ML-Based Insight
+
Explicit Benchmark Limitation
```

The absence of a top-down benchmark therefore does not prevent the new client from being
analysed.

Instead, the GenAI layer explicitly communicates that the independent external benchmark
is unavailable.

---

## Refreshing the GenAI Layer

For new Syn Bank internal data, the notebook workflow is:

```text
STEP 4
Rebuild Silver + Gold layers
        ↓
STEP 6
Generate current ElasticNet predictions
        ↓
STEP 7
Launch Dashboard + GenAI
```

Therefore, after replacing the raw Syn Bank CSV files, rerun:

**Steps 4, 6 and 7 only.**

For completely new clients, ensure their fiscal-year metadata is also present in
`client_fiscal_years.csv` before running Step 4.

Model retraining is **not required** for ordinary inference on new internal activity.

Retraining is only required when new **labelled training observations** are intentionally
being added so that the ElasticNet coefficients themselves can be updated.

---

## How New Data Reaches Each GenAI Tier

### Tier 1

`nl_query_assistant.py` builds its client universe from the current predictions returned
by:

```python
MLWalletPredictor.predict_all_clients()
```

New clients appearing in the Gold layer can therefore automatically become available to
the deterministic query assistant.

### Tier 2

`nl_query_llm.py` rebuilds its ML grounding table from:

```python
MLWalletPredictor.predict_all_clients()
```

for each live LLM request.

This ensures that Tier 2 receives the current ML portfolio rather than relying on a fixed
snapshot of the original clients.

External top-down results remain available as an independent benchmark where a matching
client exists.

---

## Running the GenAI Layer

The GenAI interface is exposed through the Streamlit dashboard:

```sh
streamlit run dashboard/app.py
```

The dashboard provides access to:

- Current portfolio-level Share-of-Wallet insights
- ElasticNet-predicted wallet and gap estimates
- Opportunity ranking
- Client-level drill-down
- Available top-down benchmark information
- Client intelligence summaries
- Natural-language querying

---

## Tier 2 Configuration

Live Tier 2 synthesis requires an Anthropic API key.

### macOS / Linux

```sh
export ANTHROPIC_API_KEY=sk-ant-...
```

### PowerShell

```powershell
$env:ANTHROPIC_API_KEY = "sk-ant-..."
```

If an API key is not configured, the deterministic Tier 1 assistant remains available
and the core dashboard can still be demonstrated.

---

## Key Implementation Files

| File | Responsibility |
|---|---|
| `dashboard/app.py` | Business-facing dashboard and GenAI interface |
| `scripts/nl_query_assistant.py` | Tier 1 deterministic natural-language query assistant |
| `scripts/nl_query_llm.py` | Tier 2 live LLM synthesis and grounding |
| `machine_learning/predict_wallet.py` | Loads the current Gold data and generates ElasticNet predictions |
| `machine_learning/wallet_math.py` | Converts predicted share into estimated wallet and gap |
| `hackathon-finreports/_extracted/wallet_model.csv` | Top-down Share-of-Wallet benchmark |
| `hackathon-finreports/_extracted/opportunity_ranking.csv` | Top-down opportunity ranking |
| `hackathon-finreports/_extracted/anomalies_detected.csv` | Rule-based anomaly information |

---

## Separation of Responsibilities

The architecture deliberately separates numerical estimation from GenAI interpretation:

```text
Syn Bank + External Data
          ↓
   Analytical Models
          ↓
Share / Wallet / Gap
          ↓
     GenAI Layer
          ↓
Explanation + Querying + Synthesis
          ↓
   Business Decision Support
```

The analytical models remain the source of the numerical estimates.

The GenAI layer provides value by making those outputs easier to **interrogate, explain,
compare, and translate into actionable business insight**, while remaining grounded in
the underlying analytical results.