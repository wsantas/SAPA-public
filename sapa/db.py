"""Shared database manager and migration runner for SAPA."""

import logging
import sqlite3
from pathlib import Path

from .config import get_config

logger = logging.getLogger(__name__)


def get_db_path() -> Path:
    config = get_config()
    config.ensure_directories()
    return config.db_path


def get_connection(db_path: Path = None) -> sqlite3.Connection:
    if db_path is None:
        db_path = get_db_path()
    conn = sqlite3.connect(db_path, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    return conn


def init_framework_tables(conn: sqlite3.Connection) -> None:
    """Create framework-owned tables."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            display_name TEXT NOT NULL,
            weight REAL,
            age INTEGER,
            sex TEXT,
            protein_goal INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS sapa_migrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plugin_id TEXT NOT NULL,
            migration_file TEXT NOT NULL,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(plugin_id, migration_file)
        );
    """)
    conn.commit()


def run_plugin_migrations(conn: sqlite3.Connection, plugin_id: str, migrations_dir: Path) -> int:
    """Run unapplied migrations for a plugin. Returns count of applied."""
    if not migrations_dir or not migrations_dir.exists():
        return 0

    # Get already-applied migrations
    cursor = conn.execute(
        "SELECT migration_file FROM sapa_migrations WHERE plugin_id = ?",
        (plugin_id,)
    )
    applied = {row['migration_file'] for row in cursor.fetchall()}

    # Find and sort migration files
    migration_files = sorted(migrations_dir.glob("*.sql"))
    count = 0

    for mf in migration_files:
        if mf.name in applied:
            continue
        logger.info(f"Applying migration {plugin_id}/{mf.name}")
        sql = mf.read_text()
        conn.executescript(sql)
        conn.execute(
            "INSERT INTO sapa_migrations (plugin_id, migration_file) VALUES (?, ?)",
            (plugin_id, mf.name)
        )
        conn.commit()
        count += 1

    return count


def ensure_default_profiles(conn: sqlite3.Connection) -> None:
    """Ensure default demo profiles exist."""
    default_profiles = [
        ('john', 'John', 170, 35, 'M', 170),
        ('jane', 'Jane', 140, 30, 'F', 110),
    ]
    default_names = [p[0] for p in default_profiles]

    # Remove any profiles not in the default set
    placeholders = ','.join('?' * len(default_names))
    conn.execute(f"DELETE FROM profiles WHERE name NOT IN ({placeholders})", default_names)

    for name, display_name, weight, age, sex, protein_goal in default_profiles:
        cursor = conn.execute("SELECT id FROM profiles WHERE name = ?", (name,))
        if cursor.fetchone():
            conn.execute(
                "UPDATE profiles SET display_name = ? WHERE name = ? AND display_name = name",
                (display_name, name)
            )
        else:
            conn.execute(
                "INSERT INTO profiles (name, display_name, weight, age, sex, protein_goal) VALUES (?, ?, ?, ?, ?, ?)",
                (name, display_name, weight, age, sex, protein_goal)
            )
    conn.commit()
