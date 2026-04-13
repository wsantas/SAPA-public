"""Homestead session tracker using SQLite.

Family-shared (no profile_id filtering).
"""

import sqlite3
from datetime import datetime
from pathlib import Path


class HomesteadTracker:
    """Track homestead sessions with SQLite backend."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, detect_types=sqlite3.PARSE_DECLTYPES, timeout=30)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA busy_timeout=30000")

    def save_history(
        self,
        session_type: str,
        topic: str = None,
        prompt: str = None,
        response: str = None,
        notes: str = None,
    ) -> int:
        """Save a session to homestead history."""
        cursor = self.conn.execute("""
            INSERT INTO homestead_history (session_type, topic, prompt, response, notes)
            VALUES (?, ?, ?, ?, ?)
        """, (session_type, topic, prompt, response, notes))
        self.conn.commit()
        return cursor.lastrowid

    def get_history(self, limit: int = 50, search: str = None) -> list[dict]:
        """Get homestead session history, optionally filtered by search term."""
        if search:
            like = f"%{search}%"
            cursor = self.conn.execute("""
                SELECT id, session_type, topic, prompt, response, notes, created_at
                FROM homestead_history
                WHERE topic LIKE ? OR response LIKE ? OR notes LIKE ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (like, like, like, limit))
        else:
            cursor = self.conn.execute("""
                SELECT id, session_type, topic, prompt, response, notes, created_at
                FROM homestead_history
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,))
        return [dict(row) for row in cursor.fetchall()]

    def get_history_entry(self, entry_id: int) -> dict | None:
        """Get a single history entry by ID."""
        cursor = self.conn.execute("""
            SELECT id, session_type, topic, prompt, response, notes, created_at
            FROM homestead_history WHERE id = ?
        """, (entry_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def delete_history(self, entry_id: int) -> bool:
        """Delete a history entry by ID."""
        cursor = self.conn.execute("DELETE FROM homestead_history WHERE id = ?", (entry_id,))
        self.conn.commit()
        return cursor.rowcount > 0

    def update_history_by_topic(self, topic: str, new_content: str, new_prompt: str = None) -> bool:
        """Update a history entry's content by matching topic name."""
        cursor = self.conn.execute(
            "SELECT id FROM homestead_history WHERE topic = ? ORDER BY created_at DESC LIMIT 1",
            (topic,)
        )
        row = cursor.fetchone()
        if row:
            self.conn.execute("""
                UPDATE homestead_history SET response = ?, prompt = ? WHERE id = ?
            """, (new_content, new_prompt or new_content[:500], row['id']))
            self.conn.commit()
            return True
        return False

    def get_all_history_prompts(self, limit: int = 1000) -> set[str]:
        """Get prompt prefixes for dedup checking."""
        cursor = self.conn.execute(
            "SELECT prompt FROM homestead_history ORDER BY created_at DESC LIMIT ?",
            (limit,)
        )
        return {row['prompt'][:100] for row in cursor.fetchall() if row['prompt']}

    # --- Topics (for gap analysis) ---

    def record_learning(self, topic: str, confidence: float = 0.5) -> None:
        """Record that a topic was learned or reviewed."""
        topic = topic.lower().strip()
        now = datetime.now()

        cursor = self.conn.execute(
            "SELECT id, review_count FROM homestead_topics WHERE name = ?",
            (topic,)
        )
        row = cursor.fetchone()

        if row:
            review_count = row["review_count"] + 1
            self.conn.execute("""
                UPDATE homestead_topics
                SET last_reviewed = ?, review_count = ?, confidence_score = ?
                WHERE name = ?
            """, (now, review_count, confidence, topic))
        else:
            self.conn.execute("""
                INSERT OR IGNORE INTO homestead_topics (name, first_learned, last_reviewed, review_count, confidence_score)
                VALUES (?, ?, ?, 0, ?)
            """, (topic, now, now, confidence))

        self.conn.commit()

    def record_learning_batch(self, topics: list[tuple[str, float]]) -> int:
        """Record multiple topics in a single transaction."""
        now = datetime.now()
        count = 0
        for topic_name, confidence in topics:
            topic_name = topic_name.lower().strip()
            cursor = self.conn.execute(
                "SELECT id, review_count FROM homestead_topics WHERE name = ?",
                (topic_name,)
            )
            row = cursor.fetchone()
            if row:
                review_count = row["review_count"] + 1
                self.conn.execute("""
                    UPDATE homestead_topics
                    SET last_reviewed = ?, review_count = ?, confidence_score = ?
                    WHERE name = ?
                """, (now, review_count, confidence, topic_name))
            else:
                self.conn.execute("""
                    INSERT OR IGNORE INTO homestead_topics (name, first_learned, last_reviewed, review_count, confidence_score)
                    VALUES (?, ?, ?, 0, ?)
                """, (topic_name, now, now, confidence))
            count += 1
        self.conn.commit()
        return count

    def get_all_topics(self) -> list[dict]:
        """Get all learned homestead topics."""
        cursor = self.conn.execute("""
            SELECT name, first_learned, last_reviewed, review_count, confidence_score
            FROM homestead_topics ORDER BY last_reviewed DESC
        """)
        return [dict(row) for row in cursor.fetchall()]

    def get_session_count(self) -> int:
        """Get total number of homestead sessions."""
        cursor = self.conn.execute("SELECT COUNT(*) as count FROM homestead_history")
        return cursor.fetchone()['count']

    def close(self) -> None:
        """Close the database connection."""
        self.conn.close()
