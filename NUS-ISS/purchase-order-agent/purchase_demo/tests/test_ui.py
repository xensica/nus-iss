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
    assert any('Products in view' in m.value and '>12<' in m.value for m in app.markdown)
    next(b for b in app.button if b.label=='Create purchase-order drafts').click().run()
    assert not app.exception and original_list(path)
    for page in ['Product insights','Scenario lab','Data & settings','Performance']:
        app.radio(key='page').set_value(page).run()
        assert not app.exception, [e.message for e in app.exception]
    next(b for b in app.button if b.label=='Run offline evaluation').click().run()
    assert not app.exception
    app.radio(key='page').set_value('Purchase orders').run()
    assert not app.exception
    assert not any(b.label=='Approve simulation' for b in app.button)
    app.selectbox(key='role').set_value('Manager').run()
    next(b for b in app.button if b.label=='Approve simulation').click().run()
    assert original_list(path)[0]['status']=='DRAFT'
    app.checkbox[0].check().run()
    next(b for b in app.button if b.label=='Approve simulation').click().run()
    assert not app.exception
    assert original_list(path)[0]['status']=='APPROVED_SIMULATION'
