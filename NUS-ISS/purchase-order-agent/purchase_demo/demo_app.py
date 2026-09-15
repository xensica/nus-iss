import hashlib
import json
import sqlite3
from datetime import date, datetime, timezone
from pathlib import Path
from uuid import uuid4

import pandas as pd
import streamlit as st
from engine import SUPPLIERS, history, run_analysis

st.set_page_config(page_title='StockPilot • Purchasing demo',page_icon='📦',layout='wide')
DB=Path(__file__).with_name('demo_orders.db')

def db():
    c=sqlite3.connect(DB)
    c.execute('CREATE TABLE IF NOT EXISTS batches (id TEXT PRIMARY KEY, fingerprint TEXT UNIQUE, status TEXT, payload TEXT, reviewed_at TEXT)')
    c.commit()
    return c

st.title('StockPilot')
st.caption('A store-to-purchase demonstration • One product: bottled coffee • No real orders sent')
st.info('Start with the defaults and click Run analysis. Sales, suppliers and events are simulated. Live AI is optional; internet event search is not connected.')
setup,results,orders_tab=st.tabs(['1 · Store & scenario','2 · Recommendation','3 · Purchase orders'])

with setup:
    with st.form('setup'):
        a,b,c=st.columns(3)
        with a:
            store=st.text_input('Store name','Stadium Drinks')
            location=st.text_input('Store location (context only)','Near a concert venue, Singapore')
            as_of=st.date_input('Simulation date',date(2026,11,1))
            stock=st.number_input('Current usable stock (units)',0,5000,180)
            incoming=st.number_input('Confirmed incoming stock (units)',0,5000,0)
            incoming_day=st.number_input('Incoming arrival: days from simulation date',1,14,5)
        with b:
            scenario=st.selectbox('Scenario',['Normal trading','Nearby concert (simulated)','Owner promotion (simulated)'])
            event_start=st.number_input('Event starts in how many days?',1,14,5)
            event_duration=st.number_input('Event duration (days)',1,7,3)
            uplift=st.slider('Assumed event sales increase (%)',0,100,35)
            adjustment=st.slider('Owner adjustment to all forecast sales (%)',-50,100,0)
            st.caption('Event uplift is your assumption, not a learned concert effect. It applies only to event days within the 14-day window.')
        with c:
            budget=st.number_input('Purchasing budget (SGD)',0,20000,1800)
            buffer=st.slider('Final safety-stock buffer (days of average demand)',0,5,1)
            quality=st.slider('Minimum supplier quality score',0,100,85)
            reliability=st.slider('Minimum supplier on-time percentage',0,100,90)
            live=st.checkbox('Use live AI agent (requires your local .env)',False)
            st.caption('Off: deterministic demo, no API calls. On: up to 6 gateway calls per analysis. Store settings are sent; your API key is never displayed.')
        submitted=st.form_submit_button('Run analysis',type='primary')
    if submitted:
        st.session_state.pop('analysis',None)
        cfg=dict(store=store,location=location,date=as_of.isoformat(),stock=stock,incoming=incoming,incoming_day=incoming_day,scenario=scenario,event_start=event_start,event_duration=event_duration,uplift=uplift,owner_adjustment=adjustment,budget=budget,buffer_days=buffer,quality=quality,reliability=reliability)
        try:
            with st.spinner('Reading history, forecasting demand and comparing purchasing plans…'):
                f,p,t,summary=run_analysis(cfg,live)
            st.session_state.analysis=dict(config=cfg,forecast=f,plan=p,trace=t,summary=summary,live=live)
            st.success('Analysis complete. Open “2 · Recommendation”.')
        except Exception as error:
            # Do not print exception bodies that could contain credentials.
            st.error(str(error) if isinstance(error,ValueError) else 'Analysis failed. Check connection/configuration, or use simulation mode. No orders were created.')
    with st.expander('View built-in sales and supplier records'):
        st.caption('Reproducible synthetic sales: 84 days before the simulation date. This demo does not yet import real store CSVs or infer annual seasonality.')
        st.line_chart(pd.DataFrame(history(as_of)).set_index('date')['units'])
        st.dataframe(pd.DataFrame([dict(Supplier=s['name'],Unit_price_SGD=s['price']/100,Delivery_fee_SGD=s['fee']/100,Estimated_days=s['days'],MOQ=s['minimum'],Capacity=s['capacity'],Quality=s['quality'],On_time_percent=s['reliability']) for s in SUPPLIERS]),hide_index=True)

with results:
    analysis=st.session_state.get('analysis')
    if not analysis:
        st.info('Fill in the store form and run an analysis first.')
    else:
        cfg,f,p=analysis['config'],analysis['forecast'],analysis['plan']
        st.subheader(f"{cfg['store']} · {cfg['scenario']}")
        st.caption(f"Snapshot from {cfg['date']}. Form edits take effect only after Run analysis. Product: bottled coffee.")
        a,b,c,d=st.columns(4)
        a.metric('14-day forecast',f"{sum(r['demand'] for r in f['daily'])} units")
        b.metric('Final safety stock',f"{f['safety']} units")
        c.metric('Purchase quantity',f"{f['quantity']} units")
        d.metric('7-day reorder point',f"{f['reorder_point']} units")
        st.caption('Forecast = recent same-weekday average × owner adjustment × event uplift on affected days. Reorder point = next 7 days of forecast demand + safety stock; illustrative economy-supplier lead time.')
        frame=pd.DataFrame(f['daily']).set_index('date')
        st.line_chart(frame[['baseline','demand']])
        if f['shortage_day']:
            st.warning(f"Without a new purchase, projected stock first becomes negative on day {f['shortage_day']}.")
        else:
            st.success('No projected shortage within 14 days before new purchases.')
        if p['status']=='blocked':
            st.error(p['reason'])
        else:
            st.subheader('Recommended allocation')
            st.dataframe(pd.DataFrame([dict(Supplier=o['supplier'],Units=o['quantity'],Estimated_arrival_day=o['delivery_days'],Total_SGD=o['cost_cents']/100) for o in p['orders']]),hide_index=True)
            st.metric('Total including delivery, excluding tax',f"SGD {p['cost_cents']/100:,.2f}")
            if p['saving_cents'] is not None:
                st.caption(f"Savings against cheapest feasible single-supplier plan: SGD {p['saving_cents']/100:.2f}.")
            else:
                st.caption('No feasible single-supplier comparator, or no purchase needed; no savings claim.')
            frame['with_plan']=p['balances']
            st.line_chart(frame[['without_new_order','with_plan']])
            st.caption('Stock chart: arrivals at start of day, sales deducted at end of day. Final buffer is enforced; deliveries are estimated. No expiry, taxes or risk-cost model. At most two suppliers and exact requested quantity.')
            if p['status']=='over_budget':
                st.error('This feasible plan exceeds your budget. Adjust the settings and rerun; draft creation is blocked.')
            if p['status']=='ready' and p['orders']:
                payload=dict(config=cfg,forecast=f,plan=p)
                fp=hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()
                if st.button('Save this plan as draft POs',key=fp):
                    batch='DEMO-'+uuid4().hex[:8].upper()
                    with db() as conn:
                        existing=conn.execute('SELECT id FROM batches WHERE fingerprint=?',(fp,)).fetchone()
                        if existing:
                            st.info(f'Identical saved plan already exists: {existing[0]}. Open Purchase orders.')
                        else:
                            conn.execute('INSERT INTO batches VALUES (?,?,?,?,?)',(batch,fp,'DRAFT',json.dumps(payload),None))
                            st.success(f'Saved {batch}. Review it under Purchase orders.')
        st.subheader('Agent summary' if analysis['live'] else 'Simulation summary')
        st.write(analysis['summary'])
        with st.expander('Show analysis steps and evidence'):
            for entry in analysis['trace']: st.text(entry)

with orders_tab:
    st.button('Refresh orders')
    with db() as conn:
        rows=conn.execute('SELECT id,status,payload,reviewed_at FROM batches ORDER BY rowid DESC').fetchall()
    if not rows: st.info('Save a recommendation as drafts to review it here.')
    else:
        chosen=st.selectbox('Saved batch',[r[0] for r in rows])
        row=next(r for r in rows if r[0]==chosen)
        payload=json.loads(row[2])
        st.write(f'**Status:** {row[1]}')
        display=[dict(PO=f'{chosen}-{i}',Supplier=o['supplier'],Quantity=o['quantity'],Estimated_days=o['delivery_days'],Cost_SGD=o['cost_cents']/100) for i,o in enumerate(payload['plan']['orders'],1)]
        st.dataframe(pd.DataFrame(display),hide_index=True)
        st.write(f"**Batch total: SGD {payload['plan']['cost_cents']/100:.2f}**")
        st.caption('Prototype review only; there is no authenticated manager role in this local demo. Nothing is sent to suppliers.')
        if row[1]=='DRAFT':
            with st.form('approval_'+chosen,enter_to_submit=False):
                checked=st.checkbox('I reviewed this exact allocation and cost.')
                a,b=st.columns(2)
                approve=a.form_submit_button('Approve simulation')
                reject=b.form_submit_button('Reject')
            if approve or reject:
                if approve and not checked: st.warning('Review and tick the checkbox first.')
                else:
                    with db() as conn:
                        cursor=conn.execute("UPDATE batches SET status=?,reviewed_at=? WHERE id=? AND status='DRAFT' AND payload=?",('APPROVED_SIMULATION' if approve else 'REJECTED',datetime.now(timezone.utc).isoformat(),chosen,row[2]))
                    if cursor.rowcount: st.rerun()
                    else: st.error('Batch changed. Refresh and review again.')
        st.download_button('Download batch record (JSON)',json.dumps(dict(batch_id=chosen,status=row[1],reviewed_at=row[3],**payload),indent=2),file_name=chosen+'.json',mime='application/json')
