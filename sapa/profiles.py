"""Profile management for SAPA."""

import sqlite3
from contextlib import contextmanager


class ProfileManager:
    """Manages family profiles in the shared database."""

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self._current_profile_id = 1

    def get_profiles(self) -> list[dict]:
        cursor = self.conn.execute(
            "SELECT id, name, display_name, created_at, weight, age, sex, protein_goal FROM profiles ORDER BY id"
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_profile(self, profile_id: int) -> dict | None:
        cursor = self.conn.execute(
            "SELECT id, name, display_name, created_at, weight, age, sex, protein_goal FROM profiles WHERE id = ?",
            (profile_id,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_profile_by_name(self, name: str) -> dict | None:
        cursor = self.conn.execute(
            "SELECT id, name, display_name, created_at, weight, age, sex, protein_goal FROM profiles WHERE name = ?",
            (name,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_current_profile(self) -> dict | None:
        return self.get_profile(self._current_profile_id)

    def get_current_profile_id(self) -> int:
        return self._current_profile_id

    def set_current_profile(self, profile_id: int) -> bool:
        profile = self.get_profile(profile_id)
        if profile:
            self._current_profile_id = profile_id
            return True
        return False

    def create_profile(self, name: str, display_name: str) -> int:
        cursor = self.conn.execute(
            "INSERT INTO profiles (name, display_name) VALUES (?, ?)",
            (name.lower().strip(), display_name.strip())
        )
        self.conn.commit()
        return cursor.lastrowid

    @contextmanager
    def profile_context(self, profile_id: int):
        """Temporarily switch to a different profile."""
        old_id = self._current_profile_id
        self._current_profile_id = profile_id
        try:
            yield
        finally:
            self._current_profile_id = old_id
