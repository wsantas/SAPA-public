"""Health tracker with spaced repetition using SQLite."""

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from ...config import get_config


# Spaced repetition intervals (in days)
REVIEW_INTERVALS = [1, 3, 7, 14, 30, 60]


class HealthTracker:
    """Track health/learning progress with SQLite backend."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._current_profile_id = 1
        self.conn = sqlite3.connect(db_path, detect_types=sqlite3.PARSE_DECLTYPES, timeout=30)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA busy_timeout=30000")

    # --- Profile helpers (needed by routes) ---

    def get_current_profile_id(self) -> int:
        """Get the current profile ID."""
        return self._current_profile_id

    @contextmanager
    def profile_context(self, profile_id: int):
        """Temporarily switch to a different profile for processing."""
        old_id = self._current_profile_id
        self._current_profile_id = profile_id
        try:
            yield
        finally:
            self._current_profile_id = old_id

    def get_current_profile(self) -> dict | None:
        """Get the current profile with all metadata."""
        return self.get_profile(self._current_profile_id)

    def get_profile(self, profile_id: int) -> dict | None:
        """Get a profile by ID."""
        cursor = self.conn.execute(
            "SELECT id, name, display_name, created_at, weight, age, sex, protein_goal FROM profiles WHERE id = ?",
            (profile_id,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_profile_by_name(self, name: str) -> dict | None:
        """Get a profile by name."""
        cursor = self.conn.execute(
            "SELECT id, name, display_name, created_at, weight, age, sex, protein_goal FROM profiles WHERE name = ?",
            (name,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    # --- Spaced repetition ---

    def _calculate_next_review(self, review_count: int, confidence: float) -> datetime:
        """Calculate next review date based on spaced repetition."""
        interval_idx = min(review_count, len(REVIEW_INTERVALS) - 1)
        base_days = REVIEW_INTERVALS[interval_idx]
        adjustment = 1.0 + (confidence - 0.5)
        adjusted_days = int(base_days * adjustment)
        return datetime.now() + timedelta(days=max(1, adjusted_days))

    def record_learning(self, topic: str, confidence: float = 0.5) -> None:
        """Record that a topic was learned or reviewed."""
        topic = topic.lower().strip()
        now = datetime.now()
        next_review = self._calculate_next_review(0, confidence)
        profile_id = self._current_profile_id

        # Try to update existing, otherwise insert
        cursor = self.conn.execute(
            "SELECT id, review_count FROM topics WHERE name = ? AND profile_id = ?",
            (topic, profile_id)
        )
        row = cursor.fetchone()

        if row:
            review_count = row["review_count"] + 1
            # Confidence grows with reviews: starts at caller value, approaches 1.0
            # Formula: base + (1 - base) * (1 - 1/(1 + reviews/3))
            new_confidence = confidence + (1.0 - confidence) * (1.0 - 1.0 / (1.0 + review_count / 3.0))
            new_confidence = min(new_confidence, 1.0)
            next_review = self._calculate_next_review(review_count, new_confidence)
            self.conn.execute("""
                UPDATE topics
                SET last_reviewed = ?, review_count = ?, confidence_score = ?, next_review = ?
                WHERE name = ? AND profile_id = ?
            """, (now, review_count, new_confidence, next_review, topic, profile_id))
        else:
            self.conn.execute("""
                INSERT OR IGNORE INTO topics (name, first_learned, last_reviewed, review_count, confidence_score, next_review, profile_id)
                VALUES (?, ?, ?, 0, ?, ?, ?)
            """, (topic, now, now, confidence, next_review, profile_id))

        self._update_streak()
        self._record_daily_session(topics_learned=1)
        self.conn.commit()

    def record_learning_batch(self, topics: list[tuple[str, float, int]]) -> int:
        """Record multiple topics in a single transaction.

        Args:
            topics: list of (topic_name, confidence, profile_id) tuples

        Returns:
            Number of topics recorded.
        """
        now = datetime.now()
        count = 0
        profiles_seen = set()
        for topic_name, confidence, profile_id in topics:
            topic_name = topic_name.lower().strip()
            next_review = self._calculate_next_review(0, confidence)

            cursor = self.conn.execute(
                "SELECT id, review_count FROM topics WHERE name = ? AND profile_id = ?",
                (topic_name, profile_id)
            )
            row = cursor.fetchone()

            if row:
                review_count = row["review_count"] + 1
                new_confidence = confidence + (1.0 - confidence) * (1.0 - 1.0 / (1.0 + review_count / 3.0))
                new_confidence = min(new_confidence, 1.0)
                next_review = self._calculate_next_review(review_count, new_confidence)
                self.conn.execute("""
                    UPDATE topics
                    SET last_reviewed = ?, review_count = ?, confidence_score = ?, next_review = ?
                    WHERE name = ? AND profile_id = ?
                """, (now, review_count, new_confidence, next_review, topic_name, profile_id))
            else:
                self.conn.execute("""
                    INSERT OR IGNORE INTO topics (name, first_learned, last_reviewed, review_count, confidence_score, next_review, profile_id)
                    VALUES (?, ?, ?, 0, ?, ?, ?)
                """, (topic_name, now, now, confidence, next_review, profile_id))
            count += 1
            profiles_seen.add(profile_id)

        # Update streaks and daily sessions once per profile, not per topic
        old_profile = self._current_profile_id
        for pid in profiles_seen:
            self._current_profile_id = pid
            self._update_streak()
            self._record_daily_session(topics_learned=1)
        self._current_profile_id = old_profile

        self.conn.commit()
        return count

    def _update_streak(self) -> None:
        """Update the learning streak."""
        today = datetime.now().date()
        profile_id = self._current_profile_id

        cursor = self.conn.execute(
            "SELECT current, longest, last_active FROM streaks WHERE profile_id = ?",
            (profile_id,)
        )
        row = cursor.fetchone()

        if not row:
            # Create streak entry for this profile
            self.conn.execute(
                "INSERT INTO streaks (profile_id, current, longest, last_active) VALUES (?, 1, 1, ?)",
                (profile_id, today)
            )
            return

        current = row["current"] or 0
        longest = row["longest"] or 0
        last_active = row["last_active"]

        if last_active:
            if isinstance(last_active, str):
                last_active = datetime.strptime(last_active, "%Y-%m-%d").date()
            days_diff = (today - last_active).days

            if days_diff == 0:
                pass  # Already active today
            elif days_diff == 1:
                current += 1
            else:
                current = 1
        else:
            current = 1

        longest = max(longest, current)

        self.conn.execute("""
            UPDATE streaks SET current = ?, longest = ?, last_active = ? WHERE profile_id = ?
        """, (current, longest, today, profile_id))

    def _record_daily_session(self, topics_learned: int = 0, quizzes_taken: int = 0) -> None:
        """Record activity for today's session."""
        today = datetime.now().date()
        profile_id = self._current_profile_id

        self.conn.execute("""
            INSERT INTO daily_sessions (session_date, topics_learned, quizzes_taken, profile_id)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(session_date, profile_id) DO UPDATE SET
                topics_learned = topics_learned + excluded.topics_learned,
                quizzes_taken = quizzes_taken + excluded.quizzes_taken
        """, (today, topics_learned, quizzes_taken, profile_id))

    def get_due_reviews(self) -> list[str]:
        """Get topics that are due for review."""
        now = datetime.now()
        profile_id = self._current_profile_id
        cursor = self.conn.execute("""
            SELECT name FROM topics
            WHERE next_review <= ? AND profile_id = ?
            ORDER BY next_review ASC
        """, (now, profile_id))
        return [row["name"] for row in cursor.fetchall()]

    def get_review_timeline(self) -> dict:
        """Get review schedule grouped by time bucket."""
        now = datetime.now()
        profile_id = self._current_profile_id
        cursor = self.conn.execute("""
            SELECT name, next_review, confidence_score FROM topics
            WHERE profile_id = ?
            ORDER BY next_review ASC
        """, (profile_id,))

        overdue = []
        this_week = []
        next_week = []
        later = []
        solid = []

        week_end = now + timedelta(days=7)
        two_weeks = now + timedelta(days=14)

        for row in cursor.fetchall():
            nr = row["next_review"]
            if isinstance(nr, str):
                try:
                    nr = datetime.strptime(nr, "%Y-%m-%d %H:%M:%S.%f")
                except ValueError:
                    nr = datetime.strptime(nr, "%Y-%m-%d %H:%M:%S")
            item = {"name": row["name"], "confidence": round(row["confidence_score"], 2)}
            if nr <= now:
                overdue.append(item)
            elif nr <= week_end:
                this_week.append(item)
            elif nr <= two_weeks:
                next_week.append(item)
            elif row["confidence_score"] >= 0.9:
                solid.append(item)
            else:
                later.append(item)

        return {
            "overdue": overdue,
            "this_week": this_week,
            "next_week": next_week,
            "later": later,
            "solid": solid,
        }

    def get_new_vs_review_stats(self) -> dict:
        """Get new topics vs reviewed topics breakdown by week."""
        profile_id = self._current_profile_id
        today = datetime.now().date()
        weeks = []
        for w in range(3, -1, -1):
            week_start = today - timedelta(days=today.weekday() + 7 * w)
            week_end = week_start + timedelta(days=7)
            cursor = self.conn.execute("""
                SELECT COUNT(*) as cnt FROM topics
                WHERE first_learned >= ? AND first_learned < ? AND profile_id = ?
            """, (week_start.strftime("%Y-%m-%d"), week_end.strftime("%Y-%m-%d"), profile_id))
            new_count = cursor.fetchone()["cnt"]
            cursor = self.conn.execute("""
                SELECT COUNT(*) as cnt FROM topics
                WHERE last_reviewed >= ? AND last_reviewed < ?
                AND first_learned < ? AND profile_id = ?
            """, (week_start.strftime("%Y-%m-%d"), week_end.strftime("%Y-%m-%d"),
                  week_start.strftime("%Y-%m-%d"), profile_id))
            review_count = cursor.fetchone()["cnt"]
            weeks.append({
                "week": week_start.strftime("%b %d"),
                "new": new_count,
                "review": review_count,
                "current": w == 0,
            })
        return {"weeks": weeks}

    def record_quiz_result(self, topic: str, score: float) -> None:
        """Record a quiz result for a topic."""
        topic = topic.lower().strip()
        profile_id = self._current_profile_id

        # Get or create topic
        cursor = self.conn.execute(
            "SELECT id FROM topics WHERE name = ? AND profile_id = ?",
            (topic, profile_id)
        )
        row = cursor.fetchone()

        if not row:
            self.record_learning(topic, confidence=score)
            cursor = self.conn.execute(
                "SELECT id FROM topics WHERE name = ? AND profile_id = ?",
                (topic, profile_id)
            )
            row = cursor.fetchone()

        topic_id = row["id"]

        # Record quiz result
        self.conn.execute("""
            INSERT INTO quiz_results (topic_id, score) VALUES (?, ?)
        """, (topic_id, score))

        # Update confidence based on recent quizzes
        cursor = self.conn.execute("""
            SELECT AVG(score) as avg_score FROM (
                SELECT score FROM quiz_results
                WHERE topic_id = ?
                ORDER BY taken_at DESC LIMIT 5
            )
        """, (topic_id,))
        avg_score = cursor.fetchone()["avg_score"] or score

        # Update topic confidence and next review
        cursor = self.conn.execute("SELECT review_count FROM topics WHERE id = ?", (topic_id,))
        review_count = cursor.fetchone()["review_count"]
        next_review = self._calculate_next_review(review_count, avg_score)

        self.conn.execute("""
            UPDATE topics SET confidence_score = ?, next_review = ? WHERE id = ?
        """, (avg_score, next_review, topic_id))

        self._record_daily_session(quizzes_taken=1)
        self.conn.commit()

    def get_knowledge_gaps(self) -> list[str]:
        """Get topics with low confidence scores."""
        profile_id = self._current_profile_id
        cursor = self.conn.execute("""
            SELECT name FROM topics
            WHERE confidence_score < 0.6 AND profile_id = ?
            ORDER BY confidence_score ASC
        """, (profile_id,))
        return [row["name"] for row in cursor.fetchall()]

    def get_weekly_report(self) -> dict:
        """Generate a weekly learning report."""
        week_ago = datetime.now() - timedelta(days=7)
        profile_id = self._current_profile_id

        # New topics this week
        cursor = self.conn.execute("""
            SELECT name FROM topics WHERE first_learned >= ? AND profile_id = ?
        """, (week_ago, profile_id))
        new_topics = [row["name"] for row in cursor.fetchall()]

        # Reviewed topics this week
        cursor = self.conn.execute("""
            SELECT name FROM topics
            WHERE last_reviewed >= ? AND first_learned < ? AND profile_id = ?
        """, (week_ago, week_ago, profile_id))
        reviewed_topics = [row["name"] for row in cursor.fetchall()]

        # Quiz stats this week (via topic_id which is already profile-scoped)
        cursor = self.conn.execute("""
            SELECT COUNT(*) as count, AVG(score) as avg_score
            FROM quiz_results qr
            JOIN topics t ON qr.topic_id = t.id
            WHERE qr.taken_at >= ? AND t.profile_id = ?
        """, (week_ago, profile_id))
        quiz_row = cursor.fetchone()
        quiz_count = quiz_row["count"] or 0
        avg_quiz_score = quiz_row["avg_score"] or 0

        # Streak info
        cursor = self.conn.execute(
            "SELECT current, longest FROM streaks WHERE profile_id = ?",
            (profile_id,)
        )
        streak_row = cursor.fetchone()

        # Total topics
        cursor = self.conn.execute(
            "SELECT COUNT(*) as count FROM topics WHERE profile_id = ?",
            (profile_id,)
        )
        total_topics = cursor.fetchone()["count"]

        # Total sessions from history
        cursor = self.conn.execute(
            "SELECT COUNT(*) as count FROM history WHERE profile_id = ?",
            (profile_id,)
        )
        session_count = cursor.fetchone()["count"]

        # Daily activity for last 7 days (for bar chart)
        daily_activity = {}
        today = datetime.now().date()
        day_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        weekly_chart = []
        for i in range(6, -1, -1):
            d = today - timedelta(days=i)
            weekly_chart.append({"date": d.strftime("%Y-%m-%d"), "day": day_names[d.weekday()], "isToday": i == 0})
        cursor = self.conn.execute("""
            SELECT session_date, topics_learned + quizzes_taken as activity
            FROM daily_sessions
            WHERE session_date >= ? AND profile_id = ?
        """, ((today - timedelta(days=7)).strftime("%Y-%m-%d"), profile_id))
        for row in cursor.fetchall():
            date_str = str(row["session_date"])
            daily_activity[date_str] = row["activity"] or 0

        return {
            "new_topics_count": len(new_topics),
            "new_topics": new_topics,
            "reviewed_topics_count": len(reviewed_topics),
            "reviewed_topics": reviewed_topics,
            "quiz_count": quiz_count,
            "avg_quiz_score": avg_quiz_score,
            "current_streak": streak_row["current"] if streak_row else 0,
            "longest_streak": streak_row["longest"] if streak_row else 0,
            "total_topics": total_topics,
            "session_count": session_count,
            "daily_activity": daily_activity,
            "weekly_chart": weekly_chart,
        }

    def get_streak_info(self) -> dict:
        """Get current streak information."""
        profile_id = self._current_profile_id
        cursor = self.conn.execute(
            "SELECT current, longest, last_active FROM streaks WHERE profile_id = ?",
            (profile_id,)
        )
        row = cursor.fetchone()

        # Get active days for last 28 days (for calendar)
        active_days = []
        cursor = self.conn.execute("""
            SELECT DISTINCT session_date FROM daily_sessions
            WHERE session_date >= date('now', '-28 days', 'localtime') AND profile_id = ?
            ORDER BY session_date
        """, (profile_id,))
        for r in cursor.fetchall():
            active_days.append(str(r["session_date"]))

        return {
            "current": row["current"] if row else 0,
            "longest": row["longest"] if row else 0,
            "last_active": str(row["last_active"]) if row and row["last_active"] else None,
            "active_days": active_days,
        }

    def get_all_topics(self) -> list[dict]:
        """Get all topics with their stats."""
        profile_id = self._current_profile_id
        cursor = self.conn.execute("""
            SELECT name, first_learned, last_reviewed, review_count, confidence_score, next_review
            FROM topics WHERE profile_id = ? ORDER BY last_reviewed DESC
        """, (profile_id,))
        return [dict(row) for row in cursor.fetchall()]

    def export_to_markdown(self) -> str:
        """Export learning history to markdown format."""
        lines = ["# Learning Progress Report", ""]
        lines.append(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

        # Stats
        cursor = self.conn.execute("SELECT COUNT(*) as count FROM topics")
        total = cursor.fetchone()["count"]
        streak = self.get_streak_info()

        lines.append(f"**Total Topics Learned**: {total}")
        lines.append(f"**Current Streak**: {streak['current']} days")
        lines.append(f"**Longest Streak**: {streak['longest']} days")
        lines.append("")

        # Topics by confidence
        lines.append("## Topics by Confidence")
        cursor = self.conn.execute("""
            SELECT name, confidence_score, review_count
            FROM topics ORDER BY confidence_score DESC
        """)
        for row in cursor.fetchall():
            lines.append(f"- {row['name']}: {row['confidence_score']:.0%} (reviewed {row['review_count']}x)")
        lines.append("")

        # Due for review
        due = self.get_due_reviews()
        if due:
            lines.append("## Due for Review")
            for topic in due:
                lines.append(f"- {topic}")
            lines.append("")

        return "\n".join(lines)

    # --- History ---

    def save_history(
        self,
        session_type: str,
        topic: str = None,
        prompt: str = None,
        response: str = None,
        notes: str = None,
    ) -> int:
        """Save a session to history."""
        profile_id = self._current_profile_id
        cursor = self.conn.execute("""
            INSERT INTO history (session_type, topic, prompt, response, notes, profile_id)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (session_type, topic, prompt, response, notes, profile_id))
        self.conn.commit()
        return cursor.lastrowid

    def get_history(self, limit: int = 50, session_type: str = None) -> list[dict]:
        """Get session history."""
        profile_id = self._current_profile_id
        if session_type:
            cursor = self.conn.execute("""
                SELECT id, session_type, topic, prompt, response, notes, created_at
                FROM history
                WHERE session_type = ? AND profile_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (session_type, profile_id, limit))
        else:
            cursor = self.conn.execute("""
                SELECT id, session_type, topic, prompt, response, notes, created_at
                FROM history
                WHERE profile_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (profile_id, limit))
        return [dict(row) for row in cursor.fetchall()]

    def get_history_entry(self, entry_id: int) -> dict:
        """Get a single history entry by ID."""
        cursor = self.conn.execute("""
            SELECT id, session_type, topic, prompt, response, notes, created_at
            FROM history WHERE id = ?
        """, (entry_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def update_history_by_topic(self, topic: str, new_content: str, new_prompt: str = None) -> bool:
        """Update a history entry's content by matching topic name."""
        profile_id = self._current_profile_id
        cursor = self.conn.execute(
            "SELECT id FROM history WHERE topic = ? AND profile_id = ? ORDER BY created_at DESC LIMIT 1",
            (topic, profile_id)
        )
        row = cursor.fetchone()
        if row:
            self.conn.execute("""
                UPDATE history SET response = ?, prompt = ? WHERE id = ?
            """, (new_content, new_prompt or new_content[:500], row['id']))
            self.conn.commit()
            return True
        return False

    def delete_history(self, history_id: int) -> bool:
        """Delete a history/session entry by ID."""
        cursor = self.conn.execute("DELETE FROM history WHERE id = ?", (history_id,))
        self.conn.commit()
        return cursor.rowcount > 0

    def get_all_history_prompts(self, limit: int = 1000) -> set[str]:
        """Get prompt prefixes from all profiles for dedup checking."""
        cursor = self.conn.execute(
            "SELECT prompt FROM history ORDER BY created_at DESC LIMIT ?",
            (limit,)
        )
        return {row['prompt'][:100] for row in cursor.fetchall() if row['prompt']}

    # --- Notes ---

    def add_note(self, topic: str, content: str, source: str = None) -> int:
        """Add a note/learning to the database."""
        profile_id = self._current_profile_id
        cursor = self.conn.execute("""
            INSERT INTO notes (topic, content, source, profile_id)
            VALUES (?, ?, ?, ?)
        """, (topic.lower().strip(), content, source, profile_id))

        # Also record as a learned topic
        self.record_learning(topic, confidence=0.6)

        self.conn.commit()
        return cursor.lastrowid

    def get_notes(self, topic: str = None, limit: int = 50) -> list[dict]:
        """Get notes, optionally filtered by topic."""
        profile_id = self._current_profile_id
        if topic:
            cursor = self.conn.execute("""
                SELECT id, topic, content, source, created_at
                FROM notes
                WHERE topic LIKE ? AND profile_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (f"%{topic.lower()}%", profile_id, limit))
        else:
            cursor = self.conn.execute("""
                SELECT id, topic, content, source, created_at
                FROM notes
                WHERE profile_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (profile_id, limit))
        return [dict(row) for row in cursor.fetchall()]

    def search_notes(self, query: str) -> list[dict]:
        """Search notes by content."""
        profile_id = self._current_profile_id
        cursor = self.conn.execute("""
            SELECT id, topic, content, source, created_at
            FROM notes
            WHERE (content LIKE ? OR topic LIKE ?) AND profile_id = ?
            ORDER BY created_at DESC
            LIMIT 50
        """, (f"%{query}%", f"%{query}%", profile_id))
        return [dict(row) for row in cursor.fetchall()]

    def delete_note(self, note_id: int) -> bool:
        """Delete a note by ID."""
        cursor = self.conn.execute("DELETE FROM notes WHERE id = ?", (note_id,))
        self.conn.commit()
        return cursor.rowcount > 0

    # --- Export / Import ---

    def export_data(self) -> dict:
        """Export all learning data for backup."""
        data = {
            "version": 1,
            "exported_at": datetime.now().isoformat(),
            "topics": [],
            "quiz_results": [],
            "streaks": None,
            "daily_sessions": [],
            "history": [],
            "notes": [],
        }

        # Export topics
        cursor = self.conn.execute("SELECT * FROM topics")
        data["topics"] = [dict(row) for row in cursor.fetchall()]

        # Export quiz_results
        cursor = self.conn.execute("SELECT * FROM quiz_results")
        data["quiz_results"] = [dict(row) for row in cursor.fetchall()]

        # Export streaks
        cursor = self.conn.execute("SELECT * FROM streaks WHERE id = 1")
        row = cursor.fetchone()
        if row:
            data["streaks"] = dict(row)

        # Export daily_sessions
        cursor = self.conn.execute("SELECT * FROM daily_sessions")
        data["daily_sessions"] = [dict(row) for row in cursor.fetchall()]

        # Export history
        cursor = self.conn.execute("SELECT * FROM history")
        data["history"] = [dict(row) for row in cursor.fetchall()]

        # Export notes
        cursor = self.conn.execute("SELECT * FROM notes")
        data["notes"] = [dict(row) for row in cursor.fetchall()]

        return data

    def import_data(self, data: dict, merge: bool = False) -> dict:
        """Import learning data from backup.

        Args:
            data: The exported data dict
            merge: If True, merge with existing data. If False, replace all.

        Returns:
            Stats about what was imported
        """
        stats = {
            "topics": 0,
            "quiz_results": 0,
            "daily_sessions": 0,
            "history": 0,
            "notes": 0,
        }

        if not merge:
            # Clear existing data
            self.conn.executescript("""
                DELETE FROM notes;
                DELETE FROM history;
                DELETE FROM daily_sessions;
                DELETE FROM quiz_results;
                DELETE FROM topics;
                UPDATE streaks SET current = 0, longest = 0, last_active = NULL WHERE id = 1;
            """)

        # Import topics
        for topic in data.get("topics", []):
            try:
                self.conn.execute("""
                    INSERT OR REPLACE INTO topics
                    (id, name, first_learned, last_reviewed, review_count, confidence_score, next_review, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    topic.get("id"), topic["name"], topic["first_learned"],
                    topic["last_reviewed"], topic.get("review_count", 0),
                    topic.get("confidence_score", 0.5), topic.get("next_review"),
                    topic.get("created_at")
                ))
                stats["topics"] += 1
            except Exception:
                pass  # Skip duplicates in merge mode

        # Import quiz_results
        for quiz in data.get("quiz_results", []):
            try:
                self.conn.execute("""
                    INSERT OR REPLACE INTO quiz_results (id, topic_id, score, taken_at)
                    VALUES (?, ?, ?, ?)
                """, (quiz.get("id"), quiz["topic_id"], quiz["score"], quiz.get("taken_at")))
                stats["quiz_results"] += 1
            except Exception:
                pass

        # Import streaks
        if data.get("streaks"):
            s = data["streaks"]
            self.conn.execute("""
                UPDATE streaks SET current = ?, longest = ?, last_active = ? WHERE id = 1
            """, (s.get("current", 0), s.get("longest", 0), s.get("last_active")))

        # Import daily_sessions
        for session in data.get("daily_sessions", []):
            try:
                self.conn.execute("""
                    INSERT OR REPLACE INTO daily_sessions
                    (id, session_date, topics_learned, quizzes_taken, created_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    session.get("id"), session["session_date"],
                    session.get("topics_learned", 0), session.get("quizzes_taken", 0),
                    session.get("created_at")
                ))
                stats["daily_sessions"] += 1
            except Exception:
                pass

        # Import history
        for entry in data.get("history", []):
            try:
                self.conn.execute("""
                    INSERT OR REPLACE INTO history
                    (id, session_type, topic, prompt, response, notes, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    entry.get("id"), entry["session_type"], entry.get("topic"),
                    entry.get("prompt"), entry.get("response"), entry.get("notes"),
                    entry.get("created_at")
                ))
                stats["history"] += 1
            except Exception:
                pass

        # Import notes
        for note in data.get("notes", []):
            try:
                self.conn.execute("""
                    INSERT OR REPLACE INTO notes (id, topic, content, source, created_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    note.get("id"), note["topic"], note["content"],
                    note.get("source"), note.get("created_at")
                ))
                stats["notes"] += 1
            except Exception:
                pass

        self.conn.commit()
        return stats

    # ============== HULK Protocol Methods ==============

    # Workouts
    def create_workout(
        self,
        workout_type: str,
        date: str = None,
        duration: int = None,
        rpe: int = None,
        notes: str = None,
    ) -> int:
        """Create a new workout."""
        profile_id = self._current_profile_id
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")

        cursor = self.conn.execute("""
            INSERT INTO workouts (profile_id, date, type, duration, rpe, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (profile_id, date, workout_type, duration, rpe, notes))
        self.conn.commit()
        return cursor.lastrowid

    def add_exercise(
        self,
        workout_id: int,
        name: str,
        sets: int = None,
        reps: str = None,
        weight: str = None,
        rpe: int = None,
        notes: str = None,
        order_index: int = 0,
    ) -> int:
        """Add an exercise to a workout."""
        cursor = self.conn.execute("""
            INSERT INTO exercises (workout_id, name, sets, reps, weight, rpe, notes, order_index)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (workout_id, name, sets, reps, weight, rpe, notes, order_index))
        self.conn.commit()

        # Check for PR
        if weight and reps:
            try:
                weight_val = float(weight.replace('lbs', '').replace('kg', '').strip())
                reps_val = int(reps.split('-')[0]) if '-' in str(reps) else int(reps)
                self._check_and_record_pr(name, weight_val, reps_val, workout_id)
            except (ValueError, TypeError):
                pass

        return cursor.lastrowid

    def update_workout_totals(self, workout_id: int) -> None:
        """Update workout totals from exercises."""
        cursor = self.conn.execute("""
            SELECT SUM(sets) as total_sets, SUM(CAST(sets AS INTEGER) * CAST(reps AS INTEGER)) as total_reps
            FROM exercises WHERE workout_id = ?
        """, (workout_id,))
        row = cursor.fetchone()
        if row:
            self.conn.execute("""
                UPDATE workouts SET total_sets = ?, total_reps = ? WHERE id = ?
            """, (row['total_sets'] or 0, row['total_reps'] or 0, workout_id))
            self.conn.commit()

    def get_workouts(self, limit: int = 20, workout_type: str = None) -> list[dict]:
        """Get workouts for current profile."""
        profile_id = self._current_profile_id
        if workout_type:
            cursor = self.conn.execute("""
                SELECT * FROM workouts WHERE profile_id = ? AND type = ?
                ORDER BY date DESC, created_at DESC LIMIT ?
            """, (profile_id, workout_type, limit))
        else:
            cursor = self.conn.execute("""
                SELECT * FROM workouts WHERE profile_id = ?
                ORDER BY date DESC, created_at DESC LIMIT ?
            """, (profile_id, limit))
        return [dict(row) for row in cursor.fetchall()]

    def get_workout(self, workout_id: int) -> dict | None:
        """Get a single workout with exercises."""
        cursor = self.conn.execute(
            "SELECT * FROM workouts WHERE id = ?", (workout_id,)
        )
        workout = cursor.fetchone()
        if not workout:
            return None

        workout_dict = dict(workout)
        cursor = self.conn.execute(
            "SELECT * FROM exercises WHERE workout_id = ? ORDER BY order_index",
            (workout_id,)
        )
        workout_dict['exercises'] = [dict(row) for row in cursor.fetchall()]
        return workout_dict

    def delete_workout(self, workout_id: int) -> bool:
        """Delete a workout and its exercises."""
        cursor = self.conn.execute("DELETE FROM workouts WHERE id = ?", (workout_id,))
        self.conn.commit()
        return cursor.rowcount > 0

    # Recovery
    def log_recovery(
        self,
        date: str = None,
        sleep_hours: float = None,
        sleep_quality: int = None,
        soreness: int = None,
        energy: int = None,
        stress: int = None,
        motivation: int = None,
        notes: str = None,
    ) -> int:
        """Log daily recovery metrics."""
        profile_id = self._current_profile_id
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")

        # Upsert - update if exists for this date, otherwise insert
        cursor = self.conn.execute("""
            INSERT INTO recovery_logs (profile_id, date, sleep_hours, sleep_quality, soreness, energy, stress, motivation, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(date, profile_id) DO UPDATE SET
                sleep_hours = excluded.sleep_hours,
                sleep_quality = excluded.sleep_quality,
                soreness = excluded.soreness,
                energy = excluded.energy,
                stress = excluded.stress,
                motivation = excluded.motivation,
                notes = excluded.notes
        """, (profile_id, date, sleep_hours, sleep_quality, soreness, energy, stress, motivation, notes))
        self.conn.commit()
        return cursor.lastrowid

    def get_recovery_today(self) -> dict | None:
        """Get today's recovery log."""
        profile_id = self._current_profile_id
        today = datetime.now().strftime("%Y-%m-%d")
        cursor = self.conn.execute(
            "SELECT * FROM recovery_logs WHERE profile_id = ? AND date = ?",
            (profile_id, today)
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_recovery_history(self, limit: int = 30) -> list[dict]:
        """Get recovery history."""
        profile_id = self._current_profile_id
        cursor = self.conn.execute("""
            SELECT * FROM recovery_logs WHERE profile_id = ?
            ORDER BY date DESC LIMIT ?
        """, (profile_id, limit))
        return [dict(row) for row in cursor.fetchall()]

    def get_readiness_score(self) -> dict:
        """Calculate readiness score from recent recovery data."""
        profile_id = self._current_profile_id
        today = datetime.now().strftime("%Y-%m-%d")

        cursor = self.conn.execute(
            "SELECT * FROM recovery_logs WHERE profile_id = ? AND date = ?",
            (profile_id, today)
        )
        today_log = cursor.fetchone()

        if not today_log:
            return {"score": None, "status": "no_data", "message": "Log recovery to see readiness"}

        # Calculate score (0-100) from metrics
        # Each metric is 1-10, we weight them
        weights = {
            "sleep_quality": 0.25,
            "energy": 0.25,
            "soreness": 0.20,  # Inverted - lower soreness = better
            "stress": 0.15,   # Inverted - lower stress = better
            "motivation": 0.15,
        }

        score = 0
        for metric, weight in weights.items():
            val = today_log[metric]
            if val is not None:
                if metric in ("soreness", "stress"):
                    score += (11 - val) * 10 * weight  # Invert
                else:
                    score += val * 10 * weight

        score = min(100, max(0, score))

        # Status based on score
        if score >= 80:
            status = "excellent"
            message = "Ready to push hard"
        elif score >= 60:
            status = "good"
            message = "Good for moderate training"
        elif score >= 40:
            status = "moderate"
            message = "Consider lighter session"
        else:
            status = "low"
            message = "Recovery day recommended"

        return {
            "score": round(score),
            "status": status,
            "message": message,
            "sleep_hours": today_log["sleep_hours"],
            "metrics": {
                "sleep_quality": today_log["sleep_quality"],
                "energy": today_log["energy"],
                "soreness": today_log["soreness"],
                "stress": today_log["stress"],
                "motivation": today_log["motivation"],
            }
        }

    # Body Logs
    def log_body_measurement(
        self,
        date: str = None,
        weight: float = None,
        waist: float = None,
        chest: float = None,
        arms: float = None,
        body_fat: float = None,
        notes: str = None,
    ) -> int:
        """Log body measurements."""
        profile_id = self._current_profile_id
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")

        cursor = self.conn.execute("""
            INSERT INTO body_logs (profile_id, date, weight, waist, chest, arms, body_fat, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (profile_id, date, weight, waist, chest, arms, body_fat, notes))
        self.conn.commit()
        return cursor.lastrowid

    def get_body_logs(self, limit: int = 30) -> list[dict]:
        """Get body log history."""
        profile_id = self._current_profile_id
        cursor = self.conn.execute("""
            SELECT * FROM body_logs WHERE profile_id = ?
            ORDER BY date DESC LIMIT ?
        """, (profile_id, limit))
        return [dict(row) for row in cursor.fetchall()]

    # Meals
    def log_meal(
        self,
        meal_name: str,
        date: str = None,
        category: str = None,
        calories: int = None,
        protein: int = None,
        carbs: int = None,
        fat: int = None,
        notes: str = None,
    ) -> int:
        """Log a meal."""
        profile_id = self._current_profile_id
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")

        cursor = self.conn.execute("""
            INSERT INTO meal_logs (profile_id, meal_name, date, category, calories, protein, carbs, fat, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (profile_id, meal_name, date, category, calories, protein, carbs, fat, notes))
        self.conn.commit()
        return cursor.lastrowid

    def get_meals_today(self) -> dict:
        """Get today's meals with totals and profile goals."""
        profile_id = self._current_profile_id
        today = datetime.now().strftime("%Y-%m-%d")

        cursor = self.conn.execute("""
            SELECT * FROM meal_logs WHERE profile_id = ? AND date = ?
            ORDER BY created_at
        """, (profile_id, today))
        meals = [dict(row) for row in cursor.fetchall()]

        # Calculate totals
        totals = {"calories": 0, "protein": 0, "carbs": 0, "fat": 0}
        for meal in meals:
            for key in totals:
                totals[key] += meal.get(key) or 0

        # Include profile goals
        profile = self.get_current_profile()
        goals = {
            "protein": profile.get("protein_goal") or 100,
            "calories": 2500,
            "carbs": 250,
            "fat": 80,
        }

        return {"meals": meals, "totals": totals, "goals": goals}

    def get_meal_history(self, limit: int = 50) -> list[dict]:
        """Get meal history."""
        profile_id = self._current_profile_id
        cursor = self.conn.execute("""
            SELECT * FROM meal_logs WHERE profile_id = ?
            ORDER BY date DESC, created_at DESC LIMIT ?
        """, (profile_id, limit))
        return [dict(row) for row in cursor.fetchall()]

    def delete_meal(self, meal_id: int) -> bool:
        """Delete a meal."""
        cursor = self.conn.execute("DELETE FROM meal_logs WHERE id = ?", (meal_id,))
        self.conn.commit()
        return cursor.rowcount > 0

    # Goals
    def create_goal(
        self,
        category: str,
        name: str,
        target: float,
        unit: str,
        current: float = None,
        deadline: str = None,
    ) -> int:
        """Create a new goal."""
        profile_id = self._current_profile_id
        cursor = self.conn.execute("""
            INSERT INTO goals (profile_id, category, name, target, current, unit, deadline)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (profile_id, category, name, target, current, unit, deadline))
        self.conn.commit()
        return cursor.lastrowid

    def get_goals(self, include_completed: bool = False) -> list[dict]:
        """Get goals for current profile."""
        profile_id = self._current_profile_id
        if include_completed:
            cursor = self.conn.execute(
                "SELECT * FROM goals WHERE profile_id = ? ORDER BY completed, created_at DESC",
                (profile_id,)
            )
        else:
            cursor = self.conn.execute(
                "SELECT * FROM goals WHERE profile_id = ? AND completed = 0 ORDER BY created_at DESC",
                (profile_id,)
            )
        return [dict(row) for row in cursor.fetchall()]

    def update_goal(self, goal_id: int, current: float = None, completed: bool = None) -> bool:
        """Update goal progress."""
        updates = []
        params = []
        if current is not None:
            updates.append("current = ?")
            params.append(current)
        if completed is not None:
            updates.append("completed = ?")
            params.append(1 if completed else 0)

        if not updates:
            return False

        params.append(goal_id)
        cursor = self.conn.execute(
            f"UPDATE goals SET {', '.join(updates)} WHERE id = ?",
            params
        )
        self.conn.commit()
        return cursor.rowcount > 0

    def delete_goal(self, goal_id: int) -> bool:
        """Delete a goal."""
        cursor = self.conn.execute("DELETE FROM goals WHERE id = ?", (goal_id,))
        self.conn.commit()
        return cursor.rowcount > 0

    # Personal Records
    def _check_and_record_pr(self, exercise: str, weight: float, reps: int, workout_id: int = None) -> bool:
        """Check if this is a PR and record it."""
        profile_id = self._current_profile_id
        exercise_lower = exercise.lower().strip()

        # Calculate estimated 1RM using Epley formula
        estimated_1rm = weight * (1 + reps / 30) if reps > 1 else weight

        # Check existing PR for this exercise
        cursor = self.conn.execute("""
            SELECT MAX(estimated_1rm) as best_1rm FROM personal_records
            WHERE profile_id = ? AND LOWER(exercise) = ?
        """, (profile_id, exercise_lower))
        row = cursor.fetchone()
        best_1rm = row['best_1rm'] if row and row['best_1rm'] else 0

        # If this is a new PR, record it
        if estimated_1rm > best_1rm:
            date = datetime.now().strftime("%Y-%m-%d")
            self.conn.execute("""
                INSERT INTO personal_records (profile_id, exercise, weight, reps, estimated_1rm, workout_id, date)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (profile_id, exercise_lower, weight, reps, estimated_1rm, workout_id, date))
            self.conn.commit()
            return True
        return False

    def get_personal_records(self) -> list[dict]:
        """Get all PRs for current profile, one per exercise (the best)."""
        profile_id = self._current_profile_id
        cursor = self.conn.execute("""
            SELECT exercise, MAX(estimated_1rm) as best_1rm, weight, reps, date
            FROM personal_records
            WHERE profile_id = ?
            GROUP BY LOWER(exercise)
            ORDER BY date DESC
        """, (profile_id,))
        return [dict(row) for row in cursor.fetchall()]

    def get_pr_history(self, exercise: str = None, limit: int = 20) -> list[dict]:
        """Get PR history, optionally filtered by exercise."""
        profile_id = self._current_profile_id
        if exercise:
            cursor = self.conn.execute("""
                SELECT * FROM personal_records
                WHERE profile_id = ? AND LOWER(exercise) = ?
                ORDER BY date DESC LIMIT ?
            """, (profile_id, exercise.lower().strip(), limit))
        else:
            cursor = self.conn.execute("""
                SELECT * FROM personal_records WHERE profile_id = ?
                ORDER BY date DESC LIMIT ?
            """, (profile_id, limit))
        return [dict(row) for row in cursor.fetchall()]

    # Volume Analytics
    def get_volume_analytics(self, days: int = 30) -> dict:
        """Get volume load analytics for the specified period."""
        profile_id = self._current_profile_id
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

        # Get workouts in period
        cursor = self.conn.execute("""
            SELECT w.id, w.date, w.type, w.total_sets, w.total_reps, w.rpe
            FROM workouts w
            WHERE w.profile_id = ? AND w.date >= ?
            ORDER BY w.date
        """, (profile_id, start_date))
        workouts = [dict(row) for row in cursor.fetchall()]

        # Calculate volume by day
        daily_volume = {}
        workout_counts = {"total": 0}
        for w in workouts:
            date = w['date']
            daily_volume[date] = daily_volume.get(date, 0) + (w['total_sets'] or 0)
            workout_counts["total"] += 1
            wtype = w['type'] or 'other'
            workout_counts[wtype] = workout_counts.get(wtype, 0) + 1

        # Weekly averages
        total_sets = sum(daily_volume.values())
        weeks = max(1, days / 7)
        avg_sets_per_week = total_sets / weeks

        return {
            "period_days": days,
            "total_workouts": workout_counts["total"],
            "workout_counts": workout_counts,
            "total_sets": total_sets,
            "avg_sets_per_week": round(avg_sets_per_week, 1),
            "daily_volume": daily_volume,
        }

    # Streaks for HULK
    def get_hulk_streaks(self) -> dict:
        """Get workout and recovery logging streaks."""
        profile_id = self._current_profile_id
        today = datetime.now().date()

        # Workout streak
        cursor = self.conn.execute("""
            SELECT DISTINCT date FROM workouts WHERE profile_id = ?
            ORDER BY date DESC
        """, (profile_id,))
        workout_dates = [datetime.strptime(row['date'], "%Y-%m-%d").date() for row in cursor.fetchall()]

        workout_streak = 0
        check_date = today
        for d in workout_dates:
            if d == check_date or d == check_date - timedelta(days=1):
                workout_streak += 1
                check_date = d - timedelta(days=1)
            else:
                break

        # Recovery streak
        cursor = self.conn.execute("""
            SELECT DISTINCT date FROM recovery_logs WHERE profile_id = ?
            ORDER BY date DESC
        """, (profile_id,))
        recovery_dates = [datetime.strptime(row['date'], "%Y-%m-%d").date() for row in cursor.fetchall()]

        recovery_streak = 0
        check_date = today
        for d in recovery_dates:
            if d == check_date or d == check_date - timedelta(days=1):
                recovery_streak += 1
                check_date = d - timedelta(days=1)
            else:
                break

        # Nutrition streak
        cursor = self.conn.execute("""
            SELECT DISTINCT date FROM meal_logs WHERE profile_id = ?
            ORDER BY date DESC
        """, (profile_id,))
        meal_dates = [datetime.strptime(row['date'], "%Y-%m-%d").date() for row in cursor.fetchall()]

        nutrition_streak = 0
        check_date = today
        for d in meal_dates:
            if d == check_date or d == check_date - timedelta(days=1):
                nutrition_streak += 1
                check_date = d - timedelta(days=1)
            else:
                break

        return {
            "workout": workout_streak,
            "recovery": recovery_streak,
            "nutrition": nutrition_streak,
        }

    # --- Protein ---

    def get_protein_today(self) -> dict:
        """Get today's protein intake and goal for current profile."""
        profile = self.get_current_profile()
        meals = self.get_meals_today()
        return {
            "consumed": meals["totals"]["protein"],
            "goal": profile.get("protein_goal") or 100,
            "remaining": max(0, (profile.get("protein_goal") or 100) - meals["totals"]["protein"]),
            "meals": meals["meals"]
        }

    def quick_add_protein(self, name: str, protein: int) -> int:
        """Quick-add protein without full meal details."""
        return self.log_meal(meal_name=name, protein=protein, category="protein")

    def get_protein_streak(self) -> dict:
        """Count consecutive days (backwards from today) where protein >= 80% of goal."""
        profile_id = self._current_profile_id
        profile = self.get_current_profile()
        goal = profile.get("protein_goal") or 100
        threshold = goal * 0.8

        cursor = self.conn.execute("""
            SELECT date, SUM(protein) as total_protein
            FROM meal_logs WHERE profile_id = ?
            GROUP BY date ORDER BY date DESC
        """, (profile_id,))
        rows = cursor.fetchall()

        streak = 0
        best = 0
        current_streak = 0
        today = datetime.now().strftime("%Y-%m-%d")
        expected_date = datetime.now()

        for row in rows:
            row_date = row["date"]
            total = row["total_protein"] or 0
            expected_str = expected_date.strftime("%Y-%m-%d")

            # Skip future dates
            if row_date > today:
                continue

            # If there's a gap, break current streak
            if row_date != expected_str:
                if current_streak > best:
                    best = current_streak
                if streak == 0:
                    streak = current_streak
                current_streak = 0
                # Fast-forward expected_date to match row_date
                try:
                    expected_date = datetime.strptime(row_date, "%Y-%m-%d")
                except ValueError:
                    break

            if row_date == expected_date.strftime("%Y-%m-%d") and total >= threshold:
                current_streak += 1
                expected_date -= timedelta(days=1)
            else:
                if current_streak > best:
                    best = current_streak
                if streak == 0:
                    streak = current_streak
                current_streak = 0
                break

        # Final check
        if current_streak > best:
            best = current_streak
        if streak == 0:
            streak = current_streak

        return {"streak": streak, "best": best}

    # --- Protocols ---

    def create_protocol(self, name: str, description: str = None, started_at: str = None, phases: str = None) -> int:
        """Create a new protocol."""
        import json as _json
        profile_id = self._current_profile_id
        started = started_at or datetime.now().strftime("%Y-%m-%d")
        cursor = self.conn.execute("""
            INSERT INTO protocols (profile_id, name, description, started_at, phases)
            VALUES (?, ?, ?, ?, ?)
        """, (profile_id, name, description, started, phases))
        self.conn.commit()
        return cursor.lastrowid

    def get_protocols(self, status: str = None) -> list[dict]:
        """Get protocols for current profile."""
        import json as _json
        profile_id = self._current_profile_id
        if status:
            cursor = self.conn.execute(
                "SELECT * FROM protocols WHERE profile_id = ? AND status = ? ORDER BY created_at DESC",
                (profile_id, status))
        else:
            cursor = self.conn.execute(
                "SELECT * FROM protocols WHERE profile_id = ? ORDER BY created_at DESC",
                (profile_id,))
        results = []
        for row in cursor.fetchall():
            d = dict(row)
            # Compute current phase from started_at + cumulative duration
            if d.get("phases") and d["status"] == "active":
                try:
                    phases = _json.loads(d["phases"])
                    started = datetime.strptime(d["started_at"], "%Y-%m-%d")
                    elapsed = (datetime.now() - started).days
                    total_days = sum(p.get("duration_days", 0) for p in phases)

                    # Cycle finished but protocol still active (user decides when done)
                    if elapsed >= total_days:
                        last = phases[-1]
                        d["computed_phase"] = len(phases) - 1
                        d["elapsed_days"] = elapsed
                        d["total_days"] = total_days
                        d["phase_day"] = last.get("duration_days", 0)
                        d["phase_duration"] = last.get("duration_days", 0)
                        d["phase_name"] = last.get("name", f"Phase {len(phases)}")
                        d["cycle_complete"] = True
                        d["days_past"] = elapsed - total_days
                        d["phases_parsed"] = phases
                    else:
                        cumulative = 0
                        computed_phase = 0
                        for i, phase in enumerate(phases):
                            dur = phase.get("duration_days", 0)
                            if elapsed < cumulative + dur:
                                computed_phase = i
                                break
                            cumulative += dur
                        d["computed_phase"] = computed_phase
                        d["elapsed_days"] = elapsed
                        d["total_days"] = total_days
                        phase_start = sum(p.get("duration_days", 0) for p in phases[:computed_phase])
                        d["phase_day"] = elapsed - phase_start
                        d["phase_duration"] = phases[computed_phase].get("duration_days", 0)
                        d["phase_name"] = phases[computed_phase].get("name", f"Phase {computed_phase + 1}")
                        d["phases_parsed"] = phases
                except (ValueError, KeyError, IndexError):
                    pass
            results.append(d)
        return results

    def update_protocol(self, protocol_id: int, **kwargs) -> bool:
        """Update a protocol."""
        allowed = {"name", "description", "started_at", "phases", "current_phase", "status"}
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            return False
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [protocol_id, self._current_profile_id]
        cursor = self.conn.execute(
            f"UPDATE protocols SET {set_clause} WHERE id = ? AND profile_id = ?",
            values)
        self.conn.commit()
        return cursor.rowcount > 0

    def delete_protocol(self, protocol_id: int) -> bool:
        """Delete a protocol."""
        cursor = self.conn.execute(
            "DELETE FROM protocols WHERE id = ? AND profile_id = ?",
            (protocol_id, self._current_profile_id))
        self.conn.commit()
        return cursor.rowcount > 0

    # --- Reminders ---

    def create_reminder(self, title: str, schedule: str, description: str = None, protocol_id: int = None) -> int:
        """Create a reminder for the current profile."""
        import json as _json
        profile_id = self._current_profile_id
        cursor = self.conn.execute("""
            INSERT INTO reminders (profile_id, protocol_id, title, description, schedule)
            VALUES (?, ?, ?, ?, ?)
        """, (profile_id, protocol_id, title, description, schedule))
        self.conn.commit()
        return cursor.lastrowid

    def get_reminders(self, enabled_only: bool = True) -> list[dict]:
        """Get reminders for current profile."""
        profile_id = self._current_profile_id
        if enabled_only:
            cursor = self.conn.execute(
                "SELECT * FROM reminders WHERE profile_id = ? AND enabled = 1 ORDER BY created_at",
                (profile_id,))
        else:
            cursor = self.conn.execute(
                "SELECT * FROM reminders WHERE profile_id = ? ORDER BY created_at",
                (profile_id,))
        return [dict(row) for row in cursor.fetchall()]

    def get_due_reminders(self) -> list[dict]:
        """Get reminders that are due now based on schedule."""
        import json as _json
        reminders = self.get_reminders(enabled_only=True)
        now = datetime.now()
        current_time = now.strftime("%H:%M")
        due = []
        for r in reminders:
            try:
                sched = _json.loads(r["schedule"])
                sched_type = sched.get("type", "daily")
                sched_time = sched.get("time", "07:00")
                if sched_type == "daily":
                    # Due if current hour:minute matches (within 30 min window)
                    sh, sm = map(int, sched_time.split(":"))
                    ch, cm = now.hour, now.minute
                    diff = abs((ch * 60 + cm) - (sh * 60 + sm))
                    if diff <= 30:
                        due.append(r)
            except (ValueError, KeyError):
                continue
        return due

    def update_reminder(self, reminder_id: int, **kwargs) -> bool:
        """Update a reminder."""
        allowed = {"title", "description", "schedule", "enabled", "protocol_id"}
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            return False
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [reminder_id, self._current_profile_id]
        cursor = self.conn.execute(
            f"UPDATE reminders SET {set_clause} WHERE id = ? AND profile_id = ?",
            values)
        self.conn.commit()
        return cursor.rowcount > 0

    def delete_reminder(self, reminder_id: int) -> bool:
        """Delete a reminder."""
        cursor = self.conn.execute(
            "DELETE FROM reminders WHERE id = ? AND profile_id = ?",
            (reminder_id, self._current_profile_id))
        self.conn.commit()
        return cursor.rowcount > 0

    def seed_default_reminders(self) -> None:
        """Seed default reminders if none exist for the current profile."""
        import json as _json
        pid = self._current_profile_id
        existing = self.conn.execute(
            "SELECT COUNT(*) as c FROM reminders WHERE profile_id = ?", (pid,)
        ).fetchone()
        if existing and existing["c"] > 0:
            return

        self.conn.execute("""
            INSERT INTO reminders (profile_id, protocol_id, title, description, schedule)
            VALUES (?, NULL, 'Morning stretch routine', '10 minutes of dynamic stretching and mobility work.', ?)
        """, (pid, _json.dumps({"type": "daily", "time": "07:00"})))
        self.conn.commit()

    def seed_default_protocols(self) -> None:
        """Seed default protocols if none exist for the current profile."""
        import json as _json
        pid = self._current_profile_id
        existing = self.conn.execute(
            "SELECT COUNT(*) as c FROM protocols WHERE profile_id = ?", (pid,)
        ).fetchone()
        if existing and existing["c"] > 0:
            return

        phases = _json.dumps([
            {"name": "Phase 1 - Foundation", "duration_days": 28, "description": "Build base strength with compound movements 3x/week."},
            {"name": "Phase 2 - Build", "duration_days": 28, "description": "Increase volume and intensity. Add accessory work."},
            {"name": "Phase 3 - Peak", "duration_days": 14, "description": "Test new maxes. Deload and reassess."}
        ])
        self.conn.execute("""
            INSERT INTO protocols (profile_id, name, description, started_at, phases, status)
            VALUES (?, 'Beginner Strength Program', 'A simple 3-phase strength program focusing on compound lifts and progressive overload.', date('now'), ?, 'active')
        """, (pid, phases))

        self.conn.commit()

    # --- Cleanup ---

    def close(self) -> None:
        """Close the database connection."""
        self.conn.close()

    # Property to maintain compatibility with old code
    @property
    def topics_learned(self) -> dict:
        """Get topics as a dict for compatibility."""
        profile_id = self._current_profile_id
        cursor = self.conn.execute(
            "SELECT name, confidence_score FROM topics WHERE profile_id = ?",
            (profile_id,)
        )
        return {row["name"]: {"confidence_score": row["confidence_score"]} for row in cursor.fetchall()}

    @property
    def streaks(self):
        """Return a streak-like object for compatibility."""
        class StreakCompat:
            def __init__(self, tracker):
                self._tracker = tracker

            def update(self):
                self._tracker._update_streak()
                self._tracker.conn.commit()

            @property
            def current(self):
                return self._tracker.get_streak_info()["current"]

            @property
            def longest(self):
                return self._tracker.get_streak_info()["longest"]

        return StreakCompat(self)
