# Pipeline Reference — Syn Bank Share of Wallet Intelligence Engine

This document is the detailed technical reference for the submission: what each file
produces, what it consumes, and which components execute live versus which were run once
during data preparation. For a high-level overview and quick start, see `ReadME.md`.

The machine-learning model and the GenAI layer are not independent components. The ML
model's predictions are one of two data sources the GenAI layer is grounded in — every
GenAI-generated answer that addresses a client's wallet cites both the top-down model and
the ML model, labelled and side by side. The mechanism is described in §9.

---

## 1. What is run to evaluate this submission

| Artifact | Command | Description |
|---|---|---|
| **Interactive dashboard** | `streamlit run dashboard/app.py` | The executive dashboard: portfolio KPIs, opportunity ranking, per-client drill-down (top-down estimate, AI briefing note, and ML cross-check in one view), and a live "Ask a Question" assistant. |
| **Reproducible notebook** | Open `wallet_engine.ipynb` and run all cells | The full technical narrative: ingestion, internal/external wallet construction, ML training (live), and the GenAI layer (live where noted). This is the "reproducible Python notebook" deliverable specified in `PLAN.md`. |

All other files in the repository are either an input to one of these two artifacts, or a
standalone script that one of them calls. Nothing else needs to be executed directly — see §2.

---

## 2. Live execution versus offline data preparation

Not every script in the repository runs when the notebook or dashboard is opened. Some
scripts already ran once, during data preparation, and their output is committed to the
repository; others execute live, every time. The table below states which is which for each
stage of the pipeline.

| Stage | Script(s) | Output | Executes live? |
|---|---|---|---|
| Raw internal data → bronze/silver/gold | `medallion-pipeline/scripts/bronze_silver_transformation.py`, `silver_gold_transformation.py` (PySpark) | `medallion-pipeline/gold/*.csv` | No. Requires a JVM and processes a 2.8M-row file; output is committed. |
| External PDFs → structured financials | `scripts/extract_financials.py` / `extract_financials_multiyear.py`, `merge_extraction.py` / `merge_multiyear.py`, `split_by_category.py` | `financials_extracted.csv`, `financials_multiyear.csv`, `financials_multiyear_ml.csv`, 3 pillar-split CSVs | No. Uses an AI agent over source PDFs at build time; output is committed. |
| Internal pillar-spend snapshot | `scripts/build_pillar_spend.py`, `build_pillar_spend_multiyear.py` | `pillar_spend_wide.csv`, `pillar_spend_long.csv`, multi-year variants | No — reads the 2.8M-row `transactional_banking.csv` directly. Notebook Section 5 reads its output. |
| Top-down wallet model | `scripts/build_wallet_model.py` | `wallet_model.csv`, `opportunity_ranking.csv` | No. Notebook Sections 6-8 read these files directly. |
| **ElasticNet ML model (training)** | `machine_learning/elastic_net.py` | `machine_learning/models/*.pkl` | **Yes.** Notebook Section 10 imports this module directly, re-running the full hyperparameter search, Leave-One-Group-Out cross-validation, and final refit (~15 seconds) on every execution. |
| **ML inference** (share → wallet → gap, and its GenAI narrative) | `machine_learning/wallet_math.py`, `predict_wallet.py` | Not persisted — computed on demand | **Yes.** Called by the notebook (Section 10), the dashboard (ML cross-check card and every Tier 1 client answer), and the Tier 2 grounding context. |
| Anomaly detection | `scripts/detect_anomalies.py` | `anomalies_detected.csv` | **Yes**, in Section 11a and the dashboard. |
| **NL query assistant (Tier 1 + Tier 2)** | `scripts/nl_query_assistant.py`, `nl_query_llm.py` | — | **Yes**, in Section 11b and the dashboard's "Ask a Question" panel. |
| Client briefing notes (text) | Generated once against `wallet_model.csv`, per `docs/genai/briefing_note_prompt.md` | `client_briefing_notes.md` | Text is static; the grounding check (`verify_briefing_notes.py`) executes live in Section 9 and in the dashboard. |

**Summary:** any stage requiring the raw internal datasets, PySpark, or AI-assisted PDF
extraction was run once, offline, with its output committed to the repository. Every stage
downstream of those committed files — the ML model, the wallet-gap derivation, the GenAI
querying layer, and the dashboard — executes live, on every run.

---

## 3. End-to-end pipeline

```text
┌─────────────────────────────┐        ┌──────────────────────────────────┐
│   INTERNAL (Syn Bank)        │        │   EXTERNAL (public financials)    │
│                               │        │                                    │
│ transactional_banking.csv    │        │ Company AFS / Integrated Report   │
│ trade_finance.csv            │        │ PDFs (hackathon-finreports*/)     │
│ cross_border_payments.csv    │        │        │                          │
│        │                     │        │        ▼ AI-assisted extraction  │
│        ▼ medallion pipeline  │        │ multi_year_figures.json          │
│    (PySpark, offline)        │        │        │                          │
│  bronze → silver → gold      │        │        ▼ merge + fx convert       │
│        │                     │        │ financials_multiyear.csv          │
│        ▼                     │        │        │                          │
│ medallion-pipeline/gold/*.csv│        │        ▼ split by pillar          │
│ (ML training features)       │        │ financials_extracted.csv +        │
│        │                     │        │ 3 pillar-split CSVs               │
│        │                     │        └────────────┬───────────────────┘
│        │                     ┌────────────────────────────────────────┐
│        │                     │  scripts/build_pillar_spend.py          │
│        │                     │  (trailing-12mo snapshot, offline)      │
│        │                     │  → pillar_spend_wide.csv                │
│        │                     └───────────────────┬──────────────────────┘
│        │                                          │
│        │                     ┌────────────────────▼──────────────────────┐
│        │                     │  scripts/build_wallet_model.py             │
│        │                     │  (top-down proxy, reliability tiering,     │
│        │                     │   offline) → wallet_model.csv,             │
│        │                     │   opportunity_ranking.csv                  │
│        │                     └────────────────────┬──────────────────────┘
│        │                                          │
│        ▼                                          │
│ machine_learning/elastic_net.py                    │
│ (ElasticNet, live - notebook Section 10)           │
│ → machine_learning/models/*.pkl                    │
│        │                                          │
│        ▼                                          │
│ machine_learning/predict_wallet.py                 │
│ (share → total wallet → gap, live)                 │
│        │                                          │
│        └──────────────┬───────────────────────────┘
│                        ▼
│         ┌──────────────────────────────────────────┐
│         │        GenAI layer (docs/genai/)           │
│         │  grounded in both sources above, labelled   │
│         │                                             │
│         │  • Client briefing notes (wallet_model.csv) │
│         │  • Anomaly explanations (wallet_model.csv)  │
│         │  • NL query Tier 1 (both sources, every     │
│         │    answer)                                  │
│         │  • NL query Tier 2 - live LLM (both, in one │
│         │    grounding context, source-labelled)      │
│         └───────────────────┬───────────────────────┘
│                              ▼
│              ┌───────────────────────────────┐
│              │   dashboard/app.py (Streamlit)  │
│              │   wallet_engine.ipynb (notebook)│
│              └───────────────────────────────┘
```

---

## 4. Internal data: the medallion pipeline

Three raw Syn Bank datasets are required at the repository root. They are excluded from
version control due to file size and are obtained separately:

| File | Rows | Pillar |
|---|---:|---|
| `transactional_banking.csv` | ~2.8M | Transactional Banking |
| `trade_finance.csv` | ~20K | Trade & Working Capital |
| `cross_border_payments.csv` | ~241K | Foreign / Cross-Border |

These feed two independent downstream paths, both reading the same raw files:

1. **`scripts/build_pillar_spend.py`** — a trailing-12-month (2025-07-01 to 2026-06-30),
   gross-flow (both directions summed) snapshot per client, used by the top-down wallet
   model (§6). One row per client.
2. **`medallion-pipeline/scripts/bronze_silver_transformation.py` →
   `silver_gold_transformation.py`** — a bronze/silver/gold aggregation used to build the
   ML training features (§7). Bronze retains the raw, deduplicated data; Silver applies
   cleaning and standardisation; Gold aggregates to company-and-fiscal-year level:

   | Gold file | Columns | Used for |
   |---|---|---|
   | `trade_finance_gold.csv` | `synbank_trade_receivables`, `synbank_trade_payables` | Trade Finance ML target |
   | `transactional_banking_gold.csv` | `collections`, `supplier_payments` | Transactional Banking ML target |
   | `cross_border_gold.csv` | `cross_border_inflows` | FX ML target |

   These two builds of internal activity are deliberately separate: the top-down model
   requires one current snapshot per client, while the ML model requires a panel spanning
   multiple fiscal years per client (up to 43 company-years across 20 clients) to have
   sufficient training rows. `build_pillar_spend_multiyear.py` is the fiscal-year-aligned
   variant used for the latter.

Fiscal-year alignment is a further requirement: client companies do not share a common
financial calendar (31 December, 30 June, 31 March, and others all occur in the portfolio).
Each company's `fiscal_year_end`, taken from its external filing, is used to construct its
own 12-month window, and internal transactions are assigned to fiscal years using that
company-specific window, so internal and external figures are always compared over the same
period.

---

## 5. External data: the financial-report extraction pipeline

```text
External Financial Report PDFs
              |
              v
extract_financials_multiyear.py  (select the relevant pages per company/year)
              |
              +-----------------------+
              |                       |
              v                       v
   multi_year_figures.json       fx_rates.json
   (AI agent reads the PDFs        (SARB rates, for
    and extracts 12 target          converting non-ZAR
    fields per company-year)        reporters to ZAR)
              |                       |
              +-----------+-----------+
                          |
                          v
                 merge_multiyear.py
                          |
                          v
       hackathon-finreports/_extracted/financials_multiyear.csv
                          |
                          v
                 split_by_category.py
                          |
            +-------------+-------------+
            |             |             |
            v             v             v
          Trade      Transactional      FX
      (working capital)  (revenue/    (foreign-revenue
                          cost of sales)   split)
```

**Step 1** (`extract_financials.py` / `extract_financials_multiyear.py`) narrows full annual
reports to the pages relevant to the 12 target fields (revenue, cost of sales, trade
receivables/payables, inventory, foreign-revenue percentage, FX gains/losses, and others).
An AI agent then reads the narrowed pages and produces structured JSON
(`multi_year_figures.json`) — one record per company-year, with `source_file`, `page_ref`,
and `notes` fields for traceability to the original filing. Fields that cannot be reliably
identified are recorded as `null` rather than estimated.

**Step 2** (`merge_multiyear.py`) combines that JSON with `fx_rates.json` (SARB exchange
rates) to produce `financials_multiyear.csv`, with every value expressed both in the
original reporting currency (`*_m` columns) and converted to ZAR millions (`*_zar_m`
columns), so that companies reporting in USD, EUR, or GBP are placed on the same footing as
ZAR reporters in downstream calculations.

**Step 3** (`split_by_category.py`) splits the consolidated table into the three
pillar-specific external tables required by the wallet model.

`extract_financials_multiyear.py` is the multi-year extension of this pipeline: the team
curated three single-file-per-company folders (`hackathon-finreports-2024/-2025/-2026`) to
give the ML model more than 20 samples to train on — up to three fiscal years per company.

---

## 6. Top-down wallet model (`scripts/build_wallet_model.py`)

The first of the project's two independent wallet-size estimates. It combines:
- `pillar_spend_wide.csv` (internal, Syn Bank captured gross flow)
- `financials_extracted.csv` (external, most-current-FY financials)
- `financials_multiyear_ml.csv` (external, numeric `foreign_revenue_pct` where disclosed)

into a Total Wallet proxy per pillar, derived entirely from each company's own disclosed
financials, with no competitor or market data (the scoped-out bottom-up path is documented
in §14):

| Pillar | Total Wallet proxy | Rationale |
|---|---|---|
| 1 — Transactional Banking | `revenue + cost_of_sales` (revenue only where `cost_of_sales` does not structurally exist — insurers, REITs, telcos, holding companies) | Mirrors the P&L-driven cash-in/cash-out flowing through a transactional relationship |
| 2 — Trade & Working Capital | `inventory + trade_receivables + trade_payables` | The working-capital base that trade-finance instruments could finance |
| 3 — Foreign/Cross-Border | `revenue × foreign_revenue_pct`, computed only for the 4 of 20 companies with a disclosed numeric split (MTN, Naspers, Sanlam, Vodacom); left as "not estimated" for the remaining 16 | The largest documented gap in this pass, flagged explicitly rather than zero-filled |

Per pillar and blended: `share_pct = internal / total_wallet × 100`,
`gap = total_wallet - internal`.

**Reliability tiering** determines how a given Rand figure should be interpreted:

| Tier | Trigger | Interpretation |
|---|---|---|
| `insufficient` | Pillar 1 external wallet missing entirely (only company-level AFS located, not Group — e.g. Bidvest) | Blended total is voided (`NaN`) rather than computed from 2 of 3 pillars |
| `low` | Currency ≠ ZAR (9 of 20 companies) | Consolidated global figures for a multinational — the percentage share is meaningful, but the Rand gap should be read as directional only, and never summed into a portfolio total |
| `moderate` | ZAR reporter (10 of 20 companies with a blended figure) | Financials pertain to the SA-listed entity itself — the Rand gap is literal |

Output: `wallet_model.csv` (one row per client, all three pillars plus blended) and
`opportunity_ranking.csv` (the same data ranked by total Rand gap, with an
actionable/moderate-reliability-only view for the literal-Rand-figure subset).

---

## 7. Machine learning: ElasticNet share-of-wallet models

The second, independent wallet-size estimate — implemented in
`machine_learning/elastic_net.py`. Where the top-down model requires the client's external
total (missing or low-reliability for many clients), this model requires only Syn Bank's own
internal activity — always available in production — making it the only usable quantitative
estimate precisely where the top-down model is weakest.

### Model choice and structure

With only 17-39 rows and 1-2 features per pillar, Ridge regression (L2-only) is forced to
retain every feature at some shrunk weight. ElasticNet's L1 component can eliminate a
feature that contributes only noise, and outperforms Ridge on every target with measurable
signal (Trade Receivables/Payables, Transactional Revenue/Cost).

Trade and Transactional each predict two distinct targets (for example, receivables share
versus payables share) that do not necessarily correlate, so each is fitted as its own
independently-tuned ElasticNet estimator rather than a single multi-output regressor forced
to share coefficients. These are packaged one bundle per pillar (`trade_model.pkl` =
`{receivables_model, payables_model, ...}`; FX has a single target and remains one model).

### Historical share targets

```text
                      SynBank-observed activity
Historical Share = ------------------------------------
                     External company financial activity
```

| Pillar | Internal feature(s) | External measure | Historical share |
|---|---|---|---|
| Trade receivables | `synbank_trade_receivables` (export LCs/collections) | `trade_receivables` | `synbank_trade_receivables / trade_receivables` |
| Trade payables | `synbank_trade_payables` (import LCs) | `trade_payables` | `synbank_trade_payables / trade_payables` |
| Transactional revenue | `synbank_collections` | `revenue` | `synbank_collections / revenue` |
| Transactional cost | `synbank_supplier_payments` | `cost_of_sales` | `synbank_supplier_payments / cost_of_sales` |
| FX foreign revenue | `cross_border_inflows` | `revenue × foreign_revenue_pct` | `cross_border_inflows / foreign_revenue` |

These internal/external pairs are not assumed to be identical measures (for example,
SynBank collections and accounting revenue can differ in timing) — the internal figure is
treated as an observable proxy for, not a restatement of, the corresponding external
measure.

### Validation and hyperparameter search

With only 17-43 company-years available, a single train/test split would produce an
unreliable estimate of generalisation. **Leave-One-Group-Out cross-validation**
(`LeaveOneGroupOut`, grouped by `entity_name`) is used instead: each company is held out
completely once, with the scaler and model fitted only on the remaining companies, so every
prediction is strictly out-of-sample. This directly evaluates the production use case — the
model's ability to predict share of wallet for a client it has not seen during training.

Two hyperparameters are searched independently per target (25 combinations: 5 values of
`alpha` × 5 values of `l1_ratio`), with each target selecting its own best combination by
cross-validated R²:

| Target | R² (out-of-fold) | Note |
|---|---:|---|
| Trade receivables | ~0.34 | Measurable signal |
| Trade payables | ~0.24 | Measurable signal |
| Transactional revenue | ~0.39 | Measurable signal |
| Transactional cost | ~0.27 | Measurable signal |
| FX foreign revenue | Negative across all 25 combinations | A data-coverage limitation (only 17 of 43 company-years have a usable label), not a modelling deficiency — documented rather than tuned away |

Final models are refit on all available data (not held out) for deployment, and persisted
via `joblib`:

```text
machine_learning/models/
  trade_model.pkl           trade_scaler.pkl
  transactional_model.pkl   transactional_scaler.pkl
  fx_model.pkl               fx_scaler.pkl
```

`wallet_engine.ipynb` Section 10 re-runs this training script in full (`import
elastic_net`; approximately 15 seconds), with `joblib.dump` neutralised for the duration of
the notebook cell so that running the notebook cannot overwrite the committed `.pkl` files.
Each execution of the notebook therefore demonstrates that the training pipeline functions
end to end, rather than confirming only that a stored artifact loads correctly.

---

## 8. ML inference: total wallet, gap, and narrative synthesis

`machine_learning/elastic_net.py` predicts share only. Two additional modules extend that
output into the full picture without retraining:

**`machine_learning/wallet_math.py`** — `derive_wallet_and_gap(internal_value,
predicted_share)`. Since every target above is defined as `share = internal / external`, and
`internal` is already known for any client, `total_wallet = internal / share` and
`gap = total_wallet - internal` follow directly — the same relationship the top-down model
uses. ElasticNet is not constrained to positive outputs, so a predicted share can be zero or
negative for a low-signal target; such cases are reported as **not computable** rather than
as an inverted or fabricated figure.

**`machine_learning/predict_wallet.py`** — `MLWalletPredictor`, an inference API that loads
the trained `.pkl` bundles without retraining. It is kept in a separate module from
`elastic_net.py` specifically so that importing it for inference never re-triggers training
or overwrites the committed models:

- `predict_for_client(entity_name)` returns `{pillar_name: [{target, internal_zar,
  predicted_share_pct, predicted_total_wallet_zar_m, predicted_gap_zar_m}, ...]}`
- `describe(entity_name)` returns a narrative synthesis of the above (the target with the
  largest computable gap leads, remaining targets are summarised, non-computable targets
  are stated explicitly). This is the point at which the ML model's output becomes
  GenAI-facing: the predictions are the input, and this sentence is the synthesis a
  relationship banker reads. No LLM call is required — the figures are already known, and
  this is templated synthesis, using the same approach as Tier 1 NL querying (§10) — which
  keeps it free and always available.

This output is displayed in the dashboard's "ML cross-check" card and is included in every
Tier 1 client answer (§9).

---

## 9. GenAI layer: grounded in both models

Full design rationale is documented in `docs/genai/README.md`. The table below summarises
how each of the three required GenAI use cases (`PLAN.md` §1.4: client briefing notes, NL
querying, anomaly explanations) is grounded, with particular attention to how the ML model's
output is incorporated:

| Use case | Grounded in | Executes live? |
|---|---|---|
| **Client briefing notes** (`client_briefing_notes.md`) | Top-down `wallet_model.csv`, one prompt application per client | Text is static; the grounding check (`scripts/verify_briefing_notes.py`) executes live and checks both numeric claims and the stated reliability-tier wording |
| **Anomaly explanations** (`anomaly_explanations.md`) | Top-down `wallet_model.csv`, via `scripts/detect_anomalies.py` (deterministic code, no LLM involvement, so it cannot miss or hallucinate an anomaly type) | Detection executes live; explanation text is static |
| **NL query, Tier 1** (`scripts/nl_query_assistant.py`) | Both models. `QueryAssistant` accepts an optional `ml_predictor`; every per-client answer appends `MLWalletPredictor.describe()` alongside the top-down figures, and an explicit query such as "what does the ML model predict for X" routes directly to the ML-only narrative | Fully live, zero-cost, deterministic |
| **NL query, Tier 2** (`scripts/nl_query_llm.py`) | Both models, combined in a single grounding context sent to Claude: `wallet_model.csv` / `opportunity_ranking.csv` / `anomalies_detected.csv` (top-down) and `ml_predictions.csv` (all 20 clients' ElasticNet predictions, built fresh from `MLWalletPredictor` on each call). The system prompt requires every cited figure to be labelled with its source, and any material disagreement between the two models to be stated explicitly | Live when `ANTHROPIC_API_KEY` is configured; otherwise falls back to Tier 1 (which itself includes the ML cross-check) — see §10 |

**Grounding verification** provides an auditable answer to whether generated text cites
figures present in the source data:

```sh
python scripts/verify_briefing_notes.py       # 20/20 clients, every % and Rand figure, plus reliability-tier wording
python scripts/verify_nl_query_examples.py    # 10 Tier-2 worked examples, portfolio-wide numeric match
```

Each script writes a full audit trail CSV to `hackathon-finreports/_extracted/`.

---

## 10. Tier 1 / Tier 2 querying design

`scripts/nl_query_assistant.py` (Tier 1) is a rule-based intent classifier with templated
synthesis — not an LLM call. It requires no API key, incurs no cost, and is fully
deterministic, which makes it safe to demonstrate live with no risk of hallucination or
service outage. It handles lookups, comparisons, rankings, reliability checks, and ML
cross-check questions, covering an estimated 80% of the questions a relationship banker
would ask in practice.

For open-ended questions requiring judgment across multiple rows (for example, "which three
clients should sales prioritise this quarter and why"), Tier 1 declines explicitly and
`scripts/nl_query_llm.py` (Tier 2) takes over, provided `ANTHROPIC_API_KEY` is configured —
issuing a `claude-opus-5` call grounded in both models (§9). If no key is configured, or the
live call fails for any reason (invalid key, network error, rate limit), the dashboard falls
back to the Tier 1 answer with a plain-language note, and logs the underlying exception to
the console rather than the chat interface, so the demonstration does not fail on a missing
or invalid key.

Static worked examples for Tier 2, used when no API key is available, are provided in
`hackathon-finreports/_extracted/nl_query_examples.md`, generated once under the same prompt
contract and verified by the same grounding process as the live path.

---

## 11. Dashboard (`dashboard/app.py`)

A single-page Streamlit application. Sections, top to bottom:

1. **Header** — team and project identification.
2. **Portfolio KPIs** — clients analysed, average blended share (actionable tier), combined
   gap, anomalies flagged, reliability-tier mix.
3. **Top opportunities** (bar chart, top-down) and **reliability tier mix** (donut chart).
4. **Anomalies by type** (bar chart).
5. **Client drill-down** — for any of the 20 clients:
   - Top-down summary, reliability badge, and pillar chart (§6 output)
   - **AI briefing note** — the client's section from `client_briefing_notes.md`, linked to
     the grounding-verification audit trail
   - **ML cross-check** — `MLWalletPredictor.describe()`'s narrative, followed by the full
     per-target table (§8 output)
6. **Ask a Question** — a modal dialog providing Tier 1/Tier 2 NL querying (§10), example
   questions, and free-text input.

`@st.cache_resource` is used for the ElasticNet predictor and for `QueryAssistant`, which is
constructed with the already-cached predictor passed in, so the `.pkl` bundles are loaded
once rather than once per component.

---

## 12. File reference

| Path | Produces | Reads | Execution |
|---|---|---|---|
| `medallion-pipeline/scripts/bronze_silver_transformation.py` | `medallion-pipeline/silver/*.csv` | 3 raw internal CSVs (repo root) | Offline, once |
| `medallion-pipeline/scripts/silver_gold_transformation.py` | `medallion-pipeline/gold/*.csv` | silver CSVs | Offline, once |
| `scripts/extract_financials.py` | `file_selection_audit.csv`, extracted page text | AFS PDFs | Offline, once |
| `scripts/extract_financials_multiyear.py` | multi-year extracted page text | 3-year PDF folders | Offline, once |
| `scripts/merge_extraction.py` | `financials_extracted.csv` | audit CSV + agent JSON | Offline, once |
| `scripts/merge_multiyear.py` | `financials_multiyear.csv` | audit + JSON + fx_rates.json | Offline, once |
| `scripts/split_by_category.py` | 3 pillar-split external CSVs | `financials_extracted.csv` | Offline, once |
| `scripts/build_pillar_spend.py` | `pillar_spend_wide.csv`, `pillar_spend_long.csv` | raw `transactional_banking.csv` etc. | Offline (2.8M rows) |
| `scripts/build_pillar_spend_multiyear.py` | multi-year pillar spend | same, fiscal-year-aligned | Offline |
| `scripts/build_wallet_model.py` | `wallet_model.csv`, `opportunity_ranking.csv` | pillar spend + external financials | Offline; notebook reads output |
| `scripts/build_wallet_model_multiyear.py` | ML training table (multi-year) | multi-year pillar spend + financials | Offline |
| `scripts/detect_anomalies.py` | `anomalies_detected.csv` | `wallet_model.csv` | Live — Section 11a, dashboard |
| `scripts/verify_briefing_notes.py` | `briefing_notes_verification.csv` | `client_briefing_notes.md`, `wallet_model.csv` | Live — Section 9, dashboard |
| `scripts/verify_nl_query_examples.py` | `nl_query_examples_verification.csv` | `nl_query_examples.md`, `wallet_model.csv`, `opportunity_ranking.csv` | Live — run manually to audit |
| `scripts/nl_query_assistant.py` | — | `wallet_model.csv`, `opportunity_ranking.csv`, `anomalies_detected.csv`, `MLWalletPredictor` | Live — Section 11b, dashboard |
| `scripts/nl_query_llm.py` | — | same, plus `MLWalletPredictor` (builds `ml_predictions.csv` in memory) | Live (requires `ANTHROPIC_API_KEY`) — dashboard Tier 2 |
| `machine_learning/elastic_net.py` | `machine_learning/models/*.pkl` | medallion gold CSVs + `financials_multiyear.csv` | Live — notebook Section 10 |
| `machine_learning/wallet_math.py` | — (pure function) | — | Imported by `elastic_net.py`, `predict_wallet.py` |
| `machine_learning/predict_wallet.py` | — | trained `.pkl` bundles + gold CSVs | Live — notebook, dashboard, Tier 1, Tier 2 |
| `dashboard/app.py` | — | all outputs above | Live — `streamlit run dashboard/app.py` |
| `wallet_engine.ipynb` | — | all outputs above, and re-runs the live ML/GenAI stages | Live — run all cells |
| `docs/genai/*.md` | — (prompt templates and design documentation) | — | Reference material |

---

## 13. Running the project

```sh
pip install -r requirements.txt

# Interactive dashboard
streamlit run dashboard/app.py

# Full notebook (Jupyter / VS Code / JupyterLab)
jupyter lab wallet_engine.ipynb
# Run All. The 3 raw internal CSVs are required at the repository root for
# Section 2's ingestion cell only; every section from Section 5 onward reads
# already-committed CSVs and does not require them.

# Optional: live Tier 2 NL querying (falls back to static examples otherwise)
export ANTHROPIC_API_KEY=sk-ant-...        # macOS/Linux
$env:ANTHROPIC_API_KEY = "sk-ant-..."      # PowerShell

# Standalone checks (no dashboard or notebook required)
python scripts/nl_query_assistant.py       # Tier 1 demonstration + edge-case handling
python scripts/nl_query_llm.py             # Tier 2 demonstration (requires the API key)
python machine_learning/predict_wallet.py  # ML predictions for 3 sample clients
python scripts/verify_briefing_notes.py    # grounding audit
python scripts/verify_nl_query_examples.py # grounding audit
```

Re-running the offline data-preparation scripts (medallion pipeline, extraction pipeline,
`build_wallet_model.py`) is only necessary if the underlying raw data changes. Their outputs
are committed to the repository and are not regenerated by running the dashboard or notebook.

---

## 14. Documented limitations

- **The top-down wallet model is financials-only.** `DATA_SOURCES.md` documents a
  researched, scoped-out bottom-up approach (SARB BA900 per-bank deposit data, JSE SENS
  disclosures) that would calibrate the top-down proxy against system-wide market share.
  This was excluded from the current submission due to the hackathon's time constraints.
  Full detail: `docs/reports/2026-08-13-wallet-model-summary.md`.
- **Foreign/Cross-Border wallet is estimated for 4 of 20 clients only** (MTN, Naspers,
  Sanlam, Vodacom). The remaining 16 clients have measurable internal cross-border activity
  with no disclosed external benchmark for comparison. This is flagged as
  `wallet_unavailable` rather than zero-filled, and represents the largest data gap in the
  top-down model by row count.
- **The FX ElasticNet target shows no measurable signal** (R² negative across all 25
  hyperparameter combinations tested), attributable to a data-coverage limitation (17 of 43
  company-years carry a usable label) rather than a modelling deficiency, and is documented
  as such rather than adjusted to appear otherwise.
- **9 of 20 clients are foreign-currency reporters.** Their top-down Rand gaps are
  directional only (consolidated global figures) and are never summed into a portfolio
  total; the dashboard's KPI row uses the actionable (ZAR-reporter) subset specifically to
  avoid overstating the combined figure.
