"""Calendar plugin for SAPA."""

import json
import logging
from pathlib import Path

from fastapi import APIRouter

from ...plugin import SAPAPlugin, PluginManifest, ModuleType
from . import routes

logger = logging.getLogger(__name__)


def _config_path() -> Path:
    """Return the calendar plugin config path, honoring SAPA_CONFIG_DIR."""
    from ...config import get_config
    return get_config().config_dir / "plugins" / "calendar" / "config.json"


class CalendarPlugin(SAPAPlugin):
    """Calendar plugin - read-only Proton Calendar ICS feed."""

    def manifest(self) -> PluginManifest:
        return PluginManifest(
            id="calendar",
            name="Calendar",
            version="1.0.0",
            module_type=ModuleType.FAMILY,
            nav_items=[],
        )

    def get_router(self) -> APIRouter:
        return routes.router

    def get_css(self) -> str:
        return self._read_static("calendar.css")

    def get_nav_html(self) -> str:
        return self._read_static("nav.html")

    def get_panels_html(self) -> str:
        return self._read_static("panels.html")

    def get_modals_html(self) -> str:
        return ""

    def get_js(self) -> str:
        return self._read_static("calendar.js")

    async def on_startup(self, app, db_path):
        """Read ICS URL from config and wire into routes."""
        if _config_path().exists():
            try:
                with open(_config_path()) as f:
                    config = json.load(f)
                routes.ics_url = config.get("ics_url")
                if routes.ics_url:
                    logger.info("Calendar plugin: ICS URL loaded")
                else:
                    logger.warning("Calendar plugin: config exists but no ics_url set")
            except Exception as e:
                logger.error(f"Calendar plugin: failed to read config: {e}")
        else:
            logger.warning(f"Calendar plugin: no config at {_config_path()}")

    async def on_shutdown(self):
        pass
