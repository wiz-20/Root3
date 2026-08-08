# Financial Report Extraction Pipeline — Design

**Date:** 2026-08-08
**Status:** Approved
**Context:** `hackathon-finreports/` contains 44 annual report PDFs across 20 company folders (one per entity in `PLAN.md`'s confirmed 20-entity scope). Manually pasting each PDF into a chat one at a time (the workflow used so far) doesn't scale to 20 companies and wastes context on irrelevant pages. This defines a script-assisted pipeline to get from raw PDFs to the structured external-financials table that `2026-08-08-pillar-spend-split-design.md`'s "External/company financial data to look for" column needs.

## Problem

Each company folder has 1-4 PDFs (different fiscal years, AFS vs. Integrated Report vs. circulars, sizes from 0.4MB to 72.6MB). We need 12 specific fields per company extracted reliably, with page citations, without either (a) hand-scanning hundreds of pages per report or (b) dumping full PDFs into a chat context window.

## Pipeline

```
44 PDFs (20 folders)
   │
   ▼
Step 1 — Select AFS file per company (script)
   ▼
Step 2 — Extract + narrow to relevant pages (script)
   ▼
Step 3 — Structured field extraction (agent reads narrowed excerpts)
   ▼
financials_extracted.csv (1 row per company)
```

### Step 1 — File selection

For each of the 20 folders, pick exactly one PDF:

1. Filter to filenames containing `afs` or `annual financial statement(s)` (case-insensitive).
2. If one or more match, pick the one with the latest 4-digit year found in the filename.
3. If none match, fall back to the newest-dated "annual report" / "integrated report" PDF in the folder, and flag the company as `fallback_no_afs_label`.
4. Additional flags raised regardless of the above: filename suggests a different entity than the folder name (e.g. "AGA" inside `angloamerican/`), or filename suggests Company-level (not Group/consolidated) financials.

Output: `hackathon-finreports/_extracted/file_selection_audit.csv` — columns `folder, chosen_file, method, year_detected, flag`.

Known flags to expect at first run (from manual file listing): Bidvest FY2025 AFS available is Company-level only (Group FY2025 AFS absent from folder); Sanlam's latest AFS-labeled file is 2023; `angloamerican/` contains a file named referencing "AGA" (AngloGold Ashanti's ticker). These are **not blockers** — extraction proceeds with best-available file, flags are surfaced in the audit CSV for manual follow-up.

### Step 2 — Extract + narrow

Using PyMuPDF (`fitz`), for the chosen PDF per company:

1. Extract text per page.
2. Match each page's text against keyword groups, one per target field cluster:
   - Revenue / cost of sales / opex: `revenue`, `cost of sales`, `operating expenses`
   - Receivables / payables: `trade receivables`, `trade payables`
   - Inventory / working capital: `inventor`, `working capital`
   - Imports/exports / trade facilities: `import`, `export`, `letter of credit`, `guarantee`, `trade facilit`
   - Geographic / foreign revenue: `geographical`, `segment information`, `revenue by`, `foreign revenue`
   - FX gains/losses & exposure: `foreign exchange`, `exchange difference`, `currency risk`, `financial risk management`
3. Keep any page that matches, plus one page before and after (notes commonly span page breaks).
4. Write a per-company excerpt file with page numbers labeled, so citations stay traceable.

Output: `hackathon-finreports/_extracted/<folder>_excerpt.txt` per company. This turns e.g. MTN's 72.6MB report into a few dozen relevant pages instead of the full document.

### Step 3 — Structured extraction

The agent (not a separate LLM API call — no key required) reads each company's excerpt file and fills in the output row. Work is batched across companies (using parallel subagents where independent) rather than done as 20 sequential manual reads, since each company's extraction has no dependency on any other's.

## Output schema — `financials_extracted.csv`

One row per company:

| Column | Notes |
|---|---|
| `entity_name` | matches `PLAN.md` entity list |
| `source_file` | chosen PDF filename |
| `fiscal_year` | as detected/confirmed from the report |
| `revenue`, `cost_of_sales`, `operating_expenses` | Pillar 1 |
| `trade_receivables`, `trade_payables` | Pillar 1 & 2 |
| `inventory`, `imports_exports`, `working_capital_notes` | Pillar 2 |
| `foreign_revenue_pct`, `geographic_revenue_split` | Pillar 3 |
| `fx_gains_losses`, `fx_exposure_notes` | Pillar 3 |
| `page_ref` | page citation(s) per field, semicolon-separated |
| `notes` | extraction caveats (e.g. "not disclosed", "estimated from segment note") |

### Step 4 — Currency normalization to ZAR

11 of the 20 companies report in USD, EUR or GBP rather than ZAR (Anglo American, AngloGold Ashanti, BHP, Glencore, Gold Fields, Naspers, Prosus report USD; NEPI Rockcastle reports EUR; Shaftesbury Capital reports GBP). Since the wallet model's internal Syn Bank data (`pillar_spend_wide`) is entirely in ZAR, the five core balance-sheet/income-statement numbers per company (`revenue`, `cost_of_sales`, `trade_receivables`, `trade_payables`, `inventory`) are converted to ZAR for direct comparability.

**Source data:** `hackathon-finreports/_extracted/primary_figures.json` — one clean numeric value per field per company (millions of original currency), hand-verified against the free-text `extracted_fields.json` values from Step 3. Left `null` where no single officially-disclosed line exists (e.g. no "cost of sales" for insurers/telcos/REITs) rather than approximating from unrelated cost components.

**FX rates:** `hackathon-finreports/_extracted/fx_rates_zar.json` — pulled live from the SARB public API (`CurrentMarketRates` endpoint, no auth required — the same source flagged in `DATA_SOURCES.md`), as of 2026-08-07: USD/ZAR 16.3213, GBP/ZAR 21.9424, EUR/ZAR 18.8014.

**Limitation (for methodology appendix):** a single current spot rate is applied uniformly to every company regardless of its specific fiscal year-end, rather than each company's historical average rate for its own reporting period. This is a stated simplification for time constraints, not a precision claim - flag before using these converted figures for anything beyond relative sizing/ranking.

Output columns added to `financials_extracted.csv`: `currency`, `fx_rate_to_zar`, `fx_rate_date`, and `{field}_m` / `{field}_zar_m` pairs for the five core numeric fields.

## Out of scope (for this step)

- Fully automated LLM-API extraction (no key available/needed — agent does the reading).
- Resolving the Bidvest/Sanlam/Anglo American file flags — surfaced for manual follow-up, not resolved automatically.
- Feeding `financials_extracted.csv` into the wallet model itself — that's the external wallet estimation step in `PLAN.md` Section 5, which consumes this output but is built separately.

## Assumptions & Limitations (for methodology appendix)

- Keyword-based page narrowing may miss disclosures that use non-standard note terminology; the excerpt approach trades recall risk for tractability across 20 large PDFs.
- One AFS chosen per company (not all historical filings) — trend analysis across years is not in scope here.
- Extraction is done by an LLM (the agent) reading real page text, not OCR — reports that are scanned images rather than text-based PDFs would need a different approach (not observed in this file set on initial inspection).
