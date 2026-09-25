import copy
import json
import sqlite3
import time
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import Mock
import pytest
from purchase_demo.data_io import sample_data, csv_text, load_dataset, load_sales, load_inventory
from purchase_demo.catalogue import analyse, DEFAULTS, stress_test, compare_suppliers
from purchase_demo.engine import forecast, plan, SUPPLIERS
from purchase_demo.evaluation import evaluate, metrics, replay
from purchase_demo.storage import draft_payload, save_draft, list_batches, review, connect
from purchase_demo.gateway import brief
from purchase_demo.uci_import import prepare_uci


@pytest.fixture(scope='module')
def dataset(): return sample_data()


@pytest.fixture(scope='module')
def analysis(dataset): return analyse(dataset,dict(DEFAULTS))


def config(**changes):
    return dict(DEFAULTS,stock=100,incoming=0,incoming_day=5,**changes)


def test_sample_roundtrip(dataset):
    loaded=load_dataset(csv_text(dataset['sales']),csv_text(dataset['inventory']))
    assert len(loaded['products'])==12
    assert loaded['products']==dataset['products']
    assert loaded['source'].startswith('Uploaded')


def test_export_neutralises_formula_labels():
    assert "'=HYPERLINK" in csv_text([dict(name='=HYPERLINK',units=2)])


def test_uci_preparation_audit_and_customer_exclusion():
    rows=['InvoiceNo,StockCode,Description,Quantity,InvoiceDate,UnitPrice,CustomerID']
    for i in range(60):
        d=(date(2011,1,1)+timedelta(days=i)).strftime('%m/%d/%Y')+' 08:00'
        rows.append(f'1000,X,Gift,10,{d},2.5,PRIVATE')
    rows.append('C100,X,Gift,10,01/01/2011 08:00,2.5,PRIVATE')
    data=prepare_uci('\n'.join(rows).encode())
    assert data['cleaning']['excluded_rows']==1
    assert len(data['sales'])==60
    assert 'PRIVATE' not in json.dumps(data)
    assert data['inventory'][0]['unit_price_cents']==200


@pytest.mark.parametrize('text',[
    'date,product_id,units\n2026-09-01,X,-2',
    'date,product_id,units\n2026-09-01,X,NaN',
    'date,product_id,units\n2026-09-01,X,2.5',
    'date,product_id,units\nnot-a-date,X,2',
    'date,product_id,units\n2026-09-01,X,2\n2026-09-01,X,3',
    'date,product_id\n2026-09-01,X',
    'date,product_id,units\n2026-09-01,X,2,extra',
    'date,product_id,units\n2026-09-01,=FORMULA,2',
])
def test_invalid_sales(text):
    with pytest.raises(ValueError): load_sales(text)


def test_inventory_validation():
    with pytest.raises(ValueError): load_inventory('product_id,current_stock,incoming_units\nX,10,2')
    with pytest.raises(ValueError): load_inventory('product_id,current_stock\nX,10\nX,20')
    with pytest.raises(ValueError): load_dataset('date,product_id,units\n2026-09-01,X,3','product_id,current_stock\nY,2')


def test_zero_quantity_still_detects_timing_shortage():
    cfg=dict(DEFAULTS,stock=0,incoming=1000,incoming_day=14)
    records=[dict(date=(date(2026,9,24)-timedelta(days=i)).isoformat(),units=10) for i in range(1,29)]
    f=forecast(cfg,records)
    assert f['quantity']==0 and f['shortage_day']==1
    assert plan(cfg,f)['status']=='blocked'


def test_sparse_and_stale_history():
    f=forecast(config(),[dict(date='2026-09-23',units=10)])
    assert f['needs_review'] and 'fallback' in f['method']
    with pytest.raises(ValueError): forecast(config(),[dict(date='2020-01-01',units=100)])


def test_future_observations_do_not_leak(dataset):
    records=dataset['products'][0]['history']
    assert forecast(config(),records)==forecast(config(),records+[dict(date='2030-01-01',units=999999)])


def test_event_only_changes_window(dataset):
    records=dataset['products'][0]['history']
    base=forecast(config(),records)
    changed=config(); changed.update(scenario='Event',event_start=5,event_duration=2,uplift=50)
    event=forecast(changed,records)
    for a,b in zip(base['daily'],event['daily']):
        assert (b['demand']>a['demand']) == (5<=a['day']<7)
    assert event['reorder_point']>base['reorder_point']


def test_catalogue_budget_and_performance(dataset,analysis):
    started=time.perf_counter(); result=analyse(dataset,dict(DEFAULTS,budget=2000))
    assert time.perf_counter()-started<10
    assert result['over_budget']
    selected=[pid for pid,r in result['results'].items() if r['plan']['status']=='ready']
    with pytest.raises(ValueError): draft_payload(result,selected)
    for r in analysis['results'].values():
        if r['plan']['status']=='ready':
            assert min(r['plan']['balances'])>=0
            assert r['plan']['balances'][-1]>=r['forecast']['safety']


def test_split_and_single_capacity_are_distinct():
    cfg=dict(DEFAULTS,stock=100,incoming=0,incoming_day=1)
    f=dict(quantity=200,safety=0,daily=[dict(demand=20) for _ in range(14)])
    suppliers=[dict(s,minimum=10,capacity=120,days=2) for s in SUPPLIERS]
    p=plan(cfg,f,suppliers)
    assert p['status']=='ready' and len(p['orders'])==2
    assert p['saving_cents'] is None
    rows=compare_suppliers(cfg,f,suppliers)
    assert all('capacity' in row['Whole_order'] for row in rows)
    assert all(row['Split_share'].startswith('Eligible') for row in rows)


def test_urgent_and_bounds(analysis):
    r=analysis['results']['COF']
    p=plan(r['config'],r['forecast'],r['suppliers'],urgent_quantity=100,urgent_days=2)
    assert p['status']=='ready'
    assert sum(o['quantity'] for o in p['orders'] if o['delivery_days']<=2)>=100
    assert plan(r['config'],r['forecast'],r['suppliers'],urgent_quantity=100,urgent_days=1)['status']=='blocked'
    assert plan(r['config'],dict(r['forecast'],quantity=2001))['status']=='blocked'


def test_stress_does_not_mutate_plan(analysis):
    r=copy.deepcopy(analysis['results']['COF']); before=copy.deepcopy(r)
    normal=stress_test(r,0,0)
    assert [d['balance'] for d in normal]==r['plan']['balances']
    assert min(d['balance'] for d in stress_test(r,100,5))<0
    assert r==before


def test_migration_preserves_legacy_rows(tmp_path):
    path=tmp_path/'old.db'
    with sqlite3.connect(path) as c:
        c.execute('CREATE TABLE batches (id TEXT PRIMARY KEY,fingerprint TEXT UNIQUE,status TEXT,payload TEXT,reviewed_at TEXT)')
        c.execute("INSERT INTO batches VALUES ('old','fp','DRAFT','{}',NULL)")
    connect(path).close(); connect(path).close()
    rows=list_batches(path)
    assert rows[0]['id']=='old' and rows[0]['reviewed_role'] is None


def test_dedup_role_and_tamper_guard(tmp_path,analysis):
    path=tmp_path/'orders.db'; payload=draft_payload(analysis,['COF','TEA'])
    batch=save_draft(payload,path)
    assert save_draft(payload,path)==batch
    row=list_batches(path)[0]
    with pytest.raises(ValueError): review(batch,row['payload'],'APPROVED_SIMULATION','Operator',path)
    assert not review(batch,'{}','APPROVED_SIMULATION','Manager',path)
    assert review(batch,row['payload'],'APPROVED_SIMULATION','Manager',path)
    assert not review(batch,row['payload'],'REJECTED','Manager',path)
    assert list_batches(path)[0]['reviewed_role']=='Manager'


def test_metrics_and_replay():
    assert metrics([0,10],[5,5])==dict(MAE=5,MAPE=50,WAPE=100)
    assert metrics([0],[0])['WAPE'] is None
    assert replay([3,4],2,[])==dict(stockout_days=2,lost_units=5,ending_stock=0)


def test_evaluation_split_reproducibility(dataset):
    a=evaluate(dataset); b=evaluate(dataset)
    assert a==b and len(a['summary'])==3 and len(a['decisions'])==24
    assert all(r['train_end']<r['test_start']<=r['test_end'] for r in a['forecasts'])
    assert not a['skipped']


def test_evaluation_excludes_sparse_series(dataset):
    data=copy.deepcopy(dataset); data['products'][0]['history'].pop(5)
    assert data['products'][0]['product_id'] in evaluate(data)['skipped']


def test_gateway_errors_never_expose_key(monkeypatch,analysis):
    monkeypatch.setenv('LLM_GATEWAY_URL','https://example.invalid')
    monkeypatch.setenv('LLM_GATEWAY_API_KEY','SECRET-CANARY')
    monkeypatch.setenv('LLM_MODEL','test')
    with pytest.raises(ValueError) as error: brief(analysis,Mock(side_effect=RuntimeError('SECRET-CANARY')))
    assert 'SECRET-CANARY' not in str(error.value)


def test_gateway_validates_sequence(monkeypatch,analysis):
    monkeypatch.setenv('LLM_GATEWAY_URL','https://example.invalid'); monkeypatch.setenv('LLM_GATEWAY_API_KEY','canary'); monkeypatch.setenv('LLM_MODEL','test')
    responses=[]
    for action in [dict(type='tool',name=n) for n in ['read_inventory','read_recommendations','check_budget']]+[dict(type='answer',message='Review blocked products.')]:
        response=Mock(); response.json.return_value={'message':{'content':json.dumps(action)}}; responses.append(response)
    text,trace=brief(analysis,Mock(side_effect=responses))
    assert len(trace)==3 and text=='Review blocked products.'
    response=Mock(); response.json.return_value={'message':{'content':'{"type":"tool","name":"approve"}'}}
    with pytest.raises(ValueError): brief(analysis,Mock(return_value=response))
