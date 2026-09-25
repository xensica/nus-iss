"""StockPilot - a guided, human-reviewed purchasing workspace."""
import json
import sys
from datetime import date, timedelta
from html import escape
from pathlib import Path
import pandas as pd
import streamlit as st

sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from purchase_demo.catalogue import DEFAULTS, analyse
from purchase_demo.data_io import load_dataset, csv_text
from purchase_demo.evaluation import evaluate
from purchase_demo.gateway import brief
from purchase_demo.storage import draft_payload, save_draft, list_batches, review
from purchase_demo.uci_import import prepare_uci
from purchase_demo.visuals import CSS, risk_map, order_document
from purchase_demo.local_context import search_places, discover_events
from purchase_demo.workspace import tea_demo, clear_event_overrides, event_summary, today_sg
from purchase_demo.ui_details import product_detail, event_detail

st.set_page_config(page_title='StockPilot · Your next restock',page_icon='🌱',layout='wide',initial_sidebar_state='expanded')
st.markdown(CSS,unsafe_allow_html=True)
S=st.session_state


def money(cents): return f'S${cents/100:,.2f}'
def go(page): S.route=page
def heading(kicker,title,body=''):
    st.markdown(f'<div class="eyebrow">{escape(kicker)}</div>',unsafe_allow_html=True)
    st.title(title)
    if body:st.caption(body)
def recalculate():
    S.analysis=analyse(S.dataset,S.settings,S.overrides);S.pop('briefing',None)
def reset_selection():
    S.selection_version=S.get('selection_version',0)+1
    S.selected=[pid for pid,r in S.analysis['results'].items() if r['plan']['status']=='ready']
def load_data(data,as_of):
    S.dataset=data;S.settings=dict(DEFAULTS,date=as_of);S.overrides={}
    S.pop('event_report',None);S.pop('evaluation',None);recalculate();reset_selection()

def change_location(location):
    S.location=dict(location);S.pop('event_report',None)
    S.overrides=clear_event_overrides(S.overrides);recalculate();reset_selection()

if 'route' not in S:
    S.route='Today';S.onboarded=False;S.store_name='Marina Bay Tea';S.store_type='Tea & drinks';S.location=None
    S.radius=2.0;S.selection_version=0
    load_data(tea_demo(),today_sg().isoformat())


def location_setup():
    st.caption('Find your public store location. Search shares this text with Photon / OpenStreetMap.')
    with st.form('location_search'):
        query=st.text_input('Mall, street or postal code',value='Marina Bay Sands' if S.location is None else S.location['label'],max_chars=180)
        find=st.form_submit_button('Find store location')
    if find:
        try:
            with st.spinner('Finding matching places…'):S.place_matches=search_places(query)
            if not S.place_matches:st.info('No match found. Try a landmark or enter coordinates below.')
        except ValueError as e:st.warning(str(e))
    if S.get('place_matches'):
        index=st.selectbox('Confirm the matching place',range(len(S.place_matches)),format_func=lambda i:S.place_matches[i]['label'])
        candidate=S.place_matches[index]
        st.caption(f"Map point: {candidate['lat']:.5f}, {candidate['lon']:.5f}. Confirm this is near your storefront.")
        if st.button('Use this location',type='primary'):
            change_location(candidate);S.pop('place_matches',None);st.rerun()
    with st.expander('Enter map coordinates instead'):
        with st.form('coordinates'):
            label=st.text_input('Location label','Near Marina Bay Sands')
            a,b=st.columns(2)
            lat=a.number_input('Latitude',1.1,1.5,float((S.location or {}).get('lat',1.2834)),format='%.6f')
            lon=b.number_input('Longitude',103.5,104.2,float((S.location or {}).get('lon',103.8607)),format='%.6f')
            if st.form_submit_button('Save map point'):
                change_location(dict(label=label,lat=lat,lon=lon,source='User-entered approximate map point'));st.rerun()
    st.caption('Location data © OpenStreetMap contributors · ODbL. Radius uses approximate straight-line distance.')


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
    a,b=st.columns([1,1],gap='large')
    with a,st.container(border=True):
        st.subheader('Store profile')
        with st.form('profile'):
            name=st.text_input('Store name',S.store_name,max_chars=80)
            kinds=['Tea & drinks','Convenience retail','Snacks & gifts','Other'];kind=st.selectbox('Store type',kinds,index=kinds.index(S.store_type))
            radius=st.slider('Nearby-event radius (km)',.5,5.0,float(S.radius),.5)
            if st.form_submit_button('Save store'):
                S.store_name=name.strip() or 'My store';S.store_type=kind
                if S.radius!=radius:
                    S.overrides=clear_event_overrides(S.overrides);recalculate();reset_selection()
                S.radius=radius;S.pop('event_report',None);st.rerun()
        location_setup()
    with b,st.container(border=True):
        st.subheader('Sales & current stock');st.caption(S.dataset['source'])
        sales=st.file_uploader('Daily sales CSV',type=['csv']);stock=st.file_uploader('Inventory CSV',type=['csv'])
        snapshot=st.date_input('Inventory snapshot date',date.fromisoformat(S.settings['date']))
        if st.button('Load files & build my plan',type='primary',disabled=sales is None or stock is None,width='stretch'):
            try:load_data(load_dataset(sales.getvalue(),stock.getvalue()),snapshot.isoformat());S.onboarded=True;S.route='Today';st.rerun()
            except ValueError as e:st.error(str(e))
        sample=tea_demo();a1,b1=st.columns(2);a1.download_button('Sales template',csv_text(sample['sales']),file_name='sales.csv',mime='text/csv');b1.download_button('Stock template',csv_text(sample['inventory']),file_name='inventory.csv',mime='text/csv')
        with st.expander('File format & data rules'):
            st.code('sales: date,product_id,units\ninventory: product_id,current_stock\noptional: incoming_units,incoming_day,name,category,unit_price_cents')
            st.write('Use UTF-8 CSV, ISO dates and nonnegative whole units. One row per product/day. Include explicit zeros. Product IDs must match. Maximum 15 products, 100,000 rows and 10 MB per daily file. Stock must match the snapshot date. Supplier terms remain simulated.')
        if st.button('Use the tea-shop sample instead'):
            load_data(tea_demo(),today_sg().isoformat());S.onboarded=True;S.route='Today';st.rerun()
    with st.expander('Budget & planning assumptions',expanded=True):
        with st.form('settings'):
            a,b,c=st.columns(3);budget=a.number_input('Purchasing budget (SGD)',0,1000000,int(S.settings['budget']));buffer=b.slider('Safety buffer (days)',0,5,int(S.settings['buffer_days']));asof=c.date_input('Analysis / stock snapshot',date.fromisoformat(S.settings['date']))
            a,b,c=st.columns(3);adjust=a.slider('Overall demand adjustment (%)',-50,100,int(S.settings['owner_adjustment']));quality=b.slider('Supplier quality minimum',0,100,int(S.settings['quality']));reliability=c.slider('Supplier on-time score minimum',0,100,int(S.settings['reliability']))
            a,b,c=st.columns(3);manual=a.checkbox('Model a known promotion',value=S.settings['scenario']!='Normal trading');start=b.number_input('Starts on forecast day',1,14,int(S.settings['event_start']));duration=c.number_input('Duration (days)',1,14,int(S.settings['event_duration']));uplift=a.slider('Assumed promotion uplift (%)',0,100,int(S.settings['uplift']))
            st.caption('Promotion effects are your assumptions. Product and nearby-event overrides take priority.')
            if st.form_submit_button('Save & see my plan →',type='primary'):
                if asof.isoformat()!=S.settings['date']:
                    S.overrides=clear_event_overrides(S.overrides);S.pop('event_report',None)
                S.settings=dict(DEFAULTS,date=asof.isoformat(),budget=budget,buffer_days=buffer,owner_adjustment=adjust,quality=quality,reliability=reliability,scenario='Promotion / event' if manual else 'Normal trading',event_start=start,event_duration=duration,uplift=uplift)
                recalculate();reset_selection();S.onboarded=True;S.route='Today';st.rerun()
    with st.expander('Import a UCI-format transaction ledger'):
        raw=st.file_uploader('Transaction CSV',type=['csv'],key='uci_file');fmt=st.text_input('Timestamp format','%m/%d/%Y %H:%M');cap=st.number_input('Maximum units per transaction',1,1000000,1000)
        complete=st.checkbox('The ledger is complete; missing product/day transactions may be treated as zero.')
        if st.button('Prepare transaction data',disabled=raw is None or not complete):
            try:
                data=prepare_uci(raw.getvalue(),fmt,max_transaction_units=cap);load_data(data,data['cleaning']['analysis_date']);S.onboarded=True;S.route='Today';st.rerun()
            except ValueError as e:st.error(str(e))
        st.caption('Customer identifiers are not retained. Stock, supplier terms and SGD purchase prices remain simulated. Returns are excluded, not netted.')

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
