"""Presentation-only components. Every value comes from existing analysis results."""
from datetime import date, timedelta
from html import escape

CSS = '''<style>
:root{--ink:#22231f;--muted:#74766d;--paper:#f5f4ee;--line:#dedfd4;--orange:#e95827;--lime:#dce99a}
.stApp{background:var(--paper);color:var(--ink);font-family:Inter,Arial,sans-serif}
.block-container{max-width:1550px;padding:1.4rem 3.2rem 3rem}
header[data-testid="stHeader"]{background:transparent;height:1.5rem}
h1,h2,h3{color:var(--ink)!important;letter-spacing:-.045em!important}
h1{font-size:clamp(2.6rem,4vw,4.6rem)!important;line-height:1.03!important;font-weight:750!important;max-width:1000px;margin-bottom:.3rem!important}
h2{font-size:1.7rem!important}h3{font-size:1.12rem!important;letter-spacing:-.02em!important}
p,li{line-height:1.6}.eyebrow{font:600 10px 'Consolas',monospace;letter-spacing:.18em;text-transform:uppercase;color:var(--orange);margin:22px 0 12px}
.masthead{display:flex;align-items:center;gap:14px;height:60px}
.brand-symbol{width:38px;height:38px;display:grid;place-items:center;background:var(--orange);color:#fff;font-size:27px;font-weight:800;border-radius:5px;transform:rotate(-7deg)}
.brand-name{font-size:25px;font-weight:800;letter-spacing:-1.1px}.brand-tag{font:10px 'Consolas',monospace;color:var(--muted);letter-spacing:.14em;text-transform:uppercase;border-left:1px solid var(--line);padding:8px 16px;margin-left:8px}
.status-line{display:flex;gap:18px;justify-content:space-between;flex-wrap:wrap;font:10px 'Consolas',monospace;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);padding:14px 0;border-bottom:1px solid var(--line)}
[data-testid="stRadio"]>div[role="radiogroup"]{gap:4px!important;padding:10px 0 16px;border-bottom:1px solid var(--line)}
[data-testid="stRadio"]>div[role="radiogroup"] label{padding:7px 14px!important;border-radius:5px;background:#ecece4;border:1px solid transparent;font-size:12px}
[data-testid="stRadio"]>div[role="radiogroup"] label:has(input:checked){background:#252820;color:white}
[data-testid="stRadio"]>div[role="radiogroup"] label>div:first-child{display:none}
.hero{background:#252820;color:#f5f4ee;border-radius:4px;padding:25px 28px;margin:18px 0}.hero h2{color:#fff!important}.hero p{color:#c7cabd;margin:0}
.ledger{display:grid;grid-template-columns:1.25fr 1fr 1fr 1fr;border-top:1px solid var(--ink);border-bottom:1px solid var(--line);margin:26px 0 24px;padding:20px 0}
.ledger-cell{padding:0 22px;border-left:1px solid var(--line)}.ledger-cell:first-child{padding-left:0;border:0}.ledger-label{font:10px 'Consolas',monospace;text-transform:uppercase;letter-spacing:.07em;color:var(--muted)}.ledger-value{font-size:32px;font-weight:650;letter-spacing:-1.4px;margin:5px 0}.ledger-value.accent{color:var(--orange)}.ledger-note{font-size:11px;color:var(--muted)}
.section-head{display:flex;justify-content:space-between;gap:15px;align-items:center;padding:14px 0}.section-head b{font-size:19px;letter-spacing:-.5px}.section-head span{font:10px 'Consolas',monospace;color:var(--muted);text-transform:uppercase;letter-spacing:.06em}
.map-scroll{overflow:auto;border:1px solid var(--line);background:#fffef9;border-radius:6px;padding:14px 16px 8px}
.risk-map{width:100%;border-collapse:separate;border-spacing:4px 5px;min-width:680px}.risk-map th{font:10px 'Consolas',monospace;color:var(--muted);text-align:center;font-weight:400;height:24px}.risk-map th:first-child{text-align:left;width:175px}.risk-map td.product{font-size:12px;font-weight:600;white-space:nowrap;padding-right:10px}.risk-map td.product small{display:block;font:9px 'Consolas',monospace;color:var(--muted);margin-top:3px}.risk-map td.tile{text-align:center;border-radius:3px;height:26px;font:10px 'Consolas',monospace;min-width:25px}.safe{background:#e4edcb;color:#526339}.low{background:#f5e3b5;color:#755826}.risk{background:#f2baaa;color:#892f1c}.unknown{background:#e8e8e1;color:#73746d}
.map-legend{display:flex;gap:18px;flex-wrap:wrap;font:10px 'Consolas',monospace;color:var(--muted);padding:14px 0 2px}.map-legend i{display:inline-block;width:9px;height:9px;border-radius:2px;margin-right:6px}
.exception{padding:14px 0;border-top:1px solid var(--line)}.exception-tag{font:9px 'Consolas',monospace;text-transform:uppercase;letter-spacing:.1em;color:var(--orange)}.exception-title{font-size:16px;font-weight:650;margin:5px 0}.exception-note{color:var(--muted);font-size:12px;line-height:1.5}
.stButton button,.stFormSubmitButton button,.stDownloadButton button{border-radius:4px;font-weight:600;min-height:40px;font-size:12px}
.stButton button[kind="primary"],.stFormSubmitButton button[kind="primary"]{background:var(--orange);border-color:var(--orange);color:white}
[data-testid="stMetric"]{background:transparent;border-top:1px solid var(--line);padding:14px 0;border-radius:0}
[data-testid="stMetricLabel"]{color:var(--muted);font-size:11px}[data-testid="stMetricValue"]{color:var(--ink);font-size:28px;font-weight:600}
[data-testid="stVerticalBlockBorderWrapper"]{border-radius:5px!important}
.step{padding:16px 20px;background:#e9eddb;border-left:3px solid #87944c;font-size:13px;margin:18px 0;border-radius:0 4px 4px 0}
.pill{display:inline-block;background:#e6ecd5;border:1px solid #d3ddbb;padding:5px 10px;border-radius:3px;font:10px 'Consolas',monospace;letter-spacing:.07em}
.shipments{display:flex;gap:14px;flex-wrap:wrap;margin:14px 0 20px}.shipment{flex:1;min-width:210px;background:#fffef9;border:1px solid var(--line);border-top:3px solid var(--orange);padding:20px;border-radius:4px}.shipment:nth-child(2){border-top-color:#839051}.shipment-label{font:10px 'Consolas',monospace;text-transform:uppercase;color:var(--muted);letter-spacing:.08em}.shipment-units{font-size:40px;letter-spacing:-2px;font-weight:650;margin:10px 0 0}.shipment-units small{font-size:12px;letter-spacing:0;color:var(--muted);font-weight:400}.shipment-supplier{font-size:14px;font-weight:600;margin:0 0 16px}.shipment-meta{display:flex;justify-content:space-between;border-top:1px solid var(--line);padding-top:12px;font-size:11px;color:var(--muted)}.shipment-price{font-size:18px;color:var(--ink);font-weight:600;margin-top:12px}.allocation{display:flex;height:12px;border-radius:2px;overflow:hidden;margin:14px 0}.allocation span{background:var(--orange)}.allocation span:nth-child(2){background:#839051}
.review-paper{background:#fffefa;padding:28px;border:1px solid var(--line);border-top:4px solid var(--ink);margin:18px 0}.paper-top{display:flex;justify-content:space-between;gap:20px;border-bottom:1px solid var(--line);padding-bottom:20px}.paper-title{font-size:24px;font-weight:700;letter-spacing:-1px}.paper-number{font:11px 'Consolas',monospace;color:var(--muted);margin-top:5px}.paper-total{font-size:30px;font-weight:600;letter-spacing:-1px;text-align:right}.paper-total small{display:block;font:10px 'Consolas',monospace;color:var(--muted);letter-spacing:.05em;margin-bottom:6px}.order-lines{width:100%;border-collapse:collapse;margin-top:14px}.order-lines th{text-align:left;font:10px 'Consolas',monospace;color:var(--muted);padding:10px 0}.order-lines td{font-size:12px;padding:14px 0;border-bottom:1px solid #eeeee5}.order-lines th:last-child,.order-lines td:last-child{text-align:right}
@media(max-width:900px){.block-container{padding:1rem}.ledger{grid-template-columns:1fr 1fr;gap:18px}.ledger-cell:nth-child(3){padding-left:0;border:0}.brand-tag{display:none}.ledger-value{font-size:26px}.paper-top{flex-wrap:wrap}.order-lines{min-width:500px}.review-paper{overflow:auto}.stApp h1{font-size:2.6rem!important}}
</style>'''


def ledger(analysis):
    results=analysis['results']
    risks=[r['forecast']['shortage_day'] for r in results.values() if r['forecast'] and r['forecast']['shortage_day']]
    ready=sum(r['plan']['status']=='ready' for r in results.values())
    blocks=[('Next shortage',f'{min(risks)} days' if risks else 'None','Before any new purchases',True),
        ('Products in view',str(len(results)),f'{len(risks)} projected shortages',False),
        ('Ready to purchase',str(ready),'Feasible recommendations',False),
        ('Proposed spend',f"S${analysis['total_cents']/100:,.2f}",f"Budget S${analysis['budget_cents']/100:,.0f}",False)]
    return '<div class="ledger">'+''.join(f'<div class="ledger-cell"><div class="ledger-label">{escape(label)}</div><div class="ledger-value {"accent" if accent else ""}">{escape(value)}</div><div class="ledger-note">{escape(note)}</div></div>' for label,value,note,accent in blocks)+'</div>'


def risk_map(results, ordered, as_of, with_plan=False):
    start=date.fromisoformat(as_of)
    headers='<th scope="col">PRODUCT / '+('WITH PLAN' if with_plan else 'BEFORE PURCHASE')+'</th>'+''.join(f'<th scope="col">{(start+timedelta(days=d)).strftime("%d %b")}</th>' for d in range(1,15))
    rows=[]
    for pid in ordered:
        result=results[pid]; f=result['forecast']; p=result['plan']
        balances=p.get('balances') if with_plan else None
        label=escape(result['product']['name'])
        cells=f'<td class="product">{label}<small>{escape(pid)} · {escape(p["status"].replace("_"," "))}</small></td>'
        for i in range(14):
            if f is None:
                tone='unknown'; value='?'; description='No valid forecast'
            else:
                balance=balances[i] if balances is not None else f['daily'][i]['without_new_order']
                tone='risk' if balance<0 else ('low' if balance<f['safety'] else 'safe')
                value='×' if balance<0 else ('·' if tone=='safe' else '!')
                description=f"Day {i+1}: {balance} units; "+('with recommended arrivals' if balances is not None else 'without new purchases')
            cells+=f'<td class="tile {tone}" title="{escape(description)}" aria-label="{label}: {escape(description)}">{value}</td>'
        rows.append('<tr>'+cells+'</tr>')
    return '<div class="map-scroll"><table class="risk-map" aria-label="Daily stock coverage"><thead><tr>'+headers+'</tr></thead><tbody>'+''.join(rows)+'</tbody></table><div class="map-legend"><span><i class="safe"></i>· At / above buffer</span><span><i class="low"></i>! Below buffer</span><span><i class="risk"></i>× Shortage</span><span>Hover a cell for the stock balance</span></div></div>'


def shipment_cards(orders):
    orders=sorted(orders,key=lambda o:o['delivery_days'])
    total=sum(o['quantity'] for o in orders)
    bar='<div class="allocation">'+''.join(f'<span style="width:{o["quantity"]/total*100:.3f}%" title="{escape(o["supplier"])}: {o["quantity"]} units"></span>' for o in orders)+'</div>' if total else ''
    cards=[]
    for i,o in enumerate(orders):
        cards.append(f'<div class="shipment"><div class="shipment-label">Shipment {i+1:02d} / estimated day {o["delivery_days"]}</div><div class="shipment-units">{o["quantity"]} <small>units</small></div><div class="shipment-supplier">{escape(o["supplier"])}</div><div class="shipment-meta"><span>S${o["unit_price_cents"]/100:.2f} / unit</span><span>Delivery S${o["delivery_fee_cents"]/100:.2f}</span></div><div class="shipment-price">S${o["cost_cents"]/100:,.2f}</div></div>')
    return bar+'<div class="shipments">'+''.join(cards)+'</div>'


def order_document(batch_id,payload):
    lines=[]
    for o in payload['plan']['orders']:
        lines.append(f'<tr><td>{escape(o.get("product","Bottled coffee (legacy)"))}<br><small>{escape(o["supplier"])}</small></td><td>{o["quantity"]}</td><td>Day {o["delivery_days"]}</td><td>S${o["cost_cents"]/100:,.2f}</td></tr>')
    return f'<div class="review-paper"><div class="paper-top"><div><div class="paper-title">Purchase order batch</div><div class="paper-number">{escape(batch_id)} / SIMULATION ONLY</div></div><div class="paper-total"><small>TOTAL INCLUDING DELIVERY</small>S${payload["plan"]["cost_cents"]/100:,.2f}</div></div><table class="order-lines"><thead><tr><th>PRODUCT / SUPPLIER</th><th>UNITS</th><th>EST. ARRIVAL</th><th>AMOUNT</th></tr></thead><tbody>{"".join(lines)}</tbody></table></div>'


# The guided workspace keeps the useful evidence components above, with a calmer shell.
CSS += '''<style>
:root{--ink:#21372f;--muted:#697a72;--paper:#f6f8f6;--line:#e0e7e1;--orange:#28785f;--lime:#d6ebdf}
.stApp{background:var(--paper);color:var(--ink);font-family:Inter,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif}
.block-container{max-width:1260px;padding:2.4rem 3rem 4rem}
h1{font-size:clamp(1.85rem,2.6vw,2.65rem)!important;font-weight:700!important;line-height:1.16!important;letter-spacing:-.045em!important;max-width:850px}
h2{font-size:1.4rem!important}h3{font-size:1.14rem!important;letter-spacing:-.02em!important}
p,li{line-height:1.5}.eyebrow{font:600 10px Inter,Arial,sans-serif;letter-spacing:.14em;margin:6px 0 12px;color:#5d8c76}
[data-testid="stSidebar"]{background:#eef3ef;border-right:1px solid #dfe7e0}
[data-testid="stSidebar"] .stButton button{justify-content:flex-start;border:0;background:transparent;padding:10px 15px;font-size:14px;color:#52675b;box-shadow:none}
[data-testid="stSidebar"] .stButton button[kind="primary"]{background:#dcebe1;color:#1c6247;font-weight:650}
[data-testid="stSidebar"] .stButton button:hover{background:#e1ece4}
[data-testid="stSidebar"] hr{margin:1rem 0}
.side-brand{font-size:25px;font-weight:720;letter-spacing:-1px;display:flex;align-items:center;gap:10px;margin:10px 0 24px}
.side-brand span{display:grid;place-items:center;width:34px;height:34px;color:white;background:#28785f;border-radius:10px;font-size:23px;box-shadow:0 4px 12px #28785f20}
[data-testid="stVerticalBlockBorderWrapper"]{border-radius:14px!important;background:#fff;border-color:#e1e8e2!important}
[data-testid="stVerticalBlock"]>[data-testid="stVerticalBlockBorderWrapper"]{box-shadow:0 2px 4px #21372f03}
[data-testid="stMetric"]{border:0;padding:15px 18px;background:white;border-radius:12px;margin:8px 0 18px}
[data-testid="stMetricLabel"]{font-size:12px;color:#718075}[data-testid="stMetricValue"]{font-size:29px;color:#21372f;letter-spacing:-1px}
.stButton button,.stFormSubmitButton button,.stDownloadButton button,.stLinkButton a{border-radius:8px!important;min-height:39px;font-size:13px;border-color:#dce5df;font-weight:600;transition:background .12s}
.stButton button[kind="primary"],.stFormSubmitButton button[kind="primary"]{background:#28785f;border-color:#28785f;color:white}
.stButton button[kind="primary"]:hover,.stFormSubmitButton button[kind="primary"]:hover{background:#20664f;border-color:#20664f}
[data-testid="stExpander"]{border-color:#e1e8e2;border-radius:10px;background:transparent}
[data-testid="stExpander"] summary{font-size:13px}
[data-testid="stCaptionContainer"]{color:#76847b;font-size:12px}
.welcome-steps{display:grid;grid-template-columns:repeat(3,1fr);gap:24px;margin:30px 0 36px;border-top:1px solid #e0e7e1;padding-top:24px}
.welcome-steps div{display:flex;flex-direction:column;gap:9px}.welcome-steps b{color:#78a58d;font-size:12px;font-weight:600}.welcome-steps strong{font-size:18px;font-weight:600;letter-spacing:-.4px}.welcome-steps span{font-size:13px;color:#78837a}
.shipment{border-radius:12px;background:#f8faf8;padding:18px;border-top-color:#28785f}.shipment:nth-child(2){border-top-color:#91b5a0}.shipment-units{font-size:32px;letter-spacing:-1px}.shipment-label{font-family:Inter,Arial,sans-serif;letter-spacing:.04em}.allocation{border-radius:8px;height:8px}.allocation span{background:#28785f}.allocation span:nth-child(2){background:#91b5a0}
.review-paper{border-radius:12px;border-top:3px solid #28785f;background:white}.paper-title{font-size:23px}.paper-total{font-size:29px}
.map-scroll{background:white;border-radius:12px}.risk-map td.tile{border-radius:5px}.risk{background:#f7d8ce;color:#8f3d28}.safe{background:#dceee2;color:#476d54}.low{background:#fcf0d2;color:#8c7338}
[data-testid="stDialog"] h2{font-size:1.4rem!important}
button:focus-visible,a:focus-visible{outline:3px solid #a8cebb!important;outline-offset:3px}
@media(max-width:900px){.block-container{padding:1.2rem 1rem 3rem}.stApp h1{font-size:1.9rem!important}.welcome-steps{gap:14px}.welcome-steps strong{font-size:15px}.welcome-steps span{font-size:12px}}
</style>'''
