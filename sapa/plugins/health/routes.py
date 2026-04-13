"""Health plugin API routes.

Extracted from the original monolithic web.py into a FastAPI APIRouter.
"""

import asyncio
import json
import logging
import os
import re
import shutil
from contextlib import nullcontext
from pathlib import Path
from typing import Optional
from urllib.parse import unquote

from fastapi import APIRouter, HTTPException, Request

from .content import extract_topics_from_content, extract_title_from_content, extract_key_takeaways
from .equipment import PROFILE_EQUIPMENT
from .gap_targets import PROFILE_GAP_TARGETS
from ...gaps import compute_gap_analysis
from ...watcher import FolderWatcher, WatchedFile
from ...websocket import broadcast, connected_clients
from ...config import get_config

logger = logging.getLogger(__name__)

router = APIRouter()

# Module-level references, set during plugin startup
tracker: "HealthTracker | None" = None
watcher: FolderWatcher | None = None


# ============== Inbox Profile Mapping ==============

INBOX_PROFILE_MAP = {
    'john': 'john',
    'jane': 'jane',
}

PROFILE_INBOX_DIR = {v: k for k, v in INBOX_PROFILE_MAP.items()}


# ============== Helper Functions ==============

def get_profile_id_for_path(file_path: Path) -> Optional[int]:
    """Get profile ID based on inbox subdirectory, or None for root inbox."""
    if not tracker or not watcher:
        return None
    try:
        rel = file_path.relative_to(watcher.watch_path)
        if len(rel.parts) > 1:
            subdir = rel.parts[0].lower()
            profile_name = INBOX_PROFILE_MAP.get(subdir)
            if profile_name:
                profile = tracker.get_profile_by_name(profile_name)
                if profile:
                    return profile['id']
    except ValueError:
        pass
    return None


def file_belongs_to_profile(file_path: Path, profile_id: int) -> bool:
    """Check if a file belongs to the given profile.

    Files in a profile subdirectory belong to that profile.
    Files in the root inbox belong to every profile (backward compat).
    """
    file_profile = get_profile_id_for_path(file_path)
    if file_profile is None:
        # Root inbox file -- show to everyone
        return True
    return file_profile == profile_id


async def process_new_file(watched: WatchedFile, profile_id: Optional[int] = None):
    """Process a new file and extract learning data.

    If profile_id is given, processes under that profile. Otherwise uses the current active profile.
    """
    if not tracker:
        return

    # Use specified profile or current
    ctx = tracker.profile_context(profile_id) if profile_id else nullcontext()
    with ctx:
        # Extract topics from content
        topics = extract_topics_from_content(watched.content)

        # Save to history - prefer H1 title, then frontmatter topic, then extracted topics
        title = extract_title_from_content(watched.content) or watched.topic or ', '.join(topics[:3]) or 'General'

        # Dedup: skip if same topic+profile was inserted within last 60 seconds
        pid = profile_id or tracker.get_current_profile_id()
        existing = tracker.conn.execute(
            "SELECT id FROM history WHERE topic = ? AND profile_id = ? AND created_at >= datetime('now', '-60 seconds') LIMIT 1",
            (title, pid)
        ).fetchone()
        if not existing:
            # Also check by content prefix (catches older re-feeds)
            prompt_prefix = watched.content[:500]
            existing = tracker.conn.execute(
                "SELECT id FROM history WHERE topic = ? AND profile_id = ? AND prompt = ? LIMIT 1",
                (title, pid, prompt_prefix)
            ).fetchone()
        if existing:
            logger.info(f"Dedup skip: {watched.name} ({title}) already exists for profile {pid}")
            return

        # Record topics
        for topic in topics:
            tracker.record_learning(topic, confidence=0.6)

        tracker.save_history(
            session_type=watched.file_type or 'session',
            topic=title,
            prompt=watched.content[:500],
            response=watched.content,
        )

        target = f"profile {profile_id}" if profile_id else "current profile"
        logger.info(f"Processed file: {watched.name} -> {target}, extracted {len(topics)} topics")

    # Broadcast update
    await broadcast("file_processed", {
        "name": watched.name,
        "topics": topics,
        "type": watched.file_type,
    })


# ============== Recipes Helpers ==============

def load_all_recipes():
    """Load all recipes from JSON files."""
    recipes_dir = Path(__file__).parent / "data" / "recipes"
    all_recipes = []

    if not recipes_dir.exists():
        return all_recipes

    for json_file in recipes_dir.rglob("*.json"):
        try:
            with open(json_file) as f:
                data = json.load(f)
                all_recipes.extend(data)
        except Exception as e:
            logger.error(f"Error loading {json_file}: {e}")

    return all_recipes


# ============== Ingredient Categories ==============

INGREDIENT_CATEGORIES = {
    'produce': ['lettuce', 'tomato', 'onion', 'garlic', 'pepper', 'carrot', 'celery', 'broccoli', 'spinach', 'kale', 'cabbage', 'cucumber', 'zucchini', 'squash', 'potato', 'sweet potato', 'mushroom', 'avocado', 'lemon', 'lime', 'orange', 'apple', 'banana', 'berry', 'strawberry', 'blueberry', 'grape', 'mango', 'pineapple', 'cilantro', 'parsley', 'basil', 'mint', 'rosemary', 'thyme', 'ginger', 'jalapeño', 'serrano', 'scallion', 'green onion', 'shallot', 'leek', 'asparagus', 'corn', 'peas', 'beans', 'bell pepper', 'chili', 'radish', 'beet', 'turnip', 'eggplant', 'artichoke', 'fennel', 'bok choy', 'arugula', 'watercress', 'endive', 'radicchio'],
    'meat': ['chicken', 'beef', 'pork', 'steak', 'ground beef', 'ground turkey', 'turkey', 'bacon', 'sausage', 'ham', 'lamb', 'veal', 'duck', 'ribs', 'roast', 'brisket', 'tenderloin', 'sirloin', 'ribeye', 'chuck', 'flank', 'skirt', 'drumstick', 'thigh', 'breast', 'wing', 'meatball', 'hot dog', 'chorizo', 'prosciutto', 'salami', 'pepperoni', 'fish', 'salmon', 'tuna', 'shrimp', 'crab', 'lobster', 'scallop', 'mussel', 'clam', 'oyster', 'cod', 'tilapia', 'halibut', 'trout', 'mahi', 'snapper', 'anchovy', 'sardine', 'catfish', 'crawfish', 'calamari', 'octopus'],
    'dairy': ['milk', 'cheese', 'butter', 'cream', 'yogurt', 'sour cream', 'cream cheese', 'cottage cheese', 'ricotta', 'mozzarella', 'cheddar', 'parmesan', 'feta', 'goat cheese', 'brie', 'swiss', 'provolone', 'gouda', 'jack', 'colby', 'american cheese', 'half and half', 'heavy cream', 'whipping cream', 'buttermilk', 'egg', 'eggs'],
    'pantry': ['oil', 'olive oil', 'vegetable oil', 'coconut oil', 'vinegar', 'soy sauce', 'fish sauce', 'worcestershire', 'hot sauce', 'ketchup', 'mustard', 'mayonnaise', 'honey', 'maple syrup', 'sugar', 'brown sugar', 'flour', 'rice', 'pasta', 'noodle', 'bread crumb', 'panko', 'oat', 'quinoa', 'couscous', 'barley', 'lentil', 'chickpea', 'black bean', 'kidney bean', 'pinto bean', 'navy bean', 'cannellini', 'salt', 'pepper', 'paprika', 'cumin', 'oregano', 'cinnamon', 'nutmeg', 'cayenne', 'chili powder', 'curry', 'turmeric', 'coriander', 'cardamom', 'clove', 'bay leaf', 'vanilla', 'baking soda', 'baking powder', 'yeast', 'cornstarch', 'tomato paste', 'tomato sauce', 'diced tomato', 'crushed tomato', 'broth', 'stock', 'bouillon', 'coconut milk', 'almond', 'walnut', 'pecan', 'cashew', 'peanut', 'pine nut', 'sesame', 'chia', 'flax', 'tahini', 'peanut butter', 'jam', 'jelly', 'preserve', 'raisin', 'dried fruit', 'crouton', 'tortilla', 'taco shell', 'wrap', 'pita', 'naan'],
    'frozen': ['frozen', 'ice cream', 'popsicle', 'frozen vegetable', 'frozen fruit', 'frozen pizza', 'frozen dinner', 'frozen fries', 'frozen pie'],
    'bakery': ['bread', 'bun', 'roll', 'bagel', 'croissant', 'muffin', 'donut', 'cake', 'pie', 'cookie', 'pastry', 'tortilla', 'pita', 'naan', 'focaccia', 'ciabatta', 'sourdough', 'baguette', 'brioche']
}


def categorize_ingredient(ingredient_name: str) -> str:
    """Auto-categorize an ingredient based on its name."""
    name_lower = ingredient_name.lower()
    for category, keywords in INGREDIENT_CATEGORIES.items():
        for keyword in keywords:
            if keyword in name_lower:
                return category
    return 'other'


# ============== API Routes ==============

@router.get("/api/status")
async def get_status():
    """Get server status."""
    config = get_config()
    return {
        "status": "running",
        "watch_path": str(watcher.watch_path) if watcher else None,
        "files_count": len(watcher.files) if watcher else 0,
        "connected_clients": len(connected_clients),
        "user_name": config.user_name,
    }


@router.get("/api/sessions")
async def get_sessions(request: Request, limit: int = 50):
    """Get learning sessions from watched files for the current profile."""
    if not watcher or not tracker:
        return []

    profile_id = tracker.get_current_profile_id()
    sessions = []
    for f in watcher.get_files():
        if not file_belongs_to_profile(f.path, profile_id):
            continue
        topics = extract_topics_from_content(f.content)
        takeaways = extract_key_takeaways(f.content)
        # Extract title from H1 heading first, then fallback to frontmatter or topics
        title = extract_title_from_content(f.content) or f.topic or ', '.join(topics[:3]) or 'General'
        sessions.append({
            "name": f.name,
            "path": str(f.path),
            "type": f.file_type or 'session',
            "topic": title,
            "topics": topics,
            "takeaways": takeaways,
            "content": f.content,
            "created": f.created_at.isoformat() if f.created_at else None,
            "status": f.status,
        })

    return sorted(sessions, key=lambda x: x.get('created') or '', reverse=True)[:limit]


@router.delete("/api/sessions/{filename:path}")
async def delete_session(filename: str):
    """Delete a session file and its history entry."""
    if not watcher:
        return {"success": False, "error": "Watcher not initialized"}

    # Decode URL-encoded filename
    filename = unquote(filename)
    actual_name = Path(filename).name  # Get just the filename for watcher cleanup

    # Find the file - first try exact path, then search by name in watcher
    file_path = (watcher.watch_path / filename).resolve()

    # Prevent path traversal - ensure resolved path stays within watch_path
    if not str(file_path).startswith(str(watcher.watch_path.resolve())):
        return {"success": False, "error": "Invalid filename"}
    found_key = None

    if not file_path.exists():
        # Search in watcher's files by name (handles profile subdirectories)
        for key, watched in watcher.files.items():
            if watched.name == filename or watched.name == actual_name:
                file_path = watched.path
                actual_name = watched.name
                found_key = key
                break

    if file_path.exists():
        os.remove(file_path)
        # Remove from watcher's internal list
        if found_key:
            watcher.files.pop(found_key, None)
        else:
            watcher.files = {k: v for k, v in watcher.files.items() if v.name != actual_name}

    # Delete from history by matching the topic/content
    if tracker:
        history = tracker.get_history(limit=500)
        for h in history:
            if h.get('topic', '').lower().replace(' ', '_') in actual_name.lower().replace(' ', '_'):
                tracker.delete_history(h['id'])
                break

    return {"success": True}


@router.post("/api/sessions/share")
async def share_session(request: Request):
    """Copy a session file to another profile's inbox, or create one from history."""
    if not watcher or not tracker:
        return {"success": False, "error": "Not initialized"}

    data = await request.json()
    filename = data.get("filename", "")
    history_id = data.get("history_id")
    target_profile_id = data.get("profile_id")
    if not target_profile_id:
        return {"success": False, "error": "profile_id required"}

    # Resolve target subdirectory first
    target_profile = tracker.get_profile(target_profile_id)
    if not target_profile:
        return {"success": False, "error": "Profile not found"}
    target_dir_name = PROFILE_INBOX_DIR.get(target_profile['name'])
    if not target_dir_name:
        return {"success": False, "error": "No inbox directory for profile"}

    dest_dir = watcher.watch_path / target_dir_name
    dest_dir.mkdir(exist_ok=True)

    # If history_id provided, create a file from history content
    if history_id:
        entry = tracker.get_history_entry(history_id)
        if not entry:
            return {"success": False, "error": "History entry not found"}

        # Create filename from topic
        safe_topic = re.sub(r'[^\w\s-]', '', entry.get('topic', 'session')).strip().lower()
        safe_topic = re.sub(r'[-\s]+', '_', safe_topic)[:50]
        dest_name = f"{safe_topic}.md"
        dest = dest_dir / dest_name

        # Handle duplicates
        counter = 1
        while dest.exists():
            dest_name = f"{safe_topic}_{counter}.md"
            dest = dest_dir / dest_name
            counter += 1

        # Write the history content as a new file
        # Watchdog will detect and process it automatically
        content = entry.get('response') or entry.get('prompt') or ''
        dest.write_text(content)

        return {"success": True, "profile": target_profile['display_name']}

    # Otherwise, share an inbox file
    if not filename:
        return {"success": False, "error": "filename or history_id required"}

    # Find the source file in the watcher (search by name, handles subdirectories)
    actual_name = Path(filename).name
    source = None
    for f in watcher.get_files():
        if f.name == filename or f.name == actual_name:
            source = f
            break
    if not source or not source.path.exists():
        return {"success": False, "error": "File not found"}

    # Resolve target subdirectory
    target_profile = tracker.get_profile(target_profile_id)
    if not target_profile:
        return {"success": False, "error": "Profile not found"}
    target_dir_name = PROFILE_INBOX_DIR.get(target_profile['name'])
    if not target_dir_name:
        return {"success": False, "error": "No inbox directory for profile"}

    dest_dir = watcher.watch_path / target_dir_name
    dest_dir.mkdir(exist_ok=True)
    dest = dest_dir / source.name
    if dest.exists():
        return {"success": False, "error": "File already exists for that profile"}

    # Copy file to target inbox — watchdog will detect and process it automatically
    shutil.copy2(source.path, dest)

    return {"success": True, "profile": target_profile['display_name']}


@router.get("/api/analytics")
async def get_analytics():
    """Get comprehensive learning analytics."""
    if not tracker:
        return {}

    report = tracker.get_weekly_report()
    streak = tracker.get_streak_info()
    topics = tracker.get_all_topics()
    history = tracker.get_history(limit=500)

    total_sessions = len(history)

    # Topic frequency (top 15 by review count)
    topic_freq = {}
    for t in topics:
        topic_freq[t['name']] = t.get('review_count', 1)
    top_topics = dict(sorted(topic_freq.items(), key=lambda x: x[1], reverse=True)[:15])

    # Session types breakdown
    type_counts = {}
    for h in history:
        t = h.get('session_type', 'other')
        type_counts[t] = type_counts.get(t, 0) + 1

    # 90-day daily activity from DB
    from datetime import datetime, timedelta
    daily_activity_90 = {}
    today = datetime.now().date()
    cursor = tracker.conn.execute("""
        SELECT session_date, topics_learned + quizzes_taken as activity
        FROM daily_sessions
        WHERE session_date >= ? AND profile_id = ?
    """, ((today - timedelta(days=90)).strftime("%Y-%m-%d"), tracker._current_profile_id))
    for row in cursor.fetchall():
        daily_activity_90[str(row["session_date"])] = row["activity"] or 0

    # Confidence distribution
    confidence_buckets = {"mastered": 0, "strong": 0, "learning": 0, "weak": 0}
    for t in topics:
        score = t.get('confidence_score', 0)
        if score >= 0.8:
            confidence_buckets["mastered"] += 1
        elif score >= 0.6:
            confidence_buckets["strong"] += 1
        elif score >= 0.3:
            confidence_buckets["learning"] += 1
        else:
            confidence_buckets["weak"] += 1

    # Weekly totals for last 12 weeks
    weekly_totals = []
    for w in range(11, -1, -1):
        week_start = today - timedelta(days=today.weekday() + 7 * w)
        week_end = week_start + timedelta(days=6)
        total = sum(
            v for k, v in daily_activity_90.items()
            if week_start.strftime("%Y-%m-%d") <= k <= week_end.strftime("%Y-%m-%d")
        )
        weekly_totals.append({
            "week": week_start.strftime("%b %d"),
            "total": total,
            "current": w == 0,
        })

    due_reviews = tracker.get_due_reviews()
    review_timeline = tracker.get_review_timeline()
    new_vs_review = tracker.get_new_vs_review_stats()

    return {
        "overview": {
            "total_topics": report.get('total_topics', 0),
            "total_sessions": total_sessions,
            "current_streak": streak.get('current', 0),
            "longest_streak": streak.get('longest', 0),
            "this_week": report.get('new_topics_count', 0),
            "due_reviews": len(due_reviews),
        },
        "streak": streak,
        "topics": topics[:20],
        "topic_frequency": top_topics,
        "confidence_distribution": confidence_buckets,
        "session_types": type_counts,
        "daily_activity": daily_activity_90,
        "weekly_chart": report.get('weekly_chart', []),
        "weekly_totals": weekly_totals,
        "knowledge_gaps": tracker.get_knowledge_gaps()[:10],
        "due_reviews": due_reviews[:15],
        "review_timeline": review_timeline,
        "new_vs_review": new_vs_review,
    }


@router.get("/api/topics")
async def get_topics():
    """Get all topics with details."""
    if not tracker:
        return []
    return tracker.get_all_topics()


@router.get("/api/debug/topics/{profile_id}")
async def debug_topics(profile_id: int):
    """Debug: get topics for a specific profile directly."""
    if not tracker:
        return {"error": "Not initialized"}
    cursor = tracker.conn.execute(
        "SELECT name, profile_id FROM topics WHERE profile_id = ? LIMIT 20",
        (profile_id,)
    )
    return [dict(row) for row in cursor.fetchall()]


@router.get("/api/gap-analysis")
async def get_gap_analysis():
    """Analyze learning gaps based on target knowledge areas."""
    if not tracker:
        return {"categories": [], "summary": {}}
    profile_id = tracker.get_current_profile_id()
    gap_targets = PROFILE_GAP_TARGETS.get(profile_id, {})
    learned_topics = {t['name'].lower() for t in tracker.get_all_topics()}
    return compute_gap_analysis(learned_topics, gap_targets)


@router.get("/api/history")
async def get_history(limit: int = 50, session_type: Optional[str] = None):
    """Get session history."""
    if not tracker:
        return []
    return tracker.get_history(limit=limit, session_type=session_type)


@router.get("/api/history/{entry_id}")
async def get_history_entry(entry_id: int):
    """Get a single history entry by ID."""
    if not tracker:
        return {}
    entry = tracker.get_history_entry(entry_id)
    if not entry:
        return {}
    return entry


@router.delete("/api/history/{entry_id}")
async def delete_history_entry(entry_id: int):
    """Delete a history entry by ID."""
    if not tracker:
        return {"success": False, "error": "Tracker not initialized"}
    try:
        tracker.delete_history(entry_id)
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============== Profile Management ==============

@router.get("/api/profiles")
async def get_profiles():
    """Get all profiles."""
    from ...app import get_profile_manager
    pm = get_profile_manager()
    if not pm:
        return []
    return pm.get_profiles()


@router.get("/api/profiles/current")
async def get_current_profile(request: Request):
    """Get the current active profile (from cookie)."""
    if not tracker:
        return {"error": "Not initialized"}
    # Middleware already set _current_profile_id from cookie
    profile = tracker.get_current_profile()
    return profile if profile else {"error": "No profile"}


@router.put("/api/profiles/current/{profile_id}")
async def set_current_profile(profile_id: int):
    """Confirm a profile switch. Actual state comes from the profile_id cookie per-browser."""
    if not tracker:
        return {"success": False, "error": "Not initialized"}
    profile = tracker.get_profile(profile_id)
    if profile:
        return {"success": True, "profile": profile}
    return {"success": False, "error": "Profile not found"}


@router.post("/api/profiles")
async def create_profile(request: Request):
    """Create a new profile."""
    from ...app import get_profile_manager
    pm = get_profile_manager()
    if not pm:
        return {"error": "Not initialized"}
    try:
        data = await request.json()
        name = data.get("name", "").lower().strip()
        display_name = data.get("display_name", name).strip()
        if not name:
            return {"error": "Name is required"}
        profile_id = pm.create_profile(name, display_name)
        return {"success": True, "profile_id": profile_id}
    except Exception as e:
        return {"error": str(e)}


# ============== Protocols ==============

@router.get("/api/protocols")
async def get_protocols(status: Optional[str] = None):
    """Get protocols for current profile."""
    if not tracker:
        return []
    return tracker.get_protocols(status=status)


@router.post("/api/protocols")
async def create_protocol(request: Request):
    """Create a new protocol."""
    if not tracker:
        return {"error": "Not initialized"}
    data = await request.json()
    pid = tracker.create_protocol(
        name=data.get("name", ""),
        description=data.get("description"),
        started_at=data.get("started_at"),
        phases=json.dumps(data["phases"]) if "phases" in data else None,
    )
    return {"success": True, "id": pid}


@router.put("/api/protocols/{protocol_id}")
async def update_protocol(protocol_id: int, request: Request):
    """Update a protocol."""
    if not tracker:
        return {"error": "Not initialized"}
    data = await request.json()
    if "phases" in data and isinstance(data["phases"], list):
        data["phases"] = json.dumps(data["phases"])
    ok = tracker.update_protocol(protocol_id, **data)
    return {"success": ok}


@router.delete("/api/protocols/{protocol_id}")
async def delete_protocol(protocol_id: int):
    """Delete a protocol."""
    if not tracker:
        return {"error": "Not initialized"}
    ok = tracker.delete_protocol(protocol_id)
    return {"success": ok}


# ============== Reminders ==============

@router.get("/api/reminders")
async def get_reminders():
    """Get all reminders for current profile."""
    if not tracker:
        return []
    return tracker.get_reminders(enabled_only=False)


@router.get("/api/reminders/due")
async def get_due_reminders():
    """Get reminders that are due now."""
    if not tracker:
        return []
    return tracker.get_due_reminders()


@router.post("/api/reminders")
async def create_reminder(request: Request):
    """Create a new reminder."""
    if not tracker:
        return {"error": "Not initialized"}
    data = await request.json()
    rid = tracker.create_reminder(
        title=data.get("title", ""),
        description=data.get("description"),
        schedule=json.dumps(data.get("schedule", {"type": "daily", "time": "07:00"})),
        protocol_id=data.get("protocol_id"),
    )
    return {"success": True, "id": rid}


@router.put("/api/reminders/{reminder_id}")
async def update_reminder(reminder_id: int, request: Request):
    """Update a reminder."""
    if not tracker:
        return {"error": "Not initialized"}
    data = await request.json()
    if "schedule" in data and isinstance(data["schedule"], dict):
        data["schedule"] = json.dumps(data["schedule"])
    ok = tracker.update_reminder(reminder_id, **data)
    return {"success": ok}


@router.delete("/api/reminders/{reminder_id}")
async def delete_reminder(reminder_id: int):
    """Delete a reminder."""
    if not tracker:
        return {"error": "Not initialized"}
    ok = tracker.delete_reminder(reminder_id)
    return {"success": ok}


_rescan_lock = asyncio.Lock()

@router.post("/api/rescan")
async def rescan_files():
    """Re-scan all inbox files from disk and re-extract topics."""
    if not watcher or not tracker:
        return {"error": "Not initialized"}

    # Prevent concurrent rescans from deadlocking the DB
    if _rescan_lock.locked():
        return {"success": False, "error": "Rescan already in progress"}

    async with _rescan_lock:
        all_topics = []  # (topic_name, confidence, profile_id)
        files_scanned = 0

        # Clear and reload all files from disk
        watcher.files.clear()
        for pattern in ["*.md", "*.txt", "*/*.md", "*/*.txt"]:
            for path in watcher.watch_path.glob(pattern):
                if path.name.startswith("."):
                    continue
                try:
                    rel = path.relative_to(watcher.watch_path)
                    if 'archive' in rel.parts:
                        continue
                except ValueError:
                    continue
                try:
                    watched = WatchedFile.from_path(path)
                    watcher.files[str(path)] = watched
                    files_scanned += 1

                    # Use correct profile based on file path
                    profile_id = get_profile_id_for_path(path)
                    pid = profile_id or tracker.get_current_profile_id()
                    topics = extract_topics_from_content(watched.content)
                    for topic in topics:
                        all_topics.append((topic, 0.6, pid))
                except Exception as e:
                    logger.error(f"Error scanning {path}: {e}")

        # Single transaction for all topic recordings
        topics_added = tracker.record_learning_batch(all_topics)

    return {
        "success": True,
        "files_scanned": files_scanned,
        "topics_recorded": topics_added
    }


# ============== Import/Export ==============

@router.get("/api/export")
async def export_data():
    """Export all learning data and inbox files for backup."""
    if not tracker or not watcher:
        return {"error": "Not initialized"}

    # Get database export
    data = tracker.export_data()

    # Add inbox files
    data["inbox_files"] = []
    for path in watcher.watch_path.glob("*.md"):
        if path.name.startswith("."):
            continue
        try:
            content = path.read_text(errors="replace")
            data["inbox_files"].append({
                "name": path.name,
                "content": content,
            })
        except Exception:
            pass

    return data


@router.post("/api/import")
async def import_data(request: Request):
    """Import learning data from backup."""
    if not tracker or not watcher:
        return {"error": "Not initialized"}

    try:
        data = await request.json()
    except Exception as e:
        return {"error": f"Invalid JSON: {e}"}

    merge = data.get("merge", False)

    # Import database data
    stats = tracker.import_data(data, merge=merge)

    # Import inbox files
    files_imported = 0
    for file_data in data.get("inbox_files", []):
        try:
            name = file_data.get("name", "")
            content = file_data.get("content", "")
            if name and content and name.endswith(".md"):
                file_path = watcher.watch_path / name
                if merge and file_path.exists():
                    continue  # Skip existing in merge mode
                file_path.write_text(content)
                files_imported += 1
        except Exception:
            pass

    stats["inbox_files"] = files_imported

    return {"success": True, "stats": stats}


# ============== Recipes API ==============

@router.get("/api/recipes")
async def get_recipes(category: Optional[str] = None, framework: Optional[str] = None, search: Optional[str] = None):
    """Get all recipes with optional filtering."""
    recipes = load_all_recipes()

    if category:
        recipes = [r for r in recipes if r.get("category") == category]

    if framework:
        recipes = [r for r in recipes if framework in r.get("frameworks", [])]

    if search:
        search_lower = search.lower()
        recipes = [r for r in recipes if
                   search_lower in r.get("title", "").lower() or
                   search_lower in r.get("description", "").lower() or
                   any(search_lower in tag.lower() for tag in r.get("tags", [])) or
                   any(search_lower in ing.get("name", "").lower() for ing in r.get("ingredients", []))]

    return recipes


# ============== Recipe Favorites & Cook Log API ==============
# NOTE: These must be registered BEFORE /api/recipes/{recipe_id} to avoid path capture

@router.get("/api/recipes/favorites")
async def get_recipe_favorites():
    """Get current profile's favorite recipe IDs."""
    if not tracker:
        return []
    try:
        cursor = tracker.conn.cursor()
        cursor.execute(
            "SELECT recipe_id FROM recipe_favorites WHERE profile_id = ?",
            (tracker._current_profile_id,)
        )
        return [row['recipe_id'] for row in cursor.fetchall()]
    except Exception as e:
        return {"error": str(e)}


@router.post("/api/recipes/favorites")
async def toggle_recipe_favorite(request: Request):
    """Toggle favorite on a recipe (add/remove)."""
    if not tracker:
        return {"error": "Not initialized"}
    try:
        data = await request.json()
        recipe_id = data.get("recipe_id")
        if not recipe_id:
            return {"error": "recipe_id required"}

        cursor = tracker.conn.cursor()
        # Check if already favorited
        existing = cursor.execute(
            "SELECT id FROM recipe_favorites WHERE profile_id = ? AND recipe_id = ?",
            (tracker._current_profile_id, recipe_id)
        ).fetchone()

        if existing:
            cursor.execute("DELETE FROM recipe_favorites WHERE id = ?", (existing['id'],))
            tracker.conn.commit()
            return {"success": True, "favorited": False}
        else:
            cursor.execute(
                "INSERT INTO recipe_favorites (profile_id, recipe_id) VALUES (?, ?)",
                (tracker._current_profile_id, recipe_id)
            )
            tracker.conn.commit()
            return {"success": True, "favorited": True}
    except Exception as e:
        return {"error": str(e)}


@router.get("/api/recipes/cook-log")
async def get_recipe_cook_log():
    """Get cooking history for current profile."""
    if not tracker:
        return []
    try:
        cursor = tracker.conn.cursor()
        cursor.execute("""
            SELECT recipe_id, servings, cooked_at
            FROM recipe_cook_log
            WHERE profile_id = ?
            ORDER BY cooked_at DESC
            LIMIT 200
        """, (tracker._current_profile_id,))
        return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        return {"error": str(e)}


@router.post("/api/recipes/cook-log")
async def log_recipe_cook(request: Request):
    """Log that a recipe was cooked."""
    if not tracker:
        return {"error": "Not initialized"}
    try:
        data = await request.json()
        recipe_id = data.get("recipe_id")
        if not recipe_id:
            return {"error": "recipe_id required"}

        servings = data.get("servings", 1)
        cursor = tracker.conn.cursor()
        cursor.execute(
            "INSERT INTO recipe_cook_log (profile_id, recipe_id, servings) VALUES (?, ?, ?)",
            (tracker._current_profile_id, recipe_id, servings)
        )
        tracker.conn.commit()
        return {"success": True, "id": cursor.lastrowid}
    except Exception as e:
        return {"error": str(e)}


@router.get("/api/recipes/{recipe_id}")
async def get_recipe(recipe_id: str):
    """Get a single recipe by ID."""
    recipes = load_all_recipes()
    for recipe in recipes:
        if recipe.get("id") == recipe_id or recipe.get("slug") == recipe_id:
            return recipe
    return {"error": "Recipe not found"}


@router.post("/api/grocery/from-recipe")
async def add_recipe_to_grocery(request: Request):
    """Add a recipe's ingredients to the grocery list."""
    if not tracker:
        return {"error": "Not initialized"}
    try:
        data = await request.json()
        recipe_id = data.get("recipe_id")
        if not recipe_id:
            return {"error": "recipe_id required"}

        multiplier = float(data.get("servings", 1))

        # Find the recipe
        all_recipes = load_all_recipes()
        recipe = None
        for r in all_recipes:
            if r.get('id') == recipe_id:
                recipe = r
                break
        if not recipe:
            return {"error": "Recipe not found"}

        cursor = tracker.conn.cursor()
        added = 0
        for ing in recipe.get('ingredients', []):
            name = ing.get('name', '')
            if not name:
                continue
            amount = ing.get('amount', '')
            unit = ing.get('unit', '')
            category = ing.get('category', categorize_ingredient(name))

            qty = None
            if amount:
                try:
                    scaled = float(amount) * multiplier
                    display = str(int(scaled)) if scaled == int(scaled) else f"{scaled:.1f}"
                    qty = f"{display} {unit}".strip()
                except (ValueError, TypeError):
                    qty = f"{amount} {unit}".strip()

            # Check if item already exists unchecked - aggregate
            existing = cursor.execute(
                "SELECT id, quantity FROM grocery_list WHERE LOWER(item) = ? AND checked = 0 LIMIT 1",
                (name.lower(),)
            ).fetchone()

            if existing and existing['quantity'] and qty:
                # Append to existing quantity
                new_qty = existing['quantity'] + ' + ' + qty
                cursor.execute("UPDATE grocery_list SET quantity = ? WHERE id = ?", (new_qty, existing['id']))
            else:
                cursor.execute(
                    "INSERT INTO grocery_list (item, category, quantity, source) VALUES (?, ?, ?, 'generated')",
                    (name, category, qty)
                )
            added += 1

        tracker.conn.commit()
        return {"success": True, "added": added, "recipe": recipe.get('title', '')}
    except Exception as e:
        return {"error": str(e)}


# ============== Meal Planner API ==============

@router.post("/api/meal-requests")
async def create_meal_request(request: Request):
    """Create a meal request (any profile can request)."""
    if not tracker:
        return {"error": "Not initialized"}
    try:
        data = await request.json()
        cursor = tracker.conn.cursor()
        cursor.execute("""
            INSERT INTO meal_requests (profile_id, recipe_id, recipe_name, notes, requested_date, status)
            VALUES (?, ?, ?, ?, ?, 'pending')
        """, (
            tracker._current_profile_id,
            data.get("recipe_id"),
            data.get("recipe_name", "Custom Request"),
            data.get("notes"),
            data.get("requested_date")
        ))
        tracker.conn.commit()
        return {"success": True, "request_id": cursor.lastrowid}
    except Exception as e:
        return {"error": str(e)}


@router.get("/api/meal-requests")
async def get_meal_requests(status: str = None):
    """Get meal requests. All profiles can see all requests."""
    if not tracker:
        return []
    try:
        cursor = tracker.conn.cursor()
        if status:
            cursor.execute("""
                SELECT mr.*, p.display_name as requester_name
                FROM meal_requests mr
                JOIN profiles p ON mr.profile_id = p.id
                WHERE mr.status = ?
                ORDER BY mr.created_at DESC
            """, (status,))
        else:
            cursor.execute("""
                SELECT mr.*, p.display_name as requester_name
                FROM meal_requests mr
                JOIN profiles p ON mr.profile_id = p.id
                ORDER BY mr.created_at DESC
            """)
        return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        return {"error": str(e)}


@router.put("/api/meal-requests/{request_id}")
async def update_meal_request(request_id: int, request: Request):
    """Update a meal request status."""
    if not tracker:
        return {"error": "Not initialized"}
    try:
        data = await request.json()
        tracker.conn.execute("""
            UPDATE meal_requests SET status = ? WHERE id = ?
        """, (data.get("status", "pending"), request_id))
        tracker.conn.commit()
        return {"success": True}
    except Exception as e:
        return {"error": str(e)}


@router.post("/api/meal-plans")
async def create_meal_plan(request: Request):
    """Create a meal plan entry."""
    if not tracker:
        return {"error": "Not initialized"}
    try:
        data = await request.json()
        cursor = tracker.conn.cursor()
        cursor.execute("""
            INSERT INTO meal_plans (plan_date, meal_type, recipe_id, recipe_name, notes, request_id)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            data.get("plan_date"),
            data.get("meal_type", "dinner"),
            data.get("recipe_id"),
            data.get("recipe_name"),
            data.get("notes"),
            data.get("request_id")
        ))
        tracker.conn.commit()
        # If fulfilling a request, mark it as planned
        if data.get("request_id"):
            tracker.conn.execute("""
                UPDATE meal_requests SET status = 'planned' WHERE id = ?
            """, (data.get("request_id"),))
            tracker.conn.commit()
        return {"success": True, "plan_id": cursor.lastrowid}
    except Exception as e:
        return {"error": str(e)}


@router.get("/api/meal-plans")
async def get_meal_plans(start_date: str = None, end_date: str = None):
    """Get meal plans for a date range."""
    if not tracker:
        return []
    try:
        cursor = tracker.conn.cursor()
        if start_date and end_date:
            cursor.execute("""
                SELECT * FROM meal_plans
                WHERE plan_date >= ? AND plan_date <= ?
                ORDER BY plan_date, meal_type
            """, (start_date, end_date))
        else:
            # Default to this week
            cursor.execute("""
                SELECT * FROM meal_plans
                WHERE plan_date >= date('now', '-1 day', 'localtime')
                ORDER BY plan_date, meal_type
                LIMIT 50
            """)
        return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        return {"error": str(e)}


@router.delete("/api/meal-plans/{plan_id}")
async def delete_meal_plan(plan_id: int):
    """Delete a meal plan entry."""
    if not tracker:
        return {"error": "Not initialized"}
    try:
        tracker.conn.execute("DELETE FROM meal_plans WHERE id = ?", (plan_id,))
        tracker.conn.commit()
        return {"success": True}
    except Exception as e:
        return {"error": str(e)}


# ============== Grocery List API ==============

@router.get("/api/grocery")
async def get_grocery_list():
    """Get all grocery list items."""
    if not tracker:
        return []
    try:
        cursor = tracker.conn.cursor()
        cursor.execute("""
            SELECT * FROM grocery_list ORDER BY checked, category, created_at
        """)
        return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        return {"error": str(e)}


@router.post("/api/grocery")
async def add_grocery_item(request: Request):
    """Add item to grocery list."""
    if not tracker:
        return {"error": "Not initialized"}
    try:
        data = await request.json()
        cursor = tracker.conn.cursor()
        cursor.execute("""
            INSERT INTO grocery_list (item, category, quantity, source) VALUES (?, ?, ?, 'manual')
        """, (data.get("item"), data.get("category", "other"), data.get("quantity")))
        tracker.conn.commit()
        return {"success": True, "id": cursor.lastrowid}
    except Exception as e:
        return {"error": str(e)}


@router.put("/api/grocery/{item_id}")
async def update_grocery_item(item_id: int, request: Request):
    """Update a grocery item (toggle checked, etc)."""
    if not tracker:
        return {"error": "Not initialized"}
    try:
        data = await request.json()
        if "checked" in data:
            tracker.conn.execute("UPDATE grocery_list SET checked = ? WHERE id = ?", (data["checked"], item_id))
        if "item" in data:
            tracker.conn.execute("UPDATE grocery_list SET item = ? WHERE id = ?", (data["item"], item_id))
        if "quantity" in data:
            tracker.conn.execute("UPDATE grocery_list SET quantity = ? WHERE id = ?", (data["quantity"], item_id))
        if "category" in data:
            tracker.conn.execute("UPDATE grocery_list SET category = ? WHERE id = ?", (data["category"], item_id))
        tracker.conn.commit()
        return {"success": True}
    except Exception as e:
        return {"error": str(e)}


@router.delete("/api/grocery/checked")
async def clear_checked_groceries():
    """Clear all checked grocery items."""
    if not tracker:
        return {"error": "Not initialized"}
    try:
        tracker.conn.execute("DELETE FROM grocery_list WHERE checked = 1")
        tracker.conn.commit()
        return {"success": True}
    except Exception as e:
        return {"error": str(e)}


@router.delete("/api/grocery/all")
async def clear_all_groceries():
    """Clear all grocery items."""
    if not tracker:
        return {"error": "Not initialized"}
    try:
        tracker.conn.execute("DELETE FROM grocery_list")
        tracker.conn.commit()
        return {"success": True}
    except Exception as e:
        return {"error": str(e)}


@router.delete("/api/grocery/{item_id}")
async def delete_grocery_item(item_id: int):
    """Delete a grocery item."""
    if not tracker:
        return {"error": "Not initialized"}
    try:
        tracker.conn.execute("DELETE FROM grocery_list WHERE id = ?", (item_id,))
        tracker.conn.commit()
        return {"success": True}
    except Exception as e:
        return {"error": str(e)}


@router.post("/api/grocery/generate")
async def generate_grocery_list(request: Request):
    """Generate grocery list from this week's meal plan."""
    if not tracker:
        return {"error": "Not initialized"}
    try:
        # Optional servings multiplier from request body
        multiplier = 1
        try:
            data = await request.json()
            multiplier = float(data.get("servings_multiplier", 1))
        except Exception:
            pass

        # Get this week's meal plans
        cursor = tracker.conn.cursor()
        cursor.execute("""
            SELECT recipe_name, recipe_id FROM meal_plans
            WHERE plan_date >= date('now', '-1 day', 'localtime')
            AND plan_date <= date('now', '+7 days', 'localtime')
        """)
        meal_plans = cursor.fetchall()

        if not meal_plans:
            return {"error": "No meals planned for this week", "added": 0}

        # Load all recipes
        all_recipes = load_all_recipes()
        recipe_map = {r.get('title', '').lower(): r for r in all_recipes}
        recipe_id_map = {r.get('id', ''): r for r in all_recipes}

        # Aggregate ingredients: key -> {item, category, amounts: [(amount, unit)]}
        aggregated = {}

        for plan in meal_plans:
            recipe_name = plan['recipe_name']
            recipe_id = plan['recipe_id']

            recipe = None
            if recipe_id:
                recipe = recipe_id_map.get(recipe_id)
            if not recipe:
                recipe = recipe_map.get(recipe_name.lower())

            if recipe and 'ingredients' in recipe:
                for ing in recipe['ingredients']:
                    name = ing.get('name', '')
                    if not name:
                        continue
                    key = name.lower()
                    amount = ing.get('amount', '')
                    unit = ing.get('unit', '')
                    # Use recipe's category field, fall back to name matching
                    category = ing.get('category', categorize_ingredient(name))

                    if key not in aggregated:
                        aggregated[key] = {
                            'item': name,
                            'category': category,
                            'amounts': []
                        }
                    if amount:
                        try:
                            aggregated[key]['amounts'].append((float(amount) * multiplier, unit))
                        except (ValueError, TypeError):
                            aggregated[key]['amounts'].append((amount, unit))

        # Build final quantities by combining matching units
        ingredients_to_add = {}
        for key, data in aggregated.items():
            amounts = data['amounts']
            if not amounts:
                ingredients_to_add[key] = {
                    'item': data['item'],
                    'quantity': None,
                    'category': data['category']
                }
                continue

            # Group by unit and sum
            unit_totals = {}
            for amt, unit in amounts:
                unit_key = (unit or '').strip().lower()
                if isinstance(amt, (int, float)):
                    unit_totals[unit_key] = unit_totals.get(unit_key, 0) + amt
                else:
                    # Non-numeric, just append
                    unit_totals[unit_key] = str(amt)

            # Format quantity string
            parts = []
            for unit_key, total in unit_totals.items():
                if isinstance(total, (int, float)):
                    # Clean display: show as int if whole number
                    display = str(int(total)) if total == int(total) else f"{total:.1f}"
                    parts.append(f"{display} {unit_key}".strip())
                else:
                    parts.append(f"{total} {unit_key}".strip())

            ingredients_to_add[key] = {
                'item': data['item'],
                'quantity': ', '.join(parts) if parts else None,
                'category': data['category']
            }

        # Only clear generated items, preserve manual items
        tracker.conn.execute("DELETE FROM grocery_list WHERE checked = 0 AND source = 'generated'")

        added = 0
        for ing_data in ingredients_to_add.values():
            cursor.execute("""
                INSERT INTO grocery_list (item, category, quantity, source) VALUES (?, ?, ?, 'generated')
            """, (ing_data['item'], ing_data['category'], ing_data['quantity']))
            added += 1

        tracker.conn.commit()
        return {"success": True, "added": added, "from_meals": len(meal_plans)}
    except Exception as e:
        return {"error": str(e)}


# ============== HULK Protocol API ==============

@router.post("/api/workouts")
async def create_workout(request: Request):
    """Create a new workout."""
    if not tracker:
        return {"error": "Not initialized"}
    try:
        data = await request.json()
        workout_id = tracker.create_workout(
            workout_type=data.get("type", "strength"),
            date=data.get("date"),
            duration=data.get("duration"),
            rpe=data.get("rpe"),
            notes=data.get("notes"),
        )
        # Add exercises if provided
        exercises = data.get("exercises", [])
        for i, ex in enumerate(exercises):
            tracker.add_exercise(
                workout_id=workout_id,
                name=ex.get("name", ""),
                sets=ex.get("sets"),
                reps=ex.get("reps"),
                weight=ex.get("weight"),
                rpe=ex.get("rpe"),
                notes=ex.get("notes"),
                order_index=i,
            )
        tracker.update_workout_totals(workout_id)
        return {"success": True, "workout_id": workout_id}
    except Exception as e:
        return {"error": str(e)}


@router.get("/api/workouts")
async def get_workouts(limit: int = 20, type: str = None):
    """Get workouts for current profile."""
    if not tracker:
        return []
    return tracker.get_workouts(limit=limit, workout_type=type)


@router.get("/api/workouts/{workout_id}")
async def get_workout(workout_id: int):
    """Get a single workout with exercises."""
    if not tracker:
        return {"error": "Not initialized"}
    workout = tracker.get_workout(workout_id)
    if not workout:
        raise HTTPException(status_code=404, detail="Workout not found")
    return workout


@router.delete("/api/workouts/{workout_id}")
async def delete_workout(workout_id: int):
    """Delete a workout."""
    if not tracker:
        return {"error": "Not initialized"}
    success = tracker.delete_workout(workout_id)
    return {"success": success}


@router.post("/api/recovery")
async def log_recovery(request: Request):
    """Log daily recovery metrics."""
    if not tracker:
        return {"error": "Not initialized"}
    try:
        data = await request.json()
        log_id = tracker.log_recovery(
            date=data.get("date"),
            sleep_hours=data.get("sleep_hours"),
            sleep_quality=data.get("sleep_quality"),
            soreness=data.get("soreness"),
            energy=data.get("energy"),
            stress=data.get("stress"),
            motivation=data.get("motivation"),
            notes=data.get("notes"),
        )
        return {"success": True, "id": log_id}
    except Exception as e:
        return {"error": str(e)}


@router.get("/api/recovery")
async def get_recovery(limit: int = 30):
    """Get recovery history."""
    if not tracker:
        return []
    return tracker.get_recovery_history(limit=limit)


@router.get("/api/recovery/today")
async def get_recovery_today():
    """Get today's recovery log."""
    if not tracker:
        return None
    return tracker.get_recovery_today()


@router.get("/api/readiness")
async def get_readiness():
    """Get readiness score from recovery data."""
    if not tracker:
        return {"score": None, "status": "no_data"}
    return tracker.get_readiness_score()


@router.post("/api/body")
async def log_body(request: Request):
    """Log body measurements."""
    if not tracker:
        return {"error": "Not initialized"}
    try:
        data = await request.json()
        log_id = tracker.log_body_measurement(
            date=data.get("date"),
            weight=data.get("weight"),
            waist=data.get("waist"),
            chest=data.get("chest"),
            arms=data.get("arms"),
            body_fat=data.get("body_fat"),
            notes=data.get("notes"),
        )
        return {"success": True, "id": log_id}
    except Exception as e:
        return {"error": str(e)}


@router.get("/api/body")
async def get_body_logs(limit: int = 30):
    """Get body measurement history."""
    if not tracker:
        return []
    return tracker.get_body_logs(limit=limit)


@router.post("/api/meals")
async def log_meal(request: Request):
    """Log a meal."""
    if not tracker:
        return {"error": "Not initialized"}
    try:
        data = await request.json()
        log_id = tracker.log_meal(
            meal_name=data.get("meal_name", "Meal"),
            date=data.get("date"),
            category=data.get("category"),
            calories=data.get("calories"),
            protein=data.get("protein"),
            carbs=data.get("carbs"),
            fat=data.get("fat"),
            notes=data.get("notes"),
        )
        return {"success": True, "id": log_id}
    except Exception as e:
        return {"error": str(e)}


@router.get("/api/meals")
async def get_meals(limit: int = 50):
    """Get meal history."""
    if not tracker:
        return []
    return tracker.get_meal_history(limit=limit)


@router.get("/api/meals/today")
async def get_meals_today():
    """Get today's meals with totals."""
    if not tracker:
        return {"meals": [], "totals": {}}
    return tracker.get_meals_today()


@router.delete("/api/meals/{meal_id}")
async def delete_meal(meal_id: int):
    """Delete a meal."""
    if not tracker:
        return {"error": "Not initialized"}
    success = tracker.delete_meal(meal_id)
    return {"success": success}


@router.get("/api/protein/today")
async def get_protein_today():
    """Get today's protein intake and goal."""
    if not tracker:
        return {"consumed": 0, "goal": 100, "remaining": 100, "meals": []}
    return tracker.get_protein_today()


@router.post("/api/protein/quick")
async def quick_add_protein(request: Request):
    """Quick-add protein."""
    if not tracker:
        return {"error": "Not initialized"}
    try:
        data = await request.json()
        log_id = tracker.quick_add_protein(
            name=data.get("name", "Protein"),
            protein=data.get("protein", 0),
        )
        return {"success": True, "id": log_id}
    except Exception as e:
        return {"error": str(e)}


@router.get("/api/protein/streak")
async def get_protein_streak():
    """Get protein streak data."""
    if not tracker:
        return {"streak": 0, "best": 0}
    return tracker.get_protein_streak()


@router.post("/api/goals")
async def create_goal(request: Request):
    """Create a new goal."""
    if not tracker:
        return {"error": "Not initialized"}
    try:
        data = await request.json()
        goal_id = tracker.create_goal(
            category=data.get("category", "general"),
            name=data.get("name", "Goal"),
            target=data.get("target", 0),
            unit=data.get("unit", ""),
            current=data.get("current"),
            deadline=data.get("deadline"),
        )
        return {"success": True, "goal_id": goal_id}
    except Exception as e:
        return {"error": str(e)}


@router.get("/api/goals")
async def get_goals(include_completed: bool = False):
    """Get goals for current profile."""
    if not tracker:
        return []
    return tracker.get_goals(include_completed=include_completed)


@router.put("/api/goals/{goal_id}")
async def update_goal(goal_id: int, request: Request):
    """Update goal progress."""
    if not tracker:
        return {"error": "Not initialized"}
    try:
        data = await request.json()
        success = tracker.update_goal(
            goal_id=goal_id,
            current=data.get("current"),
            completed=data.get("completed"),
        )
        return {"success": success}
    except Exception as e:
        return {"error": str(e)}


@router.delete("/api/goals/{goal_id}")
async def delete_goal(goal_id: int):
    """Delete a goal."""
    if not tracker:
        return {"error": "Not initialized"}
    success = tracker.delete_goal(goal_id)
    return {"success": success}


@router.get("/api/prs")
async def get_prs():
    """Get personal records."""
    if not tracker:
        return []
    return tracker.get_personal_records()


@router.get("/api/prs/history")
async def get_pr_history(exercise: str = None, limit: int = 20):
    """Get PR history."""
    if not tracker:
        return []
    return tracker.get_pr_history(exercise=exercise, limit=limit)


@router.get("/api/volume")
async def get_volume(days: int = 30):
    """Get volume analytics."""
    if not tracker:
        return {}
    return tracker.get_volume_analytics(days=days)


@router.get("/api/hulk-streaks")
async def get_hulk_streaks():
    """Get workout, recovery, and nutrition streaks."""
    if not tracker:
        return {"workout": 0, "recovery": 0, "nutrition": 0}
    return tracker.get_hulk_streaks()
