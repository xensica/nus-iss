"""Offline, fixed-origin 14-day holdout. Run: python -m purchase_demo.evaluation."""
import argparse
import json
import math
from datetime import date, timedelta
from pathlib import Path
from .catalogue import DEFAULTS, suppliers_for
from .data_io import sample_data, load_dataset
from .engine import forecast, plan


def metrics(actual, predicted):
    errors=[abs(a-p) for a,p in zip(actual,predicted)]
    nonzero=[abs(a-p)/a for a,p in zip(actual,predicted) if a]
    return dict(MAE=sum(errors)/len(errors),
        MAPE=100*sum(nonzero)/len(nonzero) if nonzero else None,
        WAPE=100*sum(errors)/sum(actual) if sum(actual) else None)


def replay(actual, stock, orders):
    balance=stock
    stockout_days=0
    lost_units=0
    for day, demand in enumerate(actual,1):
        balance+=sum(o['quantity'] for o in orders if o['delivery_days']==day)
        if demand>balance:
            stockout_days+=1
            lost_units+=demand-balance
        balance=max(0,balance-demand)
    return dict(stockout_days=stockout_days,lost_units=lost_units,ending_stock=balance)


def evaluate(dataset):
    rows, decisions, skipped=[],[],[]
    aggregates={name:([],[]) for name in ('Weekday average','Last week','Moving average')}
    for product in dataset['products']:
        records=product['history']
        dates=[date.fromisoformat(r['date']) for r in records]
        if len(records)<42 or any((b-a).days!=1 for a,b in zip(dates,dates[1:])):
            skipped.append(product['product_id'])
            continue
        train,test=records[:-14],records[-14:]
        as_of=train[-1]['date']
        avg=sum(r['units'] for r in train[-28:])/28
        stock=math.ceil(avg*5)  # same synthetic starting stock for every purchasing policy
        cfg=dict(DEFAULTS,date=as_of,stock=stock,incoming=0,incoming_day=1,budget=1_000_000)
        prediction=forecast(cfg,train)
        actual=[r['units'] for r in test]
        forecasts={'Weekday average':[d['demand'] for d in prediction['daily']],
            'Last week':[train[-7+i%7]['units'] for i in range(14)],
            'Moving average':[math.ceil(avg)]*14}
        for method, predicted in forecasts.items():
            rows.append(dict(product_id=product['product_id'],method=method,
                train_end=as_of,test_start=test[0]['date'],test_end=test[-1]['date'],**metrics(actual,predicted)))
            aggregates[method][0].extend(actual)
            aggregates[method][1].extend(predicted)
        suppliers=suppliers_for(product)
        agent=plan(cfg,prediction,suppliers)
        # One decision at the same origin: reorder if stock < 7-day mean + buffer;
        # order up to 14-day mean + buffer from cheapest threshold-eligible supplier.
        qty=max(0,math.ceil(avg*15-stock)) if stock<avg*8 else 0
        baseline_orders=[]
        candidates=[s for s in suppliers if s['minimum']<=qty<=s['capacity'] and s['quality']>=cfg['quality'] and s['reliability']>=cfg['reliability']]
        if candidates:
            s=min(candidates,key=lambda s:qty*s['price']+s['fee'])
            baseline_orders=[dict(quantity=qty,delivery_days=s['days'],cost_cents=qty*s['price']+s['fee'])]
        for policy,orders,feasible in [('Agent',agent.get('orders',[]),agent['status']!='blocked'),('Reorder-point baseline',baseline_orders,qty==0 or bool(candidates))]:
            decisions.append(dict(product_id=product['product_id'],policy=policy,feasible=feasible,
                cost_SGD=sum(o['cost_cents'] for o in orders)/100,**replay(actual,stock,orders)))
    summary=[dict(method=method,**metrics(a,p)) for method,(a,p) in aggregates.items() if a]
    return dict(dataset=dataset['fingerprint'],source=dataset['source'],run_date=date.today().isoformat(),
        horizon=14,summary=summary,forecasts=rows,decisions=decisions,skipped=skipped,
        notes='Fixed-origin last-14-day holdout; at least 42 consecutive daily observations required. Missing days are not treated as zero. MAPE excludes zero actuals; WAPE undefined for all-zero actuals. Purchasing replay is simulated, with identical starting stock (5 days of training mean), no incoming stock, one decision, lost sales and unchanged supplier constraints. Baseline buys on a 7-day reorder point from cheapest eligible supplier; unlike the agent it does not check daily coverage. Costs and service must be read together, not as like-for-like savings. No accuracy or savings target is asserted as achieved.')


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--data',type=Path)
    args=parser.parse_args()
    dataset=load_dataset((args.data/'sales.csv').read_bytes(),(args.data/'inventory.csv').read_bytes()) if args.data else sample_data()
    print(json.dumps(evaluate(dataset),indent=2))
