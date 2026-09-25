# Design — Purchasing Agent

## Overview

This design implements the authoritative scope: **CSV inputs, 10–15 products, three
simulated approved suppliers, forecasting, shortage detection, supplier splitting, PO drafts,
simulated human approval**, plus an **evaluation plan** with defined metrics, fair baselines,
and held-out data. Numerical success targets are treated as **unverified until measured**.

Decisions carried from the prior revision:

- **StockPilot (`purchase_demo/`) is the starting application and stays in place.** All work
  lands inside `purchase_demo/`.
- **Structural refactoring is deferred** (shared package, `legacy/` move, cross-project
  solver unification).

The two largest new dimensions are **CSV ingestion** and **multi-product (10–15 SKUs)**.
Both cut across forecasting, shortage detection, splitting, drafts, and evaluation, so the
design centres on a per-product data model that the existing single-product logic is lifted
into.

Nothing here is implemented yet.

---

## Implemented vs missing (grounded in the code)

| Capability | State | Where |
|---|---|---|
| Weekday-average forecast, 1 product | IMPLEMENTED | `engine.forecast()` |
| Reorder point, safety stock | IMPLEMENTED (1 product) | `engine.forecast()` |
| Day-by-day balance + shortage day | IMPLEMENTED (1 product) | `engine.forecast()`/`plan.assess` |
| Purchase quantity formula | IMPLEMENTED (1 product) | `engine.forecast()` |
| 3 simulated suppliers, compare + rank | IMPLEMENTED | `engine.SUPPLIERS`, `engine.plan()` |
| Split solver (1–2 suppliers, ≤2000u) | IMPLEMENTED | `engine.plan()` |
| Draft save / de-dup / guarded review / JSON export | IMPLEMENTED (1 product) | `demo_app.py` |
| Simulated approval status | IMPLEMENTED | `demo_app.py` |
| **CSV sales/inventory ingestion** | MISSING | — |
| **10–15 product catalogue** | MISSING | hard-wired single product |
| **Zero-qty timing-shortage surfacing** | MISSING (correction) | `demo_app.py` |
| **Named single- vs split-eligibility in UI** | PARTIAL | logic exists, labelling missing |
| **Optional urgent/deadline overlay** | MISSING | — |
| **Manager role gate + `reviewed_role` + migration** | MISSING | — |
| **Evaluation harness (metrics/baselines/held-out)** | MISSING | — |
| **Sparse-history forecast fallback** | MISSING | — |

---

## Files touched (all inside `purchase_demo/`)

```
purchase_demo/
├─ data_io.py       # NEW — CSV load/validate, source labelling, simulated fallback
├─ catalogue.py     # NEW — product catalogue model (10–15 SKUs), per-product records
├─ engine.py        # forecast()/plan() generalised to per-product; zero-qty fix;
│                   #   optional urgent overlay; sparse-history fallback
├─ demo_app.py      # product selector + catalogue overview; CSV upload; source labels;
│                   #   eligibility labelling; assumption captions; manager role gate
├─ migrations.py    # NEW — additive, idempotent SQLite migration (reviewed_role)
├─ evaluation.py    # NEW — held-out split, metrics, baselines, reproducible report
├─ sample_data/     # NEW — sample sales.csv & inventory.csv for 10–15 products
├─ .env.example     # unchanged
├─ requirements.txt # add pytest (pandas already present)
└─ tests/           # NEW — targeted tests
   ├─ test_data_io.py
   ├─ test_forecast.py
   ├─ test_plan.py
   ├─ test_store.py
   └─ test_evaluation.py
```

Root project files are **not** modified.

---

## CSV ingestion (`data_io.py`) — Requirement 1

### Schemas (documented, validated)

- **sales.csv:** `date` (ISO `YYYY-MM-DD`), `product_id` (string), `units` (non-negative
  integer). One row per product per day.
- **inventory.csv:** `product_id`, `current_stock` (non-negative int), `incoming_units`
  (non-negative int, default 0), `incoming_day` (1..horizon, required if `incoming_units`
  > 0).

### Behaviour

- `load_sales(path) -> dict[product_id -> list[day records]]` and `load_inventory(path)`,
  both **strictly validated**: required columns present, types coercible, dates parseable,
  values non-negative. On any violation, raise a `ValueError` with a **non-sensitive**
  message naming the offending column/row; **no partial ingestion** (validate fully, then
  commit). (R1.3)
- **Source labelling:** each dataset carries `source ∈ {"uploaded_csv", "simulated"}` so the
  UI can label every figure. (R1.5)
- **Fallback:** when no CSV is supplied, generate a clearly-labelled **multi-product**
  simulated dataset (extend today's deterministic generator to 10–15 SKUs with per-product
  base levels and weekday shape). (R1.4)
- **Sample set:** commit `sample_data/sales.csv` and `sample_data/inventory.csv` for 10–15
  products for demos and tests. (R1.6)

Uploads in Streamlit are read from the in-memory buffer; file contents are treated as
untrusted data (validated, never executed).

---

## Multi-product model (`catalogue.py`) — Requirement 2

- `Product`: `id`, `name`, `history` (daily records), `current_stock`, `incoming_units`,
  `incoming_day`, and optional per-product supplier overrides.
- `Catalogue`: 10–15 `Product`s; helpers to iterate, select one, and build a **catalogue
  overview** (per product: forecast total, shortage day if any, recommended quantity, plan
  status). (R2.3)
- Analysis runs **per product**: `forecast()` and `plan()` are called for each SKU; results
  keyed by `product_id`. (R2.2)
- **Suppliers stay three and simulated.** If per-product supplier attributes are provided
  they are used; otherwise the shared A/B/C values are used and the **shared-assumption
  fallback is stated** in the UI. (R2.4, R7.5)
- **Performance:** the split solver is exhaustive; per-product quantity is bounded (≤2000u)
  and only 3 suppliers, so 10–15 sequential solves are expected to stay well within
  interactive time. This is asserted, not assumed — a timing check is part of testing. (R2.5)

The existing single-product functions are generalised by parameterising them on a product's
records/stock rather than global config — a mechanical lift, not a rewrite.

---

## Functional corrections (carried forward)

- **C1 — zero net purchase still runs the shortage check (R5.3).** Always evaluate and
  surface the per-product day-by-day projection even when quantity is zero; only supplier
  selection is skipped. Distinct "timing shortage" message when quantity is zero but a
  shortage day exists (e.g. incoming stock arrives too late). Test locks it in.
- **C2 — single- vs split-eligibility named in the UI (R7.2).** Present the whole-quantity
  single-supplier comparison (with exclusion reasons) alongside the chosen split allocation,
  per product, so a supplier excluded as a sole source is visibly still available for a
  share.
- **C3 — solver disclosure matches code (R8.4).** State "1–2 suppliers, up to 2000 units,
  exact requested quantity."

## Optional urgent/later overlay (R9)

`plan(..., urgent_quantity=0, urgent_days=None)`: when set, feasible allocations must also
deliver at least `urgent_quantity` from suppliers with `days <= urgent_days`, on top of the
daily-balance feasibility. Defaults reproduce today's behaviour. UI exposes it as an
off-by-default per-product option, with a caption that early coverage is enforced by the
balance projection when the overlay is unused.

## Sparse-history fallback (R3.6)

When a product has too few matching-weekday samples, fall back to a recent overall mean and
label the forecast as using a fallback method. Prevents CSV products with short series from
producing empty or divide-by-zero forecasts.

---

## Evaluation plan (`evaluation.py`) — Requirement 10

The evaluation is a **reproducible offline harness** over simulated/CSV data. It never calls
the gateway and never touches the live app DB.

### Data split (no leakage)

- Split each product's series into a **training window** (earlier days) and a **held-out
  test window** (most recent K days, e.g. 14). Forecasts for the test window use **only**
  training data. Split points and any seed are fixed and documented. (R10.1, R10.7)

### Forecast metrics

- Per product and aggregated: **MAE** and **MAPE**; use **WAPE** where zero-demand days make
  MAPE unstable. Report all three where relevant. (R10.2)

### Fair baselines (reported alongside, not replaced)

- **Naïve** — last value / same weekday last week.
- **Moving average** — trailing mean over a fixed window.
- **Weekday-average** — the app's method.
  All three run on the identical split so the comparison is fair. (R10.3)

### Purchasing/decision metrics

- Replay each method's recommended plan against the held-out actuals and compute:
  **simulated stockout days** and **total purchasing cost**, versus a **simple
  reorder-point baseline**. Labelled simulated. (R10.4, R10.5)

### Reporting and honesty about targets

- Output a table of measured values with the **run date** and **dataset name**.
- The spec and UI/report **do not assert** numerical targets (e.g. "20% fewer stockouts");
  any such target is a **hypothesis until this harness measures it**, and only measured
  numbers with their provenance are shown. (R10.6)
- A documented command (e.g. `python -m purchase_demo.evaluation --data sample_data`)
  regenerates the numbers deterministically. (R10.7)

---

## SQLite migration for `reviewed_role` (R11.6)

Current schema:

```
batches (id TEXT PRIMARY KEY, fingerprint TEXT UNIQUE, status TEXT, payload TEXT, reviewed_at TEXT)
```

`migrations.py`, run at connect time:

1. `CREATE TABLE IF NOT EXISTS` (unchanged).
2. `PRAGMA table_info(batches)`; if `reviewed_role` absent, `ALTER TABLE batches ADD COLUMN
   reviewed_role TEXT` (nullable, default NULL).
3. Idempotent (column-exists guard); never drops/recreates; existing rows preserved and read
   back with `reviewed_role` NULL.

Multi-product drafts are stored in the existing `payload` JSON (now spanning products); no
schema change needed beyond `reviewed_role`.

---

## Simulated manager review (R11.5)

Operator/Manager role selector, labelled "Simulated role — not authentication." Approve/
Reject controls render only in Manager mode; Operator sees a "manager must approve" note.
The approving role + timestamp are written to `reviewed_role`/`reviewed_at`. The model
context has no approval tool, so the AI cannot flip status regardless of role.

---

## LLM gateway integration (unchanged posture)

Direct `requests.post` to `POST {LLM_GATEWAY_URL}/api/chat` with `X-API-Key`; no LangChain.
The model orchestrates and summarises; Python computes everything; no approve/send tool.
Failures degrade to labelled messages and never expose the key. Live loop bounded (≤6 steps,
capped `num_predict`); simulation mode makes no calls; evaluation makes no calls.

### Forecasting assumptions

Per the requirements appendix: weekly pattern only; annual seasonality explicitly NOT
modelled (history too short) and said so in the UI; events are owner assumptions with no
internet search; owner adjustment is a blanket percentage; sparse products fall back to a
recent mean (labelled); accuracy is unmeasured except via Requirement 10; synthetic data is
deterministic.

---

## Error handling

- `ValueError` (including CSV validation) surfaces its non-sensitive message.
- Other exceptions surface a generic message, never the body (no credential/PII leak).
- Review uses a payload-guarded conditional UPDATE; zero rows → batch changed → ask refresh.

---

## Testing strategy (targeted)

No live gateway calls anywhere in the suite.

- **`test_data_io.py`** — valid CSV loads per product; malformed/missing-column/negative
  values rejected with clear errors and no partial ingestion; source labelling; simulated
  fallback produces 10–15 products.
- **`test_forecast.py`** — weekday averaging golden values; owner adjustment/event uplift
  applied to correct days; **zero-quantity timing shortage** yields a shortage day (C1);
  reorder point recomputes on demand change; **sparse-history fallback** engaged and labelled.
- **`test_plan.py`** — single vs split selection; tie-break fewer shipments; savings vs
  cheapest single; `blocked` with no silent relaxation; disclosed limits match (C3);
  **single- vs split-eligibility** (capacity-limited supplier excluded as sole source but
  usable in a split, C2); optional urgent overlay forces a faster supplier; multi-product
  solve completes within a reasonable time bound (R2.5).
- **`test_store.py`** — save→load round trip; de-dup; guarded review rejects changed payload
  and non-draft; **migration** adds column, preserves old rows, NULL role, idempotent;
  `reviewed_role` recorded; role gating; **gateway error path never emits the key**.
- **`test_evaluation.py`** — train/test split has no leakage (test window excluded from
  training); MAE/MAPE/WAPE computed correctly on a tiny fixture; baselines run on the same
  split; stockout-day/cost decision metrics computed; report is deterministic across runs;
  no numerical target is hard-coded as a pass/fail threshold (targets are reported, not
  asserted).
