from pokemonorders.app import create_app, parse_bulk_cards
from pokemonorders.db import create_user, dashboard_stats, get_user_by_username, list_pricing_entries, list_requests


def make_app(tmp_path, monkeypatch):
    monkeypatch.setenv("POKEMONORDERS_DB", str(tmp_path / "test.db"))
    return create_app()


def login(client, username="person", password="secret"):
    return client.post("/login", data={"username": username, "password": password}, follow_redirects=True)


def test_default_admin_exists_and_public_dashboard_loads(tmp_path, monkeypatch):
    app = make_app(tmp_path, monkeypatch)
    client = app.test_client()

    assert get_user_by_username("admin") is not None
    assert client.post("/login", data={"username": "admin", "password": "admin"}, follow_redirects=True).status_code == 200

    client.post("/logout")
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"Recent requests" in resp.data


def test_submit_requires_login(tmp_path, monkeypatch):
    app = make_app(tmp_path, monkeypatch)
    resp = app.test_client().post("/requests", data={"bulk_cards": "Mew (FCO 29)"})
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_parse_bulk_cards_supports_hyphen_per_line_variants():
    rows = parse_bulk_cards("""
    Misty's Starmie (DRI 047) - Reverse Holo
    2 Cramorant (LOR 050) - Holo
    3x Black Bolt JP Booster Box
    Boss's Orders - Ghetsis (MEG 114)
    """)

    assert rows == [
        {"quantity": 1, "card_name_code": "Misty's Starmie (DRI 047)", "variant": "Reverse Holo"},
        {"quantity": 2, "card_name_code": "Cramorant (LOR 050)", "variant": "Holo"},
        {"quantity": 3, "card_name_code": "Black Bolt JP Booster Box", "variant": None},
        {"quantity": 1, "card_name_code": "Boss's Orders - Ghetsis (MEG 114)", "variant": None},
    ]


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


def test_submit_bulk_request_allows_per_card_variants(tmp_path, monkeypatch):
    app = make_app(tmp_path, monkeypatch)
    create_user("person", "secret", "Person", "person@example.com")
    client = app.test_client()
    login(client)

    resp = client.post("/requests", data={
        "bulk_cards": "Misty's Starmie (DRI 047) - Reverse Holo\n2 Cramorant (LOR 050) - Holo\nMew (FCO 29)",
        "language": "English",
        "minimum_condition": "Near Mint",
        "variant": "Default",
        "seller": "bubusini",
    }, follow_redirects=True)

    assert resp.status_code == 200
    rows = list_requests()
    variants_by_card = {row["card_name_code"]: row["variant"] for row in rows}
    assert variants_by_card["Misty's Starmie (DRI 047)"] == "Reverse Holo"
    assert variants_by_card["Cramorant (LOR 050)"] == "Holo"
    assert variants_by_card["Mew (FCO 29)"] == "Default"


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


def test_admin_can_parse_cardmarket_receipt_into_pricing_rows(tmp_path, monkeypatch):
    app = make_app(tmp_path, monkeypatch)
    create_user("boss", "secret", "Boss", "boss@example.com", is_admin=True)
    client = app.test_client()
    login(client, "boss", "secret")

    receipt = """
    1x    Magnezone Lv.48 (DP 8)
    #8
    EX
        3,99 €
    1x    Silvally GX (CEC 262)
    #262
    GD
        14,99 €
    """
    resp = client.post("/admin/pricing/receipt", data={"receipt": receipt, "requester_name": "Mikey"}, follow_redirects=True)

    assert resp.status_code == 200
    assert b"Imported 2 pricing rows from receipt." in resp.data
    rows = list_pricing_entries()
    assert len(rows) == 2
    assert rows[0]["requester_name"] == "Mikey"
    assert rows[0]["card_product"] == "Magnezone Lv.48 (DP 8)"
    assert rows[0]["requested_condition"] == "Excellent"
    assert rows[0]["total_price"] == 3.99
