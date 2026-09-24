"""StockPilot: purchasing decisions, explained. Never dispatches real orders."""
import json
import sys
from datetime import date, datetime, timezone
from html import escape
from pathlib import Path
from time import perf_counter
import altair as alt
import pandas as pd
import streamlit as st

sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from purchase_demo.catalogue import DEFAULTS, analyse, compare_suppliers, explanation, stress_test
from purchase_demo.data_io import sample_data, load_dataset, csv_text
from purchase_demo.evaluation import evaluate
from purchase_demo.gateway import brief
from purchase_demo.storage import draft_payload, save_draft, list_batches, review
from purchase_demo.uci_import import prepare_uci
from purchase_demo.visuals import CSS, ledger, risk_map, shipment_cards, order_document

st.set_page_config(page_title='StockPilot | Purchasing intelligence',page_icon='◈',layout='wide')
st.markdown(CSS,unsafe_allow_html=True)


def heading(kicker,title,subtitle):
    st.markdown(f'<div class="eyebrow">{escape(kicker)}</div>',unsafe_allow_html=True)
    st.title(title)
    st.caption(subtitle)


def money(cents): return f'S${cents/100:,.2f}'


def recalculate():
    start=perf_counter()
    st.session_state.analysis=analyse(st.session_state.dataset,st.session_state.settings,st.session_state.overrides)
    st.session_state.elapsed=perf_counter()-start
    st.session_state.calculated_at=datetime.now(timezone.utc).isoformat()
    st.session_state.pop('briefing',None)


def chart(rows,columns,height=260):
    frame=pd.DataFrame(rows)[['date']+columns].melt('date',var_name='Series',value_name='Units')
    lines=alt.Chart(frame).mark_line(strokeWidth=3).encode(x=alt.X('date:T',title=None,axis=alt.Axis(format='%d %b',labelAngle=0)),y='Units:Q',color=alt.Color('Series:N',scale=alt.Scale(range=['#e95827','#82924e','#797e91']),legend=alt.Legend(orient='bottom',title=None)),tooltip=['date:T','Series:N','Units:Q'])
    zero=alt.Chart(pd.DataFrame({'zero':[0]})).mark_rule(color='#b9c6ce',strokeDash=[4,4]).encode(y='zero:Q')
    st.altair_chart((lines+zero).properties(height=height).configure_view(stroke=None).configure(background='#f5f4ee').configure_axis(gridColor='#e3e3d9',labelColor='#74766d',titleColor='#74766d').configure_legend(labelColor='#56584f'),width='stretch')


if 'dataset' not in st.session_state:
    st.session_state.dataset=sample_data()
    st.session_state.settings=dict(DEFAULTS)
    st.session_state.overrides={}
    recalculate()

def open_product(pid):
    st.session_state.page='Product insights'
    st.session_state.insight_product=pid


brand,workspace,identity=st.columns([3,1.3,1.1],vertical_alignment='center')
with brand:
    st.markdown('<div class="masthead"><div class="brand-symbol">S</div><div class="brand-name">StockPilot<span style="color:#e95827">.</span></div><div class="brand-tag">The purchasing<br>control room</div></div>',unsafe_allow_html=True)
with workspace:
    st.caption('MERIDIAN STORE / SGD')
    st.caption('Human decisions. Assisted by evidence.')
with identity:
    role=st.selectbox('Review as',['Operator','Manager'],key='role')
    st.caption('Simulated role · not authentication')
page_names={'Overview':'Control room','Product insights':'Sourcing desk','Scenario lab':'Disruption lab','Purchase orders':'Order review','Data & settings':'Data studio','Performance':'Evidence'}
page=st.radio('Workspace',list(page_names),format_func=page_names.get,horizontal=True,label_visibility='collapsed',key='page')

analysis=st.session_state.analysis
dataset=st.session_state.dataset
results=analysis['results']
ordered=sorted(results,key=lambda pid:(results[pid]['forecast']['shortage_day'] or 999) if results[pid]['forecast'] else -1)
st.markdown(f'<div class="status-line"><span>{escape(dataset["source"])}</span><span>Snapshot {analysis["settings"]["date"]} / 14-day outlook</span><span>Simulation · no orders sent</span></div>',unsafe_allow_html=True)

if page=='Overview':
    heading('01 / Control room','Know what to buy. Before you run out.','A forward view of your shelves, the decisions that matter, and a plan you can explain.')
    blocked=[pid for pid in ordered if results[pid]['plan']['status']=='blocked']
    ready=[pid for pid in ordered if results[pid]['plan']['status']=='ready']
    st.markdown(ledger(analysis),unsafe_allow_html=True)
    if analysis['over_budget']: st.error('The full proposal exceeds the shared budget. Select a smaller batch or revise the budget in Data studio.')
    left,right=st.columns([2.7,1],gap='large')
    with left:
        st.markdown('<div class="section-head"><b>The next 14 days</b><span>Stock coverage / all products</span></div>',unsafe_allow_html=True)
        with_plan=st.toggle('Show recommended arrivals',value=False,help='Compare current coverage with the proposed plan. Blocked products retain their unmitigated projection.')
        st.markdown(risk_map(results,ordered,analysis['settings']['date'],with_plan),unsafe_allow_html=True)
        st.caption('End-of-day balances. For blocked products, no new arrivals are added. Hover a cell to inspect units. Delivery timing is estimated.')
        with st.expander('View the underlying quantities and costs'):
            rows=[]
            for pid in ordered:
                r=results[pid]; f=r['forecast']; p=r['plan']
                rows.append({'SKU':pid,'Product':r['product']['name'],'On hand':r['config']['stock'],'First shortage day':f['shortage_day'] if f else None,'Buy units':f['quantity'] if f else None,'Plan cost (S$)':p.get('cost_cents',0)/100,'Status':p['status']})
            st.dataframe(pd.DataFrame(rows),hide_index=True,width='stretch')
    with right:
        st.markdown('<div class="section-head"><b>Decision queue</b><span>Start here</span></div>',unsafe_allow_html=True)
        attention=list(dict.fromkeys(blocked+ordered))[:3]
        for i,pid in enumerate(attention):
            r=results[pid]; f=r['forecast']; p=r['plan']
            tag='Intervention needed' if p['status']=='blocked' else (f'Shortage in {f["shortage_day"]} days' if f and f['shortage_day'] else 'Coverage review')
            note=p['reason'] if p['status']=='blocked' else (f'{f["quantity"]} units recommended · '+money(p.get('cost_cents',0)))
            st.markdown(f'<div class="exception"><div class="exception-tag">{i+1:02d} / {escape(tag)}</div><div class="exception-title">{escape(r["product"]["name"])}</div><div class="exception-note">{escape(note)}</div></div>',unsafe_allow_html=True)
            st.button('Inspect '+r['product']['name']+' →',key='inspect_'+pid,on_click=open_product,args=(pid,),width='stretch')
    st.divider()
    left,right=st.columns([1.6,1],gap='large')
    with left:
        st.markdown('<div class="section-head"><b>Build a purchase batch</b><span>Human review comes next</span></div>',unsafe_allow_html=True)
        selected=st.multiselect('Include these products',ready,default=ready,format_func=lambda pid:results[pid]['product']['name'])
        total=sum(results[pid]['plan']['cost_cents'] for pid in selected)
        st.write(f'**{len(selected)} products · {money(total)}**')
        st.caption(f'Available budget: {money(analysis["budget_cents"])}. Fees apply per product/supplier allocation.')
        if st.button('Create purchase-order drafts',type='primary',disabled=not selected or total>analysis['budget_cents'],width='stretch'):
            try: st.success(f"{save_draft(draft_payload(analysis,selected))} saved. Open Order review to inspect it.")
            except ValueError as error: st.error(str(error))
        st.caption('Identical batches are deduplicated. Overlapping batches do not reserve inventory; reconcile them before approval.')
    with right,st.container(border=True):
        st.markdown('<div class="eyebrow">Optional / live AI</div>',unsafe_allow_html=True)
        st.subheader('Turn the evidence into a briefing.')
        st.write('A concise explanation of the calculated recommendations, exceptions and budget for your manager.')
        st.caption('Sends SKU-level quantities, allocations and budget to your configured gateway. Up to four calls. No customer records.')
        if st.button('Generate AI briefing',width='stretch'):
            try:
                with st.spinner('Reviewing the evidence…'): st.session_state.briefing=brief(analysis)
            except ValueError as error: st.error(str(error))
        if 'briefing' in st.session_state:
            st.write(st.session_state.briefing[0])
            st.caption('AI explanation: verify against calculations. Tools: '+' → '.join(st.session_state.briefing[1]))
    st.caption(f"Calculated in {st.session_state.elapsed:.2f}s. This is not a measurement of human PO preparation time.")

elif page=='Product insights':
    heading('02 / Sourcing desk','The right quantity. The right arrival.','Follow one product from demand to delivery. Every allocation has its evidence.')
    pid=st.selectbox('Product',ordered,format_func=lambda pid:results[pid]['product']['name'],key='insight_product')
    r=results[pid]; f=r['forecast']; p=r['plan']; cfg=r['config']
    if not f: st.error(p['reason'])
    else:
        a,b,c,d=st.columns(4)
        a.metric('Forecast demand',sum(row['demand'] for row in f['daily'])); b.metric('Recommended purchase',f['quantity'])
        c.metric('Safety stock',f['safety']); d.metric('7-day reorder point',f['reorder_point'])
        st.markdown(f'<div class="step">{escape(explanation(r))}</div>',unsafe_allow_html=True)
        if f['needs_review']: st.warning(f"History needs review: {f['method']}, {f['observations']} observed days in the last 28. Missing dates are unknown, not zero sales.")
        if p['status']=='blocked': st.error(p['reason'])
        a,b=st.columns(2,gap='large')
        with a:
            st.subheader('Demand outlook')
            chart([dict(date=d['date'],Baseline=d['baseline'],Forecast=d['demand']) for d in f['daily']],['Baseline','Forecast'])
        with b:
            st.subheader('Stock coverage')
            rows=[dict(date=d['date'],**{'Without purchase':d['without_new_order']}) for d in f['daily']]; cols=['Without purchase']
            if 'balances' in p:
                for row,bal in zip(rows,p['balances']): row['With recommendation']=bal
                cols.append('With recommendation')
            chart(rows,cols)
        st.caption('Arrivals at day start; sales at day end. Reorder point assumes seven-day lead time. Weekly patterns only; no annual seasonality. Event uplift is an owner assumption.')
        st.subheader('Recommended shipments')
        if p.get('orders'):
            st.markdown(shipment_cards(p['orders']),unsafe_allow_html=True)
            saving=p.get('saving_cents')
            st.caption(f'Saving vs cheapest feasible single supplier: {money(saving)}.' if saving is not None else 'No feasible single-supplier comparator; no savings claim.')
        elif p['status']=='no_purchase_needed': st.success('Existing and incoming stock cover the forecast and safety buffer.')
        with st.expander('Compare all three approved suppliers',expanded=False):
            st.dataframe(pd.DataFrame(compare_suppliers(cfg,f,r['suppliers'])),hide_index=True,width='stretch')
            st.caption('Simulated suppliers and scores. Product prices use reference price × 1.0 / 0.8 / 0.9 for A/B/C. Other supplier assumptions are shared across products. A supplier excluded for a whole order may supply a feasible share.')
        with st.expander('Adjust this product and recalculate'):
            with st.form('override_'+pid):
                a,b,c=st.columns(3)
                stock=a.number_input('Usable stock',0,1000000,int(cfg['stock'])); incoming=b.number_input('Incoming units',0,1000000,int(cfg['incoming'])); incoming_day=c.number_input('Incoming day',1,14,int(cfg['incoming_day']))
                adj=a.slider('Demand adjustment (%)',-50,100,int(cfg['owner_adjustment'])); buffer=b.slider('Safety buffer (days)',0,5,int(cfg['buffer_days']))
                urgent=c.number_input('Optional urgent units',0,2000,int(cfg.get('urgent_quantity',0))); deadline=c.number_input('Urgent arrival by day',1,14,int(cfg.get('urgent_days') or 3))
                st.caption('Daily coverage is always enforced. Urgent units add a deadline constraint. Overrides are recorded in drafts.')
                if st.form_submit_button('Apply product adjustments',type='primary'):
                    st.session_state.overrides[pid]=dict(stock=stock,incoming=incoming,incoming_day=incoming_day,owner_adjustment=adj,buffer_days=buffer,urgent_quantity=urgent,urgent_days=deadline)
                    recalculate(); st.rerun()
            if st.button('Reset this product to dataset values'):
                st.session_state.overrides.pop(pid,None); recalculate(); st.rerun()
        with st.expander('Historical sales and calculation snapshot'):
            st.line_chart(pd.DataFrame(r['product']['history']).set_index('date')['units'],color='#e95827')
            st.json(dict(source=dataset['source'],dataset=dataset['fingerprint'],method=f['method'],config=cfg,overrides=r['overrides']))
        st.caption('Search: 1–2 suppliers, ≤2,000 units/product, exact requested quantity. No MOQ over-ordering, expiry, tax, shared supplier capacity or probabilistic risk model.')

elif page=='Scenario lab':
    heading('03 / Disruption lab','Good on paper. What about Monday?','Put the same purchase plan under pressure: more demand, later deliveries, and nowhere to hide a shortage.')
    pid=st.selectbox('Product to stress-test',ordered,format_func=lambda pid:results[pid]['product']['name'],key='stress_product'); r=results[pid]
    a,b=st.columns(2); increase=a.slider('Unexpected demand increase (%)',0,100,20); delay=b.slider('New shipments arrive late (days)',0,7,2)
    rows=stress_test(r,increase,delay)
    if rows:
        first=next((row['day'] for row in rows if row['balance']<0),None)
        if first: st.warning(f'Stress scenario: shortage on day {first}. Consider more safety stock, an earlier shipment, or expediting incoming stock.')
        else: st.success('The current allocation covers demand throughout this stress scenario.')
        f=r['forecast']; p=r['plan']; balances=p.get('balances',[d['without_new_order'] for d in f['daily']])
        chart([dict(date=row['date'],**{'Stress scenario':row['balance'],'Current plan':balances[i]}) for i,row in enumerate(rows)],['Current plan','Stress scenario'],350)
        a,b,c=st.columns(3); a.metric('First stressed shortage',f'Day {first}' if first else 'None'); b.metric('Lowest stressed balance',min(row['balance'] for row in rows)); c.metric('Existing planned spend',money(p.get('cost_cents',0)))
    st.info('This is an assumed scenario, not a probability or a new recommendation. Confirmed incoming stock keeps its original date; only new supplier shipments are delayed. Saved plans remain unchanged.')
    st.subheader('Expecting a change? Plan for it.')
    st.write('Use Data studio to apply a promotion window and recalculate. For product-specific safety stock, open the Sourcing desk.')

elif page=='Purchase orders':
    heading('04 / Order review','Your signature. Your decision.','Inspect the purchase record and its assumptions. Every approval stays in this simulation.')
    batches=list_batches()
    if not batches: st.info('Your review queue is empty. Create a draft batch from the Overview.')
    else:
        labels={r['id']:f"{r['id']} · {r['status'].replace('_',' ').title()}" for r in batches}
        chosen=st.selectbox('Review batch',list(labels),format_func=labels.get); row=next(r for r in batches if r['id']==chosen); payload=json.loads(row['payload'])
        st.markdown(f'<span class="pill">{escape(row["status"].replace("_"," "))}</span>',unsafe_allow_html=True)
        st.markdown(order_document(chosen,payload),unsafe_allow_html=True)
        display=[dict(Product=o.get('product','Bottled coffee (legacy)'),Supplier=o['supplier'],Units=o['quantity'],Estimated_day=o['delivery_days'],Cost_SGD=o['cost_cents']/100) for o in payload['plan']['orders']]

        with st.expander('Assumptions, overrides and calculation evidence'): st.json(payload)
        st.caption('Approval does not reserve stock or update incoming inventory. Check overlapping batches. Freight is charged per product/supplier allocation.')
        if row['status']=='DRAFT':
            if role!='Manager': st.info('Switch “Review as” at the top to Manager to approve or reject this simulation.')
            else:
                with st.form('review_'+chosen):
                    checked=st.checkbox('I reviewed these quantities, costs, assumptions and manual adjustments.')
                    a,b=st.columns(2); approve=a.form_submit_button('Approve simulation',type='primary'); reject=b.form_submit_button('Reject recommendation')
                if approve or reject:
                    if approve and not checked: st.warning('Confirm you reviewed the exact draft first.')
                    elif review(chosen,row['payload'],'APPROVED_SIMULATION' if approve else 'REJECTED',role): st.rerun()
                    else: st.error('This draft changed. Refresh and review it again.')
        else: st.caption(f"Reviewed by {row['reviewed_role'] or 'legacy reviewer'} · {row['reviewed_at']}")
        a,b=st.columns(2)
        if display: a.download_button('Download order lines (CSV)',csv_text(display),file_name=chosen+'.csv',mime='text/csv')
        b.download_button('Download audit record',json.dumps(dict(batch_id=chosen,status=row['status'],reviewed_at=row['reviewed_at'],reviewed_role=row['reviewed_role'],payload=payload),indent=2),file_name=chosen+'.json',mime='application/json')

elif page=='Data & settings':
    heading('05 / Data studio','Start with the shelf. Add the context.','Bring daily sales and inventory, then tell us what changes next week.')
    st.subheader('1. Choose your data'); st.caption(f"Active: {dataset['source']} · {len(dataset['products'])} products · ID {dataset['fingerprint']}")
    with st.container(border=True):
        a,b=st.columns(2); sales=a.file_uploader('Daily sales CSV',type=['csv']); inventory=b.file_uploader('Inventory CSV',type=['csv'])
        if st.button('Validate & load both files',type='primary',disabled=sales is None or inventory is None):
            try:
                loaded=load_dataset(sales.getvalue(),inventory.getvalue()); st.session_state.dataset=loaded; st.session_state.overrides={}
                st.session_state.settings['date']=max(r['date'] for r in loaded['sales'])
                recalculate(); st.session_state.pop('evaluation',None); st.rerun()
            except ValueError as error: st.error(str(error))
        a,b,c=st.columns(3); sample=sample_data()
        a.download_button('Sample sales CSV',csv_text(sample['sales']),file_name='sales.csv',mime='text/csv')
        b.download_button('Sample inventory CSV',csv_text(sample['inventory']),file_name='inventory.csv',mime='text/csv')
        if c.button('Restore simulated sample'):
            st.session_state.dataset=sample; st.session_state.settings=dict(DEFAULTS); st.session_state.overrides={}; recalculate(); st.session_state.pop('evaluation',None); st.rerun()
        with st.expander('CSV format and data quality rules'):
            st.code('sales.csv: date,product_id,units\ninventory.csv: product_id,current_stock,incoming_units,incoming_day,name,category,unit_price_cents')
            st.write('ISO dates, non-negative whole units, one row/product/day. Include explicit zeros for zero-sales days; missing dates stay unknown. Both files must have identical product IDs. Up to 15 products, 100,000 rows and 10 MB/file. Stock is the snapshot at the chosen analysis date.')
            st.write('Inventory requires product_id and current_stock. Incoming defaults to zero; arrival day must be 1–14 when incoming stock exists. Reference price defaults to 200 cents. Suppliers remain simulated. Exclude customer identifiers.')
            st.caption('Raw UCI transactions need cleaning and daily aggregation first. Remove cancellations/returns as appropriate, resolve invalid records and retain a cleaning log. Bundled data is synthetic, not UCI.')
    with st.expander('Have the UCI Online Retail transaction CSV instead?'):
        st.write('Export the original workbook to UTF-8 CSV, then upload it here. We clean transactions, select up to 12 products and create daily sales. Stock and SGD purchase prices remain simulated.')
        raw=st.file_uploader('UCI-format transaction CSV',type=['csv'],key='uci_file')
        date_format=st.text_input('Transaction timestamp format','%m/%d/%Y %H:%M',help='Example: 12/1/2010 8:26. For ISO timestamps use %Y-%m-%d %H:%M:%S.')
        cap=st.number_input('Exclude transaction quantities above',1,1000000,1000)
        complete=st.checkbox('This is a complete ledger for the observation period; absent product/day transactions may be treated as zero sales.')
        if st.button('Prepare UCI-format data',disabled=raw is None or not complete):
            try:
                loaded=prepare_uci(raw.getvalue(),date_format,max_transaction_units=cap)
                st.session_state.dataset=loaded; st.session_state.overrides={}; st.session_state.settings['date']=loaded['cleaning']['analysis_date']
                recalculate(); st.session_state.pop('evaluation',None); st.rerun()
            except ValueError as error: st.error(str(error))
        st.caption('Source: Chen, D. (2015), UCI Online Retail, CC BY 4.0. https://doi.org/10.24432/C5BW33. Imported provenance is user-supplied, not independently verified.')
    if 'cleaning' in dataset:
        with st.expander('Data cleaning audit',expanded=True): st.json(dataset['cleaning'])
    st.subheader('2. Set planning assumptions'); settings=st.session_state.settings
    with st.form('settings'):
        a,b,c=st.columns(3)
        as_of=a.date_input('Inventory snapshot / analysis date',date.fromisoformat(settings['date'])); budget=a.number_input('Shared purchasing budget (SGD)',0,1000000,int(settings['budget'])); buffer=a.slider('Default safety buffer (days)',0,5,int(settings['buffer_days']))
        scenario=b.selectbox('Business scenario',['Normal trading','Promotion / event'],index=0 if settings['scenario']=='Normal trading' else 1)
        start=b.number_input('Event starts on forecast day',1,14,int(settings['event_start'])); duration=b.number_input('Event duration (days)',1,14,int(settings['event_duration'])); uplift=b.slider('Assumed event demand uplift (%)',0,100,int(settings['uplift']))
        adjustment=c.slider('Overall demand adjustment (%)',-50,100,int(settings['owner_adjustment'])); quality=c.slider('Minimum supplier quality',0,100,int(settings['quality'])); reliability=c.slider('Minimum supplier on-time score',0,100,int(settings['reliability']))
        st.caption('Events apply to all products during their window. Product overrides take priority over defaults until reset. No event search or learned event effect is claimed.')
        if st.form_submit_button('Update assumptions & recalculate',type='primary'):
            st.session_state.settings=dict(date=as_of.isoformat(),budget=budget,buffer_days=buffer,scenario=scenario,event_start=start,event_duration=duration,uplift=uplift,owner_adjustment=adjustment,quality=quality,reliability=reliability); recalculate(); st.rerun()
    with st.expander('Active inventory'): st.dataframe(pd.DataFrame(dataset['inventory']),hide_index=True,width='stretch')

elif page=='Performance':
    heading('06 / Evidence','Make the case with numbers.','Hold out unseen sales, compare methods fairly, and keep assumptions in plain sight.')
    st.markdown('<div class="hero"><h2>Hold out the last 14 days.</h2><p>Forecast from earlier observations only. Compare weekday, last-week and moving-average methods on identical dates.</p></div>',unsafe_allow_html=True)
    if st.button('Run offline evaluation',type='primary'):
        with st.spinner('Measuring forecasts and purchasing decisions…'): st.session_state.evaluation=evaluate(dataset)
    report=st.session_state.get('evaluation')
    if report and report['dataset']==dataset['fingerprint']:
        st.caption(f"Measured {report['run_date']} · Dataset {report['dataset']} · {report['source']}")
        if report['summary']:
            st.subheader('Forecast performance'); st.dataframe(pd.DataFrame(report['summary']).round(2),hide_index=True,width='stretch')
            st.caption('MAE: absolute error in units. MAPE: percentage error on nonzero actuals. WAPE: absolute error / actual units × 100; undefined for all-zero sales. Lower is better.')
            st.subheader('Purchasing replay · simulated'); decisions=pd.DataFrame(report['decisions'])
            st.dataframe(decisions.groupby('policy')[['stockout_days','lost_units','cost_SGD','ending_stock']].sum().round(2),width='stretch')
            st.info('Read cost and stockouts together. The cheap reorder-point baseline can miss early demand. This is not a savings claim at equal service levels.')
            with st.expander('Per-product evidence and replay assumptions'):
                st.dataframe(pd.DataFrame(report['forecasts']).round(2),hide_index=True); st.dataframe(decisions,hide_index=True); st.write(report['notes'])
        if report['skipped']: st.warning(f"Skipped {len(report['skipped'])} products: evaluation needs 42 consecutive daily observations. Missing days are not silently filled.")
        st.download_button('Download evaluation evidence',json.dumps(report,indent=2),file_name='stockpilot-evaluation.json',mime='application/json')
    st.subheader('Proposal targets · not yet demonstrated in operations')
    st.dataframe(pd.DataFrame([
        {'Measure':'PO preparation','Target':'Under 5 minutes','Verification':'Time a human review-to-draft workflow against a measured manual baseline.'},
        {'Measure':'Forecast error','Target':'Below 20% WAPE','Verification':'Use holdout results; synthetic accuracy does not validate real-store performance.'},
        {'Measure':'Stockout warning','Target':'At least 7 days early','Verification':'Record lead time per scenario; late data can make this impossible.'},
        {'Measure':'Purchasing savings','Target':'5–10%','Verification':'Compare cheapest feasible single supplier under identical constraints and fees.'},
    ]),hide_index=True,width='stretch')

st.divider()
st.caption('STOCKPILOT / PURCHASE ORDER PREPARATION · Simulated suppliers and approval · No real orders dispatched')
with st.expander('Calculation audit status'):
    st.warning('Known issues awaiting correction: percentage rounding can overstate demand; the supplier comparison may omit optional urgent-deadline constraints; one zero-quantity conflict message can be misleading. This visual redesign does not resolve those calculation-audit findings.')
