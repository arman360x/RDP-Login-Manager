import sqlite3
import os
import json
import base64
from datetime import datetime
from pathlib import Path


DB_DIR = Path.home() / ".rdpmanager"
DB_PATH = DB_DIR / "connections.db"


def get_db_path() -> Path:
    DB_DIR.mkdir(parents=True, exist_ok=True)
    return DB_PATH


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(get_db_path()))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            sort_order INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS connections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            hostname TEXT NOT NULL,
            port INTEGER DEFAULT 3389,
            username TEXT DEFAULT '',
            encrypted_password TEXT DEFAULT '',
            category_id INTEGER,
            screen_mode INTEGER DEFAULT 2,
            desktop_width INTEGER DEFAULT 1920,
            desktop_height INTEGER DEFAULT 1080,
            color_depth INTEGER DEFAULT 32,
            redirect_clipboard INTEGER DEFAULT 1,
            redirect_printers INTEGER DEFAULT 0,
            redirect_drives INTEGER DEFAULT 0,
            notes TEXT DEFAULT '',
            last_connected TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL
        );
    """)
    conn.commit()
    conn.close()


# --- Settings ---

def get_setting(key: str) -> str | None:
    conn = get_connection()
    row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else None


def set_setting(key: str, value: str):
    conn = get_connection()
    conn.execute(
        "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = ?",
        (key, value, value),
    )
    conn.commit()
    conn.close()


# --- Categories ---

def get_categories() -> list[dict]:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM categories ORDER BY sort_order, name").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_category(name: str) -> int:
    conn = get_connection()
    cur = conn.execute("INSERT INTO categories (name) VALUES (?)", (name,))
    conn.commit()
    cat_id = cur.lastrowid
    conn.close()
    return cat_id


def rename_category(cat_id: int, new_name: str):
    conn = get_connection()
    conn.execute("UPDATE categories SET name = ? WHERE id = ?", (new_name, cat_id))
    conn.commit()
    conn.close()


def delete_category(cat_id: int):
    conn = get_connection()
    conn.execute("DELETE FROM categories WHERE id = ?", (cat_id,))
    conn.commit()
    conn.close()


# --- Connections ---

def get_connections(category_id: int | None = None) -> list[dict]:
    conn = get_connection()
    if category_id is not None:
        rows = conn.execute(
            "SELECT * FROM connections WHERE category_id = ? ORDER BY name", (category_id,)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM connections ORDER BY name").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_connections_uncategorized() -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM connections WHERE category_id IS NULL ORDER BY name"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_connection_by_id(conn_id: int) -> dict | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM connections WHERE id = ?", (conn_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def add_connection(**kwargs) -> int:
    fields = [
        "name", "hostname", "port", "username", "encrypted_password",
        "category_id", "screen_mode", "desktop_width", "desktop_height",
        "color_depth", "redirect_clipboard", "redirect_printers",
        "redirect_drives", "notes",
    ]
    data = {f: kwargs.get(f) for f in fields if f in kwargs}
    cols = ", ".join(data.keys())
    placeholders = ", ".join(["?"] * len(data))
    conn = get_connection()
    cur = conn.execute(
        f"INSERT INTO connections ({cols}) VALUES ({placeholders})",
        list(data.values()),
    )
    conn.commit()
    conn_id = cur.lastrowid
    conn.close()
    return conn_id


def update_connection(conn_id: int, **kwargs):
    fields = [
        "name", "hostname", "port", "username", "encrypted_password",
        "category_id", "screen_mode", "desktop_width", "desktop_height",
        "color_depth", "redirect_clipboard", "redirect_printers",
        "redirect_drives", "notes", "last_connected",
    ]
    data = {f: kwargs[f] for f in fields if f in kwargs}
    if not data:
        return
    set_clause = ", ".join(f"{k} = ?" for k in data)
    conn = get_connection()
    conn.execute(
        f"UPDATE connections SET {set_clause} WHERE id = ?",
        list(data.values()) + [conn_id],
    )
    conn.commit()
    conn.close()


def delete_connection(conn_id: int):
    conn = get_connection()
    conn.execute("DELETE FROM connections WHERE id = ?", (conn_id,))
    conn.commit()
    conn.close()


def duplicate_connection(conn_id: int) -> int | None:
    original = get_connection_by_id(conn_id)
    if not original:
        return None
    data = dict(original)
    del data["id"]
    del data["created_at"]
    del data["last_connected"]
    data["name"] = f"{data['name']} (Copy)"
    return add_connection(**data)


def search_connections(query: str) -> list[dict]:
    conn = get_connection()
    pattern = f"%{query}%"
    rows = conn.execute(
        "SELECT * FROM connections WHERE name LIKE ? OR hostname LIKE ? OR username LIKE ? OR notes LIKE ? ORDER BY name",
        (pattern, pattern, pattern, pattern),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_last_connected(conn_id: int):
    update_connection(conn_id, last_connected=datetime.now().isoformat())


# --- Import / Export ---

def export_connections(master_password: str = None) -> dict:
    categories = get_categories()
    connections = get_connections()
    return {
        "version": 1,
        "exported_at": datetime.now().isoformat(),
        "categories": categories,
        "connections": connections,
    }


def import_connections(data: dict):
    cat_map = {}
    for cat in data.get("categories", []):
        existing = get_categories()
        found = next((c for c in existing if c["name"] == cat["name"]), None)
        if found:
            cat_map[cat["id"]] = found["id"]
        else:
            new_id = add_category(cat["name"])
            cat_map[cat["id"]] = new_id

    for conn_data in data.get("connections", []):
        conn_data.pop("id", None)
        conn_data.pop("created_at", None)
        conn_data.pop("last_connected", None)
        old_cat_id = conn_data.pop("category_id", None)
        if old_cat_id and old_cat_id in cat_map:
            conn_data["category_id"] = cat_map[old_cat_id]
        add_connection(**conn_data)
