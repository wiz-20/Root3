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

### Q: Why does OUTsurance Group show a 491% Trade & Working Capital share - is Syn Bank really capturing five times more activity than the client's own external benchmark?

**A:** No - that's a proxy_breakdown anomaly, not a real relationship. OUTsurance's Pillar 2 internal activity is R78.6m against an external benchmark of only R16.0m, producing the impossible 491.3% figure; Sanlam shows the identical pattern on Pillar 3 (133.5% share, R2664.9m internal vs R1996.3m external). Both are insurers, and this is structural, not coincidental: the revenue-based proxy used for Trade & Working Capital / Foreign wallet doesn't map onto how an insurer's treasury and reinsurance flows actually work, so the "external total" undershoots the client's real scale. Read both figures as "the proxy is broken for this pillar," not as a relationship-strength signal - the trustworthy numbers for these two clients are their Pillar 1 shares (OUTsurance 0.9%, Sanlam 18.7%), which come from a benchmark that actually works.

---

### Q: How does the insurance sector's wallet penetration compare with consumer retail?

**A:** On paper insurance looks stronger - Sanlam's 13.8% blended share dwarfs Shoprite's 3.1%, Bid Corporation's 4.2%, and even Pepkor's 20.9% looks close - but that comparison is misleading, because both insurers' non-Pillar-1 figures are proxy_breakdown anomalies (Sanlam 133.5% on Pillar 3, OUTsurance 491.3% on Pillar 2), not real capture. Stripped to the one pillar where the proxy actually works for every client (Pillar 1, Transactional Banking), the picture flips: Sanlam's 18.7% and OUTsurance's 0.9% bracket the range, against Pepkor's 22.4%, Bid Corporation's 3.1%, and Shoprite's 2.4%. Insurance isn't uniformly stronger than retail - Sanlam is a strong transactional relationship, OUTsurance is a weak one - and the sector-level comparison only holds pillar-by-pillar, not as a blended-share average.

---

### Q: Pepkor Holdings has by far the strongest blended share in the portfolio - does that mean there's no more opportunity there?

**A:** No - Pepkor is simultaneously the strongest relationship AND a top-15 gap by Rand size (portfolio rank #13, R160.5bn), because its 20.9% blended share is a Pillar 1-driven average masking a much weaker Pillar 2. Transactional Banking share is 22.4% - the highest in the portfolio by a wide margin - but Trade & Working Capital sits at just 3.1%, and Foreign/Cross-Border has no usable external benchmark at all (flagged `wallet_unavailable`: R6655.5m of internal cross-border activity with nothing to compare it to). The right read isn't "Pepkor is done," it's "a Pillar 1 success story that hasn't been cross-sold into Trade & Working Capital" - exactly the headroom a single blended percentage hides. One more caveat before pitching this: Pepkor's 20.9% blended share is itself a `statistical_outlier_high` versus the moderate-reliability peer-group mean of 5.8% (z=2.31) - worth a sanity-check on the underlying financials before building a deck around it.

---

### Q: If you had to give the exec team one portfolio-level number to remember, what would it be and what's the caveat?

**A:** 5.8% - the average blended share across the actionable (moderate-reliability, ZAR-reporter) tier, the only subset where the figure is a literal, trustworthy Rand-denominated share rather than a directional foreign-currency proxy. The caveat is what it excludes: 9 of 20 clients are foreign-currency reporters whose consolidated Rand gaps (Glencore's R9.5 trillion the most extreme) can't be summed into any portfolio total, and 1 client (Bidvest) has no blended figure at all because Group financials aren't disclosed. So 5.8% is honestly "the actionable half of the book," not "the whole portfolio" - repeating it without that scope caveat would overstate confidence to the room.

---

*Tier 1 (instant, deterministic lookups): `scripts/nl_query_assistant.py`. Design rationale: `docs/genai/nl_query_prompt.md`.*
