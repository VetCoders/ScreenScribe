"""Asset loader for HTML Pro template.

Loads CSS, JavaScript, and HTML template files from html_pro_assets directory.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

# Asset directory (sibling to this package)
ASSETS_DIR = Path(__file__).parent.parent / "html_pro_assets"


@lru_cache(maxsize=10)
def load_asset(filename: str) -> str:
    """Load an asset file from html_pro_assets directory.

    Args:
        filename: Relative path within html_pro_assets (e.g., "styles/quantum_vista.css")

    Returns:
        File contents as string

    Raises:
        FileNotFoundError: If asset file doesn't exist
    """
    asset_path = ASSETS_DIR / filename
    if not asset_path.exists():
        raise FileNotFoundError(f"Asset not found: {asset_path}")
    return asset_path.read_text(encoding="utf-8")


def load_css() -> str:
    """Load the Quantum Vista CSS stylesheet."""
    return load_asset("styles/quantum_vista.css")


def load_js_video_player() -> str:
    """Load the video player JavaScript."""
    return load_asset("scripts/video_player.js")


def load_js_review_app() -> str:
    """Load the review/annotation JavaScript application."""
    return load_asset("scripts/review_app.js")


def load_html_template() -> str:
    """Load the HTML report template."""
    return load_asset("templates/report.html")
