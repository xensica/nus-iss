# StockPilot — purchasing intelligence, explained

A 12-product purchasing workspace for the NUS-ISS **Purchase Order Preparation** problem.
Start with the reproducible sample, upload daily CSVs, or prepare an exported UCI transaction CSV.
No real supplier order or email is ever sent.

## Run locally

From C:\NUS-ISS\purchase-order-agent:

```powershell
.\.venv\Scripts\python.exe -m pip install -r purchase_demo\requirements.txt
.\purchase_demo\Start-StockPilot.ps1
```

Open http://127.0.0.1:8504. No API key is needed for the calculation workflow.
The redesign uses warm paper, charcoal and orange, with top navigation rather than a sidebar.
Control room includes a 14-day stock map with a before/after arrival toggle; Sourcing desk
shows delivery-ordered shipment cards; Order review presents a purchase-document layout.
Data studio, Disruption lab and Evidence retain the import, stress-test and evaluation workflows.

### Outstanding calculation audit findings

This redesign changes presentation, not algorithms. Percentage adjustment rounding can
overstate demand (25 units + 12% currently gives 29 rather than 28); supplier comparison
does not forward the optional urgent deadline; a zero-quantity urgent constraint conflict
can incorrectly blame late incoming stock. These issues remain pending and are disclosed
in the app's calculation audit panel. Do not treat passing UI tests as full mathematical validation.

## A three-minute demonstration

1. **Overview:** 12 products, an urgency-sorted action list, one shared budget. Explain the difference between “needs intervention” and “ready for review.”
2. **Product insights → Cold brew coffee:** show the purchase calculation, stock coverage, early/late shipment split, and the comparison with a feasible single supplier.
3. **Scenario lab:** increase demand and delay new shipments. Show how an otherwise feasible plan can fail under changed assumptions.
4. **Data & settings:** model a promotion, recalculate, then revisit the product. Explain that events are owner assumptions.
5. **Overview:** select products and create a draft. A shared-budget breach blocks drafting.
6. **Order review:** the Operator cannot approve. Switch the top-right Review as selector to the clearly labelled simulated Manager role, review exact details, tick the confirmation and approve. Download order lines and the audit record.
7. **Performance:** run offline evaluation. Show the held-out dates, three forecasting methods, and cost alongside service outcomes. Do not claim the synthetic results validate real shops.

The differentiator is an explainable, testable decision: **why this quantity, why these suppliers, what could break the plan, and who approved it**.

## Data

Bundled sample_data/sales.csv and inventory.csv contain 84 synthetic daily observations for each of 12 products. The default inventory snapshot is 2026-09-24; sample sales end 2026-09-23.

Daily sales columns: date,product_id,units.
Required inventory columns: product_id,current_stock.
Optional inventory columns: incoming_units,incoming_day,name,category,unit_price_cents.

Dates use YYYY-MM-DD; units are non-negative integers. One row per product/date. Both files must contain identical product IDs. Maximum 15 products, 100,000 rows and 10 MB per daily CSV. Import is atomic: an invalid file does not replace the active dataset.

Absent daily records are **unknown**, not automatically zero. Sparse history uses a labelled recent-mean fallback; stale history blocks a recommendation. Inventory must correspond to the selected analysis date. Supplier prices are **simulated purchase prices in SGD cents**, not observed sale prices.

### UCI data preparation

Data & settings contains a UCI-format transaction CSV importer. Export the original workbook to UTF-8 CSV and specify its exact timestamp format. The importer never retains CustomerID; cancellation invoices, invalid or nonpositive quantities/prices, missing required fields and quantities above the explicit cap are excluded. The audit records exclusion counts and assumptions. Returns are excluded rather than netted. The quantity cap may exclude legitimate wholesale orders.

The user must confirm ledger completeness before missing product/day transactions are filled with zero. Up to 12 products are selected by **training-period** trading-day coverage, not holdout accuracy. Stock is simulated at five days of recent mean, and purchase reference prices remain a fixed S$2.00; original GBP sale prices are not silently treated as SGD purchase prices.

The actual UCI workbook is not bundled or downloaded. Source: Chen, D. (2015). Online Retail [Dataset]. UCI Machine Learning Repository. https://doi.org/10.24432/C5BW33 (CC BY 4.0). Dataset page: https://archive.ics.uci.edu/dataset/352/online+retail.
This dataset represents historical UK gift retail, not current Singapore SME demand.

## Model and solver

- Recent matching-weekday averages over 28 calendar days; 14-day horizon.
- Weekly patterns only. No annual seasonality, learned event effect or calibrated confidence probability.
- Safety stock = configured days × average forecast demand.
- Reorder point = next seven days of forecast + safety stock.
- Zero net quantity still checks delivery timing for shortages.
- Three simulated approved suppliers. Product reference price multipliers A/B/C: 1.0 / 0.8 / 0.9. Quality, reliability, delivery days, MOQ, capacity and fees use shared assumptions.
- Exact quantity, one or two suppliers, maximum 2,000 units/product. All daily balances and final safety buffer must be satisfied.
- Optional urgent units/deadline add a constraint. Product overrides are recorded with the draft.
- Delivery fees are per product/supplier allocation. **No cross-product freight consolidation or shared supplier capacity optimisation**.
- A blocked result means no feasible plan in the restricted search. No automatic MOQ over-ordering.
- Stress tests replay the same allocation. Only new supplier deliveries are delayed; existing incoming stock keeps its date. Stress tests are assumptions, not probabilities.

## Approval and persistence

SQLite demo_orders.db is preserved. Startup adds reviewed_role via an additive, idempotent migration.
Existing single-product records remain readable. New drafts contain product-level evidence and overrides.
Drafts are fingerprint-deduplicated. Review checks the exact persisted payload and DRAFT status.
Manager role is simulated, not authenticated production access.

Approvals do not create inventory reservations or add confirmed incoming stock. Revised/overlapping batches need manual reconciliation. No real orders are sent. All draft/approval tests use isolated databases.

## Optional AI briefing

Configure purchase_demo/.env using .env.example. Do not commit actual keys.
The **Generate AI briefing** button makes up to four direct HTTPS gateway calls via POST /api/chat and X-API-Key.
It uses a strict read_inventory → read_recommendations → check_budget → answer sequence.
Only computed SKU-level purchasing evidence is supplied. No approval, dispatch, arbitrary tool arguments or database writes are available to the model.
Python performs forecasting and optimisation independently of the model. The AI explains and inspects results; it does not compute the recommendations.
Live gateway compatibility is **not verified in this build**. Mocked tests cover sequence validation and credential-safe errors.

## Verification and evaluation

```powershell
.\.venv\Scripts\python.exe -m pytest purchase_demo\tests -q
.\.venv\Scripts\python.exe -m purchase_demo.evaluation
.\.venv\Scripts\python.exe -m purchase_demo.evaluation --data purchase_demo\sample_data
```

Evaluation uses a fixed-origin final-14-day holdout with at least 42 consecutive daily observations. Training excludes the holdout. Weekday, last-week and moving-average methods use the same split. Report MAE, MAPE (nonzero actuals) and WAPE; all-zero actuals have undefined WAPE.

Purchasing replay uses identical synthetic starting stock (five days of training mean), no incoming stock, one decision and lost-sales accounting. The reorder-point baseline buys when below seven days plus buffer and chooses the cheapest threshold-eligible supplier. It does not enforce daily coverage. Compare **cost and service together**; this is not an equal-service savings claim.

The app separately compares each feasible allocation with its cheapest feasible single-supplier alternative under the same constraints. If none exists, no savings are claimed.

The proposal's <5 minutes, <20% error, 7-day warning and 5–10% savings remain targets. Synthetic holdout measurements are not evidence of real operational outcomes. App calculation time is not human preparation time.

## Delivery status

Implemented: CSV validation; 12-product sample; UCI-format CSV preparation; catalogue analysis; product explanations; supplier comparison; shared-budget draft gate; stress lab; simulated manager review; preserved SQLite records; CSV/JSON downloads; offline evaluation; mocked gateway integration; automated UI workflow tests.

Not verified: live team gateway, deployment to AWS, actual UCI workbook processing, and browser screenshot/visual inspection (no browser automation surface was available in this session). Automated Streamlit tests exercise all six screens.

Before an external demo: try the actual gateway with the organiser's model and credentials, rehearse on the chosen cleaned data, and confirm the deployed environment's access restrictions. This prototype has simulated roles and must not be treated as production purchasing authorization.

All development changes are within purchase_demo/. The original single-product UI is preserved in single_product_reference.py. Root scripts are untouched.
