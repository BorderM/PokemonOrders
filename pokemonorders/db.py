from __future__ import annotations

import os
import sqlite3
from pathlib import Path

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS people (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    requester_id INTEGER NOT NULL,
    card_name_code TEXT NOT NULL,
    language TEXT NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1,
    minimum_condition TEXT NOT NULL,
    variant TEXT NOT NULL DEFAULT 'Default',
    seller TEXT,
    new_seller TEXT,
    notes TEXT,
    status TEXT NOT NULL DEFAULT 'requested',
    source TEXT NOT NULL DEFAULT 'web',
    FOREIGN KEY(requester_id) REFERENCES people(id)
);

CREATE TABLE IF NOT EXISTS pricing_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id INTEGER,
    requester_name TEXT,
    quantity INTEGER,
    card_product TEXT NOT NULL,
    requested_condition TEXT,
    purchased_condition TEXT,
    variant TEXT,
    unit_price REAL,
    total_price REAL,
    shipping_units REAL,
    seller TEXT,
    notes TEXT,
    source_sheet TEXT,
    source_row INTEGER,
    imported_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(request_id) REFERENCES requests(id)
);

CREATE TABLE IF NOT EXISTS shipping_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rule TEXT NOT NULL,
    units REAL NOT NULL DEFAULT 1,
    priority INTEGER DEFAULT 99,
    min_unit_value REAL,
    max_unit_value REAL,
    extra_units REAL DEFAULT 0
);
"""


def db_path() -> Path:
    return Path(os.environ.get("POKEMONORDERS_DB", "instance/pokemonorders.db"))


def connect() -> sqlite3.Connection:
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    with connect() as conn:
        conn.executescript(SCHEMA)


def upsert_person(email: str, name: str | None = None) -> int:
    clean_email = email.strip().lower()
    display_name = (name or clean_email.split("@")[0]).strip() or clean_email
    with connect() as conn:
        existing = conn.execute("SELECT id FROM people WHERE lower(email)=?", (clean_email,)).fetchone()
        if existing:
            if name:
                conn.execute("UPDATE people SET name=? WHERE id=?", (display_name, existing["id"]))
            return int(existing["id"])
        cur = conn.execute("INSERT INTO people(email, name) VALUES (?, ?)", (clean_email, display_name))
        return int(cur.lastrowid)


def list_people() -> list[sqlite3.Row]:
    with connect() as conn:
        return conn.execute("SELECT * FROM people ORDER BY name COLLATE NOCASE").fetchall()


def create_request(data: dict) -> int:
    requester_id = upsert_person(data["email"], data.get("name"))
    with connect() as conn:
        cur = conn.execute(
            """INSERT INTO requests(
                requester_id, card_name_code, language, quantity, minimum_condition,
                variant, seller, new_seller, notes, source
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                requester_id,
                data["card_name_code"].strip(),
                data["language"].strip(),
                int(data["quantity"]),
                data["minimum_condition"].strip(),
                data.get("variant", "Default").strip(),
                data.get("seller") or None,
                data.get("new_seller") or None,
                data.get("notes") or None,
                data.get("source", "web"),
            ),
        )
        return int(cur.lastrowid)


def list_requests(limit: int = 300) -> list[sqlite3.Row]:
    with connect() as conn:
        return conn.execute(
            """SELECT r.*, p.email, p.name
               FROM requests r
               JOIN people p ON p.id = r.requester_id
               ORDER BY r.id DESC
               LIMIT ?""",
            (limit,),
        ).fetchall()


def dashboard_stats() -> dict:
    with connect() as conn:
        row = conn.execute(
            """SELECT
                COUNT(*) AS requests,
                COALESCE(SUM(quantity),0) AS quantity,
                COUNT(DISTINCT requester_id) AS people
               FROM requests"""
        ).fetchone()
        priced = conn.execute("SELECT COUNT(*) AS count, COALESCE(SUM(total_price),0) AS value FROM pricing_entries").fetchone()
        return {
            "requests": row["requests"],
            "quantity": row["quantity"],
            "people": row["people"],
            "priced_entries": priced["count"],
            "priced_value": priced["value"],
        }
