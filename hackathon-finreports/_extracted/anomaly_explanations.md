# Anomaly Explanations — GenAI-Generated

**Generated using:** the prompt in `docs/genai/anomaly_explanation_prompt.md`, applied only to the code-generated `anomalies_detected.csv` (never to raw financials directly — see that doc for why this two-stage design matters for grounding).
**Detection engine:** `scripts/detect_anomalies.py` — 5 fixed, documented rules checked across all 60 client×pillar cells (20 clients × 3 pillars) plus the blended total.
**Result:** 27 anomalies detected across 18/20 clients, grouped below into 6 distinct patterns.

Every pattern below is classified as one of:
- 🟢 **Finding** — a genuine signal a banker should act on
- 🟡 **Limitation** — a proxy/data artifact; the direction may be informative but the magnitude should not be read literally
- 🔵 **Research gap** — real activity exists but no external benchmark could be computed yet

---

## 1. Proxy breakdown (share % > 100) — 🟡 Limitation
*3 instances: OUTsurance (Pillar 2), The Bidvest Group (Pillar 2), Sanlam (Pillar 3)*

This happens when internal Syn Bank activity in a pillar **exceeds** the top-down external wallet proxy for that pillar, producing a mathematically valid but practically meaningless share above 100%. Mechanically, it means the proxy's denominator (inventory + trade receivables + trade payables for Pillar 2; revenue × foreign-revenue% for Pillar 3) doesn't fit that company's actual balance-sheet structure:

- **OUTsurance, Pillar 2:** share 491.3% (R78.6m internal vs. an R16.0m wallet) — an insurer holds almost no inventory or trade receivables/payables, so the generic working-capital proxy collapses to an almost-zero denominator even though real treasury/float activity exists.
- **The Bidvest Group, Pillar 2:** share 666.1% (R1,464.0m internal vs. an R219.8m wallet) — the wallet here is built from *company-level*, not *Group-level*, working capital (the only AFS found), so it's structurally too small for a group of Bidvest's actual scale.
- **Sanlam, Pillar 3:** share 133.5% (R2,664.9m internal vs. R1,996.3m wallet) — an insurer's genuine treasury/FX turnover runs larger than what a simple revenue×foreign-% proxy captures.

**Action:** exclude these three share percentages from any headline Rand-gap or share number. The underlying internal figures are real evidence of activity — they just need a better-fitted external benchmark than this pass's generic proxy provides (a sector-specific proxy, e.g. gross written premium for insurers, would be the natural fix with more time).

---

## 2. External wallet unavailable — 🔵 Research gap
*18 instances across 16 clients — by far the largest category*

The most common anomaly in the whole model: real internal Syn Bank activity exists in a pillar, but no external wallet estimate could be computed because the specific disclosure needed wasn't present in that company's public annual report. This is **not** the same as "no opportunity" — it means "opportunity size currently unknowable from public financials alone," and the model deliberately leaves it blank rather than guessing.

- **Pillar 3 (Foreign/Cross-Border) — 16 of 20 companies**, including large, obviously multinational-facing names like Pepkor Holdings (R6,655.5m internal activity), Bid Corporation (R6,165.6m), and Prosus (R1,973.3m). Only MTN, Naspers, Sanlam, and Vodacom disclosed a usable numeric foreign-revenue split.
- **The Bidvest Group, Pillar 1 (Transactional)** — R4,730.6m of real internal transactional activity, but no Group-level revenue was ever located in the source filing to build a wallet proxy against.
- **MTN Group, Pillar 2 (Trade & Working Capital)** — R1,443.2m of internal activity with no wallet estimate this fiscal year, a data gap in the source financials rather than a real zero.

**Action:** this is the single biggest limitation of a top-down, financials-only approach, and the strongest argument for the bottom-up external evidence (SARB BA900 filings, JSE SENS segment disclosures) that was explicitly scoped out of this pass for time (see `docs/reports/2026-08-13-wallet-model-summary.md`). If the project continues past the hackathon, closing this gap for the 16 cross-border cases should be priority #1 — it's where the most real, uncounted opportunity is likely hiding.

---

## 3. Insufficient reliability — 🟡 Limitation
*1 instance: The Bidvest Group, blended total*

Bidvest's blended (all-pillar) total was deliberately **not computed** at all, rather than being calculated from 2 of the 3 pillars (with Pillar 1, its largest, entirely missing). A partial total here would look precise while being systematically understated — the model treats "don't compute it" as more honest than "compute a plausible-looking wrong number."

**Action:** Bidvest cannot be reliably assessed at all on current data. Before any coverage conversation, source Bidvest's full Group AFS (the entity-level filing used here understates the true relationship) — flagged explicitly in Bidvest's dedicated briefing note.

---

## 4. Scale mismatch — the naive-model trap — 🟡 Limitation (most severe)
*3 instances: Glencore, BHP Group, Anglo American — all in the top quartile of Rand gaps portfolio-wide*

The three most extreme cases of a structural problem: using a global commodity/mining group's **consolidated worldwide revenue** as a proxy for an SA-specific banking wallet. All three sit far above the R430.8bn threshold that separates the top quartile of gaps from the rest of the (already low-reliability) foreign-currency tier:

- **Glencore:** R9,501.0bn gap — the most extreme single number in the whole dataset.
- **BHP Group:** R1,108.5bn gap.
- **Anglo American:** R502.7bn gap.

**Action:** these three Rand figures must never be summed into a portfolio-level total or shown at face value on a dashboard or in a deck — doing so is the exact naive-model mistake this whole reliability-tiering system exists to catch. They're already excluded from the "actionable" tier in `opportunity_ranking.csv`. Recommend a dedicated caveat slide calling this out explicitly — the fact that the model catches and flags its own biggest failure mode is itself a legitimate "business insight" talking point for judges, not just a limitation to hide.

---

## 5. Statistical outlier — high — 🟢 Finding
*1 instance: Pepkor Holdings, blended share*

Pepkor's 20.9% blended share is a genuine statistical outlier (z = 2.31) against its own peer group of 10 moderate-reliability ZAR reporters (peer mean 5.8%, std 6.5%) — more than 1.5x the next-best domestic result (Sanlam, 13.8%).

**Action:** use Pepkor internally as a case study for what a mature, well-penetrated relationship looks like. Even at 20.9% share there's still an R160.5bn gap (see Pepkor's briefing note) — and its Trade & Working Capital share (3.1%) is far below its own transactional share, making that the specific pillar to deepen next.

---

## 6. Statistical outlier — low — 🟡 Limitation with a real directional signal
*1 instance: Glencore, blended share*

Even measured only against its own low-reliability (foreign-currency) peer group of 9 companies — where everyone already looks artificially under-penetrated — Glencore's 0.1% blended share is *still* a statistical outlier on the low side (z = -2.07, peer mean 1.5%). Per the scale-mismatch caveat above, the Rand magnitude is not usable, but the direction (unusually low even among already-low peers) is a real signal.

**Action:** this is closer to "effectively no relationship" than "small relationship," even accounting for the consolidation distortion — worth a specific research note on whether Glencore's South African trading desk has any distinct banking relationship at all, separate from the meaningless group-level comparison.

---

*Detection code: `scripts/detect_anomalies.py`. Full structured output: `hackathon-finreports/_extracted/anomalies_detected.csv`. Prompt and design rationale: `docs/genai/anomaly_explanation_prompt.md`.*
