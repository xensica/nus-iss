# StockPilot local example

Extract this folder alongside your existing project. It is independent and does not overwrite existing code or purchase_orders.db.

From your existing project terminal, after copying the folder `purchase_demo` into it:

```powershell
.\.venv\Scripts\python.exe -m pip install -r purchase_demo\requirements.txt
.\.venv\Scripts\python.exe -m streamlit run purchase_demo\demo_app.py --server.address 127.0.0.1 --server.port 8502
```

Open http://localhost:8502. Run defaults, then inspect Recommendation. Return to Store & scenario, select the concert scenario and rerun. Change budget to 100 for a blocked-budget case, or current stock to 0 for a shortage before the earliest delivery. Save a ready recommendation, review its actual rows and approve in simulation. Restart to check persistence.

## Optional live agent

Copy your existing private `.env` into this folder, beside demo_app.py. No key is bundled. Enable Live AI. Gateway code uses POST /api/chat with X-API-Key, based on the organiser's starter kit. Up to 6 calls per analysis. It chooses read_store, forecast_demand and plan_purchase in a validated order; Python performs all arithmetic and enforces constraints. Credentials stay on the Python server. It has no approve/send tool. Gateway service was not live-tested during packaging; simulation mode needs no key.

## What is real and what is simulated

- Working UI, calculations, optional model tool loop, draft persistence, explicit review and JSON download.
- Synthetic 84-day sales history regenerated deterministically relative to the simulation date. Single product only.
- Forecast: mean of the last four matching weekdays, owner percentage change, explicit event percentage uplift. Not an ML model trained on actual shop data; accuracy has not been measured.
- Event location is contextual text, not geocoded. No internet search or real concerts. Assumed uplift is not causal evidence. No annual seasonality with only 84 days of history.
- Three synthetic suppliers. Quality/reliability are minimum eligibility filters; delivery uncertainty is not quantified.
- Solver compares single suppliers and pairs, exact quantity up to 2,000, one shipping fee per supplier, availability, MOQ, daily demand coverage and final safety buffer. It does not find every possible three-supplier or MOQ-overordering plan. A blocked result means no feasible plan in this restricted search.
- Incoming quantities arrive at the beginning of the chosen day. Negative earlier balances cannot be fixed by later deliveries. No inventory reservations, expiration, tax or lead-time distribution.
- SQLite records survive restarts in this folder. Approval is local and simulated, not authenticated production authorization. Identical plans are deduplicated, but overlapping/revised purchasing needs are not reconciled. Approved simulations do not update incoming inventory. Do not use as a live ordering system.
- Settings are snapshots: changing form values requires Run analysis before a new plan is used. No automatic scheduling yet.

No connection to your existing project's database. Keep .env and database files out of git. No orders, emails or supplier messages are sent.
