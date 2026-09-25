# Requirements — Purchasing Agent

## Introduction

This document defines requirements for an AI-assisted purchasing agent that helps a shop
decide, **across a small catalogue of products (10–15 SKUs)**, how much to buy, from which
of three approved suppliers, and when — then produces purchase-order (PO) drafts for a
human manager to approve in a clearly-simulated flow. Sales data enters via **CSV**.
Inference runs through the organiser-provided LLM gateway over a direct HTTP integration.
All arithmetic, constraint enforcement, and approval are performed by Python and humans —
never by the model.

This revision treats the following proposal as **authoritative scope**:

> CSV inputs, 10–15 products, three simulated approved suppliers, forecasting, shortage
> detection, supplier splitting, PO drafts, and simulated human approval — with an
> evaluation plan (defined metrics, fair baselines, held-out sales data). Numerical success
> targets are **unverified until measured**.

**Starting application.** StockPilot (`purchase_demo/`) remains the starting application.
All work lands inside `purchase_demo/`. Structural refactoring (shared packages, moving the
root scripts to `legacy/`) is **deferred**.

### Scope legend

- **[IMPLEMENTED]** — working and verified in the current code.
- **[PARTIAL]** — some of it exists; the requirement extends or corrects it.
- **[MISSING]** — not yet built; required by this scope.
- **[FUTURE]** — explicitly deferred beyond this scope.

> The current code (StockPilot) is **single-product, synthetic-history** based. Two of the
> headline scope items — **CSV inputs** and **10–15 products** — are therefore **[MISSING]
> or [PARTIAL]** across most requirements even where the single-product logic already
> exists. This is called out per requirement so implemented vs missing work is unambiguous.

### Technical constraints (apply to every requirement)

- Inference uses the organiser LLM gateway via `POST /api/chat` with an `X-API-Key` header,
  a **direct HTTP** integration; do **not** assume LangChain/LangGraph.
- API keys stay server-side, loaded from a git-ignored `.env`, never printed to logs, UI,
  exception bodies, or the model context.
- Use the platform only for inference, testing, and hosting. Do **not** train or fine-tune
  models. Keep usage economical within the ~USD 100 shared allocation.
- Simulated data and simulated approval/delivery are acceptable when **clearly labelled**.
  No real supplier orders or emails are ever sent.
- The model may orchestrate and summarise; Python performs all calculations and enforces all
  constraints. No tool can approve or send an order.

---

## Requirement 1 — Ingest current inventory and historical sales via CSV

**User story:** As a shop owner, I want to load current stock and recent sales history from
CSV files covering my whole catalogue, so that forecasts are grounded in my real figures.

#### Acceptance criteria

1. WHEN a sales CSV is provided THEN the system SHALL load per-product daily sales, with a
   documented schema (at least: `date`, `product_id`, `units`). **[MISSING — today
   `engine.history()` generates synthetic single-product data only]**
2. WHEN an inventory CSV is provided THEN the system SHALL load per-product current usable
   stock and confirmed incoming stock with arrival day. **[MISSING — today these are single
   scalar form inputs]**
3. WHEN a CSV is malformed, missing required columns, or contains invalid values THEN the
   system SHALL reject it with a clear, non-sensitive error and SHALL NOT partially ingest.
   **[MISSING]**
4. WHEN no CSV is supplied THEN the system SHALL fall back to clearly-labelled simulated
   data so the demo still runs. **[PARTIAL — synthetic generator exists; must become
   multi-product and be labelled as fallback]**
5. All ingested and simulated data SHALL be labelled by source (uploaded CSV vs simulated)
   wherever shown. **[PARTIAL — simulated labels exist; CSV-source labelling is MISSING]**
6. A sample CSV set (10–15 products) SHALL be provided for demos and tests. **[MISSING]**

---

## Requirement 2 — Support a catalogue of 10–15 products

**User story:** As a shop owner, I want the agent to handle my 10–15 products, so that I can
plan purchasing across the catalogue rather than one item at a time.

#### Acceptance criteria

1. The system SHALL represent a product catalogue of 10–15 SKUs, each with its own sales
   history, stock, incoming stock, and supplier availability. **[MISSING — code is
   hard-wired to a single "bottled coffee" product]**
2. WHEN an analysis is run THEN the system SHALL forecast, detect shortages, and recommend
   purchases **per product**. **[MISSING — single-product today]**
3. WHEN presenting results THEN the system SHALL let the user select a product and SHALL
   provide a catalogue-level overview (e.g. which products need purchasing / are at risk).
   **[MISSING]**
4. Supplier catalogues, MOQ, capacity, and price MAY differ per product; where per-product
   supplier data is unavailable THEN the system SHALL state the assumption used. **[MISSING
   — suppliers are currently product-agnostic constants]**
5. Performance SHALL remain acceptable for 10–15 products (the split solver is exhaustive;
   its per-product bounds must keep total runtime reasonable). **[PARTIAL — solver exists;
   multi-product cost not yet assessed]**

---

## Requirement 3 — Predict future demand

**User story:** As a shop owner, I want per-product demand forecasts that reflect recent
patterns and known upcoming events, so that purchase quantities match reality.

#### Acceptance criteria

1. WHEN forecasting THEN the system SHALL predict daily demand per product over a fixed
   horizon (14 days) using the average of recent matching **weekdays**. **[PARTIAL —
   implemented for one product; must generalise per product from CSV history]**
2. WHEN the owner sets a percentage adjustment THEN the system SHALL apply it to forecast
   days (globally or per product). **[PARTIAL — global single-product today]**
3. WHEN a simulated event window is configured THEN the system SHALL apply an explicit
   percentage uplift only to days inside that window. **[IMPLEMENTED — single product]**
4. The forecast SHALL document its assumptions in the UI: recent-weekday averaging; that
   event uplift is an owner assumption (not learned or internet-sourced); and that only
   **weekly** patterns are modelled — **annual seasonality is NOT modelled** because the
   history window is too short. **[PARTIAL — must be surfaced clearly and per the
   Forecasting Assumptions appendix]**
5. Forecast accuracy SHALL NOT be claimed as validated; measured accuracy comes only from
   the evaluation plan (Requirement 10). **[PARTIAL]**
6. WHEN a product has insufficient history for weekday averaging THEN the system SHALL
   degrade gracefully (e.g. fall back to an overall recent mean) and label the fallback.
   **[MISSING — real CSVs will have short/sparse series]**
7. WHEN sufficient multi-year history exists THEN the system SHALL model annual
   seasonality. **[FUTURE]**
8. WHEN event data is retrieved from a live source THEN the system SHALL cite it; no
   internet event search is connected in this scope. **[FUTURE]**

---

## Requirement 4 — Dynamically adjust restocking thresholds

**User story:** As a shop owner, I want per-product reorder thresholds that move with
expected demand, so I am not relying on stale fixed thresholds.

#### Acceptance criteria

1. WHEN the forecast changes THEN the system SHALL recompute a per-product reorder point
   from forecast demand over a lead-time window plus safety stock. **[PARTIAL — single
   product]**
2. WHEN the owner changes the safety buffer (days of average demand) THEN safety stock and
   reorder point SHALL update. **[IMPLEMENTED — single product]**
3. The reorder point SHALL be shown with the assumed lead time used to derive it.
   **[PARTIAL — must be labelled]**

---

## Requirement 5 — Detect stock shortages before they happen

**User story:** As a shop owner, I want early warning of per-product shortages that account
for delivery times and incoming stock, so I can act before running out.

#### Acceptance criteria

1. WHEN an analysis is run THEN the system SHALL project a day-by-day stock balance per
   product across the horizon, adding incoming stock on its arrival day and deducting daily
   demand. **[PARTIAL — single product]**
2. IF a projected balance goes negative on any day THEN the system SHALL report the first
   shortage day for that product. **[IMPLEMENTED — single product]**
3. WHEN the recommended purchase quantity is zero THEN the system SHALL STILL run the
   day-by-day projection before concluding no purchase is needed; it SHALL skip only
   **supplier selection**, not the shortage check. IF a timing-driven shortage exists
   (e.g. incoming stock arrives too late) THEN it SHALL be surfaced despite zero net
   quantity. **[MISSING — today a zero quantity short-circuits to "no purchase needed"]**
4. WHEN evaluating a plan THEN each supplier's delivery arrives at the start of its
   estimated delivery day and the plan SHALL keep every daily balance non-negative and end
   at or above final safety stock. **[IMPLEMENTED — single product]**
5. Delivery timing SHALL be labelled an estimate, not a guarantee. **[IMPLEMENTED]**

---

## Requirement 6 — Recommend purchase quantities with a safety buffer

**User story:** As a shop owner, I want per-product recommended purchase quantities with a
sensible safety buffer, so normal variation does not cause a stockout.

#### Acceptance criteria

1. WHEN forecasting THEN purchase quantity per product SHALL be
   `forecast demand + safety stock − current stock − incoming stock`, floored at zero and
   rounded up to whole units. **[PARTIAL — single product]**
2. Safety stock SHALL derive from the owner's buffer in days of average forecast demand.
   **[IMPLEMENTED — single product]**
3. IF a product's quantity is zero AND no shortage is projected THEN state no purchase is
   needed for it and skip supplier selection for that product only. **[PARTIAL — see R5.3
   for the zero-with-shortage case]**

---

## Requirement 7 — Compare three approved suppliers

**User story:** As a shop owner, I want the three approved suppliers compared on price,
delivery time, quality, and reliability, so I buy from the best-fitting source.

#### Acceptance criteria

1. The system SHALL use exactly **three simulated approved suppliers**, labelled simulated.
   **[IMPLEMENTED — A/B/C in `engine.py`]**
2. The system SHALL apply two distinct eligibility notions and NOT conflate them:
   - **Single-supplier eligibility:** a supplier can fill a product's **entire** quantity —
     quality/reliability pass, delivery ≤ deadline, capacity ≥ quantity, quantity ≥ MOQ.
     Excluded suppliers listed with reasons.
   - **Split-allocation eligibility:** a supplier qualifies for a **share** if
     quality/reliability pass and its **allocated** quantity is within `[MOQ, capacity]`
     and arrivals keep the daily balance feasible.
   **[PARTIAL — both notions exist in code (`compare_suppliers` vs `plan`) but must be
   named/surfaced distinctly, and applied per product]**
3. WHEN ranking eligible suppliers (single-supplier view) THEN order by total cost (units +
   one delivery fee), then delivery time. **[IMPLEMENTED]**
4. Supplier data SHALL be labelled simulated. **[IMPLEMENTED]**
5. WHERE supplier attributes differ per product THEN the system SHALL use per-product values
   or state the shared-assumption fallback. **[MISSING — suppliers are product-agnostic]**
6. An editable/manageable approved-supplier list. **[FUTURE]**

---

## Requirement 8 — Split orders between suppliers to reduce cost

**User story:** As a shop owner, I want the option to split a product's order across
suppliers when cheaper and still stockout-safe, so I lower cost without added risk.

#### Acceptance criteria

1. WHEN planning a product THEN the system SHALL evaluate single- and multi-supplier
   allocations and pick the cheapest **feasible** one, breaking ties by fewer shipments.
   **[IMPLEMENTED — StockPilot `plan()`, 1–2 suppliers, ≤2000u]**
2. WHEN a split plan is chosen THEN report its cost and the saving versus the cheapest
   feasible single-supplier plan; IF no single-supplier comparator exists THEN make no
   savings claim. **[IMPLEMENTED]**
3. IF no feasible plan exists THEN explain why and do NOT silently relax quality,
   reliability, quantity, or deadline requirements. **[IMPLEMENTED]**
4. The plan's search limits (supplier count, max quantity, exact-quantity assumption) SHALL
   be disclosed and SHALL match what the solver actually searches (1–2 suppliers, ≤2000
   units, exact requested quantity). **[PARTIAL — verify disclosure matches code]**

---

## Requirement 9 — Balance cost, quality, and delivery risk across deadlines

**User story:** As a shop owner, I want urgent stock from a faster/more reliable supplier
and later stock from a cheaper one, without overpaying for the whole order.

#### Acceptance criteria

1. The day-by-day balance check SHALL be the **primary** early-coverage mechanism: arrivals
   land on their estimated delivery day and every daily balance must stay non-negative, so
   faster suppliers are already forced to cover early demand. No extra input needed.
   **[IMPLEMENTED]**
2. Explicit urgent-quantity / urgent-deadline inputs SHALL be **optional**. Omitted → early
   coverage from the balance check alone. Supplied → additionally guarantee the urgent
   quantity arrives by the urgent deadline. **[MISSING — optional overlay to add]**
3. WHEN the urgent inputs are omitted THEN the UI SHALL state early coverage is still
   enforced by the balance projection. **[MISSING]**
4. A quantified delivery-risk cost model weighing reliability vs price. **[FUTURE]**

---

## Requirement 10 — Evaluation plan (metrics, baselines, held-out data)

**User story:** As a reviewer, I want the agent's forecasting and purchasing decisions
measured against fair baselines on held-out data, so that claimed benefits are evidenced
rather than asserted.

#### Acceptance criteria

1. The sales history SHALL be split into a **training window** and a **held-out test
   window**; forecasts SHALL be produced for the test window using only training data
   (no leakage). **[MISSING]**
2. Forecast accuracy SHALL be reported with defined metrics — at minimum **MAE** and
   **MAPE** (or WAPE where zeros make MAPE unstable) — computed per product and aggregated.
   **[MISSING]**
3. Forecasts SHALL be compared against **fair baselines**, at minimum:
   - a naïve last-value / last-week baseline, and
   - a moving-average baseline.
   The weekday-average method SHALL be reported alongside these, not in place of them.
   **[MISSING]**
4. Purchasing quality SHALL be evaluated on the held-out window with decision metrics —
   at minimum **simulated stockout days** and **total purchasing cost** — for the agent's
   plans versus a simple reorder-point baseline. **[MISSING]**
5. All metrics SHALL be computed on **simulated/CSV data only**; results SHALL be labelled
   as simulated and not generalised to real operations. **[MISSING]**
6. Numerical success targets (e.g. "X% MAPE", "Y% fewer stockouts") SHALL be treated as
   **unverified hypotheses until measured** by this plan; the spec SHALL NOT assert them as
   achieved, and the UI/report SHALL show measured values with their date and dataset.
   **[MISSING — this is a documentation + reporting rule]**
7. The evaluation SHALL be reproducible: fixed seeds/splits and a documented command or
   script to regenerate the numbers. **[MISSING]**

---

## Requirement 11 — Generate PO drafts for simulated manager approval; AI never approves

**User story:** As a manager, I want to review PO drafts and approve or reject them myself,
so no order proceeds without a human decision and the AI cannot approve on its own.

#### Acceptance criteria

1. WHEN ready plans exist THEN the system SHALL create PO drafts (spanning the affected
   products) with status `DRAFT` and persist them. **[PARTIAL — single-product batches
   today; must accommodate multiple products]**
2. Approval SHALL require an explicit human action (typed confirmation or checkbox +
   button); the model SHALL have no approval tool. **[IMPLEMENTED]**
3. WHEN approving THEN persisted order details SHALL match exactly what was shown at review;
   IF they differ THEN approval SHALL be rejected. **[IMPLEMENTED — payload-guarded UPDATE]**
4. Approval SHALL be labelled **simulated**; terminal status `APPROVED_SIMULATION` or
   `REJECTED`; nothing sent to any supplier. **[IMPLEMENTED]**
5. Drafts SHALL be presented to a **manager** role, distinct from the operator who generated
   them; a clearly-simulated role gate SHALL control the approve/reject controls. **[MISSING]**
6. WHEN the `reviewed_role` column is introduced THEN existing SQLite records SHALL be
   preserved via an additive, idempotent migration (`ALTER TABLE ... ADD COLUMN`, guarded by
   a column-exists check); pre-existing rows remain readable with `reviewed_role` NULL.
   **[MISSING]**
7. Authenticated, identity-bound production authorization. **[FUTURE]**

---

## Cross-cutting Requirement A — Starting application; refactoring deferred

#### Acceptance criteria

1. StockPilot (`purchase_demo/`) SHALL be the starting application and SHALL stay in place;
   all changes land inside `purchase_demo/`. **[decision]**
2. Structural refactoring (shared `purchasing_core` package; moving root scripts to
   `legacy/`; unifying the root `split_order_logic` with StockPilot's solver) is
   **DEFERRED**. **[FUTURE]**

---

## Cross-cutting Requirement B — Key and log hygiene

#### Acceptance criteria

1. `.env` files SHALL be git-ignored in every folder. **[IMPLEMENTED]**
2. WHEN the gateway errors THEN the system SHALL NOT include the API key or a raw exception
   body that could contain it in any surfaced message or log. **[PARTIAL — verify + test]**
3. A committed `.env.example` SHALL show variable names with placeholder values only.
   **[IMPLEMENTED — `purchase_demo/.env.example`]**

---

## Forecasting Assumptions (appendix)

- **Weekly pattern only.** Forecast = average of recent matching **weekdays** (recent
  window). Captures day-of-week rhythm.
- **No annual seasonality.** Short history (weeks, not years) cannot support month-of-year
  or holiday seasonality; it is out of scope (FUTURE) and the UI must say so, not imply a
  yearly model.
- **Events are assumptions, not evidence.** Event uplift is an owner-entered percentage on
  configured event days only; not learned, not from any internet search (none connected).
- **Owner adjustment** is a blanket percentage on forecast days.
- **Sparse products degrade gracefully** to a recent overall mean, labelled as a fallback.
- **Accuracy is unmeasured except via Requirement 10**, on held-out data, against fair
  baselines, and reported as simulated.
- **Deterministic** where synthetic data is used (fixed seed) for reproducible demos/tests.
