# CLAUDE.md

Guidance for Claude Code (claude.ai/code) when working in this repository.

## Project Overview

SAPA (Set Apart Personal Assistant) — plugin-based family dashboard built on FastAPI. Single-page app served from one assembled HTML page with per-plugin CSS/JS/panels injected at startup. SQLite persistence, watchdog-based inbox processing, WebSocket push for real-time updates.

## Development

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .
PYTHONPATH=. .venv/bin/python -m sapa.app --port 8001
```

Default config directory is `~/.sapa-public/`. Override with `SAPA_CONFIG_DIR`.

## Feeding Content

Drop `.md` files into inbox directories. The file watcher processes them: extracts topics, records history, broadcasts a WebSocket event.

- **Health:** `~/.sapa-public/plugins/health/inbox/{john,jane}/`
- **Homestead:** `~/.sapa-public/plugins/homestead/inbox/`

Files must be markdown with the title as the first H1 heading. Topics are matched against the extraction term list in `content.py` (case-insensitive).

Demo seed files live in `sapa/plugins/health/demo_inbox/` and are copied into any empty inbox subdir on startup.

## Architecture

### Startup (`sapa/app.py`)
Init config → init DB → run plugin migrations → create profile manager → create file watchers → call plugin `on_startup()` → assemble HTML page → wire watcher callbacks → scan existing inbox files. The assembled HTML is cached in `_cached_html` and served on every `GET /`.

### Plugin System (`sapa/plugin.py`)
Plugins extend `SAPAPlugin` and provide: router, CSS, JS, panels HTML, modals HTML, nav HTML, migrations dir, profile tabs, and startup/shutdown hooks. Registered in the `PLUGINS` list in `app.py`.

**Module types:**
- `PROFILE` — data scoped per person (queries filter by `profile_id`). Example: `health`.
- `FAMILY` — data shared across all profiles. Example: `homestead`, `calendar`.

### Key framework modules
- `profiles.py` — cookie-based profile switching with context manager for temporary switches during file processing
- `watcher.py` — watchdog observer for inbox directories; parses YAML frontmatter; profile subdirectories auto-route to the correct profile
- `websocket.py` — broadcast system for real-time updates
- `db.py` — SQLite with per-plugin migration tracking in `sapa_migrations`
- `gaps.py` — shared gap analysis module used by health and homestead

### Adding a plugin
1. Create `sapa/plugins/{name}/` with `plugin.py`, `routes.py`, `tracker.py`
2. Create `sapa/plugins/{name}/static/` with `{name}.css`, `{name}.js`, `panels.html`, optionally `nav.html` / `modals.html`
3. Plugin class extends `SAPAPlugin`, uses `self._read_static()` to load assets
4. Add SQL migrations in a `migrations/` subdirectory
5. Register in `PLUGINS` in `app.py`

## JS Architecture

All JS runs in a single `<script>` tag: `base.js` first, then each plugin's JS. Later function declarations override earlier ones. No modules, no build step, shared scope. Template placeholders use `$PLACEHOLDER$` syntax (not `{placeholder}`) because CSS/JS braces would collide.

## Gap Analysis Flow

1. File processed → `extract_topics_from_content()` matches terms from the hardcoded list in `content.py`
2. Each term recorded via `tracker.record_learning(topic)` into the `topics` table
3. `/api/gap-analysis` compares learned topics against targets in `gap_targets.py`
4. The extraction term list in `content.py` MUST contain every term referenced by `gap_targets.py`, or those gaps never close
5. After editing extraction terms or gap targets: restart and rescan to reprocess existing files

## Watchdog Gotchas

- `on_created` fires before content is flushed — the callback has a 300ms delay + re-read
- Callbacks run on a separate thread — use `loop.call_soon_threadsafe()` to bridge to the event loop
- Atomic-rename writes (e.g. from editors) arrive as `moved`, not `created` — if new files don't auto-process, hit `/api/rescan`
- Three events fire per file (`file_processed` + `file_created` + `file_modified`) — the shell debounces with a 500ms `_debouncedRefresh()`
