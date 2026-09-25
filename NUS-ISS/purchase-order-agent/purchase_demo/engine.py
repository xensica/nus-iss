import itertools
import json
import math
import random
from datetime import timedelta

SUPPLIERS = [
    dict(name='A • Express', price=200, fee=1500, days=2, minimum=50, capacity=1200, quality=95, reliability=98),
    dict(name='B • Economy', price=160, fee=1000, days=7, minimum=100, capacity=2000, quality=85, reliability=90),
    dict(name='C • Standard', price=180, fee=1200, days=4, minimum=50, capacity=1200, quality=90, reliability=95),
]


def history(as_of):
    rng = random.Random(42)
    return [dict(date=(as_of-timedelta(days=84-i)).isoformat(), units=max(1, round((38 if (as_of-timedelta(days=84-i)).weekday()<5 else 50)*(0.9+i/840)+rng.uniform(-7,7)))) for i in range(84)]


def forecast(config, records=None):
    from datetime import date
    as_of = date.fromisoformat(config['date'])
    records = history(as_of) if records is None else records
    records = sorted([r for r in records if r['date'] <= as_of.isoformat()], key=lambda r:r['date'])
    if not records:
        raise ValueError('No sales history exists on or before the analysis date.')
    recent = [r for r in records if r['date'] > (as_of-timedelta(days=28)).isoformat()]
    if not recent:
        raise ValueError('Sales history is stale: no observations in the last 28 days.')
    fallback = False
    daily = []
    for day in range(1,15):
        target = as_of + timedelta(days=day)
        matches = [r['units'] for r in recent if date.fromisoformat(r['date']).weekday()==target.weekday()]
        if len(matches) < 2:
            matches = [r['units'] for r in recent]
            fallback = True
        baseline = math.ceil(sum(matches)/len(matches))
        uplift = config['uplift']/100 if config['event_start'] <= day < config['event_start']+config['event_duration'] and config['scenario'] != 'Normal trading' else 0
        units = math.ceil(baseline*(1+config['owner_adjustment']/100)*(1+uplift))
        daily.append(dict(day=day, date=target.isoformat(), baseline=baseline, demand=units))
    safety = math.ceil(sum(r['demand'] for r in daily)/14*config['buffer_days'])
    need = max(0, sum(r['demand'] for r in daily)+safety-config['stock']-config['incoming'])
    balance = config['stock']
    shortage = None
    for r in daily:
        if r['day']==config['incoming_day']:
            balance += config['incoming']
        balance -= r['demand']
        r['without_new_order'] = balance
        if balance < 0 and shortage is None:
            shortage = r['day']
    return dict(daily=daily, safety=safety, quantity=need, shortage_day=shortage,
                reorder_point=sum(r['demand'] for r in daily[:7])+safety,
                method='Recent-mean fallback' if fallback else 'Recent weekday average',
                observations=len(recent), needs_review=fallback or len(recent)<28)


def plan(config, prediction, suppliers=None, urgent_quantity=0, urgent_days=None):
    suppliers = SUPPLIERS if suppliers is None else suppliers
    quantity = prediction['quantity']
    if quantity > 2000:
        return dict(status='blocked', reason='This demo supports at most 2,000 units per plan. Reduce the scenario or increase existing stock.')
    eligible = [s for s in suppliers if s['quality'] >= config['quality'] and s['reliability'] >= config['reliability'] and s.get('approved', True)]
    demands = [r['demand'] for r in prediction['daily']]
    cumulative = list(itertools.accumulate(demands))
    def assess(orders):
        cost = sum(q*s['price']+s['fee'] for s,q in orders)
        for s,q in orders:
            if not s['minimum'] <= q <= s['capacity']:
                return None
        if urgent_quantity and (urgent_days is None or sum(q for s,q in orders if s['days']<=urgent_days)<urgent_quantity):
            return None
        balances = [config['stock'] + (config['incoming'] if d>=config['incoming_day'] else 0)
                    +sum(q for s,q in orders if s['days']<=d)-used for d,used in enumerate(cumulative,1)]
        if min(balances) < 0 or balances[-1] < prediction['safety']:
            return None
        return dict(cost_cents=cost, balances=balances,
                    orders=[dict(supplier=s['name'],quantity=q,delivery_days=s['days'],unit_price_cents=s['price'],delivery_fee_cents=s['fee'],cost_cents=q*s['price']+s['fee']) for s,q in orders])
    candidates = []
    if quantity==0:
        candidate=assess([])
        if candidate: candidates.append(candidate)
    else:
        for s in eligible:
            c=assess([(s,quantity)])
            if c: candidates.append(c)
        for a,b in itertools.combinations(eligible,2):
            for qa in range(a['minimum'], min(a['capacity'],quantity-b['minimum'])+1):
                qb=quantity-qa
                if qb>b['capacity']: continue
                c=assess([(a,qa),(b,qb)])
                if c: candidates.append(c)
    if not candidates:
        reason = ('Incoming stock covers the total quantity but arrives too late. Expedite that delivery or arrange an emergency transfer.' if quantity == 0 else 'No feasible allocation in the one-or-two-supplier, exact-quantity search. Check early shortages, MOQ, capacity, urgent deadlines and supplier thresholds. Consider expediting stock or changing the inputs.')
        return dict(status='blocked',reason=reason)
    best=min(candidates,key=lambda c:(c['cost_cents'],len(c['orders'])))
    singles=[c['cost_cents'] for c in candidates if len(c['orders'])==1]
    best['saving_cents']=min(singles)-best['cost_cents'] if singles else None
    best['status']=('no_purchase_needed' if quantity==0 else 'ready') if best['cost_cents']<=round(config['budget']*100) else 'over_budget'
    best['reason']='Cheapest feasible plan within this demo’s one-or-two-supplier, exact-quantity search. Delivery dates are estimates; not risk guarantees.'
    return best


def run_analysis(config, live=False):
    trace=[]
    prediction=None
    proposal=None
    if not live:
        trace.append('Loaded 84 days of simulated sales and owner settings.')
        prediction=forecast(config)
        trace.append('Forecasted 14 days using recent same-weekday sales; applied explicit scenario and owner adjustments.')
        proposal=plan(config,prediction)
        trace.append('Compared eligible supplier allocations against daily stock balances, minimum orders and budget.')
        return prediction,proposal,trace,'Simulation workflow completed. No live AI or internet research was used.'
    import os
    from pathlib import Path
    import requests
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).with_name('.env'))
    url=os.getenv('LLM_GATEWAY_URL','').rstrip('/')
    key=os.getenv('LLM_GATEWAY_API_KEY','')
    model=os.getenv('LLM_MODEL','')
    if not (url and key and model):
        raise ValueError('Live AI needs a .env file beside demo_app.py. Use simulation mode meanwhile.')
    instruction=('You are a purchasing agent for a simulated store. Reply only JSON. '
        'Available tools have no arguments: read_store, forecast_demand, plan_purchase. '
        'Call read_store then forecast_demand then plan_purchase. '
        'Tool request: {"type":"tool","name":"read_store"}. '
        'Final response: {"type":"answer","message":"brief explanation"}. '
        'Use returned numbers only. Events are hypothetical; never claim internet research. '
        'Delivery is estimated. Never approve or place orders. Report budget or feasibility blockers.')
    messages=[dict(role='system',content=instruction),dict(role='user',content='Analyse my configured store and prepare a purchasing recommendation.')]
    read=False
    for _ in range(6):
        r=requests.post(url+'/api/chat',headers={'X-API-Key':key},json=dict(model=model,messages=messages,stream=False,options={'num_predict':350}),timeout=60)
        if not r.ok: raise ValueError(f'Gateway HTTP {r.status_code}. No approval or order was made.')
        content=r.json().get('message',{}).get('content','').strip()
        if content.startswith('```') and content.endswith('```'): content='\n'.join(content.splitlines()[1:-1]).strip()
        try: action=json.loads(content)
        except json.JSONDecodeError:
            if proposal is not None: return prediction,proposal,trace,content
            raise ValueError('AI returned text before completing its tools. Try again or use simulation mode.')
        if not isinstance(action,dict): raise ValueError('Unexpected AI response.')
        messages.append(dict(role='assistant',content=content))
        if action.get('type')=='answer' and proposal is not None:
            return prediction,proposal,trace,str(action.get('message',''))
        name=action.get('name')
        if name=='read_store':
            read=True
            result=dict(settings=config,source='Simulated 84-day sales history; synthetic suppliers; no live event search')
        elif name=='forecast_demand' and read:
            prediction=forecast(config)
            result=dict(demand=sum(d['demand'] for d in prediction['daily']),quantity=prediction['quantity'],safety=prediction['safety'],shortage_day=prediction['shortage_day'])
        elif name=='plan_purchase' and prediction is not None:
            proposal=plan(config,prediction)
            result={k:v for k,v in proposal.items() if k!='balances'}
        else: raise ValueError('AI requested an unavailable tool or skipped required data. No orders created.')
        trace.append(f'{name}: '+json.dumps(result))
        messages.append(dict(role='user',content='Application tool result: '+json.dumps(result)))
    raise ValueError('Agent step limit reached. No order was created.')
