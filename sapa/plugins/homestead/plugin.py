"""Homestead plugin for SAPA."""

from pathlib import Path

from fastapi import APIRouter

from ...plugin import SAPAPlugin, PluginManifest, ModuleType
from .gap_prompts import HOMESTEAD_GAP_PROMPTS, HOMESTEAD_DEFAULT_PROMPT
from .tracker import HomesteadTracker
from ...gaps import generate_gap_js
from . import routes


class HomesteadPlugin(SAPAPlugin):
    """Homestead plugin - family-shared homestead session tracker."""

    def __init__(self):
        self.tracker: HomesteadTracker | None = None

    def manifest(self) -> PluginManifest:
        return PluginManifest(
            id="homestead",
            name="Homestead",
            version="1.0.0",
            module_type=ModuleType.FAMILY,
            nav_items=[],
        )

    def get_router(self) -> APIRouter:
        return routes.router

    def get_css(self) -> str:
        return self._read_static("homestead.css")

    def get_nav_html(self) -> str:
        return ""

    def get_panels_html(self) -> str:
        return self._read_static("panels.html")

    def get_modals_html(self) -> str:
        return ""

    def get_js(self) -> str:
        gap_js = generate_gap_js(
            plugin_id="Homestead",
            summary_el="hsGapsSummary",
            top_gaps_el="hsTopGaps",
            categories_el="hsGapsCategories",
            prompts=HOMESTEAD_GAP_PROMPTS,
            default_prompt=HOMESTEAD_DEFAULT_PROMPT,
        )
        return self._read_static("homestead.js") + gap_js

    def get_migrations_dir(self) -> Path | None:
        return Path(__file__).parent / "migrations"

    async def on_startup(self, app, db_path):
        """Initialize tracker and wire into routes."""
        self.tracker = HomesteadTracker(db_path)
        routes.tracker = self.tracker

    async def on_shutdown(self):
        if self.tracker:
            self.tracker.close()
            self.tracker = None

    def get_profile_tabs(self) -> dict[int, list[str]]:
        return {}
