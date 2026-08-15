# Root3 — SynBank Share of Wallet Estimation

## Overview

This project develops a machine-learning pipeline for estimating the **total banking wallet** of corporate clients using a combination of:

- Internal SynBank banking data
- Publicly available external financial reports
- AI-assisted financial data extraction
- Data engineering and feature preparation
- Machine-learning models

The external financial information provides a representation of the broader financial position of each company, while SynBank's internal data represents the portion of that activity currently visible to the bank.

These datasets are subsequently combined to train models that estimate SynBank's **share of wallet** and the potential total wallet of a corporate client.

---

# 1. External Financial Data

The external financial dataset is constructed from publicly available financial reports for the companies included in the project.

The reports are processed through an AI-assisted extraction pipeline to identify the financial information required for downstream modelling.

## AI Financial Report Extraction

External financial reports are provided to an AI agent.

The agent analyses the reports and produces:

`hackathon-finreports/multi_year_figures.json`

This JSON file contains the structured financial information interpreted from each company's reports across the relevant fiscal years.

An example record is:

```json
{
    "canonical": "imaginary_company",
    "fiscal_year": 2024,
    "source_file": "example.pdf",
    "currency": "ZAR",
    "revenue": 000,
    "cost_of_sales": null,
    "operating_expenses": 000,
    "trade_receivables": 000,
    "trade_payables": 000,
    "inventory": 000,
    "foreign_revenue_pct": 000,
    "fx_gains_losses": 000,
    "fiscal_year_end": "",
    "page_ref": "",
    "notes": ""
}
```

The fields extracted by the AI agent are:

| Field | Description |
|---|---|
| `canonical` | Standardised identifier used to consistently reference the company throughout the pipeline |
| `fiscal_year` | Fiscal year represented by the extracted financial information |
| `source_file` | External financial report from which the information was extracted |
| `currency` | Reporting currency used in the source financial report |
| `revenue` | Reported company revenue |
| `cost_of_sales` | Reported cost of sales, where explicitly available |
| `operating_expenses` | Reported operating expenses |
| `trade_receivables` | Reported trade receivables |
| `trade_payables` | Reported trade payables |
| `inventory` | Reported inventory |
| `foreign_revenue_pct` | Percentage of company revenue attributable to foreign operations |
| `fx_gains_losses` | Reported foreign-exchange gains or losses |
| `fiscal_year_end` | Company's reported fiscal year-end date |
| `page_ref` | Page references identifying where the extracted information was found |
| `notes` | Additional context regarding disclosures, assumptions, or limitations in the source report |

Where a financial figure cannot be reliably identified or is not explicitly disclosed in the financial report, the corresponding value is represented as `null`.

The `source_file`, `page_ref`, and `notes` fields provide traceability back to the original external financial report and allow extracted values to be reviewed where necessary.

---

## External Financial Data Processing Pipeline

The external financial information for the 20 companies is processed through a three-step pipeline.

```text
External Financial Report PDFs
              |
              v
extract_financials_multiyear.py
              |
              v
Relevant Financial Report Text
              |
              +-----------------------+
              |                       |
              v                       v
   multi_year_figures.json       fx_rates.json
              |                       |
              +-----------+-----------+
                          |
                          v
                 merge_multiyear.py
                          |
                          v
              financials_multiyear.csv
                          |
                          v
                 split_by_category.py
                          |
            +-------------+-------------+
            |             |             |
            v             v             v
          Trade      Transactional      FX
```

### Step 1 — Extract Relevant Financial Report Text

The first stage of the pipeline is performed by:

`extract_financials_multiyear.py`

This script processes the external financial report PDFs and extracts the sections of text that are specifically informative for the financial variables required by the project.

The purpose of this stage is to isolate relevant financial information from large annual reports so that downstream extraction and processing can operate on the sections of the reports containing useful financial information.

The extracted report text is used alongside the structured information contained in `multi_year_figures.json`.

---

### Step 2 — Merge and Standardise Multi-Year Financial Data

The second stage is performed by:

`merge_multiyear.py`

This script combines:

- The financial information extracted from the external reports
- `multi_year_figures.json`
- `fx_rates.json`

The `multi_year_figures.json` file provides the structured financial figures interpreted from the source reports.

The `fx_rates.json` file provides the exchange rates required to convert financial values reported in foreign currencies into South African Rand (ZAR).

The resulting dataset is:

`hackathon-finreports/_extracted/financials_multiyear.csv`

This produces a structured numerical representation of the external financial information for each company and fiscal year.

The resulting dataset contains the following features:

| Feature | Description |
|---|---|
| `entity_name` | Company name used to join external and internal datasets |
| `canonical` | Standardised company identifier |
| `fiscal_year` | Fiscal year represented by the observation |
| `source_file` | Financial report used as the source |
| `currency` | Original reporting currency |
| `fx_rate_to_zar` | Exchange rate used to convert the reporting currency to ZAR |
| `fx_rate_date` | Date associated with the exchange rate |
| `revenue_m` | Revenue in millions of the original reporting currency |
| `revenue_zar_m` | Revenue converted to millions of ZAR |
| `cost_of_sales_m` | Cost of sales in millions of the original reporting currency |
| `cost_of_sales_zar_m` | Cost of sales converted to millions of ZAR |
| `operating_expenses_m` | Operating expenses in millions of the original reporting currency |
| `operating_expenses_zar_m` | Operating expenses converted to millions of ZAR |
| `trade_receivables_m` | Trade receivables in millions of the original reporting currency |
| `trade_receivables_zar_m` | Trade receivables converted to millions of ZAR |
| `trade_payables_m` | Trade payables in millions of the original reporting currency |
| `trade_payables_zar_m` | Trade payables converted to millions of ZAR |
| `inventory_m` | Inventory in millions of the original reporting currency |
| `inventory_zar_m` | Inventory converted to millions of ZAR |
| `foreign_revenue_pct` | Percentage of revenue generated from foreign operations |
| `fx_gains_losses_m` | FX gains or losses in millions of the original reporting currency |
| `fx_gains_losses_zar_m` | FX gains or losses converted to millions of ZAR |
| `fiscal_year_end` | Reported fiscal year-end date |
| `page_ref` | Pages supporting the extracted figures |
| `notes` | Additional extraction context or limitations |

Financial fields ending in `_m` represent values in **millions of the company's original reporting currency**.

Fields ending in `_zar_m` represent the corresponding value converted into **millions of South African Rand**.

This currency standardisation ensures that companies reporting in different currencies can be represented consistently in the downstream pipeline.

---

### Step 3 — Split Financial Data by Banking Pillar

The final stage of external financial data preparation separates the consolidated financial dataset into the financial categories required by the machine-learning models.

The data is separated according to the three banking pillars used by the project:

- **Trade Finance**
- **Transactional Banking**
- **Foreign Exchange (FX)**

Each category contains only the external financial variables relevant to that particular share-of-wallet estimation problem.

---

# 2. Internal SynBank Data

The internal datasets represent the financial activity currently visible to SynBank.

Three primary internal datasets are used:

| Dataset | Banking Pillar | Purpose |
|---|---|---|
| `trade_finance.csv` | Trade Finance | Represents trade-finance products and activity conducted through SynBank |
| `transactional_banking.csv` | Transactional Banking | Represents collections, supplier payments, and other transactional activity conducted through SynBank |
| `cross_border_payments.csv` | FX | Represents cross-border transaction activity visible to SynBank |

Unlike the external financial reports, which provide information about the broader financial position of a company, the internal datasets only represent the portion of activity observed by SynBank.

The relationship between these two sources forms the basis of the share-of-wallet modelling approach:

```text
             SynBank-observed activity
Share = ------------------------------------
          External company financial activity
```

---

## Fiscal-Year Alignment

A key consideration when combining the internal and external datasets is that companies do not necessarily operate on the same fiscal calendar.

For example, different companies may have financial years ending on:

- 31 December
- 30 June
- 31 March
- Other company-specific dates

The `fiscal_year_end` extracted from each company's external financial report is therefore used to construct the appropriate 12-month financial window for that company.

For example:

```text
Fiscal year end: 31 March 2025

Corresponding fiscal window:

1 April 2024 → 31 March 2025
```

Internal SynBank transactions are assigned to the appropriate fiscal year using these company-specific windows.

This ensures that internal SynBank activity is compared with external financial figures covering the same financial period.

---

# 3. Medallion Data Pipeline

The internal SynBank datasets are processed using a medallion-style data architecture.

```text
Raw SynBank Data
       |
       v
     Bronze
       |
       v
     Silver
       |
       v
      Gold
       |
       v
Machine-Learning Pipeline
```

The purpose of this pipeline is to transform raw transactional records into company- and fiscal-year-level financial features that can be compared with the external financial dataset.

## Bronze Layer

The Bronze layer represents the raw source data.

At this stage, the datasets retain their original transactional structure with minimal transformation.

## Silver Layer

The Silver layer performs cleaning and standardisation of the raw SynBank datasets.

This stage prepares the data for aggregation and ensures that the relevant fields are represented consistently.

## Gold Layer

The Gold layer aggregates the internal banking activity into company- and fiscal-year-level features suitable for machine learning.

The resulting Gold datasets provide the internal SynBank features used by each of the three modelling pillars.

---

# 4. Share-of-Wallet Feature Engineering

The external financial data and internal SynBank Gold datasets are joined using:

```text
entity_name + fiscal_year
```

This creates company-year observations containing both:

1. The financial activity visible to SynBank
2. The corresponding external financial measure

These values are then used to calculate historical share-of-wallet targets.

---

## Trade Finance

The Trade Finance model considers two components of the client's trade wallet:

- Trade receivables
- Trade payables

The raw SynBank trade-finance dataset contains individual trade-finance products and instruments, including:

- Letters of Credit
- Export Collections
- Guarantees

The relevant products are aggregated according to their direction and economic purpose to create the internal Trade Finance features used by the model.

Conceptually:

```text
SynBank Trade-Finance Products
              |
       +------+------+
       |             |
       v             v
 Export-side     Import-side
   Activity        Activity
       |             |
       v             v
Receivables      Payables
   Proxy           Proxy
```

### SynBank Trade Receivables

`synbank_trade_receivables` represents trade-finance activity associated with funds expected to flow **towards the client**.

This is derived primarily from export-related trade-finance products, including:

- Export Letters of Credit
- Export Collections

These products provide an observable SynBank signal for the portion of the client's trade-receivables-related activity currently handled by the bank.

The corresponding external financial variable is the company's reported total trade receivables.

The historical share is calculated as:

```text
Share of Trade Receivables
=
SynBank Export-Related Trade Finance Activity
----------------------------------------------
External Total Trade Receivables
```

or:

```text
Share of Trade Receivables
=
synbank_trade_receivables
-------------------------
trade_receivables_zar
```

### SynBank Trade Payables

`synbank_trade_payables` represents trade-finance activity associated with amounts that the client is expected to pay to suppliers or counterparties.

This is derived primarily from import-related trade-finance products, including:

- Import Letters of Credit

Import Letters of Credit therefore provide an observable SynBank signal for the portion of the client's trade-payables-related activity currently handled through the bank.

The corresponding external financial variable is the company's reported total trade payables.

The historical share is calculated as:

```text
Share of Trade Payables
=
SynBank Import-Related Trade Finance Activity
---------------------------------------------
External Total Trade Payables
```

or:

```text
Share of Trade Payables
=
synbank_trade_payables
----------------------
trade_payables_zar
```

Guarantees are retained as part of the broader Trade Finance dataset but do not necessarily map directly to accounting trade receivables or trade payables. Their treatment therefore depends on whether they can be meaningfully associated with the corresponding wallet component.

It is important to note that SynBank trade-finance instruments and accounting trade receivables/payables are **not assumed to be identical measures**.

Instead, the internal trade-finance activity provides observable banking signals that can be compared with the broader accounting position of the company.

The resulting internal features used by the Trade Finance model are:

- `synbank_trade_receivables`
- `synbank_trade_payables`

---

## Transactional Banking

The Transactional Banking model considers two major directions of day-to-day corporate cash movement:

- Collections
- Supplier payments

These internal transaction types are mapped to related external financial measures to create historical share-of-wallet targets.

Conceptually:

```text
SynBank Transactional Activity
              |
       +------+------+
       |             |
       v             v
 Collections    Supplier Payments
       |             |
       v             v
   Revenue       Cost of Sales
    Proxy            Proxy
```

### Revenue Share

`synbank_collections` represents funds collected through SynBank on behalf of the corporate client.

Collections provide an internal signal of the client's **revenue-related cash inflows** currently passing through SynBank.

The corresponding external financial measure is the company's total reported revenue.

The historical revenue share is calculated as:

```text
Share of Revenue
=
SynBank Collections
-------------------
External Total Revenue
```

or:

```text
Share of Revenue
=
synbank_collections
-------------------
revenue_zar
```

Collections and accounting revenue are **not assumed to be identical**.

For example, accounting revenue and the timing of cash collection can differ.

Instead, SynBank collections are treated as an observable proxy for the portion of the client's revenue-related transactional wallet currently visible to SynBank.

### Cost-of-Sales Share

`synbank_supplier_payments` represents payments made through SynBank to the client's suppliers.

Supplier payments provide an internal signal of the company's **supplier-related cash outflows** currently passing through SynBank.

The corresponding external financial measure is the company's reported cost of sales.

The historical cost-of-sales share is calculated as:

```text
Share of Cost of Sales
=
SynBank Supplier Payments
-------------------------
External Total Cost of Sales
```

or:

```text
Share of Cost of Sales
=
synbank_supplier_payments
-------------------------
cost_of_sales_zar
```

Supplier payments and accounting cost of sales are also **not assumed to be identical measures**.

Differences can exist due to payment timing, inventory movements, credit terms, and accounting treatment.

Instead, supplier payments are treated as an observable banking proxy for the portion of the client's supplier-related transactional wallet currently visible to SynBank.

The resulting internal features used by the Transactional Banking model are:

- `synbank_collections`
- `synbank_supplier_payments`

---

## Foreign Exchange (FX)

The FX model estimates the relationship between SynBank cross-border inflows and the company's estimated foreign revenue.

The internal SynBank cross-border dataset contains transactions occurring between the client and foreign counterparties.

Inbound cross-border activity is aggregated to produce:

`cross_border_inflows`

The external estimate of foreign revenue is calculated from:

```text
Foreign Revenue
=
Total Revenue × Foreign Revenue Percentage
```

The historical FX share is then calculated as:

```text
Share of Foreign Revenue
=
SynBank Cross-Border Inflows
----------------------------
External Total Foreign Revenue
```

The internal feature used by the FX model is:

- `cross_border_inflows`

As with the other modelling pillars, cross-border inflows and accounting foreign revenue are not assumed to represent exactly the same financial measure.

Cross-border inflows instead provide an observable SynBank signal of the client's broader foreign-revenue-related financial activity.

---

# 5. Machine-Learning Models

The project uses **Elastic Net regression** to estimate share of wallet.

Elastic Net combines L1 and L2 regularisation:

- **L1 regularisation** can reduce the influence of less informative features.
- **L2 regularisation** helps stabilise model coefficients, particularly where features may be correlated.

The modelling system is organised into three business pillars:

```text
Share-of-Wallet Modelling
|
+-- Trade Finance
|   +-- Trade Receivables estimator
|   +-- Trade Payables estimator
|
+-- Transactional Banking
|   +-- Revenue estimator
|   +-- Cost-of-Sales estimator
|
+-- Foreign Exchange
    +-- Foreign Revenue estimator
```

Although Trade Finance and Transactional Banking each contain two target-specific estimators, they remain grouped as single business modelling pillars.

This allows each target to use independently optimised Elastic Net hyperparameters while maintaining the three-pillar structure of the overall solution.

---

## Feature Scaling

The machine-learning features are standardised using `StandardScaler`.

Scaling is performed because Elastic Net regularisation is sensitive to differences in feature magnitude.

Each banking pillar has its corresponding saved scaler:

```text
trade_scaler.pkl
transactional_scaler.pkl
fx_scaler.pkl
```

During future inference, new SynBank data must be transformed using these existing scalers rather than fitting new scalers.

---

# 6. Model Validation and Hyperparameter Selection

Due to the relatively small number of companies available for training, the models are evaluated using **Leave-One-Company-Out cross-validation**.

This is implemented using `LeaveOneGroupOut`, with `entity_name` used as the grouping variable.

For each iteration:

```text
All Companies
      |
      +----> One Company Held Out
      |
      v
Remaining Companies
      |
      v
Fit Scaler + Elastic Net
      |
      v
Predict Held-Out Company
```

The process is repeated until every company has been held out once.

This prevents observations belonging to the same company from appearing in both the training and validation data during a fold.

It therefore evaluates the model according to the intended use case:

> **Can the model estimate share of wallet for a corporate client that was not included in its training data?**

The predictions generated while each company is held out are combined and evaluated using metrics including:

- R²
- Mean Squared Error (MSE)

---

## Hyperparameter Search

Elastic Net contains two primary regularisation hyperparameters:

- `alpha` — controls the overall strength of regularisation
- `l1_ratio` — controls the balance between L1 and L2 regularisation

The pipeline evaluates combinations of:

```python
alphas = [
    0.00001,
    0.0001,
    0.001,
    0.01,
    0.1
]

l1_ratios = [
    0.1,
    0.25,
    0.5,
    0.75,
    0.9
]
```

Each target is evaluated independently.

This means, for example, that the Trade Receivables estimator and Trade Payables estimator do not have to use the same `alpha` or `l1_ratio`.

Similarly, the Transactional Revenue and Cost-of-Sales estimators can select different hyperparameters.

The best-performing combination is selected according to the cross-validated R² score for the corresponding target.

---

# 7. Final Model Training and Storage

Once the optimal Elastic Net hyperparameters have been selected, each estimator is retrained using all available observations.

This allows the deployed model to make use of the complete historical dataset.

The trained models and their corresponding scalers are serialised using `joblib`.

The resulting model directory contains:

```text
machine_learning/models/

trade_model.pkl
trade_scaler.pkl

transactional_model.pkl
transactional_scaler.pkl

fx_model.pkl
fx_scaler.pkl
```

The Trade Finance model package contains the independently trained:

- Receivables estimator
- Payables estimator

The Transactional Banking model package contains:

- Revenue estimator
- Cost-of-sales estimator

The FX model contains:

- Foreign-revenue-share estimator

This maintains a simple three-pillar deployment structure while allowing individual target estimators to be independently optimised.

---

# 8. Using the Models for New Clients

Once trained, the models can estimate wallet information for a new SynBank corporate client using only the relevant internal SynBank features.

The external financial reports are required during **model development and training** because they provide the broader company financial measures needed to construct historical share-of-wallet targets.

During future inference, the trained models use the relationships learned from these historical observations.

The inference process is:

```text
New SynBank Client
       |
       v
Internal SynBank Data
       |
       v
Gold-Level Features
       |
       v
Saved StandardScaler
       |
       v
Saved Elastic Net Estimator
       |
       v
Predicted Share of Wallet
       |
       v
Estimated Total Wallet
```

For example, the Trade Finance pipeline may receive:

```text
synbank_trade_receivables
synbank_trade_payables
```

while the Transactional pipeline receives:

```text
synbank_collections
synbank_supplier_payments
```

and the FX pipeline receives:

```text
cross_border_inflows
```

The corresponding saved scaler transforms the features before they are passed into the trained estimator.

---

# 9. Estimating the Total Wallet

The machine-learning models predict the estimated proportion of the relevant client wallet currently visible to SynBank.

Conceptually:

```text
                      SynBank Activity
Predicted Share = -------------------------
                   Estimated Total Activity
```

Once the predicted share is known, the relationship can be inverted:

```text
                          SynBank Activity
Estimated Total Wallet = -----------------
                          Predicted Share
```

For example, if SynBank observes R50 million of relevant client activity and the model estimates that this represents 1% of the client's corresponding wallet:

```text
Estimated Total Wallet
=
R50 million / 0.01
=
R5 billion
```

The same principle can be applied independently across the wallet components.

For example:

```text
Trade Finance
|
+-- Estimated Total Trade Receivables
+-- Estimated Total Trade Payables

Transactional Banking
|
+-- Estimated Revenue-Related Wallet
+-- Estimated Supplier-Payment Wallet

Foreign Exchange
|
+-- Estimated Foreign-Revenue-Related Wallet
```

---

# 10. Share-of-Wallet Opportunity

Once the total wallet has been estimated, the system can compare the estimated wallet with the activity currently captured by SynBank.

Conceptually:

```text
Estimated Total Wallet
          -
Current SynBank Wallet
          =
Potential Wallet Gap
```

A larger estimated wallet gap indicates that a greater proportion of the client's financial activity may currently be taking place outside SynBank.

The resulting estimates can therefore support:

- Client opportunity identification
- Share-of-wallet analysis
- Corporate client prioritisation
- Product opportunity identification
- Relationship-manager decision support

For example, the model may indicate that SynBank already captures a relatively large proportion of a client's transactional collections but only a small proportion of its trade-finance activity.

This provides more actionable information than a single total-wallet estimate because it identifies **which banking pillar contains the greatest potential opportunity**.

The objective of the pipeline is therefore not only to estimate the size of a client's financial wallet, but to translate internal banking activity into an actionable view of **where SynBank may have additional opportunity to grow its share of that wallet**.