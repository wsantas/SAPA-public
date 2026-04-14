"""Health Bot plugin for SAPA."""

import json
from pathlib import Path

from fastapi import APIRouter

from ...plugin import SAPAPlugin, PluginManifest, ModuleType, NavItem
from .gap_prompts import HEALTH_GAP_PROMPTS, HEALTH_DEFAULT_PROMPT
from .gap_targets import PROFILE_GAP_TARGETS
from .tracker import HealthTracker
from ...gaps import generate_gap_js
from . import routes


class HealthPlugin(SAPAPlugin):
    """Health Bot plugin - elite health performance tracker."""

    def __init__(self):
        self.tracker: HealthTracker | None = None

    def manifest(self) -> PluginManifest:
        return PluginManifest(
            id="health",
            name="Health Bot",
            version="1.0.0",
            module_type=ModuleType.PROFILE,
            nav_items=[],
        )

    def get_router(self) -> APIRouter:
        return routes.router

    def get_css(self) -> str:
        return self._read_static("health.css")

    def get_nav_html(self) -> str:
        return self._read_static("nav.html")

    def get_panels_html(self) -> str:
        return self._read_static("panels.html")

    def get_modals_html(self) -> str:
        return self._read_static("modals.html")

    def get_js(self) -> str:
        gap_js = generate_gap_js(
            plugin_id="Health",
            summary_el="gapsSummary",
            top_gaps_el="topGaps",
            categories_el="gapsCategories",
            prompts=HEALTH_GAP_PROMPTS,
            default_prompt=HEALTH_DEFAULT_PROMPT,
        )
        # Build per-profile topic→category reverse lookup for review prompts
        topic_categories = {}
        for pid, targets in PROFILE_GAP_TARGETS.items():
            profile_map = {}
            for cat_name, cat_data in targets.items():
                for topic in cat_data["topics"]:
                    profile_map[topic.lower()] = cat_name
            topic_categories[pid] = profile_map
        topic_cat_js = f"\n        const healthTopicCategories = {json.dumps(topic_categories)};\n"
        # health-recipes.js is loaded first so recipe state (allRecipes,
        # recipeCookLog, recipeFavorites) is in scope before the meal planner
        # and dashboard code in health.js references it.
        return (
            self._read_static("health-recipes.js")
            + self._read_static("health.js")
            + gap_js
            + topic_cat_js
        )

    def get_migrations_dir(self) -> Path | None:
        return Path(__file__).parent / "migrations"

    async def on_startup(self, app, db_path):
        """Initialize tracker and wire into routes."""
        self.tracker = HealthTracker(db_path)
        # Wire tracker and watcher into routes module
        routes.tracker = self.tracker

        self.tracker.seed_default_protocols()
        self.tracker.seed_default_reminders()

        # Watcher will be set separately after it's created
        from ...app import get_watcher
        routes.watcher = get_watcher()

    async def on_shutdown(self):
        if self.tracker:
            self.tracker.close()
            self.tracker = None

    def get_profile_tabs(self) -> dict[int, list[str]]:
        generic_tabs = ['bodymap', 'topics', 'training', 'recovery', 'nutrition', 'recipes', 'mealplanner', 'progress']
        return {
            1: generic_tabs,
            2: generic_tabs,
        }
