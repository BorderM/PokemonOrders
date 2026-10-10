import os

from pokemonorders.app import create_app
from pokemonorders.db import dashboard_stats


def test_submit_request(tmp_path, monkeypatch):
    monkeypatch.setenv('POKEMONORDERS_DB', str(tmp_path / 'test.db'))
    app = create_app()
    client = app.test_client()

    resp = client.post('/requests', data={
        'email': 'person@example.com',
        'name': 'Person',
        'card_name_code': "Misty's Starmie (DRI 047)",
        'language': 'English',
        'quantity': '2',
        'minimum_condition': 'Near Mint',
        'variant': 'Reverse Holo',
        'seller': 'bubusini',
        'notes': 'test note',
    }, follow_redirects=True)

    assert resp.status_code == 200
    assert b'Request submitted.' in resp.data
    assert dashboard_stats()['requests'] == 1


def test_admin_page_loads(tmp_path, monkeypatch):
    monkeypatch.setenv('POKEMONORDERS_DB', str(tmp_path / 'test.db'))
    app = create_app()
    resp = app.test_client().get('/admin')
    assert resp.status_code == 200
    assert b'Orders dashboard' in resp.data
