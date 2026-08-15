# Root3 — Syn Bank Share of Wallet Intelligence Engine

**Team ROOT3** — Luke Naidoo · Wisdom Ejiro Peru · Faten Saud
Standard Bank Data School Hackathon 2026

## Overview

This project estimates Syn Bank's **share of wallet** — the proportion of a corporate
client's total banking activity that Syn Bank currently captures, and the size of the
addressable gap — across 20 JSE-listed corporate clients. The estimate is produced by two
independent models, cross-checked against each other, and made explorable through a GenAI
layer:

1. A **top-down model**, built from each client's own public financial disclosures
   (revenue, cost of sales, trade receivables/payables, disclosed foreign-revenue split).
2. A **machine-learning model** (ElasticNet), trained on Syn Bank's own internal
   transaction activity alone — providing a usable estimate precisely where the top-down
   model is weakest, i.e. where external data is missing or of low reliability.

The GenAI layer — client briefing notes, anomaly explanations, and natural-language
querying — is grounded in both models, not one. The live GenAI layer is grounded in both estimation approaches, with top-down and ML-derived figures explicitly labelled by source so that agreement or disagreement between the models can be surfaced rather than hidden.
Full technical detail — every script, its inputs and outputs, and which components run
live versus which were executed once during data preparation — is documented in
[`PIPELINE.md`](PIPELINE.md).

---

## Quick start

```sh
pip install -r requirements.txt

# Interactive executive dashboard
streamlit run dashboard/app.py

# Full reproducible notebook (open in Jupyter/VS Code, then Run All)
jupyter lab wallet_engine.ipynb
```

These two artifacts are sufficient to evaluate the submission: the **dashboard**
(`streamlit run dashboard/app.py`) and the **notebook** (`wallet_engine.ipynb`). All other
components — the medallion data pipeline, the PDF-extraction pipeline, and the top-down
model build — were executed once during data preparation, with their output committed to
the repository; neither entry point above needs to re-run them. See `PIPELINE.md` §1-2 for
the full breakdown of live versus offline components.

Optional, for live natural-language querying beyond the built-in worked examples:

```sh
export ANTHROPIC_API_KEY=sk-ant-...        # macOS/Linux
$env:ANTHROPIC_API_KEY = "sk-ant-..."      # PowerShell
```

Without a configured key, the assistant falls back automatically to a free, deterministic
rule-based layer and a set of pre-written worked examples, so the demonstration is
unaffected by a missing or invalid key.

---

## Architecture

```text
Internal Syn Bank data ─┬─→ Top-down model ───────────────┐
                         │   (financials-based proxy)       │
External financials ────┘                                  │
                                                            ├─→ GenAI layer
Internal Syn Bank data ───→ ElasticNet ML model             │       ↓
                              ↓                              │    Dashboard /
                         Predicted share                     │    Notebook
                              ↓                              │
                     Deterministic calculation              │
                              ↓                              │
                      Wallet + Gap ──────────────────────────┘
```

The ML model and the GenAI layer are integrated by design: the ML model's predictions are
one of the two inputs the GenAI layer reasons over, rather than a parallel, disconnected
analysis. The full integration is documented in `PIPELINE.md` §6-9.

---

## Feeding in new data

New data enters the system through one of two independent tracks, depending on its source.
Neither track requires any code changes — only re-running the relevant scripts in order.

### Track A — new Syn Bank internal activity (updates the ML model's predictions)

1. Replace or update the raw internal CSVs at the repository root (`transactional_banking.csv`,
   `trade_finance.csv`, `cross_border_payments.csv`).
2. Rebuild the internal gold-layer features:
   ```sh
   python medallion-pipeline/scripts/bronze_silver_transformation.py
   python medallion-pipeline/scripts/silver_gold_transformation.py
   ```
   This regenerates `medallion-pipeline/gold/*.csv`.
3. No retraining is required. `machine_learning/predict_wallet.py` reads the gold CSVs
   directly each time it loads, and the already-trained ElasticNet model predicts on
   whatever internal activity is present — including for a client outside the original 20,
   provided a row exists for them in the gold tables. This is the scenario the model's
   Leave-One-Group-Out validation was designed to demonstrate (see `PIPELINE.md` §7).
4. If the dashboard is already running, restart it (`streamlit run dashboard/app.py`) to
   load the updated gold files — the ML predictor is cached for the life of the running
   session. In the notebook, re-running the relevant cells picks up the update immediately.

Retraining (`python machine_learning/elastic_net.py`) is only necessary when adding new
**labelled** training examples — company-years where both the internal activity and the
true external wallet figure are known — so the model's coefficients themselves improve.
Predicting on new activity for inference does not require this step.

### Track B — new external financial disclosures (updates the top-down model)

1. Add the new source PDF(s) and run the extraction pipeline:
   ```sh
   python scripts/extract_financials_multiyear.py
   python scripts/merge_multiyear.py
   python scripts/split_by_category.py
   ```
2. Rebuild the top-down wallet model:
   ```sh
   python scripts/build_wallet_model.py
   ```
   This regenerates `wallet_model.csv` and `opportunity_ranking.csv`.
3. As with Track A, restart the dashboard or re-run the relevant notebook cells to load
   the updated files.

### The GenAI layer and dashboard require no separate update step

Both GenAI tiers query the live model output on every question — they do not need to be
re-run to "pick up" new data:

- **Tier 1** (`scripts/nl_query_assistant.py`) calls `MLWalletPredictor` directly for every
  client question, so it reflects whatever the model currently predicts.
- **Tier 2** (`scripts/nl_query_llm.py`) rebuilds its full ML-predictions grounding table
  from `MLWalletPredictor` on every single call — never from a cached snapshot.
- The dashboard's client drill-down (top-down summary, AI briefing note, ML cross-check)
  and the "Ask a Question" assistant all read from the same live objects.

The one step that does need repeating after new data arrives is restarting whichever
process (dashboard or notebook kernel) is already running, so it re-reads the updated
files from disk — this is a data-refresh step, not a GenAI re-run.

---

## Repository structure

| Path | Contents |
|---|---|
| `dashboard/` | The Streamlit executive dashboard |
| `wallet_engine.ipynb` | The full reproducible notebook — the primary end-to-end technical narrative |
| `scripts/` | Data preparation, the top-down wallet model, anomaly detection, the NL query assistant (Tier 1 and Tier 2), and grounding-verification scripts |
| `machine_learning/` | ElasticNet training (`elastic_net.py`), the wallet/gap derivation (`wallet_math.py`), and the inference API (`predict_wallet.py`) |
| `medallion-pipeline/` | The PySpark bronze/silver/gold pipeline over the raw internal datasets |
| `docs/genai/` | GenAI prompt templates and design rationale for all three required use cases |
| `docs/reports/` | Data-profiling reports and the wallet-model methodology document |
| `docs/deliverables/` | The one-page PDF solution summary |
| `hackathon-finreports*/` | External source PDFs and all extracted/derived CSVs (`_extracted/`) |
| `PIPELINE.md` | The detailed technical reference |
| `DATA_SOURCES.md` | Researched external data sources, including the bottom-up evidence path scoped out of this submission |
| `PLAN.md` | Project scope, team allocation, and judging-criteria weights |

---

## Documentation index

| Question | Reference |
|---|---|
| What does a given file do, and what does it produce? | `PIPELINE.md` |
| How does the GenAI layer work, and how is it grounded? | `docs/genai/README.md` |
| What external data sources were evaluated, and why? | `DATA_SOURCES.md` |
| What was the original project scope and evaluation rubric? | `PLAN.md` |

## Updating the System with New Syn Bank Data

The trained ElasticNet models are designed to score newly available Syn Bank internal activity without requiring model retraining. When new transactional, trade-finance, or cross-border data becomes available, the raw data is first processed through the medallion pipeline to regenerate the Gold-layer client features. The dashboard then automatically uses these updated features to generate new machine-learning predictions and provide the latest results to the live GenAI layer.

The operational pipeline is:

```text
Update Syn Bank Internal Data
        ↓
cross_border_payments.csv
trade_finance.csv
transactional_banking.csv
        ↓
Bronze → Silver Transformation
        ↓
Silver → Gold Transformation
        ↓
Updated Gold-Layer Datasets
        ↓
dashboard/app.py
        │
        ├──→ predict_wallet.py
        │       │
        │       ├── reads the latest Gold-layer client data
        │       ├── loads the existing trained ElasticNet models and scalers
        │       └── predicts Share of Wallet
        │
        ├──→ wallet_math.py
        │       │
        │       ├── Estimated Wallet = Syn Bank Activity / Predicted Share
        │       └── Estimated Gap = Estimated Wallet - Syn Bank Activity
        │
        └──→ GenAI Layer
                │
                ├── Tier 1: deterministic natural-language querying
                │
                └── Tier 2: live LLM synthesis grounded in the latest
                    ML predictions and top-down model results