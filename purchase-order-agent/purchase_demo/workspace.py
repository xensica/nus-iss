"""Small state helpers for the guided purchasing workspace."""
from copy import deepcopy
from datetime import datetime,timezone,timedelta
from .data_io import sample_data, assemble

TEA_NAMES=[('Jasmine milk tea','Tea'),('Roasted oolong tea','Tea'),('Mineral water','Drinks'),
    ('Oat milk tea','Tea'),('Peach green tea','Tea'),('Matcha biscuit','Snacks'),
    ('Roasted almonds','Snacks'),('Rice crackers','Snacks'),('Chocolate cookie','Snacks'),
    ('Lemon black tea','Tea'),('Butter biscuit','Snacks'),('Honey green tea','Tea')]


def today_sg():
    return datetime.now(timezone(timedelta(hours=8))).date()


def tea_demo():
    data=sample_data(today_sg())
    stock=deepcopy(data['inventory'])
    for row,(name,category) in zip(stock,TEA_NAMES): row.update(name=name,category=category)
    return assemble(data['sales'],stock,'Sample tea shop · synthetic sales, stock and suppliers')


def event_summary(analysis):
    return [dict(product_id=pid,**r['overrides']['event_evidence']) for pid,r in analysis['results'].items() if r['overrides'].get('event_evidence')]


def clear_event_overrides(overrides):
    output=deepcopy(overrides)
    for pid,values in output.items():
        if values.pop('event_evidence',None):
            for key in ['scenario','event_start','event_duration','uplift']: values.pop(key,None)
    return {pid:v for pid,v in output.items() if v}
