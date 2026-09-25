from pathlib import Path
from streamlit.testing.v1 import AppTest
from purchase_demo import storage


def test_all_pages_and_simulated_approval(tmp_path,monkeypatch):
    # Isolated database: UI tests never approve or alter the user's existing batches.
    path=tmp_path/'ui.db'
    original_list=storage.list_batches; original_save=storage.save_draft; original_review=storage.review
    monkeypatch.setattr(storage,'list_batches',lambda:original_list(path))
    monkeypatch.setattr(storage,'save_draft',lambda payload:original_save(payload,path))
    monkeypatch.setattr(storage,'review',lambda batch,payload,decision,role:original_review(batch,payload,decision,role,path))
    app=AppTest.from_file(str(Path(__file__).parents[1]/'demo_app.py'),default_timeout=30).run()
    assert not app.exception
    next(b for b in app.button if b.label=='Explore the sample store').click().run()
    assert not app.exception
    assert any(m.label=='Ready to restock' for m in app.metric)
    next(b for b in app.button if b.label=='Review this order →').click().run()
    assert not app.exception and original_list(path)
    assert app.session_state['route']=='Orders'
    for page in ['Store','Evidence']:
        app.button(key='nav_'+page).click().run()
        assert not app.exception, [e.message for e in app.exception]
    next(b for b in app.button if b.label=='Run offline evaluation').click().run()
    assert not app.exception
    app.button(key='nav_Orders').click().run()
    assert not app.exception
    assert not any(b.label=='Approve simulation' for b in app.button)
    app.selectbox(key='role').set_value('Manager').run()
    next(b for b in app.button if b.label=='Approve simulation').click().run()
    assert original_list(path)[0]['status']=='DRAFT'
    app.checkbox(key='review_confirm').check().run()
    next(b for b in app.button if b.label=='Approve simulation').click().run()
    assert not app.exception
    assert original_list(path)[0]['status']=='APPROVED_SIMULATION'


def test_product_review_stays_in_plan():
    app=AppTest.from_file(str(Path(__file__).parents[1]/'demo_app.py'),default_timeout=30).run()
    next(b for b in app.button if b.label=='Explore the sample store').click().run()
    app.button(key='detail_COF').click().run()
    assert not app.exception
    assert app.session_state['route']=='Today'
    assert any(s.value=='Jasmine milk tea' for s in app.subheader)
    next(b for b in app.button if b.label=='Remove from order').click().run()
    assert not app.exception and 'COF' not in app.session_state['selected']


def test_event_preview_needs_confirmation(monkeypatch):
    from datetime import date,timedelta
    from purchase_demo import local_context
    event=dict(id='fixture',title='Test concert',start=(date.today()+timedelta(days=2)).isoformat(),end=(date.today()+timedelta(days=2)).isoformat(),venue='Esplanade',distance_km=.9,url='https://www.esplanade.com/whats-on/test',source='Test fixture',date_note='Test date')
    monkeypatch.setattr(local_context,'discover_events',lambda *a,**kw:dict(events=[event],status='ok',checked_at='2026-09-25T10:00:00+08:00'))
    app=AppTest.from_file(str(Path(__file__).parents[1]/'demo_app.py'),default_timeout=30).run()
    next(b for b in app.button if b.label=='Explore the sample store').click().run()
    next(b for b in app.button if b.label=='Check nearby events').click().run()
    assert not app.exception
    app.button(key='event_0').click().run()
    assert not app.exception and not app.session_state['overrides']
    next(b for b in app.button if b.label=='Use this scenario').click().run()
    assert not app.exception
    assert app.session_state['overrides']['COF']['event_evidence']['title']=='Test concert'
    assert 'BAR' not in app.session_state['overrides']
    next(b for b in app.button if b.label=='Remove event scenario').click().run()
    assert not app.exception and not app.session_state['overrides']
