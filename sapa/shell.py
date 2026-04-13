"""HTML shell template for SAPA.

The framework assembles the final page from plugin contributions.
Plugins provide CSS, panels, modals, JS, and nav items.
"""

from pathlib import Path

_STATIC_DIR = Path(__file__).parent / "static"


def _read_static(filename: str) -> str:
    """Read a static file from sapa/static/."""
    return (_STATIC_DIR / filename).read_text()


def build_page(
    plugin_css: str = "",
    plugin_nav_html: str = "",
    plugin_panels_html: str = "",
    plugin_modals_html: str = "",
    plugin_js: str = "",
    title: str = "SAPA - Set Apart",
    subtitle: str = "Family Dashboard",
) -> str:
    """Assemble the full HTML page from shell + plugin contributions.

    Uses str.replace() instead of .format() because plugin content
    contains raw { and } characters from CSS and JavaScript.
    """
    page = _read_static("shell.html")
    page = page.replace("$TITLE$", title)
    page = page.replace("$SUBTITLE$", subtitle)
    page = page.replace("$BASE_CSS$", _read_static("base.css"))
    page = page.replace("$GAP_CSS$", _read_static("gap.css"))
    page = page.replace("$PLUGIN_CSS$", plugin_css)
    page = page.replace("$PLUGIN_NAV$", plugin_nav_html)
    page = page.replace("$PLUGIN_PANELS$", plugin_panels_html)
    page = page.replace("$GAP_MODAL_HTML$", _read_static("gap-modal.html"))
    page = page.replace("$PLUGIN_MODALS$", plugin_modals_html)
    page = page.replace("$BASE_JS$", _read_static("base.js"))
    page = page.replace("$GAP_BASE_JS$", _read_static("gap-base.js"))
    page = page.replace("$PLUGIN_JS$", plugin_js)
    return page
