# StockPilot

A simple purchasing workspace: choose your store, review what needs restocking,
and save an order for human review. The sample is an illustrative tea shop near
Marina Bay Sands, inspired by CHAGEE; sales, stock and supplier terms are simulated.

## Run the current app

Install **Node.js 20+** (with npm) and **Python 3.10+** (3.12/3.13 recommended).
From this repository's root ? the folder containing `package.json` ? run:

```bash
npm start
```

Open **http://localhost:8504**. First launch creates a Python virtual environment
and installs dependencies; it needs internet and may take a few minutes. Later
launches reuse it. No `npm install`, manual venv activation or API key is required.
Press Ctrl+C to stop. If another app already uses port 8504, stop that process or
set `PORT` before starting (PowerShell: `$env:PORT=8505`; bash: `PORT=8505 npm start`).

On Ubuntu, install `python3-venv` if Python reports that ensurepip is unavailable.
Node/npm must also be installed. `npm run setup` retries dependency installation.
`STOCKPILOT_PYTHON` can select a Python executable when creating a new environment.

## Use it

1. Choose **Explore the sample store** or **Set up my store**.
2. In **Store**, search a mall/address or click the map. Name the pin and select
   **Use this store location**. The circle shows the nearby-event radius.
3. Upload daily sales and current stock, or use the sample. Adjust the budget and
   select **Save & see my plan**.
4. In **Today**, see on-hand/incoming stock beside each recommendation. Open
   **Details** for the 14-day demand, safety stock and estimated delivery dates. Check nearby
   events and preview an assumed demand change before applying it.
5. Select **Review this order** to save a draft and go directly to **Orders**.
   The sidebar's simulated Manager role can review and export it.

Maps use OpenStreetMap, with no Google API key. Map tiles/address lookup need internet;
manual coordinates remain available. Event coverage currently includes **Esplanade
listings only**; proximity does not establish attendance or sales uplift. Saved drafts
persist in SQLite. Store settings and uploads are session-based. No real supplier
orders are sent, and review roles are simulated rather than authenticated accounts.

## Lightsail

After the updated code is present on the server, run these from the repository root:

```bash
npm run setup
npm run start:server
```

`start:server` listens on `0.0.0.0:8504`. Allow inbound TCP 8504 in Lightsail to access
`http://YOUR_PUBLIC_IP:8504`. Stop the existing Streamlit process before starting a
replacement on the same port. For the existing instance the URL is
http://47.129.185.138:8504. Local changes do not automatically update that server.

For a demo that stays running after SSH disconnects:

```bash
nohup npm run start:server > stockpilot.log 2>&1 < /dev/null &
```

This is a demo launch, not a reboot-persistent service. Public operational use requires
HTTPS, authentication and isolated records.

## Code map

There is one active app: `purchase-order-agent/purchase_demo`.
`npm start` always launches `purchase-order-agent/purchase_demo/demo_app.py`.

| File / folder | Purpose |
| --- | --- |
| `package.json`, `scripts/stockpilot.mjs` | One-command setup, start and tests |
| `purchase_demo/demo_app.py` | Welcome, Today, Orders and Evidence screens |
| `purchase_demo/ui_store.py` | Store profile, data upload and planning settings |
| `purchase_demo/ui_location.py` | Search, map preview and explicit pin confirmation |
| `purchase_demo/ui_state.py` | Shared session updates and recalculation |
| `purchase_demo/ui_details.py` | Product details and event-scenario dialogs |
| `purchase_demo/engine.py`, `catalogue.py` | Forecasts and supplier allocation |
| `purchase_demo/local_context.py` | Address lookup and nearby event sources |
| `purchase_demo/storage.py` | Saved drafts and simulated review |
| `purchase_demo/tests/` | Calculation and user-flow regressions |

Older prototype scripts and duplicate app copies are preserved in `.archive/` for
recovery only. That folder is ignored by Git and is not used by the launcher.
The leftover `github-nus-iss` folder contains protected Git/test metadata only; it
has no application entry point. Use this repository root for all current work.

## Validate

```bash
npm test
```

This covers calculations, imports, saving settings, map confirmation, event assumptions,
draft creation and simulated approval. Browser rendering still needs a separate visual
check; automated Streamlit tests do not exercise real map tiles or mouse interactions.

See [the app guide](purchase-order-agent/purchase_demo/README.md) for CSV schemas,
calculation assumptions, optional AI setup and source limitations. Keep `.env`, keys,
virtual environments, logs and local databases out of Git.
