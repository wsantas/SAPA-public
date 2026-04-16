"""File watcher for markdown files."""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent

from .config import get_config

logger = logging.getLogger(__name__)


def parse_frontmatter(content: str) -> tuple[dict, str]:
    """Parse YAML frontmatter from markdown content."""
    import re
    metadata = {}
    body = content

    match = re.match(r'^---\s*\n(.*?)\n---\s*\n(.*)$', content, re.DOTALL)
    if match:
        frontmatter = match.group(1)
        body = match.group(2).strip()

        for line in frontmatter.split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                metadata[key.strip().lower()] = value.strip()

    return metadata, body


@dataclass
class WatchedFile:
    """Represents a watched markdown file."""

    path: Path
    name: str
    content: str
    size: int
    modified_at: datetime
    created_at: datetime
    status: str = "pending"
    processed_at: Optional[datetime] = None
    result: Optional[str] = None
    error: Optional[str] = None
    file_type: str = "question"
    topic: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "path": str(self.path),
            "name": self.name,
            "content": self.content,
            "size": self.size,
            "modified_at": self.modified_at.isoformat(),
            "created_at": self.created_at.isoformat(),
            "status": self.status,
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
            "result": self.result,
            "error": self.error,
            "type": self.file_type,
            "topic": self.topic,
        }

    @classmethod
    def from_path(cls, path: Path) -> "WatchedFile":
        stat = path.stat()
        raw_content = path.read_text(errors="replace")

        metadata, body = parse_frontmatter(raw_content)

        response_path = path.with_suffix(".response.md")
        result = None
        status = "pending"
        if response_path.exists():
            result = response_path.read_text(errors="replace")
            status = "processed"

        file_type = metadata.get("type")
        if not file_type:
            name_lower = path.stem.lower()
            if "cheatsheet" in name_lower or "cheat_sheet" in name_lower:
                file_type = "cheatsheet"
            elif "analysis" in name_lower:
                file_type = "analysis"
            elif "protocol" in name_lower:
                file_type = "protocol"
            elif "guide" in name_lower:
                file_type = "guide"
            elif "routine" in name_lower or "workout" in name_lower:
                file_type = "routine"
            elif "notes" in name_lower:
                file_type = "notes"
            else:
                file_type = "session"

        return cls(
            path=path,
            name=path.name,
            content=body if body else raw_content,
            size=stat.st_size,
            modified_at=datetime.fromtimestamp(stat.st_mtime),
            created_at=datetime.fromtimestamp(stat.st_ctime),
            file_type=file_type,
            topic=metadata.get("topic") or None,
            result=result,
            status=status,
        )


class MarkdownHandler(FileSystemEventHandler):

    def __init__(
        self,
        created_callback: Optional[Callable[[WatchedFile], None]] = None,
        modified_callback: Optional[Callable[[WatchedFile], None]] = None,
        deleted_callback: Optional[Callable[[str], None]] = None,
    ):
        super().__init__()
        self._created_callback = created_callback
        self._modified_callback = modified_callback
        self._deleted_callback = deleted_callback
        self._processing: set[str] = set()

    def _is_markdown(self, path: str) -> bool:
        return path.endswith((".md", ".markdown", ".txt"))

    def on_created(self, event: FileSystemEvent) -> None:
        if event.is_directory or not self._is_markdown(event.src_path):
            return
        path = Path(event.src_path)
        if path.name.startswith(".") or 'archive' in path.parts:
            return
        try:
            watched = WatchedFile.from_path(path)
            logger.info(f"New file detected: {path.name}")
            if self._created_callback:
                self._created_callback(watched)
        except Exception as e:
            logger.error(f"Error reading new file {path}: {e}")

    def on_modified(self, event: FileSystemEvent) -> None:
        if event.is_directory or not self._is_markdown(event.src_path):
            return
        path = Path(event.src_path)
        if path.name.startswith(".") or 'archive' in path.parts:
            return
        if event.src_path in self._processing:
            return
        self._processing.add(event.src_path)
        try:
            watched = WatchedFile.from_path(path)
            logger.info(f"File modified: {path.name}")
            if self._modified_callback:
                self._modified_callback(watched)
        except Exception as e:
            logger.error(f"Error reading modified file {path}: {e}")
        finally:
            self._processing.discard(event.src_path)

    def on_moved(self, event: FileSystemEvent) -> None:
        dest = getattr(event, 'dest_path', None)
        if not dest or event.is_directory or not self._is_markdown(dest):
            return
        path = Path(dest)
        if path.name.startswith(".") or 'archive' in path.parts:
            return
        try:
            watched = WatchedFile.from_path(path)
            logger.info(f"File moved/renamed (treating as new): {path.name}")
            if self._created_callback:
                self._created_callback(watched)
        except Exception as e:
            logger.error(f"Error reading moved file {path}: {e}")

    def on_deleted(self, event: FileSystemEvent) -> None:
        if event.is_directory or not self._is_markdown(event.src_path):
            return
        path = Path(event.src_path)
        if path.name.startswith(".") or 'archive' in path.parts:
            return
        logger.info(f"File deleted: {path.name}")
        if self._deleted_callback:
            self._deleted_callback(str(path))


class FolderWatcher:

    def __init__(self, watch_path: Optional[Path] = None):
        config = get_config()
        config.ensure_directories()

        self.watch_path = watch_path or config.inbox_path
        self.watch_path.mkdir(parents=True, exist_ok=True)

        self.files: dict[str, WatchedFile] = {}
        self.observer: Optional[Observer] = None
        self._callbacks: dict[str, list[Callable]] = {
            "created": [],
            "modified": [],
            "deleted": [],
            "processed": [],
        }

    def on(self, event: str, callback: Callable) -> None:
        if event in self._callbacks:
            self._callbacks[event].append(callback)

    def _emit(self, event: str, data) -> None:
        for callback in self._callbacks.get(event, []):
            try:
                callback(data)
            except Exception as e:
                logger.error(f"Error in callback for {event}: {e}")

    def _on_created(self, watched: WatchedFile) -> None:
        self.files[str(watched.path)] = watched
        self._emit("created", watched)

    def _on_modified(self, watched: WatchedFile) -> None:
        existing = self.files.get(str(watched.path))
        if existing:
            watched.status = existing.status
            watched.result = existing.result
        self.files[str(watched.path)] = watched
        self._emit("modified", watched)

    def _on_deleted(self, path: str) -> None:
        self.files.pop(path, None)
        self._emit("deleted", path)

    def scan_existing(self) -> list[WatchedFile]:
        found = []
        for pattern in ["*.md", "*.txt", "*/*.md", "*/*.txt"]:
            for path in self.watch_path.glob(pattern):
                if path.name.startswith("."):
                    continue
                try:
                    rel = path.relative_to(self.watch_path)
                    if 'archive' in rel.parts:
                        continue
                except ValueError:
                    continue
                try:
                    watched = WatchedFile.from_path(path)
                    self.files[str(path)] = watched
                    found.append(watched)
                except Exception as e:
                    logger.error(f"Error scanning {path}: {e}")

        logger.info(f"Scanned {len(found)} existing files in {self.watch_path}")
        return found

    def start(self) -> None:
        if self.observer:
            return
        handler = MarkdownHandler(
            created_callback=self._on_created,
            modified_callback=self._on_modified,
            deleted_callback=self._on_deleted,
        )
        self.observer = Observer()
        self.observer.schedule(handler, str(self.watch_path), recursive=True)
        self.observer.start()
        logger.info(f"Started watching: {self.watch_path}")

    def stop(self) -> None:
        if self.observer:
            self.observer.stop()
            self.observer.join()
            self.observer = None
            logger.info("Stopped watching")

    def get_files(self) -> list[WatchedFile]:
        return list(self.files.values())

    def get_file(self, path: str) -> Optional[WatchedFile]:
        return self.files.get(path)

    def update_file_status(self, path: str, status: str, result: Optional[str] = None, error: Optional[str] = None) -> Optional[WatchedFile]:
        watched = self.files.get(path)
        if watched:
            watched.status = status
            watched.result = result
            watched.error = error
            if status == "processed":
                watched.processed_at = datetime.now()
            self._emit("processed", watched)
        return watched

    def delete_file(self, path: str) -> bool:
        watched = self.files.get(path)
        if watched and watched.path.exists():
            watched.path.unlink()
            self.files.pop(path, None)
            return True
        return False

    def archive_file(self, path: str) -> Optional[Path]:
        watched = self.files.get(path)
        if not watched or not watched.path.exists():
            return None
        archive_dir = self.watch_path / "archive"
        archive_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_path = archive_dir / f"{timestamp}_{watched.name}"
        watched.path.rename(archive_path)
        self.files.pop(path, None)
        return archive_path
