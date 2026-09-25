"""Catalogue planning, deterministic explanations and delivery stress testing."""
from copy import deepcopy
from .engine import SUPPLIERS, forecast, plan

DEFAULTS=dict(date='2026-09-24', scenario='Normal trading', event_start=5,
    event_duration=3, uplift=40, owner_adjustment=0, buffer_days=1,
    quality=85, reliability=90, budget=10000)


def suppliers_for(product):
    result=deepcopy(SUPPLIERS)
    for s, multiplier in zip(result, (1, .8, .9)):
        s['price']=round(product['unit_price_cents']*multiplier)
    return result


def compare_suppliers(config, prediction, suppliers):
    rows=[]
    for s in suppliers:
        reasons=[]
        q=prediction['quantity']
        if s['quality']<config['quality']: reasons.append('Quality below minimum')
        if s['reliability']<config['reliability']: reasons.append('Reliability below minimum')
        share_ok=not reasons
        if q<s['minimum']: reasons.append('Full quantity below MOQ')
        if q>s['capacity']: reasons.append('Full quantity exceeds capacity')
        alone=plan(config,prediction,[s],config.get('urgent_quantity',0),config.get('urgent_days'))
        if not reasons and alone['status']=='blocked': reasons.append('Arrival misses daily coverage / deadline')
        rows.append(dict(Supplier=s['name'], Unit_price=s['price']/100,
            Delivery_fee=s['fee']/100, Estimated_days=s['days'], Quality=s['quality'],
            On_time_percent=s['reliability'], MOQ=s['minimum'], Capacity=s['capacity'],
            Whole_order='Eligible' if not reasons else '; '.join(reasons),
            Split_share='Eligible within MOQ/capacity; timing checked per allocation' if share_ok else 'Excluded by thresholds',
            Whole_order_cost=(q*s['price']+s['fee'])/100))
    return sorted(rows,key=lambda r:(r['Whole_order']!='Eligible',r['Whole_order_cost'],r['Estimated_days']))


def analyse(dataset, settings, overrides=None):
    results={}
    for product in dataset['products']:
        pid=product['product_id']
        config=dict(DEFAULTS,**settings)
        config.update(stock=product['current_stock'],incoming=product['incoming_units'],incoming_day=product['incoming_day'])
        override=(overrides or {}).get(pid,{})
        config.update(override)
        suppliers=suppliers_for(product)
        try:
            prediction=forecast(config,product['history'])
            proposal=plan(config,prediction,suppliers,config.get('urgent_quantity',0),config.get('urgent_days'))
            results[pid]=dict(product=product,config=config,forecast=prediction,plan=proposal,
                suppliers=suppliers, overrides=override)
        except ValueError as error:
            results[pid]=dict(product=product,config=config,forecast=None,
                plan=dict(status='blocked',reason=str(error)),suppliers=suppliers,overrides=override)
    total=sum(r['plan'].get('cost_cents',0) for r in results.values())
    return dict(results=results,total_cents=total,budget_cents=round(settings['budget']*100),
        over_budget=total>round(settings['budget']*100),source=dataset['source'],
        fingerprint=dataset['fingerprint'],settings=settings)


def stress_test(result, demand_increase=20, delivery_delay=2):
    """Replay the SAME allocation with stressed assumptions; this is not a probability."""
    import math
    cfg,f,p=result['config'],result['forecast'],result['plan']
    if f is None: return []
    balance=cfg['stock']
    rows=[]
    for day in f['daily']:
        d=day['day']
        if d==cfg['incoming_day']: balance+=cfg['incoming']
        balance+=sum(o['quantity'] for o in p.get('orders',[]) if o['delivery_days']+delivery_delay==d)
        balance-=math.ceil(day['demand']*(1+demand_increase/100))
        rows.append(dict(date=day['date'],day=d,balance=balance))
    return rows


def explanation(result):
    f,p,c=result['forecast'],result['plan'],result['config']
    if f is None: return p['reason']
    total=sum(d['demand'] for d in f['daily'])
    text=f"{total} forecast units + {f['safety']} safety units − {c['stock']} on hand − {c['incoming']} incoming = {f['quantity']} units to purchase (floored at zero)."
    if f['shortage_day']:
        text+=f" Without a new order, the first projected shortage is day {f['shortage_day']}."
    if len(p.get('orders',[]))>1:
        text+=' The earlier shipment covers demand before the cheaper later shipment arrives.'
    if p['status']=='blocked': text+=' '+p['reason']
    return text
