"""Hermes plugin — local AI assistant for SAPA."""

from pathlib import Path

from fastapi import APIRouter

from ...plugin import SAPAPlugin, PluginManifest, ModuleType
from .tracker import HermesTracker
from . import routes


class HermesPlugin(SAPAPlugin):
    """Hermes plugin — family-shared local AI chat."""

    def __init__(self):
        self.tracker: HermesTracker | None = None

    def manifest(self) -> PluginManifest:
        return PluginManifest(
            id="hermes",
            name="Hermes",
            version="0.1.0",
            module_type=ModuleType.FAMILY,
            nav_items=[],
        )

    def get_router(self) -> APIRouter:
        return routes.router

    def get_css(self) -> str:
        return self._read_static("hermes.css")

    def get_nav_html(self) -> str:
        return self._read_static("nav.html")

    def get_panels_html(self) -> str:
        return self._read_static("panels.html")

    def get_modals_html(self) -> str:
        return ""

    def get_js(self) -> str:
        return self._read_static("hermes.js")

    def get_migrations_dir(self) -> Path | None:
        return Path(__file__).parent / "migrations"

    async def on_startup(self, app, db_path):
        self.tracker = HermesTracker(db_path)
        routes.tracker = self.tracker

        from ...hermes import hermes
        try:
            online = await hermes.health_check()
            if online:
                print(f"[hermes] backend={hermes.name} model={hermes.model} online")
            else:
                print(f"[hermes] backend={hermes.name} NOT responding — chat will return errors")
        except Exception as e:
            print(f"[hermes] health check failed: {e}")

    async def on_shutdown(self):
        from ...hermes import hermes
        await hermes.close()
        if self.tracker:
            self.tracker.close()
            self.tracker = None
