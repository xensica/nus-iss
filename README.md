# StockPilot — NUS-ISS Purchase Order Preparation

The current application is in [`NUS-ISS/purchase-order-agent/purchase_demo`](NUS-ISS/purchase-order-agent/purchase_demo).
Root-level purchasing scripts inside the project are the earlier prototype.

## Included

- Purchasing control room with a 14-day stock coverage map and decision queue.
- Twelve-product sample, validated sales/inventory CSV uploads and UCI-format transaction preparation.
- Forecasting, supplier splitting, budget checks, shipment cards and a disruption lab.
- Simulated manager review, purchase-order exports and persistent local SQLite records.
- Offline evaluation and optional organiser-gateway AI briefings.

## Windows quick start

```powershell
cd NUS-ISS\purchase-order-agent
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r purchase_demo\requirements.txt
.\purchase_demo\Start-StockPilot.ps1
```

Open http://127.0.0.1:8504.

## Ubuntu / Lightsail local preview

```bash
cd NUS-ISS/purchase-order-agent
python3 -m venv .venv
.venv/bin/pip install -r purchase_demo/requirements.txt
.venv/bin/python -m streamlit run purchase_demo/demo_app.py \
  --server.address 127.0.0.1 --server.port 8504 --server.headless true \
  --browser.gatherUsageStats false --theme.base light \
  --theme.primaryColor '#e95827' --theme.backgroundColor '#f5f4ee' \
  --theme.secondaryBackgroundColor '#fffefa' --theme.textColor '#22231f'
```

This binds to the server's loopback address. Access a remote instance through an SSH tunnel;
public hosting needs separate HTTPS, access-control and startup-service configuration.

## Verification and current limitations

From the project directory, run `python -m pytest purchase_demo/tests -q` with your virtual environment activated.
The latest local suite contains 31 passing tests. It does not establish complete mathematical correctness.

Known audit findings remain open: percentage rounding can overstate demand; the supplier comparison
may omit an optional urgent deadline; one zero-quantity conflict message can be misleading.
The redesign did not change those algorithms. Approval and supplier records are simulated, and no real
orders or emails are sent. Live gateway connectivity, actual UCI workbook validation and AWS deployment
have not been verified in this build.

See the [application guide](NUS-ISS/purchase-order-agent/purchase_demo/README.md) for the demo walkthrough,
CSV schemas, forecasting assumptions, evaluation method and gateway setup.

API keys, local databases, Python caches and virtual environments are excluded from new commits.
Previously committed generated files remain in Git history; no history rewrite was performed.
