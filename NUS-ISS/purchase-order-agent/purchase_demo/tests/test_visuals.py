from purchase_demo.catalogue import analyse, DEFAULTS
from purchase_demo.data_io import sample_data
from purchase_demo.visuals import risk_map, shipment_cards, order_document
from purchase_demo.storage import draft_payload


def test_coverage_map_uses_actual_balances():
    analysis=analyse(sample_data(),dict(DEFAULTS))
    results=analysis['results']
    before=risk_map(results,list(results),'2026-09-24')
    after=risk_map(results,list(results),'2026-09-24',True)
    expected_before=sum(d['without_new_order']<0 for r in results.values() for d in r['forecast']['daily'])
    expected_after=sum(v<0 for r in results.values() for v in r['plan'].get('balances',[d['without_new_order'] for d in r['forecast']['daily']]))
    assert before.count('class="tile risk"')==expected_before
    assert after.count('class="tile risk"')==expected_after
    assert expected_after<expected_before


def test_custom_components_escape_uploaded_names():
    analysis=analyse(sample_data(),dict(DEFAULTS))
    r=analysis['results']['COF']
    r['product']['name']='<script>alert(1)</script>'
    markup=risk_map({'COF':r},['COF'],'2026-09-24')
    assert '<script>' not in markup and '&lt;script&gt;' in markup
    payload=draft_payload(analysis,['COF'])
    markup=order_document('TEST',payload)
    assert '<script>' not in markup and '&lt;script&gt;' in markup


def test_shipment_cards_order_by_actual_arrival():
    result=analyse(sample_data(),dict(DEFAULTS))['results']['COF']
    html=shipment_cards(result['plan']['orders'])
    assert html.index('estimated day 4')<html.index('estimated day 7')
    assert 'S$177.60' in html and 'S$550.80' in html
