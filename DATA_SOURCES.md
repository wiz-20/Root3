# External Data Sources — Syn Bank Share of Wallet Challenge

Researched and endpoint-verified 8 August 2026. Every URL below was actually called; results noted.

---

## TL;DR — the three that win

1. **SARB BA900 JSON API** — per-bank, per-month corporate deposit balances for all 33 SA banks back to 2008. This is a *real market-share denominator*. Almost nobody knows it's public.
2. **JSE Client Portal JSON API** — the full listed universe (297 equity issuers) with ICB sector, market cap, sponsor/auditor, plus 11 years of SENS with PDF links, and Annual Financial Statement PDFs.
3. **stockanalysis.com + yfinance** — parsed income statement / balance sheet / cash flow for ~250 JSE tickers in under a minute, free, no key.

Everything else is supporting colour.

---

## 1. SARB — the calibration backbone ⭐⭐⭐

**No auth. No key. Plain JSON. Free.**

### 1a. BA900 per-bank regulatory returns

```
BASE = https://custom.resbank.co.za/SarbWebApi/SarbData/IFData

GET /GetPeriods/BA900                              -> 221 monthly periods, 2008-01 -> 2026-05
GET /GetInstitutions/BA900/{period}                -> 33 banks + TOTAL
GET /GetInstitutionData/BA900/{period}/{instId}    -> full BA900 form as XML inside a JSON envelope
GET /SarbData/IFData/GetAllTypes                   -> 27 other returns (BA120 income stmt, BA200 credit risk)
```

**Parameter order is `{type}/{period}/{institutionId}`.** Reversing it silently returns HTTP 500.

Institution IDs: ABSA `34118`, FirstRand `416053`, Standard Bank `416061`, Nedbank `416088`, Capitec `333107`, Investec `25054`.

The form has 18 tables split by **counterparty sector** — `Private nonfinancial corporate sector`, `Public nonfinancial corporate sector`, `Financial corporate sector`, `Household sector`. Table 1, item 25 = private non-financial corporate deposits.

**Verified pull, May 2026, corporate deposits (R'000):**

| Bank | Corporate deposits | Share |
|---|---:|---:|
| FirstRand | 491,204,432 | 31.7% |
| Standard Bank | 313,093,193 | 20.2% |
| ABSA | 270,596,488 | 17.5% |
| Nedbank | 213,183,521 | 13.8% |
| Investec | 130,134,824 | 8.4% |
| Capitec | 16,471,153 | 1.1% |
| **All 33 banks** | **1,547,699,622** | 100% |

**Why this is the differentiator:** it converts share of wallet from a guess into a constrained allocation problem. Your bottom-up client estimates must sum to something consistent with the actual system-wide corporate deposit and credit pool. Write that sentence into the methodology.

One month × all banks ≈ 6 MB, a few minutes. Full history ≈ 7,300 requests / 1.3 GB — don't, unless you need it. Rate-limit and retry; concurrency triggers resets.

### 1b. SARB economic time series

```
Swagger spec (grab this first): https://custom.resbank.co.za/SarbWebApi/swagger/v1/swagger.json
GET /WebIndicators/Shared/GetTimeseriesObservations/{code}/{start}/{end}
GET /WebIndicators/ReleaseOfSelectedData/MonthlyIndicatorsAll/{dataType}
GET /WebIndicators/CurrentMarketRates
```

The API root `/SarbWebApi/` returns 404 — that misleads people into thinking it's dead. It isn't.

| dataType | Content | Size | History |
|---|---|---|---|
| `CDACSM` | Credit detail — **Credit to the Corporate Sector**: overdrafts, general loans, mortgages, instalment sale, leasing, cards | 6.2 MB ✅ verified | 1965 → 2026-06 |
| `CDADS` | Deposit detail — **Bank Deposits of Non-Financial Corporate Sector**, private/public/FX splits | 2.5 MB | 1965 → 2026-06 |
| `MRDCM` | Capital market — bond yields and issuance | 2.5 MB | 1949 → 2026-06 |
| `MRDMA` | Money & banking, M0–M3 | 11.8 MB | 1960 → 2026-06 |

FX: `EXCX135D` (ZAR/USD), `EXCZ001D` (ZAR/GBP). Verified — 7 Aug 2026 ZAR/USD = **16.3213**. Current rates endpoint returns repo 7.00%, prime 10.50%, Sabor, Zaronia.

Balance of payments: `/WebIndicators/EconFinDataForSA/GetExternalSectorData`.

---

## 2. JSE Client Portal — the client universe ⭐⭐⭐

Undocumented but unauthenticated JSON. `Content-Type: application/json` required, POST with a JSON body.

```
BASE = https://clientportal.jse.co.za/_vti_bin/JSE/

POST CustomerRoleService.svc/GetAllIssuers
     {"filterLongName":"","filterType":"Equity Issuer"}     -> 297 equity issuers
POST CustomerRoleService.svc/GetAllIssuersNoFilter          -> 564 issuers, all types
POST SharesService.svc/GetAllInstrumentsForIssuer
     {"issuerMasterId":881}   -> ISIN, ICB Industry, ICB Sector, MarketCap, Price, ListingDate, Board
POST CustomerRoleService.svc/GetIssuerNatureOfBusiness      -> business description (good LLM input)
POST CustomerRoleService.svc/GetIssuerAssociatedRoles       -> Sponsor, Audit Firm, Transfer Secretary
POST WebstirService.svc/GetWebstirDocumentYearsByIssuerMasterId
POST WebstirService.svc/GetWebstirDocumentsByIssuerMasterIdAndYear
     {"issuerMasterId":881,"year":2026}  -> AFS / Integrated Report PDF URLs on webstir.jse.co.za
```

A full pull gave **236 ordinary-share rows with ICB sector + market cap in 34 seconds**. Sector split: Basic Materials 42, Financials 38, Real Estate 37, Industrials 34, Consumer Discretionary 34, Consumer Staples 21, Tech 11, Telecoms 7, Energy 6, Health Care 4, Utilities 2 — enough to pick 50 clients matching the brief's sector mix.

**`GetIssuerAssociatedRoles` is a sleeper wallet signal** — it names the sponsor bank/adviser already on the account.

### SENS

```
POST SENSService.svc/GetSensAnnouncementForDates
     {"from":"2021-01-01T00:00:00.000Z","to":"2026-08-07T23:59:59.000Z","issuerMasterId":881}
```

Returned **279 announcements back to 2015** for one issuer. 50 calls covers the whole portfolio. `AnnouncementText` is always null — full text is in the PDF at `https://senspdf.jse.co.za/documents/SENS_YYYYMMDD_Sxxxxxx.pdf` (free, verified, clean `pdftotext` output).

Headlines alone are already scoreable: *Trading statement, Rights offer, Acquisition, Cautionary, Redemption of notes, Disclosure of significant holding* → map straight onto DCM / ECM / M&A / trade-finance events.

Don't use `GetSensAnnouncementsByIssuerMasterId` (last 15 only) or the no-issuer variant (rolling ~2-week window).

### ⚠️ Rate limiting — read this

After roughly **350 calls in ~20 minutes**, JSE's Cloudflare returned **HTTP 522 on every JSE host** and stayed down. I re-tested it during this research and it was **still returning 522** — so treat the block as real and slow to clear.

Rules: ~1 req/sec, browser User-Agent, `Referer: https://clientportal.jse.co.za/companies-and-financial-instruments`, **cache every response to disk on first fetch**, exponential backoff on 522. Pull the universe once, pull SENS once, then work offline. You cannot afford a multi-hour block on day 6.

---

## 3. Company fundamentals — two free routes, both proven

### 3a. stockanalysis.com (scrape) — best coverage

```
https://stockanalysis.com/list/johannesburg-stock-exchange/          -> 259 JSE tickers
https://stockanalysis.com/quote/jse/{TICKER}/financials/             -> overview + segment revenue
https://stockanalysis.com/quote/jse/{TICKER}/financials/balance-sheet/
https://stockanalysis.com/quote/jse/{TICKER}/financials/cash-flow-statement/
```

Server-rendered HTML, no auth, no paywall. Bare tickers, **no `.JO` suffix**. Verified live (HTTP 200, 228 KB for SOL). A test run did **260 tickers → 207 with full financials in 27.8 seconds**.

Coverage among those 207: Cash 99%, Total Debt 98%, Payables & Interest Paid 95%, Receivables 87%, LT Debt 86%, Capex 81%, Revenue 78%, Cost of Revenue 69%, Inventory 64%, FX gain/loss 60%. The gaps are mostly *correct* — banks have no inventory, REITs no COGS.

There's also a SvelteKit route `/quote/jse/{TICKER}/financials/__data.json` that returns clean arrays (revenue, gp, opinc, netinccmn, epsdil). No official API, no CSV export — scrape politely.

**Bonus: it carries "Revenue by Segment".** Sasol splits Mining / Gas / Fuels / Chemicals Africa / America / Eurasia. Naspers splits LatAm / Europe / India. That's partial geographic revenue for free, feeding the FX-hedging dimension of the wallet model.

Dual-listed giants live on other exchange paths, all verified 200: `/quote/lon/AAL/`, `/quote/lon/GLEN/`, `/quote/swx/CFR/`, `/quote/ams/PRX/`, `/quote/asx/S32/`, and US paths for BTI, BHP, AU, SSL.

### 3b. yfinance — fastest, cleanest

`pip install yfinance` (v1.5.2 tested). Tickers use the **`.JO`** suffix.

**52 tickers → full three-statement fundamentals in 33 seconds, 52/52 success, 40,542 rows.** ~50 income items, ~72–133 balance sheet items, ~53–108 cash flow items, 4–5 fiscal years, plus a 166-key `.info` dict.

Coverage: Revenue / Net Income / EPS / Total Assets / Equity / Cash / FCF **100%**; Total Debt & Capex 98%; Operating CF 96%. Operating Income / EBITDA / Gross Profit 79% — the 11 misses are *every bank and insurer* (ABG, CPI, DSY, FSR, NED, OMU, OUT, RNI, SBK, SLM, SNT), which is correct.

**Three traps:**
1. `currency` is **`ZAc` (cents)**, `financialCurrency` is **`ZAR` (rand)**. Divide prices by 100 before any market-cap-to-revenue maths.
2. **12 of 52 don't report in ZAR.** NPN, PRX, BHG, AGL, GLN, GFI, ANG, DTC → USD. CFR, RNI, MNP → EUR. BTI → GBP. Read `financialCurrency` per ticker, never assume.
3. **Quarterlies are empty** — SA companies report semi-annually. Build annual only.

Stale tickers to fix: `AMS.JO` → `VAL.JO` (Valterra, Anglo demerger), `NHM.JO` → `NPH.JO` (Northam), `MCG.JO` delisted.

Wrap in a 3-attempt retry with backoff — transient empty responses happen and retries absorb them cleanly.

### 3c. SEC EDGAR — ~9 companies, but gold-standard

Free, no key, just a User-Agent header.

```
https://data.sec.gov/api/xbrl/companyfacts/CIK{10-digit}.json
https://www.sec.gov/files/company_tickers.json
https://efts.sec.gov/LATEST/search-index?q=...&forms=20-F&locationCode=T3
```

SA 20-F filers: Sasol `0000314590`, Gold Fields `0001172724`, Harmony `0001023514`, Sibanye `0001786909`, AngloGold `0001973832`, Karooooo `0001828102`, DRDGOLD `0001023512`, Grindrod Shipping `0001725293`, Caledonia `0000766011`. Each carries 245–296 `ifrs-full` tags including inventories, trade payables/receivables, borrowings, capex, cash-flow hedges and derivative fair values. Sasol FY2025 revenue = ZAR 249,096,000,000.

**Use it as an accuracy benchmark, not a bulk source.** *"Our LLM extraction matches audited XBRL to within X% on 9 companies"* is the single most defensible line you can put in the deck. IFRS tag names vary by filer — don't hardcode.

### 3d. Annual report PDFs — for what the parsers can't give you

Company IR pages, direct download, verified working (e.g. Sasol AFS FY24, 2.4 MB). Also reachable via the JSE Webstir endpoints above.

**Only spend LLM/PDF time on the four things structured sources structurally lack:** debt maturity ladders, FX exposure notes, derivative/hedging notes, and export/foreign revenue splits. Scope to ~50 companies × ~4 target notes. That *is* your Gen AI extraction use case.

---

## 4. Supporting sources

| Source | URL | What you get | Verdict |
|---|---|---|---|
| **DealMakers SA** | `dealmakerssouthafrica.com/dm-annual-2025` | M&A + corporate finance deal tables, **adviser league tables**, BEE & unlisted deals. Free PDFs, no login, verified 200. Prior years at `/dm-annual-2021`…`2025` | **Yes, 2–3 hrs.** Best free deal-flow proxy in SA — lets you attribute deals to specific banks, i.e. observe competitor capture directly |
| **SARS trade stats** | `tools.sars.gov.za/tradestatsportal/data_download.aspx` | Customs imports/exports by HS chapter/tariff and country of origin/destination | **Yes, but manually.** ASP.NET WebForms needs `__VIEWSTATE` round-trips. Do 3–5 targeted corridor pulls in a browser (mining→China, autos→EU/US). Don't build a scraper |
| **Stats SA** | `statssa.gov.za/?page_id=1847` | 70+ series: mining production (P2041), manufacturing, retail (P6242.1), wholesale, motor trade, CPI/PPI | **Yes, browser download only** — Imperva blocks scripted clients |
| **World Bank** | `api.worldbank.org/v2/country/ZAF/indicator/{code}?format=json` | GDP, trade, financial sector. Clean REST JSON | 30 min, good for framing |
| **African Markets** | `african-markets.com/en/stock-markets/jse/listed-companies` | 456 rows: Company, Symbol, Sector in a plain HTML table | 10-min sanity check on the JSE universe |
| **SARB C-form list** | `resbank.co.za/.../List of private sector non-financial corporations listed on the JSE.pdf` | The cross-border-payments regulator's own list of JSE non-financial corporates | Niche, but a nice citation for the FX-need narrative |
| **Kaggle** | `kaggle.com/datasets/katendencies/jse-sens-announcements` | SENS announcement text corpus | Secondary corpus for LLM work, not a fundamentals table |

---

## 5. Do not bother

| Source | Why |
|---|---|
| **CIPC XBRL** | Registered account, per-set fee + credit card + OTP, lookup by registration number, delivered as email attachments, no bulk, no API. And listed groups file *company-level* AFS, not the consolidated group accounts you want |
| **Moneyweb SENS / annual reports** | Cloudflare managed challenge, hard 403 to scripts |
| **africanfinancials.com** | Cloudflare 403, and coverage skews Zambia/Zimbabwe/Kenya not SA |
| **ShareData (sharedata.co.za)** | Connection reset / 503 from non-SA IPs. Worth one try from a local SA connection — the `?c=TICKER` pattern is clean — but don't build on it |
| **annualreports.com** | Search for "south africa" returns zero results |
| **IRESS, JSE Market Data Connect, SENS Live** | Licensed feeds, contract + fees, procurement won't clear in 8 days |
| **JSE debt market pages** | Marketing copy; instrument-level bond data is paywalled. Substitute SARB `MRDCM` + SENS |
| **FMP / Alpha Vantage / Twelve Data / Finnhub / SimFin free tiers** | Tested live with demo keys: all 401/403 or US-only. FMP needs the $149/mo Ultimate tier for global. SimFin is explicitly US-only. EODHD covers JSE but free tier is 20 calls/day and fundamentals need $59.99/mo |
| **investpy** | Dead — wheel build fails, upstream abandoned |
| **BankservAfrica BETI, PASA, vulekamali** | One headline number / government budget data. Not corporate banking |
| **Existing JSE packages** | `JSETracker` last released 2021, prices only. GitHub `jse` topic is Java SE, JSEcoin and the *Jamaica* Stock Exchange. **No public repo touches `SENSService.svc` or `senspdf.jse.co.za`** — your scraper will be the first, which is worth a line in the pitch |

---

## 6. Suggested ingestion order

| Day | Work |
|---|---|
| 1 | JSE Client Portal → 236-row master table (ticker, ISIN, ICB sector, mcap, sponsor, auditor, business description). Pick 50 clients across the brief's six sectors. **Cache everything to disk.** |
| 1 | yfinance + stockanalysis → three-statement fundamentals for all 50, 5 years. ~1 minute of runtime |
| 2 | SARB BA900 harvester → 33 banks × last 36–60 months. Build the market-share denominator |
| 2 | SARB `CDACSM` + `CDADS` + `EXCX135D` + `MRDCM` → aggregate corporate credit/deposit pool and FX |
| 3 | SENS pull for the 50 → classify headlines into DCM / trade / M&A / earnings events |
| 3 | EDGAR XBRL for the 9 SA filers → ground-truth validation set |
| 4 | DealMakers PDFs → deal table tagged by advising bank (= observed competitor capture) |
| 4 | Targeted SARS corridor pulls + Stats SA sector series (browser, manual) |
| 5–6 | LLM extraction from AFS PDFs: debt maturity ladders, FX exposure notes, hedging notes, foreign revenue splits |
| 7–8 | Model, calibrate against BA900, dashboard, write-up |

## 7. Two sentences to put in the methodology

> We calibrate our bottom-up share-of-wallet estimates against actual per-bank private non-financial corporate deposits published in SARB BA900 regulatory returns, ensuring portfolio-level estimates are consistent with observed system-wide banking market share.

> We validate LLM-extracted financial statement line items against audited XBRL filings for the nine South African SEC registrants, reporting extraction accuracy as a measured error rate rather than an assumption.
