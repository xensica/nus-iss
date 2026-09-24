import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from .migrations import migrate

DB=Path(__file__).with_name('demo_orders.db')


def connect(path=DB):
    connection=sqlite3.connect(path)
    connection.row_factory=sqlite3.Row
    migrate(connection)
    return connection


def draft_payload(analysis, selected):
    if not selected: raise ValueError('Select at least one product.')
    orders=[]
    evidence={}
    for pid in selected:
        result=analysis['results'][pid]
        if result['plan']['status']!='ready' or not result['plan'].get('orders'):
            raise ValueError('Only feasible purchase plans can become drafts.')
        for row in result['plan']['orders']:
            orders.append(dict(row,product_id=pid,product=result['product']['name']))
        evidence[pid]=dict(config=result['config'],forecast=result['forecast'],overrides=result['overrides'])
    total=sum(row['cost_cents'] for row in orders)
    if total>analysis['budget_cents']: raise ValueError('Selected products exceed the shared purchasing budget.')
    return dict(version=2,source=analysis['source'],dataset=analysis['fingerprint'],
        settings=analysis['settings'],evidence=evidence,plan=dict(orders=orders,cost_cents=total))


def save_draft(payload, path=DB):
    encoded=json.dumps(payload,sort_keys=True,ensure_ascii=False)
    fingerprint=hashlib.sha256(encoded.encode()).hexdigest()
    batch='SP-'+uuid4().hex[:8].upper()
    with connect(path) as connection:
        connection.execute('INSERT OR IGNORE INTO batches (id,fingerprint,status,payload) VALUES (?,?,?,?)',
            (batch,fingerprint,'DRAFT',encoded))
        return connection.execute('SELECT id FROM batches WHERE fingerprint=?',(fingerprint,)).fetchone()['id']


def list_batches(path=DB):
    with connect(path) as connection:
        return [dict(r) for r in connection.execute('SELECT * FROM batches ORDER BY rowid DESC')]


def review(batch_id, shown_payload, decision, role, path=DB):
    if role!='Manager': raise ValueError('Switch to the simulated Manager role to review.')
    if decision not in ('APPROVED_SIMULATION','REJECTED'): raise ValueError('Invalid review decision.')
    with connect(path) as connection:
        cursor=connection.execute("UPDATE batches SET status=?,reviewed_at=?,reviewed_role=? WHERE id=? AND status='DRAFT' AND payload=?",
            (decision,datetime.now(timezone.utc).isoformat(),role,batch_id,shown_payload))
        return cursor.rowcount==1
