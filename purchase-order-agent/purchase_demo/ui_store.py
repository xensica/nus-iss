"""Store setup: profile, map, imports and planning preferences."""
from datetime import date
import streamlit as st
from .catalogue import DEFAULTS
from .data_io import load_dataset, csv_text
from .uci_import import prepare_uci
from .workspace import tea_demo, clear_event_overrides, today_sg
from .ui_state import load_data, recalculate, reset_selection
from .ui_location import location_setup

S = st.session_state

def render_store():
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
        with st.form('planning_settings_form'):
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
