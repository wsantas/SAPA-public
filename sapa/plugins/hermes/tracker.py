"""Hermes chat history tracker (family-shared, no profile filtering)."""

import sqlite3
from pathlib import Path


class HermesTracker:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, detect_types=sqlite3.PARSE_DECLTYPES, timeout=30)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA busy_timeout=30000")

    def log_exchange(
        self,
        user_message: str,
        assistant_response: str,
        model: str = None,
        backend: str = None,
        latency_ms: int = None,
    ) -> int:
        cursor = self.conn.execute(
            """
            INSERT INTO hermes_chat (user_message, assistant_response, model, backend, latency_ms)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_message, assistant_response, model, backend, latency_ms),
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_recent(self, limit: int = 50) -> list[dict]:
        cursor = self.conn.execute(
            """
            SELECT id, user_message, assistant_response, model, backend, latency_ms, created_at
            FROM hermes_chat
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        )
        return [dict(row) for row in cursor.fetchall()]

    def clear(self) -> int:
        cursor = self.conn.execute("DELETE FROM hermes_chat")
        self.conn.commit()
        return cursor.rowcount

    def close(self) -> None:
        self.conn.close()
