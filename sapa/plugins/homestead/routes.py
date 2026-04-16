"""Homestead plugin API routes."""

import asyncio
import logging
from pathlib import Path

from fastapi import APIRouter

from .content import extract_topics_from_content, extract_title_from_content
from .gap_targets import HOMESTEAD_GAP_TARGETS
from ...gaps import compute_gap_analysis
from ...watcher import FolderWatcher, WatchedFile
from ...websocket import broadcast

logger = logging.getLogger(__name__)

router = APIRouter()

# Module-level references, set during plugin startup
tracker: "HomesteadTracker | None" = None
watcher: FolderWatcher | None = None


async def process_new_file(watched: WatchedFile):
    """Process a new homestead inbox file into history."""
    if not tracker:
        return

    topics = extract_topics_from_content(watched.content)
    for topic in topics:
        tracker.record_learning(topic, mention_weight=0.5)

    title = extract_title_from_content(watched.content) or watched.topic or ', '.join(topics[:3]) or 'General'
    tracker.save_history(
        session_type=watched.file_type or 'session',
        topic=title,
        prompt=watched.content[:500],
        response=watched.content,
    )

    logger.info(f"Homestead processed: {watched.name} -> {title} ({len(topics)} topics)")

    await broadcast("homestead_file_created", {
        "name": watched.name,
        "topic": title,
        "type": watched.file_type,
    })


# ============== API Routes ==============

@router.get("/history")
async def get_history(limit: int = 50, search: str = None):
    """Get homestead session history."""
    if not tracker:
        return []
    return tracker.get_history(limit=limit, search=search)


@router.get("/history/{entry_id}")
async def get_history_entry(entry_id: int):
    """Get a single homestead history entry."""
    if not tracker:
        return {}
    entry = tracker.get_history_entry(entry_id)
    if not entry:
        return {}
    return entry


@router.delete("/history/{entry_id}")
async def delete_history_entry(entry_id: int):
    """Delete a homestead history entry."""
    if not tracker:
        return {"success": False, "error": "Tracker not initialized"}
    try:
        tracker.delete_history(entry_id)
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/sessions")
async def get_sessions():
    """Get homestead inbox files."""
    if not watcher:
        return []

    sessions = []
    for f in watcher.get_files():
        title = extract_title_from_content(f.content) or f.topic or 'General'
        topics = extract_topics_from_content(f.content)
        sessions.append({
            "name": f.name,
            "path": str(f.path),
            "type": f.file_type or 'session',
            "topic": title,
            "topics": topics,
            "content": f.content,
            "created": f.created_at.isoformat() if f.created_at else None,
            "status": f.status,
        })
    return sorted(sessions, key=lambda s: s.get("created") or "", reverse=True)


_rescan_lock = asyncio.Lock()

@router.post("/rescan")
async def rescan_files():
    """Re-scan homestead inbox files and ingest any missing from history."""
    if not watcher or not tracker:
        return {"error": "Not initialized"}

    if _rescan_lock.locked():
        return {"success": False, "error": "Rescan already in progress"}

    async with _rescan_lock:
        files_scanned = 0
        sessions_added = 0
        all_topics = []  # (topic_name, confidence)

        existing_prompts = tracker.get_all_history_prompts(limit=1000)

        watcher.files.clear()
        for pattern in ["*.md", "*.txt"]:
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

                    topics = extract_topics_from_content(watched.content)
                    for topic in topics:
                        all_topics.append((topic, 0.6))

                    if watched.content[:100] not in existing_prompts:
                        title = extract_title_from_content(watched.content) or watched.topic or ', '.join(topics[:3]) or 'General'
                        tracker.save_history(
                            session_type=watched.file_type or 'session',
                            topic=title,
                            prompt=watched.content[:100],
                            response=watched.content,
                        )
                        sessions_added += 1
                except Exception as e:
                    logger.error(f"Error scanning {path}: {e}")

        topics_added = tracker.record_learning_batch(all_topics)

    return {"success": True, "files_scanned": files_scanned, "topics_recorded": topics_added, "sessions_added": sessions_added}


@router.get("/stats")
async def get_stats():
    """Get homestead session stats."""
    if not tracker:
        return {"session_count": 0}
    return {"session_count": tracker.get_session_count()}


@router.get("/gap-analysis")
async def get_gap_analysis():
    """Analyze homestead learning gaps against target knowledge areas."""
    if not tracker:
        return {"categories": [], "summary": {}}
    topic_rows = tracker.get_all_topics()
    return compute_gap_analysis(topic_rows, HOMESTEAD_GAP_TARGETS)
