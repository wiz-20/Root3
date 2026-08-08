# Syn Bank Share of Wallet Intelligence Engine — Team Plan

**Hackathon:** 2026 Data School Hackathon (Stellenbosch), sponsored by Standard Bank
**Challenge:** Syn Bank Share of Wallet Intelligence Challenge
**Submission deadline:** Sunday 16 August, 23:59

---

## 1. The Problem, Restated

Syn Bank is not the sole banking partner for any of its corporate clients. Our job is to build an engine that:

1. **Estimates Total Wallet** — the full banking spend of a client across ALL banks, not just Syn Bank.
2. **Quantifies Syn Bank's Share** — what % of that total wallet Syn Bank currently captures, using internal data.
3. **Identifies the Gap** — Total Wallet − Syn Bank Share, ranked by revenue opportunity, to prioritize which clients a coverage banker should chase next.
4. **Layers in Generative AI** — in a way that's genuinely decision-useful (client briefing notes, NL querying, anomaly explanations), not cosmetic.

The hard part is the denominator (Total Wallet) — we only have Syn Bank's internal data, so external evidence has to fill that gap.

---

## 2. Wallet Estimation Framework

### Numerator — Syn Bank Share (from internal data)
Build a normalized "Syn Bank revenue/volume proxy" per client by combining:
- **Transactional data** — domestic payments, collections, day-to-day volume
- **SWIFT data** — cross-border payment share (proxy for trade/FX-heavy clients)
- **Trade finance data** — LCs, guarantees, export collections (tenor, value, direction)

### Denominator — Total Wallet (external estimation, two complementary approaches)

**Top-down (financials-based proxy):**
Use each client's public financials (revenue, cost of sales, headcount, capex) to estimate banking intensity via a sector-adjusted multiplier (e.g. mining ≠ retail in trade finance need).

**Bottom-up (direct evidence of competitor banks):**
- **JSE SENS announcements** — bond issuances, DMTN programmes, syndicated loan facilities often name the arranging/lead banks
- **Annual report borrowing notes** — frequently list facility providers and undrawn amounts by bank
- **CIPC records** — registered security/notarial bonds tied to specific lenders

Combining both gives a defensible, citable wallet estimate — important for the 30%-weighted Analytical Rigor criterion.

### Signal-linking guidance (from the brief)
- Inventory balances + cost of sales → trade finance needs
- Foreign revenue → FX hedging demand
- Debt schedules → lending/capital markets opportunities

---

## 3. Data Inventory

| Dataset | Rows | Coverage | Key use |
|---|---|---|---|
| `transactional_banking.csv` | ~2.8M | 20 entities, Jul 2023–Jun 2026 | Domestic payments, collections, payroll, intercompany, tax (EFT/SWIFT/RTC/Debit Order/Internal Transfer) |
| `cross_border_payments.csv` | ~241K | Same 20 entities | Intercompany, trade, other corridor types |
| `trade_finance.csv` | ~20K | Same 20 entities | LCs, export collections, guarantees |

**⚠️ Known discrepancy:** The brief describes a 50-client portfolio, but the actual data covers **20 entities**. Confirmed entity list:

Anglo American, AngloGold Ashanti, Aspen Pharmacare, BHP Group, Bid Corporation, Clicks Group, Glencore, Gold Fields, MTN Group, NEPI Rockcastle, Naspers, OUTsurance Group, Pepkor Holdings, Prosus, Sanlam, Shaftesbury Capital plc, Shoprite Holdings, The Bidvest Group, Valterra Platinum, Vodacom Group.

**Decision needed:** treat 20 as the real scope and document it as a limitation/assumption, rather than trying to force-fit 50.

---

## 4. Team Split

| Person | Owns | First deliverable |
|---|---|---|
| **Internal data** | Clean + join the 3 Syn Bank datasets per client into a normalized revenue/volume proxy | Per-client summary table (the numerator) |
| **External research** | Pull financials, SENS announcements, borrowing notes, CIPC records for the 20 entities | Per-client external evidence table (facility sizes, competitor banks named, sector) |
| **Modeling** | Design the wallet-sizing formula (top-down multiplier + bottom-up evidence), share %, gap ranking | Wallet estimate + Syn Bank share % + prioritized gap list |
| **GenAI + dashboard** | GenAI use case (briefing notes, NL query, anomaly explanation) + dashboard build | Dashboard skeleton + first draft prompt for client briefing notes |

**Important:** the split above is for *cleaning/prep and specialization*, not final isolation — the wallet/share calculation ultimately needs all three internal datasets joined per client, and the modeling owner needs both the internal and external outputs to do the calc.

---

## 5. Notebook Structure (suggested)

1. **Setup** — imports, config, requirements
2. **Ingestion** — load 3 Syn Bank datasets + external data
3. **Cleaning & profiling** — nulls, types, per-entity aggregates, date range checks
4. **Internal wallet share build** — normalized Syn Bank revenue/volume proxy per client
5. **External wallet estimation** — top-down multiplier + bottom-up competitor evidence
6. **Wallet model** — combine into Total Wallet, Syn Bank Share %, Gap
7. **Opportunity ranking** — prioritized client list with rationale
8. **GenAI layer** — briefing note generation, prompt log
9. **Visualisation / dashboard export**
10. **Methodology appendix** — assumptions, limitations, citations

---

## 6. Deliverables Checklist

- [ ] Reproducible Python/R notebook (ingestion → transformation → modelling → visualisation)
- [ ] Documented methodology (assumptions, wallet sizing logic, limitations)
- [ ] Evidence of GenAI integration (prompts, workflow, code)
- [ ] Requirements file / reproducible environment
- [ ] Executive dashboard: portfolio summary, client drill-downs, opportunity heatmap, AI briefing notes for ≥3 clients
- [ ] Judging presentation (problem, methodology, AI component, results, next steps)
- [ ] 1-page PDF solution summary (submission requirement)
- [ ] PowerPoint presentation (submission requirement)
- [ ] Code link (GitHub or shared Google Drive)
- [ ] Team name + members on all submitted documents

---

## 7. Evaluation Criteria (for prioritizing effort)

| Criterion | Weight |
|---|---|
| Business Insight & Commercial Acumen | 40% |
| Analytical Rigor | 30% |
| Gen AI Application | 20% |
| Presentation & Storytelling | 10% |

**Takeaway:** actionable, banker-usable recommendations matter more than modeling sophistication. A simpler model with sharp, specific "what to do next" output beats a fancy model with generic output.

---

## 8. Rules Reminder

- All Syn Bank data is synthetic and confidential to the hackathon — do not attempt to link to real banks/clients.
- Cite all external sources used.
- No sharing code, methodology, or findings with other teams during the build phase.
- Only registered team members may contribute to the submission.

---

## 9. Immediate Next Actions

1. Confirm the 20-entity scope as final (not a data export issue).
2. Set up notebook skeleton per structure above.
3. Pick 3 pilot clients everyone uses as running examples while building.
4. Start the methodology doc now — log assumptions as you go, don't leave it for the end.
