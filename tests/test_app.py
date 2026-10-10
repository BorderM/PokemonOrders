from pokemonorders.app import create_app
from pokemonorders.db import create_user, dashboard_stats, list_requests


def make_app(tmp_path, monkeypatch):
    monkeypatch.setenv("POKEMONORDERS_DB", str(tmp_path / "test.db"))
    return create_app()


def login(client, username="person", password="secret"):
    return client.post("/login", data={"username": username, "password": password}, follow_redirects=True)


def test_login_required_for_request_form(tmp_path, monkeypatch):
    app = make_app(tmp_path, monkeypatch)
    resp = app.test_client().get("/")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_submit_bulk_request_uses_logged_in_user(tmp_path, monkeypatch):
    app = make_app(tmp_path, monkeypatch)
    create_user("person", "secret", "Person", "person@example.com")
    client = app.test_client()
    assert login(client).status_code == 200

    resp = client.post("/requests", data={
        "bulk_cards": "Misty's Starmie (DRI 047)\n2 Cramorant (LOR 050)",
        "language": "English",
        "minimum_condition": "Near Mint",
        "variant": "Reverse Holo",
        "seller": "bubusini",
        "notes": "same seller batch",
    }, follow_redirects=True)

    assert resp.status_code == 200
    assert b"Submitted 2 request lines." in resp.data
    assert dashboard_stats()["requests"] == 2
    rows = list_requests()
    assert {row["quantity"] for row in rows} == {1, 2}
    assert {row["name"] for row in rows} == {"Person"}


def test_admin_can_create_user_from_web(tmp_path, monkeypatch):
    app = make_app(tmp_path, monkeypatch)
    create_user("admin", "secret", "Admin", "admin@example.com", is_admin=True)
    client = app.test_client()
    assert login(client, "admin", "secret").status_code == 200

    resp = client.post("/admin/users", data={
        "username": "miko",
        "password": "pw12345",
        "display_name": "Miko",
        "email": "miko@example.com",
    }, follow_redirects=True)

    assert resp.status_code == 200
    assert b"User saved." in resp.data
    assert client.post("/login", data={"username": "miko", "password": "pw12345"}, follow_redirects=True).status_code == 200


def test_admin_page_requires_admin(tmp_path, monkeypatch):
    app = make_app(tmp_path, monkeypatch)
    create_user("person", "secret", "Person", "person@example.com")
    client = app.test_client()
    login(client)
    resp = client.get("/admin", follow_redirects=True)
    assert b"Admin access required." in resp.data
