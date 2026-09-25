import sys, json
from pathlib import Path
sys.path.insert(0, 'C:/NUS-ISS/tmp/pdfdeps')
from xml.sax.saxutils import escape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, Preformatted, Flowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
ROOT=Path('C:/NUS-ISS')
OUT=ROOT/'output/pdf/SMYA_YBQYZYHP_StockPilot_Technical_Document.pdf'
INK=colors.HexColor('#22231F'); ACC=colors.HexColor('#D94F20'); MUTED=colors.HexColor('#62665F'); PALE=colors.HexColor('#F5F4EE'); RULE=colors.HexColor('#DDDFD6')
styles=getSampleStyleSheet()
for name,size,leading,font,color,after in [
    ('Hero',30,34,'Helvetica-Bold',INK,10),('Title',21,25,'Helvetica-Bold',INK,14),
    ('Label',9,12,'Helvetica-Bold',ACC,8),('Copy',9.6,13.6,'Helvetica',INK,8),
    ('Sub',11.3,15,'Helvetica-Bold',INK,5),('Small',8.1,11,'Helvetica',MUTED,6),
    ('Cell',8.7,12,'Helvetica',INK,0),('Head',8.5,11.5,'Helvetica-Bold',colors.white,0),
    ('Mono',8,11,'Courier',INK,8)]:
    if name in styles: name='Tech'+name
    styles.add(ParagraphStyle(name=name,fontName=font,fontSize=size,leading=leading,textColor=color,spaceAfter=after))
story=[]
def p(t,s='Copy'): return Paragraph(t,styles[s if s!='Title' else 'TechTitle'])
def add(t,s='Copy'): story.append(p(t,s))
def sub(t,b): story.extend([Spacer(1,5),KeepTogether([p(t,'Sub'),p(b)])])
def code(t):
    box=Table([[Preformatted(t,styles['Mono'])]],colWidths=[498])
    box.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),PALE),('BOX',(0,0),(-1,-1),.4,RULE),('LEFTPADDING',(0,0),(-1,-1),12),('TOPPADDING',(0,0),(-1,-1),10),('BOTTOMPADDING',(0,0),(-1,-1),3)]))
    story.extend([box,Spacer(1,9)])
def table(headers,rows,widths):
    t=Table([[p(c,'Head') for c in headers]]+[[p(str(c),'Cell') for c in row] for row in rows],colWidths=widths,repeatRows=1,hAlign='LEFT')
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),INK),('ROWBACKGROUNDS',(0,1),(-1,-1),[PALE,colors.white]),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),9),('RIGHTPADDING',(0,0),(-1,-1),9),('TOPPADDING',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),8),('LINEBELOW',(0,1),(-1,-1),.4,RULE)]))
    story.extend([t,Spacer(1,9)])
def page(n,title): story.append(PageBreak()); add(n,'Label'); add(title,'Title')

class Architecture(Flowable):
    def __init__(self): super().__init__(); self.width=498; self.height=170
    def draw(self):
        c=self.canv
        def box(x,y,w,title,lines):
            c.setFillColor(PALE); c.setStrokeColor(RULE); c.roundRect(x,y,w,49,5,fill=1,stroke=1)
            c.setFillColor(INK); c.setFont('Helvetica-Bold',9); c.drawCentredString(x+w/2,y+33,title)
            c.setFont('Helvetica',8)
            for i,line in enumerate(lines): c.drawCentredString(x+w/2,y+20-i*11,line)
        def arrow(x1,y1,x2,y2):
            c.setStrokeColor(ACC); c.setFillColor(ACC); c.setLineWidth(1.2); c.line(x1,y1,x2,y2)
            if y1==y2: c.line(x2,y2,x2-5,y2+3); c.line(x2,y2,x2-5,y2-3)
            else: c.line(x2,y2,x2-3,y2+5); c.line(x2,y2,x2+3,y2+5)
        box(0,107,142,'Sales + stock CSVs',['Validated daily records'])
        box(177,107,144,'Python planning',['Forecast + allocation'])
        box(356,107,142,'Streamlit workspace',['Evidence + human review'])
        arrow(142,131,177,131); arrow(321,131,356,131)
        box(177,19,144,'Optional LLM gateway',['Read-only briefing','HTTPS /api/chat'])
        box(356,19,142,'SQLite + exports',['Draft and review record','CSV / JSON'])
        arrow(249,107,249,68); arrow(427,107,427,68)
        c.setFillColor(MUTED); c.setFont('Helvetica',7.8)
        c.drawCentredString(90,38,'No supplier dispatch')
        c.drawCentredString(90,26,'No autonomous approval')

add('TECHNICAL DOCUMENT / TEAM YBQYZYHP','Label')
add('StockPilot','Hero')
add('Purchasing intelligence, explained.','Title')
add('<b>Team Skibidi Slicers</b> | NUS-ISS Show Me Your Agent Hackathon<br/>Chia Chong En | Mohd Arif Fiqry Bin Mohd Suffian<br/>Tan Kai Hao Gerald | Trevis Tan','Small')
add('25 September 2026 | Repository: <link href="https://github.com/xensica/nus-iss" color="#D94F20">github.com/xensica/nus-iss</link>','Small')
add('01 / SYSTEM OVERVIEW','Label')
add('StockPilot prepares explainable purchase recommendations across a small retail catalogue. The current application is <b>NUS-ISS/purchase-order-agent/purchase_demo/</b> in the repository. It supports up to 15 imported products, a 12-product sample and three simulated suppliers. Calculations and state changes are deterministic application logic; optional AI explains existing evidence.')
story.append(Architecture())
table(['Module(s), relative to purchase_demo/','Responsibility'],[
    ['demo_app.py / visuals.py','Six-screen Streamlit interface, charts, review controls and escaped HTML components.'],
    ['data_io.py / uci_import.py','CSV validation, catalogue assembly, sample data and transaction preparation.'],
    ['engine.py / catalogue.py','Forecasting, supplier allocation, catalogue budget totals and stress replay.'],
    ['gateway.py','Bounded, read-only AI briefing over the organiser gateway.'],
    ['storage.py / migrations.py','SQLite draft deduplication and guarded simulated review.'],
    ['evaluation.py / tests/','Held-out forecast evaluation, purchasing replay and automated checks.']
],[224,274])
add('Scope: Control room, Sourcing desk, Disruption lab, Order review, Data studio and Evidence. Root purchasing scripts and single_product_reference.py are earlier prototypes, not the current entry point.','Small')

page('02 / DATA CONTRACTS','Inputs, provenance and validation')
table(['File / required columns','Optional fields and defaults'],[
    ['sales.csv<br/><b>date, product_id, units</b>','Daily totals; date must be YYYY-MM-DD. One row per product/date.'],
    ['inventory.csv<br/><b>product_id, current_stock</b>','incoming_units: 0; incoming_day: 1 when no incoming stock; name: product ID; category: Imported; unit_price_cents: 200.']
],[218,280])
sub('Daily CSV validation', 'UTF-8 (BOM accepted); maximum 10 MB for uploaded byte inputs and 100,000 rows per file. Column names must be unique and required columns present. Product IDs use 1-40 ASCII letters, digits, hyphens or underscores. Units and stock are integers from 0 to 1,000,000. Reference prices are positive integer SGD cents up to 100,000. Incoming stock requires a day from 1 to 14. Inventory permits at most 15 products; both files must contain identical product IDs.')
sub('Atomic loading and date semantics', 'Both files are validated and assembled before replacing the active dataset. Duplicate daily rows or inventory products are rejected. Missing daily observations stay unknown; they are not silently converted to zero. Inventory has no date column: the operator must align it with the selected analysis date. After a daily upload, the UI initially sets that date to the latest sales date; verify it before relying on a recommendation.')
code('sales.csv\ndate,product_id,units\n2026-09-23,COF,34\n\ninventory.csv\nproduct_id,current_stock,incoming_units,incoming_day,unit_price_cents\nCOF,136,0,1,200')
add('Schema illustration only: this single sales row is not sufficient for a reliable forecast or the evaluation holdout.','Small')
sub('Dataset representation', 'An assembled dataset contains products (including sorted history), original sales/inventory rows, a source label and a 16-character SHA-256-derived fingerprint. The fingerprint identifies the serialized inputs; it is not a signed authenticity guarantee. Session state holds uploaded data and analysis. Persisted order payloads retain calculation evidence and settings.')
sub('UCI-format transaction preparation', 'The optional importer reads InvoiceNo, StockCode, Description, Quantity, InvoiceDate and UnitPrice from a CSV under 100 MB. It excludes cancellations, nonpositive quantities/prices, invalid dates/codes, missing values and quantities above an explicit cap (default 1,000). It never reads CustomerID. Returns are excluded rather than netted.')
add('The UI requires ledger-completeness confirmation before absent transaction days are filled with zero. Up to 12 products are selected using training-period trading-day coverage, with at least 42 calendar days. Stock is simulated at five days of recent mean and purchase reference price fixed at S$2.00. GBP sale prices are not used as SGD purchase costs. The original UCI workbook has not been validated in this run.')

page('03 / DECISION ENGINE','Forecast, quantity and supplier allocation')
sub('Forecast calculation', 'For analysis date t, retain observations on or before t within the previous 28 calendar days. For each of the next 14 days, average matching weekdays. If fewer than two matching observations exist, use the recent overall mean and flag review. No recent observations blocks the forecast. Annual seasonality and learned event effects are outside scope.')
code('baseline[d] = ceil(mean(recent matching-weekday units))\ndemand[d]   = ceil(baseline[d] * (1 + adjustment/100)\n                   * (1 + event_uplift[d]/100))\nsafety      = ceil(mean(demand[1:14]) * buffer_days)\nquantity    = max(0, sum(demand[1:14]) + safety - stock - incoming)\nreorder_pt  = sum(demand[1:7]) + safety')
add('The ranges above are inclusive mathematical day ranges. Event uplift applies only within the configured event window and outside Normal trading. Percentage arithmetic currently uses floating point; a known rounding issue is disclosed on page 7.','Small')
table(['Simulated supplier','Price factor / fee','Arrival / MOQ / capacity','Quality / on-time score'],[
    ['A - Express','1.0x / S$15','Day 2 / 50 / 1,200','95 / 98'],
    ['B - Economy','0.8x / S$10','Day 7 / 100 / 2,000','85 / 90'],
    ['C - Standard','0.9x / S$12','Day 4 / 50 / 1,200','90 / 95']
],[100,112,163,123])
add('Price factors multiply each product\'s reference purchase price, rounded to integer cents. Fees apply per product/supplier allocation. Scores and delivery days are assumptions, not calibrated probabilities or guarantees.','Small')
sub('Exact, bounded search', 'Filter suppliers by quality, reliability and approved status. Enumerate single-supplier plans and all integer splits across each pair, for an exact requested quantity up to 2,000 units per product. Every allocation must meet MOQ/capacity. Incoming stock and supplier shipments arrive at the start of their delivery day; every end-of-day balance must be nonnegative, and final stock must meet the safety buffer. Optional urgent units must arrive by the explicit urgent deadline.')
sub('Objective, budget and statuses', 'Minimize units x price plus fees; break cost ties using fewer shipments. Return ready, no_purchase_needed, over_budget or blocked. A zero quantity still checks timing and safety feasibility. Compute savings only when a feasible single-supplier comparator exists. Catalogue totals show budget pressure, and drafting independently enforces the selected batch\'s shared budget. No global catalogue allocation optimization is performed.')
sub('Stress replay and search limits', 'Stress tests replay the same allocation with raised demand and delayed new deliveries; existing incoming stock keeps its date. The search does not optimize three-supplier splits, extra MOQ stock, cross-product freight or shared supplier capacity. With three suppliers and a 14-day horizon, enumeration is bounded by O(S squared x Q x H) per product.')

page('04 / AGENT & RECORD INTEGRITY','Read-only AI, human-controlled review')
sub('Optional AI briefing contract', 'gateway.brief() loads LLM_GATEWAY_URL, LLM_GATEWAY_API_KEY and LLM_MODEL from the server-side purchase_demo/.env file. The URL must use HTTPS. Each call posts to /api/chat with X-API-Key, model, messages, stream=false and num_predict=550; timeout is 45 seconds per call, with at most four calls. No model training or fine-tuning is performed.')
table(['Step','Required model action','Application-supplied evidence'],[
    ['1','read_inventory','Source label, product count and dataset fingerprint.'],
    ['2','read_recommendations','Per-SKU quantity, shortage day, status, cost and allocations.'],
    ['3','check_budget','Total cost, budget and over-budget flag.'],
    ['4','answer','A text briefing using the supplied evidence.']
],[38,163,297])
add('Tool requests must exactly match <font face="Courier">{"type":"tool","name":"NAME"}</font>, with no arguments or extra keys. The final object must contain only type="answer" and a string message. Unexpected order, malformed responses or transport errors produce a generic error; calculated recommendations remain available. Returned text has the configured key redacted. Live gateway compatibility is not verified.')
sub('Draft payload and persistence', 'storage.draft_payload() accepts selected products with ready plans and actual order lines, then checks their combined cost against the shared budget. Version-2 payloads store source, dataset fingerprint, settings, product forecasts/overrides and order lines. save_draft() hashes sorted JSON with SHA-256; an INSERT OR IGNORE on a unique fingerprint deduplicates identical payloads. Batch IDs use SP- plus eight UUID hexadecimal characters.')
code('SQLite: purchase_demo/demo_orders.db\nbatches(id PRIMARY KEY, fingerprint UNIQUE, status, payload,\n        reviewed_at, reviewed_role)\n\nDRAFT -- Manager review --> APPROVED_SIMULATION\nDRAFT -- Manager review --> REJECTED')
sub('Review integrity', 'The UI requires a confirmation checkbox for approval. storage.review() requires the simulated Manager role and updates only a DRAFT row whose stored payload exactly equals the reviewed string. A changed or already-reviewed record is not updated. Review time is UTC. Startup migration adds reviewed_role when absent and preserves legacy rows. Order CSV and audit JSON downloads are available.')
sub('Security boundary', 'Roles are a selector, not authenticated identity. The model has no write, approval or dispatch capability. SQL uses bound parameters; custom HTML escapes uploaded labels; CSV export prefixes formula-like strings. Gateway errors hide raw transport/model content. A shared deployment still needs authentication and data isolation: all sessions using the same SQLite file can access its review records.')

page('05 / RUN & HOST','Reproduce locally, then verify the host')
add('Commands below start the current application from a fresh repository checkout. Windows execution was tested locally; the Ubuntu steps are a deployment recipe, not evidence that an AWS instance is already serving the application.')
sub('Windows / PowerShell', 'Install Python and Git, then run the following from a chosen working directory. The included launcher binds to 127.0.0.1:8504 and applies the application theme.')
code('git clone https://github.com/xensica/nus-iss.git\ncd nus-iss/NUS-ISS/purchase-order-agent\npy -m venv .venv\n.\\.venv\\Scripts\\python.exe -m pip install -r purchase_demo/requirements.txt\n.\\purchase_demo\\Start-StockPilot.ps1')
sub('Ubuntu / Lightsail preview', 'Proposed instance: Singapore, Ubuntu 24.04 LTS, general purpose, dual-stack and 2 GB RAM. Attach a static IP. Install the following dependencies and start a loopback-only preview. Access it through an SSH tunnel, or put a configured HTTPS reverse proxy in front of it for external access. [R2, R3]')
code('sudo apt-get update\nsudo apt-get install -y python3-venv python3-pip git\ngit clone https://github.com/xensica/nus-iss.git\ncd nus-iss/NUS-ISS/purchase-order-agent\npython3 -m venv .venv\n.venv/bin/python -m pip install -r purchase_demo/requirements.txt\n.venv/bin/python -m streamlit run purchase_demo/demo_app.py \\\n  --server.address 127.0.0.1 --server.port 8504 \\\n  --server.headless true --browser.gatherUsageStats false')
add('From your own terminal, an SSH tunnel can map local port 8504 to server port 8504 using your Lightsail key and instance IP. The loopback preview is not a public deployment URL. Streamlit address/port options follow its official configuration reference. [R1]','Small')
sub('Gateway configuration', 'Copy .env.example to .env beside demo_app.py and set the organiser-provided HTTPS gateway URL, private key and supported model identifier. Keep .env out of Git. The calculation workflow works without these variables. The model identifier in .env.example is a configuration example, not confirmation of current availability.')
sub('Before public demonstration', 'Configure HTTPS, WebSocket-capable proxying, authenticated access and a startup service; keep port 8504 private behind the proxy. Restrict SSH access and check both IPv4 and IPv6 firewall rules. Back up SQLite consistently and confirm restart persistence. Record the deployed commit, reachable URL and screenshots for the separate deployment-evidence submission. [R1-R3]')
add('Dependencies: streamlit &gt;=1.63,&lt;2; pandas &gt;=2,&lt;4; requests &gt;=2.32,&lt;3; python-dotenv &gt;=1,&lt;2; pytest &gt;=8,&lt;10. Altair is imported via the installed Streamlit dependency set. Version ranges are not a frozen deployment lockfile.','Small')

page('06 / VERIFICATION & EVALUATION','Measured on 25 September 2026')
add('<b>Automated checks: 31 passed in 7.39 seconds.</b> The successful rerun used Windows and Python 3.13.3. The initial sandbox attempt hit temporary-folder permissions; the rerun completed outside that restriction. Tests use isolated databases and do not dispatch orders.')
code('# From purchase-order-agent (Windows)\n.\\.venv\\Scripts\\python.exe -m pytest purchase_demo/tests -q -p no:cacheprovider\n.\\.venv\\Scripts\\python.exe -m purchase_demo.evaluation')
add('On Linux, use .venv/bin/python in place of the Windows interpreter path.','Small')
add('Coverage includes CSV rejection and round trips, sparse/stale data, future-data exclusion, event windows, quantity/timing checks, split allocations, budget blocking, stress replay, migrations, deduplication, role/payload guards, evaluation reproducibility, mocked gateway sequence/errors, all six UI screens and a simulated approval flow. Component tests check escaping and shipment order; they are not a browser screenshot audit.')
sub('Holdout design', 'Source: deterministic synthetic 12-product sample, 84 daily records each; fingerprint <b>389855f934b519cc</b>. Training ends 9 September 2026; holdout is 10-23 September (14 days). No products were skipped. Evaluation requires at least 42 consecutive observations. The last-week and 28-day moving-average baselines use the same holdout.')
table(['Forecast method','MAE (units)','MAPE (%)','WAPE (%)'],[
    ['Weekday average','1.68','6.64','6.69'],['Last week','2.11','8.49','8.39'],['Moving average','2.70','10.87','10.71']
],[207,97,97,97])
add('MAE = mean absolute error; MAPE averages absolute percentage errors over nonzero actuals; WAPE = total absolute error / total actual units x 100. Metrics above pool all product-day observations. WAPE is undefined when all actual units are zero.','Small')
table(['Purchasing replay','Cost (SGD)','Stockout product-days','Lost units'],[
    ['Agent','4,467.35','0','0'],['Reorder-point baseline','4,127.68','20','306']
],[189,103,116,90])
add('Both policies start with five days of training-mean stock, no incoming deliveries and one order decision. The baseline selects the cheapest threshold-eligible supplier without enforcing daily stock coverage. Lost sales are not backlogged. Totals sum across products: stockout product-days are not unique calendar days.')
add('<b>Interpretation:</b> The agent costs S$339.67 more in this replay and avoids the baseline\'s simulated shortages. This is a cost/service trade-off, not a purchasing-savings result. Synthetic results do not establish real-store accuracy, preparation time, seven-day warning performance or commercial benefit.')
add('Installed versions in this run: Streamlit 1.63.0; pandas 3.0.5; requests 2.34.2; python-dotenv 1.2.3; pytest 9.1.1. Passing tests do not resolve the calculation issues on page 7.','Small')

page('07 / LIMITATIONS & REFERENCES','What is verified, and what remains open')
table(['Known finding','Effect and next check'],[
    ['Percentage rounding','Floating-point arithmetic can make 25 units + 12% round up to 29 instead of 28. Replace with an appropriate exact/decimal calculation and add boundary cases.'],
    ['Urgent supplier comparison','compare_suppliers() does not forward optional urgent parameters into its single-supplier check. Align its comparison with the actual plan constraints.'],
    ['Zero-quantity blocker text','An infeasible urgent constraint with zero net quantity can incorrectly blame late incoming stock. Distinguish shortage timing from urgent-constraint conflicts.'],
    ['Simulated approvals / shared records','Manager roles are unauthenticated. Approvals do not reserve stock or create confirmed arrivals. Reconcile overlapping batches and add identity/isolation before operational use.'],
    ['Bounded optimization','One or two suppliers, exact quantity, at most 2,000 units per product. No cross-product capacity or freight consolidation. A blocked result applies to this restricted search.'],
    ['External verification','Live gateway connectivity, AWS hosting and the original UCI workbook remain unverified. This document supplies no public deployment evidence.']
],[158,340])
sub('Reproduction and release trace', 'The local application Python modules matched the clean repository checkout at commit <b>fa252df9cbe600e09161bfe90b3e95164eb6f71d</b>. Tests and evaluation in this document ran against the local purchase_demo copy. Reproduce evaluation with python -m purchase_demo.evaluation; add --data purchase_demo/sample_data to use the bundled CSV files. Before release, capture the actual deployed revision and dependency versions.')
add('REFERENCES & SOURCE MAP','Label')
add('<b>Project source:</b> <link href="https://github.com/xensica/nus-iss/tree/fa252df9cbe600e09161bfe90b3e95164eb6f71d/NUS-ISS/purchase-order-agent/purchase_demo" color="#D94F20">StockPilot application at the reviewed commit</link>. Architecture and algorithms: engine.py, catalogue.py, gateway.py. Inputs: data_io.py, uci_import.py. Persistence: storage.py, migrations.py. Verification: evaluation.py and tests/. Current scope and audit disclosures: README.md.','Small')
add('<b>[R1] Streamlit:</b> <link href="https://docs.streamlit.io/develop/api-reference/configuration/config.toml" color="#D94F20">Configuration reference</link> - server address/port and protection settings.<br/><b>[R2] AWS:</b> <link href="https://docs.aws.amazon.com/lightsail/latest/userguide/understanding-firewall-and-port-mappings-in-amazon-lightsail.html" color="#D94F20">Lightsail firewall and port mappings</link> - public access controls.<br/><b>[R3] AWS:</b> <link href="https://docs.aws.amazon.com/lightsail/latest/userguide/lightsail-create-static-ip.html" color="#D94F20">Create and attach a static IP</link> - stable instance addressing.<br/>Documentation checked 25 September 2026. Deployment steps describe proposed configuration, not completed deployment.','Small')
add('UCI-format support references the source schema recorded in the repository; no original dataset download or independent dataset validation was performed for this document. No claim of AWS certification or direct Amazon Bedrock integration is made: the AI path is the organiser\'s HTTP gateway.','Small')

def decorate(c,doc):
    w,h=A4; c.setFillColor(ACC); c.rect(0,h-9,w,9,fill=1,stroke=0)
    c.setFillColor(MUTED); c.setFont('Helvetica-Bold',8)
    c.drawString(48,h-35,'STOCKPILOT / TECHNICAL DOCUMENT'); c.drawRightString(w-48,h-35,'SKIBIDI SLICERS')
    c.setStrokeColor(RULE); c.line(48,43,w-48,43); c.setFont('Helvetica',8)
    c.drawString(48,29,'SMYA FINAL SUBMISSION | YBQYZYHP'); c.drawRightString(w-48,29,f'{doc.page} / 7')
doc=SimpleDocTemplate(str(OUT),pagesize=A4,leftMargin=48,rightMargin=48,topMargin=60,bottomMargin=57,title='StockPilot - Technical Document - YBQYZYHP',author='Team Skibidi Slicers',subject='Architecture, implementation, validation and deployment')
doc.build(story,onFirstPage=decorate,onLaterPages=decorate)
import pymupdf
from pypdf import PdfReader
reader=PdfReader(str(OUT))
for i,pg in enumerate(reader.pages):
    txt=pg.extract_text()
    print(f'Page {i+1}: {len(txt)} chars; ends: {txt[-90:].strip()}')
renderdir=ROOT/'tmp/pdfs/technical-rendered'; renderdir.mkdir(parents=True,exist_ok=True)
for i,pg in enumerate(pymupdf.open(OUT)):
    pg.get_pixmap(matrix=pymupdf.Matrix(1.45,1.45)).save(renderdir/f'technical-{i+1}.png')
assert len(reader.pages)==7, f'Expected 7 pages, got {len(reader.pages)}'
alltext='\n'.join(pg.extract_text() for pg in reader.pages)
for item in ['31 passed','4,467.35','YBQYZYHP','APPROVED_SIMULATION','389855f934b519cc']:
    assert item in alltext,item
print(f'Created {OUT} ({OUT.stat().st_size:,} bytes)')
