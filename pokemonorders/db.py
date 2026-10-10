from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from werkzeug.security import generate_password_hash

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS people (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    display_name TEXT NOT NULL,
    email TEXT,
    is_admin INTEGER NOT NULL DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    requester_id INTEGER NOT NULL,
    user_id INTEGER,
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
    FOREIGN KEY(requester_id) REFERENCES people(id),
    FOREIGN KEY(user_id) REFERENCES users(id)
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


def ensure_column(conn: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    cols = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}
    if column not in cols:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def init_db() -> None:
    with connect() as conn:
        conn.executescript(SCHEMA)
        ensure_column(conn, "requests", "user_id", "INTEGER REFERENCES users(id)")


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


def create_user(username: str, password: str, display_name: str | None = None, email: str | None = None, is_admin: bool = False) -> int:
    username = username.strip().lower()
    name = (display_name or username).strip()
    password_hash = generate_password_hash(password)
    with connect() as conn:
        existing = conn.execute("SELECT id FROM users WHERE username=?", (username,)).fetchone()
        if existing:
            conn.execute(
                "UPDATE users SET password_hash=?, display_name=?, email=?, is_admin=? WHERE id=?",
                (password_hash, name, email, int(is_admin), existing["id"]),
            )
            return int(existing["id"])
        cur = conn.execute(
            "INSERT INTO users(username, password_hash, display_name, email, is_admin) VALUES (?, ?, ?, ?, ?)",
            (username, password_hash, name, email, int(is_admin)),
        )
        return int(cur.lastrowid)


def get_user_by_username(username: str) -> sqlite3.Row | None:
    with connect() as conn:
        return conn.execute("SELECT * FROM users WHERE username=?", (username.strip().lower(),)).fetchone()


def get_user(user_id: int) -> sqlite3.Row | None:
    with connect() as conn:
        return conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()


def list_users() -> list[sqlite3.Row]:
    with connect() as conn:
        return conn.execute("SELECT * FROM users ORDER BY display_name COLLATE NOCASE").fetchall()


def list_people() -> list[sqlite3.Row]:
    with connect() as conn:
        return conn.execute("SELECT * FROM people ORDER BY name COLLATE NOCASE").fetchall()


def create_request(data: dict) -> int:
    requester_id = upsert_person(data["email"], data.get("name"))
    with connect() as conn:
        cur = conn.execute(
            """INSERT INTO requests(
                requester_id, user_id, card_name_code, language, quantity, minimum_condition,
                variant, seller, new_seller, notes, source
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                requester_id,
                data.get("user_id"),
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


def list_requests(limit: int = 300, user_id: int | None = None) -> list[sqlite3.Row]:
    sql = """SELECT r.*, p.email, p.name, u.display_name AS account_name
               FROM requests r
               JOIN people p ON p.id = r.requester_id
               LEFT JOIN users u ON u.id = r.user_id"""
    params: list[object] = []
    if user_id is not None:
        sql += " WHERE r.user_id = ?"
        params.append(user_id)
    sql += " ORDER BY r.id DESC LIMIT ?"
    params.append(limit)
    with connect() as conn:
        return conn.execute(sql, params).fetchall()


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
        users = conn.execute("SELECT COUNT(*) AS count FROM users").fetchone()
        return {
            "requests": row["requests"],
            "quantity": row["quantity"],
            "people": row["people"],
            "users": users["count"],
            "priced_entries": priced["count"],
            "priced_value": priced["value"],
        }
