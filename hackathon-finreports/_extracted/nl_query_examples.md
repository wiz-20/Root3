# NL Query Examples — Tier 2 (Open-Ended Synthesis)

**Generated using:** the prompt in `docs/genai/nl_query_prompt.md`, applied against `wallet_model.csv`, `opportunity_ranking.csv`, and `anomalies_detected.csv`.
**For Tier 1 (lookups/rankings/comparisons)**, see `scripts/nl_query_assistant.py` — run it directly for a live, deterministic demo.

---

### Q: If you had to pick 3 clients for the sales team to prioritize this quarter, which would you pick, and why?

**A:** Shoprite Holdings, Bid Corporation, and MTN Group — the three largest gaps in the actionable (moderate-reliability, ZAR-reporter) tier, at R490.2bn, R473.5bn, and R388.2bn respectively, all with literal, trustworthy Rand figures. Each has a clear, specific next step: Shoprite and Bid Corp are both under-3% transactional share despite retail-scale payment volumes; MTN uniquely also has a validated cross-border pillar (3.5% share, disclosed 79.2% foreign revenue) making it a two-pillar pitch. Honorable mention: Valterra Platinum isn't top-3 by Rand size, but its near-zero share (0.0–0.2%) as a *domestic* ZAR reporter — not a multinational consolidation artifact — is the single sharpest relationship-gap finding in the dataset and worth flagging to the team even outside a pure size ranking.

---

### Q: Should Syn Bank be worried about losing the Sanlam relationship to a competitor?

**A:** No — the data suggests the opposite risk. Sanlam already has the best-penetrated transactional relationship in the portfolio at 18.7% share (vs. 0.1–5% for most others), so this isn't a client with weak ties to defend. The real story is under-monetization elsewhere: Trade & Working Capital share is just 0.3% (R55.4bn gap) despite the strong transactional foothold, and the 133.5% Foreign/Cross-Border "share" is a proxy artifact (an insurer's treasury/FX turnover exceeding a simple revenue-based benchmark), not a real number to act on. The actionable question isn't defense, it's expansion — cross-selling trade finance into an already-trusted relationship.

---

### Q: How confident should we be in the numbers for the foreign-currency reporting companies overall?

**A:** Directionally confident, numerically not. All 9 foreign-currency reporters (Anglo American, AngloGold Ashanti, BHP, Glencore, Gold Fields, Naspers, Prosus, NEPI Rockcastle, Shaftesbury) show consistently low blended share (0.1%–2.3%), and that pattern — low SA-specific penetration relative to enormous consolidated group revenue — is a real, trustworthy signal. But the Rand gaps for the 3 largest (Glencore R9.5 trillion, BHP R1.11 trillion, Anglo American R502.7bn) are flagged `scale_mismatch_low_reliability` and must never be summed into a portfolio total or quoted at face value — they're artifacts of comparing SA-based internal flow to worldwide group revenue. Treat every number from this tier as "this direction is real, this magnitude is not."

---

### Q: What's the single most surprising finding in this dataset?

**A:** Valterra Platinum. Every other near-zero-share client in the portfolio is either a foreign-currency multinational (where low share is expected — the wallet proxy is a global figure) or has a specific data gap explaining it. Valterra is neither: it's a ZAR reporter, meaning its financials genuinely are the SA-listed entity, and its share is still effectively zero across both measured pillars (0.0% transactional, 0.2% trade & working-capital). There's no confounding explanation available in this data — it's either a real, near-total absence of a Syn Bank relationship, or an exclusive competitor lock-in, and either way it's worth a dedicated relationship review ahead of the more diluted 2–5% opportunities elsewhere.

---

### Q: If we could only fix one data gap before next quarter, what should it be?

**A:** The Foreign/Cross-Border wallet estimate. 16 of 20 companies have real internal cross-border transaction activity (up to R6.7bn for Pepkor Holdings) but no external benchmark to compare it to, because only 4 companies (MTN, Naspers, Sanlam, Vodacom) disclosed a usable numeric foreign-revenue split in their public filings. This is the single largest blind spot in the model by row-count — closing it (via bottom-up JSE SENS segmental disclosures or direct company outreach, both previously scoped out for time) would likely surface real, currently invisible opportunity, since Pillar 3 activity already exists at meaningful scale for many of these clients.

---

### Q: Is there a sector-level pattern across the mining companies, or is each one different?

**A:** Both — the mining sector splits into two distinct patterns. Five miners (Anglo American, AngloGold Ashanti, BHP, Glencore, Gold Fields) are foreign-currency, low-reliability multinationals with consistently thin 0.8%–2.5% shares — a currency/consolidation pattern, not necessarily five independent findings. Valterra Platinum breaks that pattern entirely: it's a ZAR-reporting domestic entity with an even lower share (0.0–0.2%) that can't be explained by consolidation. That contrast is itself the insight — it confirms the other five miners' low shares are at least partly a measurement artifact, while Valterra's is a genuine, unexplained relationship gap.

---

*Tier 1 (instant, deterministic lookups): `scripts/nl_query_assistant.py`. Design rationale: `docs/genai/nl_query_prompt.md`.*
