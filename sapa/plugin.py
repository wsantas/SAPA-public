"""Plugin system for SAPA."""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from fastapi import APIRouter


class ModuleType(Enum):
    PROFILE = "profile"  # Per-person data (filtered by profile_id)
    FAMILY = "family"    # Shared across all profiles


@dataclass
class NavItem:
    """A navigation tab/button for the plugin."""
    id: str
    label: str
    icon: str  # Emoji or short text


@dataclass
class PluginManifest:
    """Metadata about a plugin."""
    id: str
    name: str
    version: str
    module_type: ModuleType
    nav_items: list[NavItem] = field(default_factory=list)


class SAPAPlugin:
    """Base class for SAPA plugins."""

    def _read_static(self, filename: str) -> str:
        """Read a file from this plugin's static/ directory."""
        static_dir = Path(__file__).parent / "plugins" / self.manifest().id / "static"
        return (static_dir / filename).read_text()

    def manifest(self) -> PluginManifest:
        """Return plugin metadata."""
        raise NotImplementedError

    def get_router(self) -> APIRouter | None:
        """Return FastAPI router with plugin routes."""
        return None

    def get_css(self) -> str:
        """Return plugin-specific CSS."""
        return ""

    def get_panels_html(self) -> str:
        """Return panel <div>s for the dashboard."""
        return ""

    def get_modals_html(self) -> str:
        """Return modal <div>s."""
        return ""

    def get_js(self) -> str:
        """Return plugin-specific JavaScript."""
        return ""

    def get_migrations_dir(self) -> Path | None:
        """Return path to SQL migration files directory."""
        return None

    async def on_startup(self, app, db_path):
        """Called during app startup."""
        pass

    async def on_shutdown(self):
        """Called during app shutdown."""
        pass

    def get_profile_tabs(self) -> dict[int, list[str]]:
        """Return tab visibility per profile. {profile_id: [tab_id, ...]}."""
        return {}
