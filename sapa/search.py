"""Content search across all plugins."""

import sqlite3
from pathlib import Path


def search_content(
    db_path: Path,
    query: str,
    profile_id: int = None,
    limit: int = 50,
) -> list[dict]:
    """Search across health history (profile-scoped) and homestead history (family).

    Returns unified results sorted by date descending.
    """
    if not query or len(query) < 2:
        return []

    conn = sqlite3.connect(db_path, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    results = []
    term = f"%{query}%"

    try:
        # Health history (profile-scoped)
        if profile_id:
            cursor = conn.execute("""
                SELECT h.id, h.topic, h.response, h.session_type, h.created_at,
                       p.display_name as profile_name
                FROM history h
                JOIN profiles p ON h.profile_id = p.id
                WHERE h.profile_id = ? AND (h.topic LIKE ? OR h.response LIKE ?)
                ORDER BY h.created_at DESC
                LIMIT ?
            """, (profile_id, term, term, limit))
        else:
            cursor = conn.execute("""
                SELECT h.id, h.topic, h.response, h.session_type, h.created_at,
                       p.display_name as profile_name
                FROM history h
                JOIN profiles p ON h.profile_id = p.id
                WHERE h.topic LIKE ? OR h.response LIKE ?
                ORDER BY h.created_at DESC
                LIMIT ?
            """, (term, term, limit))

        for row in cursor.fetchall():
            snippet = _extract_snippet(row["response"] or "", query, 200)
            results.append({
                "id": row["id"],
                "topic": row["topic"],
                "snippet": snippet,
                "session_type": row["session_type"],
                "created_at": row["created_at"],
                "category": "health",
                "profile_name": row["profile_name"],
            })

        # Homestead history (family-shared, no profile filter)
        cursor = conn.execute("""
            SELECT id, topic, response, session_type, created_at
            FROM homestead_history
            WHERE topic LIKE ? OR response LIKE ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (term, term, limit))

        for row in cursor.fetchall():
            snippet = _extract_snippet(row["response"] or "", query, 200)
            results.append({
                "id": row["id"],
                "topic": row["topic"],
                "snippet": snippet,
                "session_type": row["session_type"],
                "created_at": row["created_at"],
                "category": "homestead",
                "profile_name": "Family",
            })

        # Sort combined results by date descending
        results.sort(key=lambda r: r["created_at"] or "", reverse=True)
        return results[:limit]

    finally:
        conn.close()


def _extract_snippet(text: str, query: str, length: int = 200) -> str:
    """Extract a snippet around the first match of query in text."""
    lower = text.lower()
    idx = lower.find(query.lower())
    if idx == -1:
        return text[:length] + ("..." if len(text) > length else "")

    start = max(0, idx - length // 2)
    end = min(len(text), idx + len(query) + length // 2)
    snippet = text[start:end]

    if start > 0:
        snippet = "..." + snippet
    if end < len(text):
        snippet = snippet + "..."

    return snippet
