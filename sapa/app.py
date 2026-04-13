"""SAPA - Set Apart Personal Assistant.

FastAPI app factory with plugin loading and lifecycle management.
"""

import asyncio
import json
import logging
import shutil
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

import uvicorn
from fastapi import FastAPI, WebSocket, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response

from .config import get_config
from .db import get_db_path, get_connection, init_framework_tables, run_plugin_migrations, ensure_default_profiles
from .plugin import SAPAPlugin
from .search import search_content
from .profiles import ProfileManager
from .shell import build_page
from .watcher import FolderWatcher, WatchedFile
from .websocket import websocket_endpoint as ws_endpoint, broadcast
from .email import notify_new_session

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============== Plugin Registry ==============

from .plugins.health.plugin import HealthPlugin
from .plugins.homestead.plugin import HomesteadPlugin
from .plugins.calendar.plugin import CalendarPlugin

PLUGINS: list[SAPAPlugin] = [
    HealthPlugin(),
    HomesteadPlugin(),
    CalendarPlugin(),
]


# ============== Global State ==============

watcher: FolderWatcher | None = None
homestead_watcher: FolderWatcher | None = None
profile_mgr: ProfileManager | None = None
_cached_html: str | None = None


def get_watcher() -> FolderWatcher | None:
    return watcher


def get_homestead_watcher() -> FolderWatcher | None:
    return homestead_watcher


def get_profile_manager() -> ProfileManager | None:
    return profile_mgr


# ============== Page Assembly ==============

def assemble_page() -> str:
    """Assemble the full HTML page from all plugins. Called once at startup."""
    all_css = []
    all_nav = []
    all_panels = []
    all_modals = []
    all_js = []
    all_profile_tabs: dict[int, list[str]] = {}

    for plugin in PLUGINS:
        css = plugin.get_css()
        if css:
            all_css.append(css)

        manifest = plugin.manifest()
        # Nav items are provided as raw HTML by the plugin for now
        nav_html = getattr(plugin, 'get_nav_html', lambda: '')()
        if nav_html:
            all_nav.append(nav_html)

        panels = plugin.get_panels_html()
        if panels:
            all_panels.append(panels)

        modals = plugin.get_modals_html()
        if modals:
            all_modals.append(modals)

        js = plugin.get_js()
        if js:
            all_js.append(js)

        tabs = plugin.get_profile_tabs()
        for pid, tab_list in tabs.items():
            if pid not in all_profile_tabs:
                all_profile_tabs[pid] = []
            all_profile_tabs[pid].extend(tab_list)

    # Inject profile tabs JSON into base JS
    profile_tabs_json = json.dumps(all_profile_tabs)

    # Build the page with all plugin contributions
    page = build_page(
        plugin_css="\n".join(all_css),
        plugin_nav_html="\n".join(all_nav),
        plugin_panels_html="\n".join(all_panels),
        plugin_modals_html="\n".join(all_modals),
        plugin_js="\n".join(all_js),
        title="Set Apart",
        subtitle="Personal Assistant",
    )

    # Replace the profile tabs placeholder
    page = page.replace("$PROFILE_TABS_JSON$", profile_tabs_json)

    return page


# ============== Backup ==============

def create_backup():
    """Create a daily backup of the database."""
    backup_dir = Path.home() / "Documents" / "sapa-backups"
    backup_dir.mkdir(parents=True, exist_ok=True)

    db_path = get_db_path()
    if not db_path.exists():
        return None

    date_str = datetime.now().strftime("%Y-%m-%d")
    backup_path = backup_dir / f"learning-{date_str}.db"

    if not backup_path.exists():
        shutil.copy2(db_path, backup_path)
        logger.info(f"Backup created: {backup_path}")

        backups = sorted(backup_dir.glob("learning-*.db"), reverse=True)
        for old_backup in backups[30:]:
            old_backup.unlink()
            logger.info(f"Removed old backup: {old_backup}")

        return backup_path
    return None


# ============== Lifespan ==============

@asynccontextmanager
async def lifespan(app: FastAPI):
    global watcher, homestead_watcher, profile_mgr, _cached_html

    config = get_config()
    config.ensure_directories()

    # Create daily backup
    create_backup()

    # Initialize database
    db_path = get_db_path()
    conn = get_connection(db_path)
    init_framework_tables(conn)
    ensure_default_profiles(conn)

    # Run plugin migrations
    for plugin in PLUGINS:
        manifest = plugin.manifest()
        migrations_dir = plugin.get_migrations_dir()
        if migrations_dir:
            count = run_plugin_migrations(conn, manifest.id, migrations_dir)
            if count:
                logger.info(f"Applied {count} migrations for plugin '{manifest.id}'")

    # Initialize profile manager
    profile_mgr = ProfileManager(conn)

    # Initialize watcher
    watcher = FolderWatcher()

    # Create profile subdirectories in inbox
    inbox_map = {'john': 'john', 'jane': 'jane'}
    for subdir in inbox_map:
        (watcher.watch_path / subdir).mkdir(exist_ok=True)

    # Seed demo content into any empty inbox subdir
    import shutil
    demo_inbox_root = Path(__file__).parent / "plugins" / "health" / "demo_inbox"
    if demo_inbox_root.exists():
        for subdir in inbox_map:
            live_dir = watcher.watch_path / subdir
            seed_dir = demo_inbox_root / subdir
            if not seed_dir.exists():
                continue
            for seed_file in seed_dir.glob("*.md"):
                target = live_dir / seed_file.name
                if not target.exists():
                    shutil.copy2(seed_file, target)
                    logger.info(f"Seeded demo file: {target}")

    # Start plugins
    for plugin in PLUGINS:
        await plugin.on_startup(app, db_path)

    # Assemble and cache the HTML page
    _cached_html = assemble_page()

    # Set up watcher event handlers
    from .plugins.health.routes import process_new_file, INBOX_PROFILE_MAP
    from .plugins.health.content import extract_title_from_content

    loop = asyncio.get_running_loop()

    # Build a thread-safe profile ID lookup (no DB access needed)
    _path_profile_cache: dict[str, int] = {}
    for subdir_name, profile_name in inbox_map.items():
        p = profile_mgr.get_profile_by_name(profile_name)
        if p:
            _path_profile_cache[subdir_name] = p['id']

    def _get_profile_id_for_path_threadsafe(file_path: Path) -> int | None:
        """Resolve profile ID from path using cached dict (no DB)."""
        try:
            rel = file_path.relative_to(watcher.watch_path)
            if len(rel.parts) > 1:
                subdir = rel.parts[0].lower()
                return _path_profile_cache.get(subdir)
        except ValueError:
            pass
        return None

    # Path-based dedup to prevent double-processing from rapid watchdog events
    _processing_paths: set[str] = set()

    from .plugins.health.content import extract_topics_from_content as health_extract_topics

    async def _on_file_created_async(watched):
        path_str = str(watched.path)
        if path_str in _processing_paths:
            return
        _processing_paths.add(path_str)
        try:
            # Brief delay to let file finish writing (watchdog fires on create before content is flushed)
            await asyncio.sleep(0.3)
            # Always re-read to get final content (initial read may be empty or partial)
            if watched.path.exists():
                watched = WatchedFile.from_path(watched.path)
            profile_id = _get_profile_id_for_path_threadsafe(watched.path)
            await process_new_file(watched, profile_id=profile_id)
            await broadcast("file_created", watched.to_dict())

            # Email notification (run in thread to avoid blocking)
            title = extract_title_from_content(watched.content) or watched.topic or 'General'
            topics = health_extract_topics(watched.content)
            pid = profile_id or (profile_mgr._current_profile_id if profile_mgr else 1)
            p = profile_mgr.get_profile(pid) if profile_mgr else None
            pname = p['display_name'] if p else 'Unknown'
            await asyncio.to_thread(
                notify_new_session, title, watched.file_type or 'session',
                topics, pname, 'health', profile_id=pid,
            )
        finally:
            # Keep path guarded for 5 seconds to block duplicate events
            loop.call_later(5, _processing_paths.discard, path_str)

    def on_file_created(watched):
        loop.call_soon_threadsafe(asyncio.ensure_future, _on_file_created_async(watched))

    async def _on_file_modified_async(watched):
        from .plugins.health import routes as health_routes
        t = health_routes.tracker
        if not t:
            return
        profile_id = _get_profile_id_for_path_threadsafe(watched.path)
        from contextlib import nullcontext
        ctx = t.profile_context(profile_id) if profile_id else nullcontext()
        with ctx:
            title = extract_title_from_content(watched.content) or watched.topic or 'General'
            t.update_history_by_topic(title, watched.content, watched.content[:500])
        await broadcast("file_modified", watched.to_dict())

    def on_file_modified(watched):
        loop.call_soon_threadsafe(asyncio.ensure_future, _on_file_modified_async(watched))

    def on_file_deleted(path: str):
        loop.call_soon_threadsafe(asyncio.ensure_future, broadcast("file_deleted", {"path": path}))

    watcher.on("created", on_file_created)
    watcher.on("modified", on_file_modified)
    watcher.on("deleted", on_file_deleted)

    # Scan existing files BEFORE starting observer to avoid race
    watcher.scan_existing()

    # Process existing files that haven't been tracked yet
    from .plugins.health import routes as health_routes
    ht = health_routes.tracker
    if ht:
        from contextlib import nullcontext
        from .plugins.health.content import extract_topics_from_content as extract_topics

        # Build set of (title, profile_id) already in history for robust dedup
        existing_entries = set()
        for row in ht.conn.execute("SELECT topic, profile_id FROM history").fetchall():
            existing_entries.add((row['topic'], row['profile_id']))

        for watched_file in watcher.get_files():
            profile_id = _get_profile_id_for_path_threadsafe(watched_file.path)
            pid = profile_id or ht.get_current_profile_id()
            title = extract_title_from_content(watched_file.content) or watched_file.topic or 'General'
            if (title, pid) in existing_entries:
                continue
            ctx = ht.profile_context(profile_id) if profile_id else nullcontext()
            with ctx:
                topics = extract_topics(watched_file.content)
                for topic in topics:
                    ht.record_learning(topic, confidence=0.6)
                if not title or title == 'General':
                    title = ', '.join(topics[:3]) or 'General'
                ht.save_history(
                    session_type=watched_file.file_type or 'session',
                    topic=title,
                    prompt=watched_file.content[:500],
                    response=watched_file.content,
                )
                existing_entries.add((title, pid))
                target = f"profile {profile_id}" if profile_id else "current profile"
                logger.info(f"Processed: {watched_file.name} -> {target} ({len(topics)} topics)")

    # Start health watcher AFTER processing existing files (prevents race)
    watcher.start()

    # ============== Homestead Watcher ==============

    homestead_watcher = FolderWatcher(watch_path=config.homestead_inbox_path)

    from .plugins.homestead import routes as homestead_routes
    from .plugins.homestead.content import extract_title_from_content as hs_extract_title
    homestead_routes.watcher = homestead_watcher

    from .plugins.homestead.content import extract_topics_from_content as hs_extract_topics_email

    async def _on_hs_file_created_async(watched):
        await asyncio.sleep(0.3)
        if not watched.content.strip() and watched.path.exists():
            watched = WatchedFile.from_path(watched.path)
        await homestead_routes.process_new_file(watched)

        # Email notification
        title = hs_extract_title(watched.content) or watched.topic or 'General'
        topics = hs_extract_topics_email(watched.content)
        await asyncio.to_thread(
            notify_new_session, title, watched.file_type or 'session',
            topics, 'Family', 'homestead',
        )

    def on_hs_file_created(watched):
        loop.call_soon_threadsafe(asyncio.ensure_future, _on_hs_file_created_async(watched))

    async def _on_hs_file_modified_async(watched):
        hs_tracker = homestead_routes.tracker
        if not hs_tracker:
            return
        title = hs_extract_title(watched.content) or watched.topic or 'General'
        hs_tracker.update_history_by_topic(title, watched.content, watched.content[:500])
        await broadcast("homestead_file_modified", watched.to_dict())

    def on_hs_file_modified(watched):
        loop.call_soon_threadsafe(asyncio.ensure_future, _on_hs_file_modified_async(watched))

    def on_hs_file_deleted(path: str):
        loop.call_soon_threadsafe(asyncio.ensure_future, broadcast("homestead_file_deleted", {"path": path}))

    homestead_watcher.on("created", on_hs_file_created)
    homestead_watcher.on("modified", on_hs_file_modified)
    homestead_watcher.on("deleted", on_hs_file_deleted)

    homestead_watcher.scan_existing()

    # Process existing homestead files not yet in history
    from .plugins.homestead.content import extract_topics_from_content as hs_extract_topics
    hs_tracker = homestead_routes.tracker
    if hs_tracker:
        existing_hs = hs_tracker.get_all_history_prompts(limit=1000)
        for watched_file in homestead_watcher.get_files():
            if watched_file.content[:100] in existing_hs:
                continue
            topics = hs_extract_topics(watched_file.content)
            for topic in topics:
                hs_tracker.record_learning(topic, confidence=0.6)
            title = hs_extract_title(watched_file.content) or watched_file.topic or ', '.join(topics[:3]) or 'General'
            hs_tracker.save_history(
                session_type=watched_file.file_type or 'session',
                topic=title,
                prompt=watched_file.content[:100],
                response=watched_file.content,
            )
            logger.info(f"Homestead processed: {watched_file.name} -> {title} ({len(topics)} topics)")

    # Start homestead watcher AFTER processing existing files (prevents race)
    homestead_watcher.start()

    logger.info(f"SAPA started. Watching: {watcher.watch_path}")
    logger.info(f"Homestead watching: {homestead_watcher.watch_path}")

    yield

    # Shutdown plugins
    for plugin in PLUGINS:
        await plugin.on_shutdown()

    watcher.stop()
    homestead_watcher.stop()
    conn.close()
    logger.info("SAPA stopped")


# ============== App ==============

app = FastAPI(title="SAPA - Set Apart Personal Assistant", lifespan=lifespan)


@app.middleware("http")
async def profile_from_cookie(request: Request, call_next):
    """Set the active profile from cookie."""
    if profile_mgr:
        cookie_val = request.cookies.get("profile_id")
        if cookie_val and cookie_val.isdigit():
            pid = int(cookie_val)
            if profile_mgr.get_profile(pid):
                profile_mgr._current_profile_id = pid
                # Also update plugin trackers
                for plugin in PLUGINS:
                    tracker = getattr(plugin, 'tracker', None)
                    if tracker and hasattr(tracker, '_current_profile_id'):
                        tracker._current_profile_id = pid
    return await call_next(request)


# Mount plugin routers
for plugin in PLUGINS:
    router = plugin.get_router()
    if router:
        manifest = plugin.manifest()
        # Health plugin mounts at root (no prefix) for backward compat
        if manifest.id == "health":
            app.include_router(router)
        else:
            app.include_router(router, prefix=f"/api/{manifest.id}")


@app.websocket("/ws")
async def ws_route(websocket: WebSocket):
    await ws_endpoint(websocket, watcher=watcher)


@app.post("/api/email/test")
async def email_test():
    """Send a test email to verify SMTP configuration."""
    from .email import send_notification, _load_email_config, reload_config
    reload_config()
    cfg = _load_email_config()
    if not cfg:
        return JSONResponse({"ok": False, "error": "No email config in ~/.sapa/config.json"}, status_code=400)
    # Send test to all configured recipients
    all_addrs = set()
    for addr in cfg.get("recipients", {}).values():
        all_addrs.add(addr)
    for addr in cfg.get("homestead_recipients", []):
        all_addrs.add(addr)
    if not all_addrs:
        return JSONResponse({"ok": False, "error": "No recipients configured"}, status_code=400)
    results = {}
    for addr in all_addrs:
        ok = await asyncio.to_thread(
            send_notification, "[SAPA] Test Email", "This is a test notification from SAPA.", addr,
        )
        results[addr] = "sent" if ok else "failed"
    return {"ok": all(v == "sent" for v in results.values()), "results": results}


@app.post("/api/email/reload")
async def email_reload():
    """Reload email configuration from disk."""
    from .email import reload_config
    reload_config()
    return {"ok": True}


@app.get("/api/search")
async def api_search(q: str = "", limit: int = 50):
    """Full-text search across all content."""
    if len(q) < 2:
        return []
    pid = profile_mgr._current_profile_id if profile_mgr else 1
    return search_content(get_db_path(), q, profile_id=pid, limit=limit)


@app.get("/api/family-feed")
async def family_feed(limit: int = 30):
    """Unified activity feed across all profiles."""
    import sqlite3
    db_path = get_db_path()
    conn = sqlite3.connect(db_path, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    results = []
    try:
        # Health history across all profiles
        cursor = conn.execute("""
            SELECT h.id, h.topic, h.session_type, h.created_at,
                   p.id as profile_id, p.display_name as profile_name
            FROM history h
            JOIN profiles p ON h.profile_id = p.id
            ORDER BY h.created_at DESC
            LIMIT ?
        """, (limit,))
        for row in cursor.fetchall():
            results.append({
                "id": row["id"],
                "topic": row["topic"],
                "session_type": row["session_type"],
                "created_at": row["created_at"],
                "profile_id": row["profile_id"],
                "profile_name": row["profile_name"],
                "category": "health",
            })

        # Homestead history (family)
        cursor = conn.execute("""
            SELECT id, topic, session_type, created_at
            FROM homestead_history
            ORDER BY created_at DESC
            LIMIT ?
        """, (limit,))
        for row in cursor.fetchall():
            results.append({
                "id": row["id"],
                "topic": row["topic"],
                "session_type": row["session_type"],
                "created_at": row["created_at"],
                "profile_id": 0,
                "profile_name": "Family",
                "category": "homestead",
            })

        results.sort(key=lambda r: r["created_at"] or "", reverse=True)
        return results[:limit]
    finally:
        conn.close()


@app.get("/manifest.json")
async def manifest():
    """PWA manifest."""
    return JSONResponse({
        "name": "Set Apart Personal Assistant",
        "short_name": "SAPA",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#1a1f2e",
        "theme_color": "#10b981",
        "icons": [
            {"src": "/icon-192.svg", "sizes": "192x192", "type": "image/svg+xml"},
            {"src": "/icon-512.svg", "sizes": "512x512", "type": "image/svg+xml"},
        ],
    })


@app.get("/sw.js")
async def service_worker():
    """Serve service worker from root scope."""
    _sw_path = Path(__file__).parent / "static" / "sw.js"
    return Response(content=_sw_path.read_text(), media_type="application/javascript")


@app.get("/icon-192.svg")
async def icon_192():
    _icon_path = Path(__file__).parent / "static" / "icon-192.svg"
    return Response(content=_icon_path.read_text(), media_type="image/svg+xml")


@app.get("/icon-512.svg")
async def icon_512():
    _icon_path = Path(__file__).parent / "static" / "icon-512.svg"
    return Response(content=_icon_path.read_text(), media_type="image/svg+xml")


@app.get("/", response_class=HTMLResponse)
async def index():
    return _cached_html


# ============== Main ==============

def main():
    import argparse

    parser = argparse.ArgumentParser(description="SAPA - Set Apart Personal Assistant")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")

    args = parser.parse_args()

    config = get_config()
    config.ensure_directories()

    inbox = config.inbox_path
    inbox.mkdir(parents=True, exist_ok=True)
    hs_inbox = config.homestead_inbox_path
    hs_inbox.mkdir(parents=True, exist_ok=True)

    print()
    print("  SAPA - Set Apart Personal Assistant")
    print("  =======================================")
    print()
    print(f"  URL: http://localhost:{args.port}")
    print(f"  Health inbox:     {inbox}")
    print(f"  Homestead inbox:  {hs_inbox}")
    print()

    uvicorn.run(
        "sapa.app:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
