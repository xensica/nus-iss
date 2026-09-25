# Implementation Plan — Purchasing Agent

Authoritative scope: **CSV inputs, 10–15 products, three simulated approved suppliers,
forecasting, shortage detection, supplier splitting, PO drafts, simulated human approval,
and an evaluation plan** (metrics, fair baselines, held-out data; targets unverified until
measured). **StockPilot (`purchase_demo/`) is the starting app and stays in place**;
structural refactoring is **deferred**. All work is inside `purchase_demo/`.

Prioritisation: enabling foundations (CSV + multi-product) first because forecasting,
shortage detection, splitting, drafts, and evaluation all depend on them; then the
functional corrections; then evaluation; then approval workflow; then hygiene. Each
functional change ships with its targeted test.

- [ ] 1. Test harness
  - Add `pytest` to `purchase_demo/requirements.txt`; create `purchase_demo/tests/`.
  - _Requirements: supports all_

- [ ] 2. CSV ingestion foundation (`data_io.py`) — enables real data
- [ ] 2.1 Load and strictly validate sales/inventory CSVs
  - Documented schemas; reject malformed/missing-column/negative input with clear,
    non-sensitive errors; no partial ingestion; attach a `source` label.
  - _Requirements: 1.1, 1.2, 1.3, 1.5_
- [ ] 2.2 Multi-product simulated fallback + sample data
  - Extend the deterministic generator to 10–15 SKUs; commit `sample_data/sales.csv` and
    `sample_data/inventory.csv`; label simulated vs uploaded.
  - _Requirements: 1.4, 1.6, 2.1_
- [ ] 2.3 Tests
  - `tests/test_data_io.py`: valid load; each rejection path; source labelling; fallback
    yields 10–15 products.
  - _Requirements: 1.1, 1.3, 1.4_

- [ ] 3. Multi-product catalogue (`catalogue.py`) — enables 10–15 SKUs
- [ ] 3.1 Product/Catalogue model and per-product analysis
  - Represent 10–15 products; run forecast + plan per product keyed by `product_id`.
  - _Requirements: 2.1, 2.2_
- [ ] 3.2 Generalise `engine.forecast()`/`plan()` to a single product's records
  - Parameterise on a product's history/stock rather than global config (mechanical lift).
  - _Requirements: 2.2, 3.1, 4.1, 5.1, 6.1_
- [ ] 3.3 Product selector + catalogue overview in the UI
  - Select a product; catalogue-level table of forecast/shortage/quantity/plan status.
  - Use per-product supplier values where present, else state the shared A/B/C assumption.
  - _Requirements: 2.3, 2.4, 7.5_
- [ ] 3.4 Tests
  - `tests/test_plan.py`: multi-product solve completes within a reasonable time bound.
  - _Requirements: 2.5_

- [ ] 4. Functional correction C1 — zero net purchase still runs the shortage check
  - Always surface the per-product balance projection and shortage warning even when
    quantity is zero; distinct "timing shortage" message; skip only supplier selection.
  - `tests/test_forecast.py`: zero-quantity config with late incoming stock yields a
    shortage day.
  - _Requirements: 5.3, 5.2_

- [ ] 5. Functional correction C2 — distinguish single- vs split-supplier eligibility
  - Surface the whole-quantity single-supplier comparison (with exclusion reasons) beside
    the chosen split allocation, per product.
  - `tests/test_plan.py`: capacity-limited supplier excluded as sole source but valid in a
    split.
  - _Requirements: 7.2, 7.3, 7.4_

- [ ] 6. Functional correction C3 — solver disclosure matches code
  - State "1–2 suppliers, up to 2000 units, exact requested quantity"; test asserts match.
  - _Requirements: 8.4_

- [ ] 7. Sparse-history forecast fallback
  - When matching-weekday samples are too few, fall back to a recent overall mean; label it.
  - `tests/test_forecast.py`: fallback engaged and labelled for a short series.
  - _Requirements: 3.6_

- [ ] 8. Optional urgent/later overlay (R9)
  - `engine.plan(..., urgent_quantity=0, urgent_days=None)`; feasible plans must also
    deliver the urgent quantity by the urgent deadline when set; defaults reproduce today.
  - UI: off-by-default per-product option; caption that balance projection still enforces
    early coverage when unused.
  - `tests/test_plan.py`: urgent forces a faster supplier; omitting reproduces baseline.
  - _Requirements: 9.2, 9.3_

- [ ] 9. Evaluation plan (`evaluation.py`) — metrics, baselines, held-out data
- [ ] 9.1 Held-out split with no leakage
  - Train/test split per product; forecasts for the test window use training data only;
    fixed splits/seeds documented.
  - _Requirements: 10.1, 10.7_
- [ ] 9.2 Forecast metrics + fair baselines
  - MAE/MAPE/WAPE per product and aggregate; naïve and moving-average baselines run on the
    same split alongside the weekday-average method.
  - _Requirements: 10.2, 10.3_
- [ ] 9.3 Purchasing decision metrics
  - Replay plans against held-out actuals: simulated stockout days and total cost vs a
    reorder-point baseline; label simulated.
  - _Requirements: 10.4, 10.5_
- [ ] 9.4 Reproducible report; targets reported not asserted
  - Print a table of measured values with run date + dataset; a documented command
    regenerates deterministically; no numerical target hard-coded as achieved.
  - _Requirements: 10.6, 10.7_
- [ ] 9.5 Tests
  - `tests/test_evaluation.py`: no leakage; metric math on a fixture; baselines on same
    split; deterministic report; no target used as a pass/fail threshold.
  - _Requirements: 10.1, 10.2, 10.3, 10.6_

- [ ] 10. Clear forecast assumptions in the UI
  - Surface: weekly-pattern-only; annual seasonality NOT modelled and why; event uplift is
    an owner assumption (no internet search); assumed lead time behind reorder point;
    delivery days are estimates; accuracy only via the evaluation plan; keep source and
    simulated labels.
  - _Requirements: 3.4, 3.5, 4.3, 5.5, 7.4_

- [ ] 11. SQLite migration preserving records (R11.6)
  - `migrations.py`: additive, idempotent `ALTER TABLE ... ADD COLUMN reviewed_role`
    guarded by a column-exists check; run at connect; never drop/recreate.
  - `tests/test_store.py`: old-schema DB with rows → column added, rows preserved, role
    NULL; twice is a no-op.
  - _Requirements: 11.6_

- [ ] 12. Simulated manager review (R11.5)
  - Operator/Manager role selector labelled "Simulated role — not authentication"; Approve/
    Reject only in Manager mode; record `reviewed_role`; ensure multi-product drafts persist
    in the existing payload JSON.
  - `tests/test_store.py`: role gating; `reviewed_role` persisted; guarded review still
    rejects changed payload / non-draft.
  - _Requirements: 11.1, 11.5, 11.2, 11.3, 11.4_

- [ ] 13. Key/log hygiene verification (Cross-cutting B)
  - Confirm `.env` git-ignored and `.env.example` placeholders only; test the gateway error
    path asserts the API key never appears in surfaced output.
  - _Requirements: Constraints; Cross-cutting B.1, B.2, B.3_

---

## Deferred (FUTURE — not in this scope)

- Structural refactoring: shared `purchasing_core` package; move root scripts to `legacy/`;
  unify root `split_order_logic` with StockPilot's solver. _(Cross-cutting A.2)_
- Annual seasonality once multi-year history exists. _(R3.7)_
- Live, cited upcoming-events data source. _(R3.8)_
- Editable/manageable approved-supplier list. _(R7.6)_
- Quantified delivery-risk cost model. _(R9.4)_
- Authenticated, identity-bound manager authorization. _(R11.7)_
- Real order/email dispatch. _(excluded by constraints)_
