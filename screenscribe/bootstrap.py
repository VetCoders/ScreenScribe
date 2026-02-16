"""Fast startup entrypoint for ScreenScribe CLI.

Shows immediate visual feedback before importing heavy CLI modules.
"""

from __future__ import annotations

import os
import sys
from importlib import metadata

_BOOTSTRAP_SHOWN_ENV = "SCREENSCRIBE_BOOTSTRAP_BANNER_SHOWN"
_DISABLE_BANNER_ENV = "SCREENSCRIBE_BOOTSTRAP_NO_BANNER"


def _is_completion_invocation() -> bool:
    """Detect shell completion bootstrap calls and stay silent."""
    return any(key.endswith("_COMPLETE") for key in os.environ)


def _should_render_banner(argv: list[str]) -> bool:
    """Render banner only in interactive terminal usage."""
    if os.environ.get(_BOOTSTRAP_SHOWN_ENV) == "1":
        return False
    if os.environ.get(_DISABLE_BANNER_ENV) == "1":
        return False
    if _is_completion_invocation():
        return False
    if not sys.stdout.isatty():
        return False
    if "--help" in argv or "-h" in argv:
        return False
    return True


def _resolve_version() -> str:
    """Read installed package version without importing screenscribe package."""
    try:
        return metadata.version("screenscribe")
    except metadata.PackageNotFoundError:
        return "dev"


def _render_banner(argv: list[str]) -> None:
    """Print immediate startup feedback after command submit."""
    version = _resolve_version()
    command = argv[0] if argv else "interactive"

    # Keep it plain/fast so it appears before heavy imports begin.
    print(
        "╭────────────────────────────────────────────────────╮\n"
        f"│ ScreenScribe v{version:<36}│\n"
        "│ Video review automation powered by LibraxisAI     │\n"
        f"│ Starting command: {command:<34}│\n"
        "╰────────────────────────────────────────────────────╯",
        flush=True,
    )


def main() -> None:
    """Entry point used by console script."""
    argv = sys.argv[1:]
    if _should_render_banner(argv):
        _render_banner(argv)
        os.environ[_BOOTSTRAP_SHOWN_ENV] = "1"

    from .cli import app

    app()
