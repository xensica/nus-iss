import copy
import json
from datetime import date,timedelta
from unittest.mock import Mock
import pytest
from purchase_demo.local_context import distance_km,parse_esplanade,discover_events,scenario_overrides,search_places
from purchase_demo.catalogue import analyse,DEFAULTS,compare_suppliers
from purchase_demo.data_io import sample_data
from purchase_demo.engine import forecast,plan
from purchase_demo.workspace import clear_event_overrides
from purchase_demo.storage import draft_payload


def listing():
    return {'url':'/whats-on/test','fields':{'Page Title':{'value':'Test show'},'Production Start Date':{'value':'2026-09-25T16:00:00Z'},'Production End Date':{'value':'2026-09-26T16:00:00Z'},'Production Performance Nature':[{'name':'Onsite'}]}}


def test_distance_and_singapore_dates():
    assert distance_km(1.2837,103.8607,1.2898,103.8558)<2
    assert distance_km(1.43,103.8,1.2898,103.8558)>10
    for v in [float('nan'),float('inf'),91]:
        with pytest.raises(ValueError):distance_km(v,0,0,0)
    html='<script id="__NEXT_DATA__">'+json.dumps({'a':[listing(),listing()]})+'</script>'
    rows,_=parse_esplanade(html)
    assert len(rows)==1 and rows[0]['start']=='2026-09-26' and rows[0]['end']=='2026-09-27'


def test_outside_coverage_never_means_no_events():
    get=Mock()
    report=discover_events(dict(lat=1.43,lon=103.8),'2026-09-25','2026-10-08',get=get)
    assert report['status']=='outside_coverage';get.assert_not_called()


def test_network_failure_is_not_empty_success():
    import requests
    report=discover_events(dict(lat=1.2837,lon=103.8607),'2026-09-25','2026-10-08',get=Mock(side_effect=requests.Timeout()))
    assert report['status']=='unavailable'


def test_online_only_and_malformed_pages_are_rejected():
    v=listing();v['fields']['Production Performance Nature']=[{'name':'Online'}]
    html='<script id="__NEXT_DATA__">'+json.dumps(v)+'</script>'
    assert parse_esplanade(html)[0]==[]
    with pytest.raises(ValueError):parse_esplanade('<html>No records</html>')


def test_programme_cards_deduplicate_and_ignore_school_events():
    card=dict(title='Family concert',startDate='2026-10-02T02:00:00Z',endDate='2026-10-02T00:00:00Z',url='/whats-on/family',venueTagKeys=['venue'])
    cards=[card,card,dict(card,title='For Schools Only',url='/whats-on/schools')]
    html='<script id="__NEXT_DATA__">'+json.dumps(cards)+'</script>'
    rows,_=parse_esplanade(html)
    assert len(rows)==1 and rows[0]['start']==rows[0]['end']=='2026-10-02'
    response=Mock();response.content=html.encode();response.text=html
    report=discover_events(dict(lat=1.2837,lon=103.8607),'2026-10-01','2026-10-08',get=Mock(return_value=response))
    assert report['status']=='ok' and len(report['events'])==1 and report['events'][0]['distance_km']<2
    other=discover_events(dict(lat=1.2837,lon=103.8607),'2026-11-01','2026-11-08',get=Mock(return_value=response))
    assert other['status']=='ok' and other['events']==[]


def test_places_exclude_other_countries_and_road_fragments():
    response=Mock();response.content=b'{}';response.json.return_value={'features':[
        {'properties':{'name':'Mall','countrycode':'SG'},'geometry':{'coordinates':[103.86,1.28]}},
        {'properties':{'name':'Road','countrycode':'SG','osm_key':'highway'},'geometry':{'coordinates':[103.86,1.28]}},
        {'properties':{'name':'Elsewhere','countrycode':'GB'},'geometry':{'coordinates':[0,51]}}]}
    assert [r['label'] for r in search_places('Mall',get=Mock(return_value=response))]==['Mall']


def test_scenario_is_scoped_and_audited_without_mutation():
    data=sample_data();settings=dict(DEFAULTS);base=analyse(data,settings)
    event=dict(title='Test concert',url='https://www.esplanade.com/whats-on/test',start='2026-09-27',end='2026-09-28',source='Test source',distance_km=1.2)
    before={'COF':{'buffer_days':2}}
    overrides=scenario_overrides(event,settings['date'],['COF'],12,before)
    assert before=={'COF':{'buffer_days':2}}
    result=analyse(data,settings,overrides)
    assert result['results']['TEA']==base['results']['TEA']
    assert overrides['COF']['event_start']==3 and overrides['COF']['event_duration']==2
    assert draft_payload(result,['COF'])['evidence']['COF']['overrides']['event_evidence']['url']==event['url']
    assert clear_event_overrides(overrides)==before
    with pytest.raises(ValueError):scenario_overrides(event,'2026-10-01',['COF'],12)


def test_decimal_percentage_and_urgent_comparison():
    records=[dict(date=(date(2026,9,24)-timedelta(days=i)).isoformat(),units=25) for i in range(28)]
    cfg=dict(DEFAULTS,stock=200,incoming=0,incoming_day=1,owner_adjustment=12,urgent_quantity=50,urgent_days=2)
    f=forecast(cfg,records)
    assert all(r['demand']==28 for r in f['daily'])
    result=analyse(sample_data(),dict(DEFAULTS))['results']['COF']
    config=dict(result['config'],urgent_quantity=100,urgent_days=2)
    rows=compare_suppliers(config,result['forecast'],result['suppliers'])
    assert all(r['Whole_order']!='Eligible' for r in rows if r['Estimated_days']>2)
    conflict=plan(config,dict(result['forecast'],quantity=0),urgent_quantity=100,urgent_days=1)
    assert conflict['status']=='blocked' and 'urgent' in conflict['reason'] and 'too late' not in conflict['reason']
