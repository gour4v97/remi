"""Local SQLite persistent memory and context store for multi-turn voice interaction.

Features:
- Conversation history tracking with role/content/timestamps.
- User facts key-value store (e.g. name, preferences, favorite apps).
- Pronoun / contextual reference resolution ("open that again", "reload it").
- Built entirely on standard library sqlite3 (zero external dependencies).
"""
from __future__ import annotations

import json
import logging
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from remi.core import config

logger = logging.getLogger(__name__)


class MemoryStore:
    """Thread-safe SQLite context and facts database."""

    _instance: "MemoryStore | None" = None
    _lock = threading.Lock()

    def __init__(self, db_path: Path | None = None):
        self.db_path = db_path or (config.APPDATA / "memory.db")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._local_conn = threading.local()
        self._init_db()

    @classmethod
    def get_instance(cls, db_path: Path | None = None) -> "MemoryStore":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls(db_path)
            return cls._instance

    def _get_conn(self) -> sqlite3.Connection:
        if not hasattr(self._local_conn, "conn") or self._local_conn.conn is None:
            self._local_conn.conn = sqlite3.connect(
                str(self.db_path),
                timeout=10.0,
                check_same_thread=False,
            )
            self._local_conn.conn.row_factory = sqlite3.Row
        return self._local_conn.conn

    def _init_db(self) -> None:
        conn = self._get_conn()
        with conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS conversation_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    metadata_json TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS user_facts (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    category TEXT DEFAULT 'general',
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS context_entities (
                    entity_type TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    detail TEXT,
                    updated_at TEXT NOT NULL
                )
                """
            )

    def add_message(
        self,
        role: str,
        content: str,
        session_id: str = "default",
        metadata: dict[str, Any] | None = None,
    ) -> int:
        """Record a turn in conversation history."""
        now = datetime.now(timezone.utc).isoformat()
        conn = self._get_conn()
        meta_str = json.dumps(metadata or {})
        with conn:
            cur = conn.execute(
                """
                INSERT INTO conversation_history (session_id, role, content, metadata_json, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (session_id, role, content, meta_str, now),
            )
            return cur.lastrowid

    def get_recent_history(self, limit: int = 10, session_id: str = "default") -> list[dict[str, Any]]:
        """Retrieve recent turns formatted for LLM context prompts."""
        conn = self._get_conn()
        cur = conn.execute(
            """
            SELECT role, content, metadata_json, created_at
            FROM conversation_history
            WHERE session_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (session_id, limit),
        )
        rows = cur.fetchall()
        result = []
        for r in reversed(rows):
            result.append(
                {
                    "role": r["role"],
                    "content": r["content"],
                    "metadata": json.loads(r["metadata_json"] or "{}"),
                    "created_at": r["created_at"],
                }
            )
        return result

    def set_fact(self, key: str, value: str, category: str = "general") -> None:
        """Store or update a user fact (e.g. name, language, default_browser)."""
        now = datetime.now(timezone.utc).isoformat()
        conn = self._get_conn()
        with conn:
            conn.execute(
                """
                INSERT INTO user_facts (key, value, category, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    category = excluded.category,
                    updated_at = excluded.updated_at
                """,
                (key.lower().strip(), value.strip(), category, now),
            )

    def get_fact(self, key: str) -> str | None:
        """Retrieve stored user fact."""
        conn = self._get_conn()
        cur = conn.execute("SELECT value FROM user_facts WHERE key = ?", (key.lower().strip(),))
        row = cur.fetchone()
        return row["value"] if row else None

    def get_all_facts(self) -> dict[str, str]:
        """Return all user facts as a dictionary."""
        conn = self._get_conn()
        cur = conn.execute("SELECT key, value FROM user_facts ORDER BY key ASC")
        return {r["key"]: r["value"] for r in cur.fetchall()}

    def remember_entity(self, entity_type: str, value: str, detail: str = "") -> None:
        """Cache last active entity (e.g. 'last_url', 'last_search', 'last_file')."""
        now = datetime.now(timezone.utc).isoformat()
        conn = self._get_conn()
        with conn:
            conn.execute(
                """
                INSERT INTO context_entities (entity_type, value, detail, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(entity_type) DO UPDATE SET
                    value = excluded.value,
                    detail = excluded.detail,
                    updated_at = excluded.updated_at
                """,
                (entity_type.lower().strip(), value.strip(), detail, now),
            )

    def recall_entity(self, entity_type: str) -> dict[str, str] | None:
        """Recall last entity of a given type for contextual reference."""
        conn = self._get_conn()
        cur = conn.execute(
            "SELECT value, detail, updated_at FROM context_entities WHERE entity_type = ?",
            (entity_type.lower().strip(),),
        )
        row = cur.fetchone()
        return dict(row) if row else None


# Global convenience helper
def get_memory() -> MemoryStore:
    return MemoryStore.get_instance()
