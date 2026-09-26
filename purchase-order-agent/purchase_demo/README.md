# StockPilot - your next restock, explained

A guided purchasing workspace for the NUS-ISS Purchase Order Preparation problem.
The first-use example is an illustrative tea-and-snacks shop near Marina Bay Sands,
inspired by the user's CHAGEE example. No affiliation, actual menu, store sales,
ingredient recipe or measured CHAGEE demand is implied. All sample sales and stock
are synthetic; supplier terms and manager roles remain simulated.

## Start locally

From the repository root (the folder containing `package.json`):

```bash
npm start
```

Requires Node.js 20+ and Python 3.10+. First launch installs Python dependencies in
an isolated virtual environment; later launches reuse it. Open http://localhost:8504.
No API key is needed. `npm run setup` installs/repairs dependencies, `npm test` runs
regressions, and `npm run start:server` binds to all interfaces for a Lightsail demo.
See the repository README for server and port instructions. The Python entry point
remains `purchase_demo/demo_app.py`; earlier prototype entry points are archived and are not part of the active app.

The single active source is `purchase-order-agent/purchase_demo`. Older duplicate folders
are recovery backups in `.archive/` and are never launched.

Store setup is in `ui_store.py`, map selection in `ui_location.py`, shared session
updates in `ui_state.py`, and product/event dialogs in `ui_details.py`.

### Choose a location

In Store, search an address and choose **Show this place on the map**, or click the
map directly. A green marker and radius circle preview the proposed point. Name the
location, then press **Use this store location** to commit it. Clicking alone does not
change the saved location or event scenario. Confirmation clears the old event scenario.
The map uses [streamlit-folium](https://github.com/randyzwitch/streamlit-folium) with
OpenStreetMap tiles; no Google API key is required. Map tiles and search need internet.
Use the coordinates fallback if tiles cannot load. The map area is limited to Singapore.

## A simpler workflow

1. **Welcome:** explore the tea-shop sample, or set up your store and upload data.
2. **Today:** three summary numbers, a prioritised list (six rows by default),
   local event context and one order-review action. The sidebar stays accessible.
3. **Details:** inspect shipments, assumptions, comparisons and stress tests in a
   dialog without navigating away. Update a product or add/remove it from the order.
4. **Nearby events:** check public listings, preview a demand scenario and explicitly
   apply it. Base/scenario quantities and purchasing costs appear together.
5. **Review this order:** persist a deduplicated draft and open it immediately.
   The simulated Manager must confirm review before approval. Export CSV/JSON.
6. **Store / Evidence:** settings and deeper validation are secondary destinations.

Data, profile, location and active scenarios live in the browser's Streamlit session;
they are not a permanent user account. Saved drafts persist in SQLite. No real orders
or emails are sent. Approval does not reserve stock or add confirmed incoming stock.
Overlapping batches require manual reconciliation.

## Local context: online facts, explicit assumptions

- `local_context.py` looks up a user-submitted public Singapore address using
  [Photon](https://github.com/komoot/photon), based on OpenStreetMap data (ODbL).
  The user chooses the matching result. No background lookup or autocomplete runs.
  Calls are serialized, throttled to at most one per 1.1 seconds per process and
  cached for 24 hours. The public Photon demo service has no availability guarantee;
  use your own endpoint for larger deployments (`STOCKPILOT_GEOCODER_URL`).
- The default 2 km radius uses Haversine straight-line distance, not walking routes.
  The sample point is illustrative; confirm the actual storefront for real data.
- Events are extracted from the **public Esplanade programme pages only**:
  https://www.esplanade.com/whats-on. The root and up to three relevant festival
  pages are checked; dates are interpreted in Singapore time, deduplicated and
  filtered for the upcoming 14 days. Results are cached for 30 minutes. Venue distance
  refers to the approximate Esplanade complex; exact venues/showtimes must be checked.
  School-only and explicitly online cards are excluded.
- This is **not comprehensive Singapore event discovery**: MBS, Suntec, other malls,
  private events and unlisted programmes are not covered. Outside-coverage, failed,
  partial and successful-empty lookups are distinguished in the UI. No invented
  events or stale fallback records are injected when a source fails.
- A listing is not attendance, footfall or a learned sales effect. The user chooses
  the affected products, dates and uplift; the dialog previews the cost/quantity
  change before applying it. No model infers sales uplift from distance.
- Applying a scenario replaces the previous nearby-event scenario. Its source URL,
  dates and user assumption are preserved in product overrides, the saved draft and
  optional AI evidence. Changing the location, radius or inventory date clears it.
  Other product adjustments remain. Remove the scenario to restore the base settings.
- Public pages can change schema. A production integration should use a supported,
  licensed feed and broader venue coverage; no guarantee of complete listings is made.

## Data and calculations

Sales: `date,product_id,units`. Inventory requires `product_id,current_stock`; optional
columns are `incoming_units,incoming_day,name,category,unit_price_cents`. Use UTF-8,
ISO dates, nonnegative whole units and one sales row/product/date. Up to 15 products,
100,000 rows and 10 MB per uploaded daily CSV. Both files must have the same IDs.
Invalid imports do not replace the active dataset. The operator explicitly sets the
inventory snapshot date. Missing daily observations are unknown, not automatically zero.

Forecasts use recent matching weekdays in 28 calendar days for a 14-day horizon.
Sparse series use a labelled recent-mean fallback; stale history blocks planning.
Owner adjustments and event effects are explicit assumptions, with Decimal percentage
arithmetic and ceiling to whole units. Safety stock is buffer days times mean demand;
reorder point is seven forecast days plus safety. Net quantity subtracts on-hand and
incoming stock, floored at zero. Zero quantity still checks delivery timing.

Three simulated suppliers have price multipliers 1.0 / 0.8 / 0.9, plus delivery fees,
MOQs, capacities, quality and on-time thresholds. Search is exact quantity, one or two
suppliers, at most 2,000 units/product. Every daily balance must remain nonnegative and
final stock meet the safety buffer. Urgent units/deadlines are additional constraints.
Supplier comparisons now pass those urgent constraints too. Drafting enforces the
selected products' shared budget. No cross-product freight or shared-capacity solver
is included. Delivery estimates and supplier scores are not probabilities.

Stress tests replay the same order with higher demand and late new deliveries; already
incoming stock keeps its date. Compare savings only with a feasible single-supplier
alternative under the same conditions. Blocked costs do not represent a fulfilled plan.

## Optional briefing and approval

Configure `.env` from `.env.example`; never commit keys. `gateway.py` performs at most
four HTTPS `POST /api/chat` calls with `X-API-Key`, enforcing
`read_inventory -> read_recommendations -> check_budget -> answer`. Only computed
SKU evidence and the applied event assumption are supplied. The model cannot approve,
write or dispatch. Invalid sequences produce a credential-safe error and leave the
calculated plan available. Live organiser-gateway compatibility remains unverified.

`storage.py` retains SQLite records and guards review using the exact saved payload,
DRAFT status and simulated Manager role. `migrations.py` is additive/idempotent.
Roles are not authenticated, and a shared database is not tenant-isolated.

## Validation

```powershell
.\.venv\Scripts\python.exe -m pytest purchase_demo/tests -q -p no:cacheprovider
.\.venv\Scripts\python.exe -m purchase_demo.evaluation
```

Tests cover the welcome-to-draft-to-approval journey, in-place product review,
event preview versus confirmed application, source/date/radius filtering, graceful
network failure, calculation boundaries, budget gates, imports and persistence.
Settings-save regressions exercise changed values and repeat navigation. Map tests check
preview-before-confirmation and radius construction; actual browser interaction is separate.
The old percentage rounding, urgent comparison and misleading zero-quantity error
findings are corrected with regression tests. Browser visual review is separate
from Streamlit AppTest; no browser surface was available during this redesign.

Evaluation holds out the final 14 days with at least 42 consecutive daily observations.
Weekday, last-week and moving-average methods share the split. Report MAE, nonzero
MAPE and WAPE. Purchasing replay uses five days of synthetic starting stock, no incoming
stock, one order and lost-sales accounting. The reorder-point baseline does not enforce
daily coverage; report cost and service together. Synthetic results do not prove
operational accuracy, preparation-time reductions or purchasing savings.

The UCI CSV importer remains available in Store. It excludes cancellations, invalid
records and quantities above an explicit cap, never retains CustomerID, requires the
user to confirm ledger completeness, and labels simulated stock and SGD purchase
prices. It does not download or validate the original UCI workbook. Source recorded
in the project: Chen, D. (2015), Online Retail, https://doi.org/10.24432/C5BW33.

Design references: [Shopify inventory workflows](https://help.shopify.com/en/manual/products/inventory)
and [Linear's sidebar and simpler hierarchy](https://linear.app/changelog/2024-03-20-new-linear-ui).
This is an original Streamlit interface, not a reproduction of either product.
