"""In-place product and event reviews: keep people in the purchasing task."""
from datetime import date,timedelta
import altair as alt
import pandas as pd
import streamlit as st
from .catalogue import analyse,compare_suppliers,explanation,stress_test
from .visuals import shipment_cards
from .local_context import scenario_overrides
from .workspace import clear_event_overrides


def money(cents):return f'S${cents/100:,.2f}'
def apply_changes(overrides,reset=False):
    s=st.session_state;s.overrides=overrides;s.analysis=analyse(s.dataset,s.settings,overrides);s.pop('briefing',None)
    if reset:s.selected=[p for p,r in s.analysis['results'].items() if r['plan']['status']=='ready']
    s.selection_version+=1


def change_selection(pid,included):
    s=st.session_state
    s.selected=[p for p in s.selected if p!=pid] if included else list(dict.fromkeys(s.selected+[pid]))
    s.selection_version+=1


@st.dialog('Review this product',width='large')
def product_detail(pid):
    s=st.session_state;r=s.analysis['results'][pid];f=r['forecast'];plan=r['plan']
    st.subheader(r['product']['name'])
    if f is None:st.warning(plan['reason']);return
    a,b,c=st.columns(3);a.metric('Buy',f"{f['quantity']} units");b.metric('Total cost',money(plan.get('cost_cents',0)));c.metric('Without an order',f"Gap on day {f['shortage_day']}" if f['shortage_day'] else 'Covered')
    st.write(explanation(r))
    if plan['status']=='blocked':st.warning(plan['reason'])
    elif plan['orders']:st.markdown(shipment_cards(plan['orders']),unsafe_allow_html=True)
    if f['needs_review']:st.info('Limited recent history. Review the forecast before ordering.')
    if r['overrides'].get('event_evidence'):st.caption(f"Event scenario: {r['overrides']['event_evidence']['title']} · +{r['config']['uplift']}% chosen by you.")
    with st.expander('Why this plan?'):
        rows=[dict(date=d['date'],**{'Without order':d['without_new_order'],'With order':plan.get('balances',[x['without_new_order'] for x in f['daily']])[i]}) for i,d in enumerate(f['daily'])]
        frame=pd.DataFrame(rows).melt('date',var_name='Stock',value_name='Units')
        chart=alt.Chart(frame).mark_line(strokeWidth=2.5).encode(x=alt.X('date:T',title=None),y='Units:Q',color=alt.Color('Stock:N',scale=alt.Scale(range=['#aeb7b1','#28785f'])),tooltip=['date:T','Stock:N','Units:Q'])
        st.altair_chart(chart.properties(height=210).configure_view(stroke=None),width='stretch')
        st.dataframe(pd.DataFrame(compare_suppliers(r['config'],f,r['suppliers'])),hide_index=True,width='stretch')
        if plan.get('saving_cents') is not None:st.caption(f"{money(plan['saving_cents'])} below the cheapest feasible single supplier, using the same constraints.")
        st.caption(f"{f['method']} · {f['observations']} observations · safety buffer {f['safety']} units. Estimated deliveries; simulated terms.")
    with st.expander('What if demand rises or delivery is late?'):
        a,b=st.columns(2);up=a.slider('Extra demand (%)',0,100,20,key='stress_up');delay=b.slider('New deliveries delayed (days)',0,7,2,key='stress_delay')
        gaps=sum(x['balance']<0 for x in stress_test(r,up,delay));st.write(f'This same order has **{gaps} projected shortage days** under those assumptions.')
    with st.expander('Adjust this product'):
        with st.form('product_settings'):
            a,b=st.columns(2);buffer=a.slider('Safety buffer (days)',0,5,int(r['config']['buffer_days']));adjust=b.slider('Demand adjustment (%)',-50,100,int(r['config']['owner_adjustment']))
            urgent=a.number_input('Urgent units (optional)',0,2000,int(r['config'].get('urgent_quantity',0)));deadline=b.number_input('Urgent arrival by day',1,14,int(r['config'].get('urgent_days') or 2))
            if st.form_submit_button('Update recommendation',type='primary'):
                overrides=dict(s.overrides);overrides[pid]=dict(overrides.get(pid,{}),buffer_days=buffer,owner_adjustment=adjust,urgent_quantity=urgent,urgent_days=deadline)
                apply_changes(overrides);st.rerun()
    if plan['status']=='ready':
        included=pid in s.selected
        if st.button('Remove from order' if included else 'Add to order',type='primary',width='stretch',on_click=change_selection,args=(pid,included)):
            st.rerun()


@st.dialog('See the effect before you change the plan',width='large')
def event_detail(event):
    s=st.session_state;st.subheader(event['title'])
    st.caption(f"{event['start']} to {event['end']} · {event['venue']} · about {event['distance_km']:.1f} km away")
    st.link_button('Open the official listing',event['url'])
    st.write('Nearby activity may change demand. Choose an assumption to test; this listing does not tell us attendance or your sales uplift.')
    st.caption(event['date_note'])
    pids=list(s.analysis['results']);default=[p for p in pids if s.analysis['results'][p]['product']['category'] in ['Tea','Drinks']]
    selected=st.multiselect('Products affected',pids,default=default,format_func=lambda p:s.analysis['results'][p]['product']['name'])
    uplift=st.slider('Demand uplift to test (%)',0,50,10,help='Your what-if assumption, not an online statistic.')
    first=max(date.fromisoformat(event['start']),date.fromisoformat(s.settings['date'])+timedelta(days=1));last=min(date.fromisoformat(event['end']),date.fromisoformat(s.settings['date'])+timedelta(days=14))
    if first>last:st.info('Outside your stock-planning dates. Update the snapshot in Store settings first.');return
    a,b=st.columns(2);begin=a.date_input('Apply from',first,min_value=first,max_value=last);finish=b.date_input('Apply through',last,min_value=first,max_value=last)
    if finish<begin:st.warning('The end date must follow the start date.');return
    if not selected:st.info('Select a product to preview.');return
    chosen=dict(event,start=begin.isoformat(),end=finish.isoformat())
    baseline_overrides=clear_event_overrides(s.overrides);baseline=analyse(s.dataset,s.settings,baseline_overrides)
    overrides=scenario_overrides(chosen,s.settings['date'],selected,uplift,baseline_overrides);proposed=analyse(s.dataset,s.settings,overrides)
    rows=[]
    for pid in selected:
        before=baseline['results'][pid];after=proposed['results'][pid]
        rows.append({'Product':after['product']['name'],'Base units':before['forecast']['quantity'] if before['forecast'] else None,'Scenario units':after['forecast']['quantity'] if after['forecast'] else None,'Status':after['plan']['status'].replace('_',' ')})
    a,b=st.columns(2);a.metric('Base purchase plan',money(baseline['total_cents']));b.metric('Scenario purchase plan',money(proposed['total_cents']),money(proposed['total_cents']-baseline['total_cents']),delta_color='inverse')
    st.dataframe(pd.DataFrame(rows),hide_index=True,width='stretch')
    if any(r['plan']['status']=='blocked' for r in proposed['results'].values()):st.warning('Some products have no feasible order. Spend excludes blocked plans, so this cost difference is not like-for-like.')
    if proposed['over_budget']:st.warning('This scenario exceeds the shared budget. Select a smaller batch before drafting.')
    st.caption('Replaces the previous nearby-event scenario. Other product adjustments remain. The source and your assumption are saved with the order.')
    if st.button('Use this scenario',type='primary',width='stretch',on_click=apply_changes,args=(overrides,True)):st.rerun()
