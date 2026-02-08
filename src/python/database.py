"""SQLite database for tracking imported components."""

import os
import sqlite3
from datetime import datetime, timezone


_SCHEMA = """
CREATE TABLE IF NOT EXISTS components (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mpn TEXT UNIQUE NOT NULL,
    manufacturer TEXT,
    description TEXT,
    symbol_name TEXT,
    footprint_name TEXT,
    has_3d_model INTEGER DEFAULT 0,
    source_provider TEXT,
    source_url TEXT,
    referrer_url TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS import_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    component_id INTEGER,
    action TEXT NOT NULL,
    source_file TEXT,
    error_message TEXT,
    timestamp TEXT NOT NULL,
    FOREIGN KEY (component_id) REFERENCES components(id)
);
"""


class ComponentDB:
    def __init__(self, db_path: str):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(_SCHEMA)

    def close(self):
        self.conn.close()

    def upsert_component(self, mpn: str, symbol_name: str | None = None,
                         footprint_name: str | None = None,
                         has_3d_model: bool = False,
                         manufacturer: str | None = None,
                         description: str | None = None,
                         source_provider: str | None = None,
                         source_url: str | None = None,
                         referrer_url: str | None = None) -> int:
        """Insert or update a component by MPN. Returns the component ID."""
        now = datetime.now(timezone.utc).isoformat()
        cursor = self.conn.execute(
            """INSERT INTO components
               (mpn, manufacturer, description, symbol_name, footprint_name,
                has_3d_model, source_provider, source_url, referrer_url,
                created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(mpn) DO UPDATE SET
                   manufacturer=excluded.manufacturer,
                   description=excluded.description,
                   symbol_name=excluded.symbol_name,
                   footprint_name=excluded.footprint_name,
                   has_3d_model=excluded.has_3d_model,
                   source_provider=excluded.source_provider,
                   source_url=excluded.source_url,
                   referrer_url=excluded.referrer_url,
                   updated_at=excluded.updated_at
            """,
            (mpn, manufacturer, description, symbol_name, footprint_name,
             int(has_3d_model), source_provider, source_url, referrer_url,
             now, now)
        )
        self.conn.commit()
        # Get the ID
        row = self.conn.execute(
            "SELECT id FROM components WHERE mpn = ?", (mpn,)
        ).fetchone()
        return row["id"]

    def get_component(self, mpn: str) -> dict | None:
        """Get a component by MPN."""
        row = self.conn.execute(
            "SELECT * FROM components WHERE mpn = ?", (mpn,)
        ).fetchone()
        return dict(row) if row else None

    def component_exists(self, mpn: str) -> bool:
        """Check if a component exists."""
        row = self.conn.execute(
            "SELECT 1 FROM components WHERE mpn = ?", (mpn,)
        ).fetchone()
        return row is not None

    def list_components(self, limit: int = 100, offset: int = 0) -> list[dict]:
        """List components ordered by most recently updated."""
        rows = self.conn.execute(
            "SELECT * FROM components ORDER BY updated_at DESC LIMIT ? OFFSET ?",
            (limit, offset)
        ).fetchall()
        return [dict(r) for r in rows]

    def search_components(self, query: str) -> list[dict]:
        """Search components by MPN, manufacturer, or description."""
        like = f"%{query}%"
        rows = self.conn.execute(
            """SELECT * FROM components
               WHERE mpn LIKE ? OR manufacturer LIKE ? OR description LIKE ?
               ORDER BY updated_at DESC""",
            (like, like, like)
        ).fetchall()
        return [dict(r) for r in rows]

    def log_import(self, component_id: int | None, action: str,
                   source_file: str | None = None,
                   error_message: str | None = None) -> None:
        """Log an import action."""
        now = datetime.now(timezone.utc).isoformat()
        self.conn.execute(
            """INSERT INTO import_log (component_id, action, source_file, error_message, timestamp)
               VALUES (?, ?, ?, ?, ?)""",
            (component_id, action, source_file, error_message, now)
        )
        self.conn.commit()
