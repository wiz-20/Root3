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