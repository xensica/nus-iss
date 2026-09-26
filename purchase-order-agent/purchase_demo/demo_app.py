"""StockPilot - a guided, human-reviewed purchasing workspace."""
import json
import sys
from datetime import date, timedelta
from html import escape
from pathlib import Path
import pandas as pd
import streamlit as st

sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from purchase_demo.data_io import csv_text
from purchase_demo.evaluation import evaluate
from purchase_demo.gateway import brief
from purchase_demo.storage import draft_payload, save_draft, list_batches, review
from purchase_demo.visuals import CSS, risk_map, order_document
from purchase_demo.local_context import discover_events
from purchase_demo.workspace import tea_demo, clear_event_overrides, event_summary, today_sg
from purchase_demo.ui_details import product_detail, event_detail
from purchase_demo.ui_state import load_data, recalculate, reset_selection
from purchase_demo.ui_store import render_store

st.set_page_config(page_title='StockPilot · Your next restock',page_icon='🌱',layout='wide',initial_sidebar_state='expanded')
st.markdown(CSS,unsafe_allow_html=True)
S=st.session_state


def money(cents): return f'S${cents/100:,.2f}'
def go(page): S.route=page
def heading(kicker,title,body=''):
    st.markdown(f'<div class="eyebrow">{escape(kicker)}</div>',unsafe_allow_html=True)
    st.title(title)
    if body:st.caption(body)
if 'route' not in S:
    S.route='Today';S.onboarded=False;S.store_name='Marina Bay Tea';S.store_type='Tea & drinks';S.location=None
    S.radius=2.0;S.selection_version=0
    load_data(tea_demo(),today_sg().isoformat())


with st.sidebar:
    st.markdown('<div class="side-brand"><span>S</span> StockPilot</div>',unsafe_allow_html=True)
    st.caption('YOUR PURCHASING WORKSPACE')
    st.markdown(f'**{escape(S.store_name)}**')
    st.caption(S.location['label'] if S.location else 'Singapore · set your location')
    st.divider()
    for label,icon in [('Today','◉'),('Orders','▤'),('Store','⌂'),('Evidence','◷')]:
        st.button(f'{icon}  {label}',key='nav_'+label,type='primary' if S.route==label else 'secondary',width='stretch',on_click=go,args=(label,))
    st.divider();st.caption('Demo workspace · SGD')
    st.caption('Human review required. No supplier orders are sent.')
    with st.expander('Review role'):
        st.selectbox('Review as',['Operator','Manager'],key='role')
        st.caption('Simulated role, not authentication.')

if not S.onboarded and S.route=='Today':
    heading('A calmer way to restock','Your next order, with a clear reason.','Start with your store. Get a short list of what to buy, why it matters and what it will cost.')
    st.markdown('<div class="welcome-steps"><div><b>01</b><strong>Your store</strong><span>Sales, stock and location.</span></div><div><b>02</b><strong>Your plan</strong><span>What needs attention first.</span></div><div><b>03</b><strong>Your decision</strong><span>Review, adjust and approve.</span></div></div>',unsafe_allow_html=True)
    a,b=st.columns([1.2,1],gap='large')
    with a,st.container(border=True):
        st.subheader('Try a tea shop by the bay')
        st.write('Explore an illustrative tea-and-snacks shop near Marina Bay Sands. See what needs restocking, then check nearby events before you decide.')
        st.caption('CHAGEE-inspired example. Synthetic products and sales; no affiliation or actual CHAGEE data.')
        if st.button('Explore the sample store',type='primary',width='stretch'):
            S.onboarded=True;S.location=dict(label='Near Marina Bay Sands · demo map point',lat=1.2834,lon=103.8607,source='Illustrative store location');st.rerun()
    with b,st.container(border=True):
        st.subheader('Bring your own store')
        st.write('Add your store location and two CSV files: daily sales and current stock.')
        st.button('Set up my store',width='stretch',on_click=go,args=('Store',))
    st.stop()

if S.route=='Today':
    analysis=S.analysis;results=analysis['results']
    ready=[pid for pid,r in results.items() if r['plan']['status']=='ready']
    blocked=[pid for pid,r in results.items() if r['plan']['status']=='blocked']
    heading('TODAY / '+S.store_name,'Let’s plan your next restock.','Review what needs attention, then make one clear purchasing decision.')
    if not S.dataset['source'].startswith('Uploaded'):st.caption('SAMPLE DATA · synthetic sales & inventory · simulated supplier terms')
    a,b,c=st.columns(3)
    a.metric('Ready to restock',str(len(ready)));b.metric('Need a closer look',str(len(blocked)));c.metric('Available budget',money(analysis['budget_cents']))
    with st.expander('What is this plan based on?'):
        snapshot=date.fromisoformat(S.settings['date'])
        st.write(f"Planning window: **{snapshot+timedelta(days=1):%d %b}?{snapshot+timedelta(days=14):%d %b %Y}**. Stock snapshot: **{snapshot:%d %b %Y}**.")
        st.write('We estimate demand from recent sales, add your safety buffer, then subtract stock on hand and incoming deliveries. Supplier choices must cover daily demand and meet your quality and delivery requirements.')
        st.caption(f"{len(results)} products ? {S.settings['buffer_days']} buffer days ? {S.settings['owner_adjustment']:+}% overall demand adjustment. Open Details for stock levels, delivery dates and individual assumptions.")
        st.caption('Ready means a feasible recommendation. Your selected products must also fit the shared budget before you can save a draft.')
    left,right=st.columns([1.6,1],gap='large')
    with left,st.container(border=True):
        st.markdown('**YOUR NEXT MOVE**')
        st.subheader(f'{len(blocked)} products need your attention' if blocked else 'Your replenishment plan is ready')
        st.write('Review quantities below. Open any product to see its delivery plan and reasoning.')
        for pid in blocked[:2]:
            if st.button('Review '+results[pid]['product']['name'],key='attention_'+pid):product_detail(pid)
        active=event_summary(analysis)
        if active:
            st.caption(f"Event scenario active: {active[0]['title']} · {len(active)} products")
            if st.button('Remove event scenario'):
                S.overrides=clear_event_overrides(S.overrides);recalculate();reset_selection();st.rerun()
        with st.expander('Get an AI summary'):
            st.caption('Optional: sends calculated SKU recommendations and budget to the configured team gateway.')
            if st.button('Generate briefing'):
                try:
                    with st.spinner('Summarising your plan…'):S.briefing=brief(analysis)
                except ValueError as e:st.info(str(e))
            if S.get('briefing'):st.write(S.briefing[0])
    with right,st.container(border=True):
        st.markdown('**AROUND YOUR STORE**');st.subheader('A little local context')
        if not S.location:
            st.caption('Add your location to check nearby events.');st.button('Add store location',on_click=go,args=('Store',))
        else:
            st.caption(f"Within {S.radius:g} km · next 14 days")
            if st.button('Check nearby events',width='stretch'):
                with st.spinner('Checking published venue listings…'):
                    S.event_report=discover_events(S.location,(today_sg()+timedelta(days=1)).isoformat(),(today_sg()+timedelta(days=14)).isoformat(),S.radius)
            report=S.get('event_report')
            if report:
                if report['status'] in ['unavailable','outside_coverage']:st.info(report['message'])
                elif not report['events']:st.info('No matching events found in the connected listings. Other venues may still have events.')
                else:
                    for i,event in enumerate(report['events'][:3]):
                        st.markdown('**'+escape(event['title'])+'**');st.caption(f"{event['start']} · about {event['distance_km']:.1f} km")
                        if st.button('Preview demand impact',key='event_'+str(i),width='stretch'):event_detail(event)
                    if len(report['events'])>3:
                        with st.expander(f"{len(report['events'])-3} more events"):
                            for i,event in enumerate(report['events'][3:],3):
                                st.write(event['title']);st.caption(event['start'])
                                if st.button('Preview impact',key='event_'+str(i)):event_detail(event)
                if report['status']=='partial':st.caption('Some source pages could not be checked; results are incomplete.')
                st.caption('Checked '+report['checked_at'][:16].replace('T',' ')+' SGT')
            else:st.caption('Check event dates, then preview an assumption before changing your order.')
            st.caption('Coverage: Esplanade listings only. Not a complete scan of nearby venues.')
    st.subheader('Your restock list')
    search,view=st.columns([2,1]);query=search.text_input('Find a product',placeholder='Search your catalogue…',label_visibility='collapsed');mode=view.selectbox('Show',['Needs action','All products'],label_visibility='collapsed')
    ordered=sorted(results,key=lambda p:(results[p]['plan']['status']!='blocked',(results[p]['forecast'] or {}).get('shortage_day') or 999))
    shown=[pid for pid in ordered if query.casefold() in results[pid]['product']['name'].casefold() and (mode=='All products' or results[pid]['plan']['status']!='no_purchase_needed')]
    show_all=st.toggle(f'Show all {len(shown)} products',False) if len(shown)>6 else True
    for pid in (shown if show_all else shown[:6]):
        r=results[pid];f=r['forecast'];plan=r['plan'];valid=plan['status']=='ready'
        with st.container(border=True):
            a,b,c,d,e=st.columns([.28,2.8,1,1.1,1],vertical_alignment='center')
            checked=a.checkbox('Include '+r['product']['name'],value=pid in S.selected and valid,key=f'pick_{S.selection_version}_{pid}',disabled=not valid,label_visibility='collapsed')
            if checked and pid not in S.selected:S.selected=S.selected+[pid]
            elif not checked and pid in S.selected:S.selected=[p for p in S.selected if p!=pid]
            b.markdown('**'+escape(r['product']['name'])+'**');b.caption('Needs your attention' if plan['status']=='blocked' else (f"Stock gap in {f['shortage_day']} days" if f and f['shortage_day'] else 'Stock is covered'))
            b.caption(f"{r['config']['stock']} on hand ? {r['config']['incoming']} incoming")
            c.markdown(f"**{f['quantity'] if f else '—'}** units");d.markdown('**'+(money(plan['cost_cents']) if 'cost_cents' in plan else 'Review needed')+'**')
            if e.button('Details',key='detail_'+pid,width='stretch'):product_detail(pid)
    if not shown:st.info('No products match this view.')
    S.selected=[p for p in S.selected if p in ready];total=sum(results[p]['plan']['cost_cents'] for p in S.selected)
    with st.container(border=True):
        a,b=st.columns([2,1],vertical_alignment='center');a.markdown(f"### {len(S.selected)} products · {money(total)}");a.caption('Selected across the full catalogue, including hidden rows. Includes delivery fees.')
        if total>analysis['budget_cents']:a.warning('Over budget. Remove products or update Store settings.')
        if b.button('Review this order →',type='primary',disabled=not S.selected or total>analysis['budget_cents'],width='stretch'):
            try:S.active_batch=save_draft(draft_payload(analysis,S.selected));S.route='Orders';st.rerun()
            except ValueError as e:st.error(str(e))
    with st.expander('See 14-day stock coverage'):
        with_plan=st.toggle('Include recommended arrivals',True);st.markdown(risk_map(results,ordered,S.settings['date'],with_plan),unsafe_allow_html=True)
    st.caption(f"Inventory snapshot {S.settings['date']} · forecasts cover the next 14 days. Missing observations are not assumed zero.")

elif S.route=='Orders':
    heading('ORDERS','Review, then decide.','Your quantities, costs and assumptions stay together in one record.')
    batches=list_batches()
    if not batches:
        st.info('Your review queue is empty. Start with a restock plan.');st.button('Build my first order →',type='primary',on_click=go,args=('Today',))
    else:
        ids=[r['id'] for r in batches];labels={r['id']:r['id']+' · '+r['status'].replace('_',' ').title() for r in batches}
        chosen=st.selectbox('Order',ids,index=ids.index(S.active_batch) if S.get('active_batch') in ids else 0,format_func=labels.get)
        row=next(r for r in batches if r['id']==chosen);payload=json.loads(row['payload']);st.caption(row['status'].replace('_',' '))
        st.markdown(order_document(chosen,payload),unsafe_allow_html=True)
        with st.expander('Assumptions and calculation evidence'):st.json(payload)
        if row['status']=='DRAFT':
            if S.get('role','Operator')!='Manager':st.info('A manager must review this draft. Use Review role in the sidebar to try the simulated Manager role.')
            else:
                with st.form('review_'+chosen):
                    confirmed=st.checkbox('I reviewed the quantities, costs and assumptions.',key='review_confirm')
                    a,b=st.columns(2);approve=a.form_submit_button('Approve simulation',type='primary',width='stretch');reject=b.form_submit_button('Reject draft',width='stretch')
                if approve or reject:
                    if approve and not confirmed:st.warning('Confirm the review before approval.')
                    elif review(chosen,row['payload'],'APPROVED_SIMULATION' if approve else 'REJECTED',S.role):st.rerun()
                    else:st.error('The saved draft changed. Refresh and review it again.')
        else:st.success('Review recorded. No real order was sent.')
        a,b=st.columns(2);lines=[dict(Product=o.get('product','Legacy product'),Supplier=o['supplier'],Units=o['quantity'],Arrival_day=o['delivery_days'],Cost_SGD=o['cost_cents']/100) for o in payload['plan']['orders']]
        if lines:a.download_button('Download order CSV',csv_text(lines),file_name=chosen+'.csv',mime='text/csv',width='stretch')
        b.download_button('Download audit record',json.dumps(dict(row,payload=payload),indent=2),file_name=chosen+'.json',mime='application/json',width='stretch')
        st.caption('Approval does not reserve inventory or confirm arrivals. Check overlapping orders.')
        st.button('← Back to my restock plan',on_click=go,args=('Today',))

elif S.route=='Store':
    heading('STORE','Make it your store.','Set up this session. Adjust when your stock or trading conditions change.')
    render_store()

elif S.route=='Evidence':
    heading('EVIDENCE','Know what the numbers mean.','Check held-out forecasts, with cost and service shown together.')
    st.write('We hold out the final 14 days and compare three forecasting methods on the same dates.')
    if st.button('Run offline evaluation',type='primary'):
        with st.spinner('Comparing forecasts and purchasing outcomes…'):S.evaluation=evaluate(S.dataset)
    report=S.get('evaluation')
    if report and report['dataset']==S.dataset['fingerprint']:
        st.caption(f"{report['source']} · evaluated {report['run_date']}")
        if report['summary']:
            st.dataframe(pd.DataFrame(report['summary']).round(2),hide_index=True,width='stretch');st.caption('MAE: units of error. MAPE: percentage error for nonzero sales. WAPE: total absolute error / total sales. Lower is better.')
            decisions=pd.DataFrame(report['decisions']);st.subheader('Cost and service, together');st.dataframe(decisions.groupby('policy')[['cost_SGD','stockout_days','lost_units']].sum().round(2),width='stretch')
            st.info('A cheaper order can miss early demand. These results do not establish real-store savings.')
            with st.expander('Per-product results & assumptions'):st.dataframe(pd.DataFrame(report['forecasts']).round(2),hide_index=True);st.write(report['notes'])
        if report['skipped']:st.warning(f"Skipped {len(report['skipped'])} products without 42 consecutive observations.")
        st.download_button('Download evaluation',json.dumps(report,indent=2),file_name='stockpilot-evaluation.json',mime='application/json')
    with st.expander('Sources & product boundaries'):
        st.write('Forecasts use recent weekly patterns. Esplanade event coverage is incomplete. Straight-line proximity is not attendance, footfall or sales uplift. Scenarios change selected products after confirmation.')
        st.write('Supplier terms and review roles are simulated. Allocation searches exact quantities with one or two suppliers, up to 2,000 units per product. Approvals do not dispatch orders or reserve inventory.')
        st.markdown('[Esplanade listings](https://www.esplanade.com/whats-on) · [Photon address lookup](https://github.com/komoot/photon) · [OpenStreetMap attribution](https://www.openstreetmap.org/copyright)')
    st.button('← Back to my restock plan',on_click=go,args=('Today',))
