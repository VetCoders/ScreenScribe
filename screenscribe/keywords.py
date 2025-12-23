"""Keyword configuration loading and management."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import ClassVar

import yaml
from rich.console import Console

console = Console()

# Path to embedded default keywords
DEFAULT_KEYWORDS_PATH = Path(__file__).parent / "default_keywords.yaml"


@dataclass
class KeywordsConfig:
    """Keywords configuration for issue detection."""

    bug: list[str] = field(default_factory=list)
    change: list[str] = field(default_factory=list)
    ui: list[str] = field(default_factory=list)

    # Search paths for keywords file (in order of priority)
    SEARCH_PATHS: ClassVar[list[str]] = [
        "keywords.yaml",
        "screenscribe_keywords.yaml",
        ".screenscribe/keywords.yaml",
    ]

    @classmethod
    def load(cls, keywords_file: Path | None = None) -> "KeywordsConfig":
        """
        Load keywords configuration.

        Priority:
        1. Explicit keywords_file parameter
        2. keywords.yaml in current directory
        3. Embedded defaults

        Args:
            keywords_file: Optional explicit path to keywords file

        Returns:
            KeywordsConfig with loaded keywords
        """
        # 1. Explicit file
        if keywords_file:
            if keywords_file.exists():
                return cls._load_from_file(keywords_file)
            console.print(f"[yellow]Keywords file not found: {keywords_file}[/]")
            console.print("[dim]Falling back to defaults[/]")

        # 2. Search in common locations
        for search_path in cls.SEARCH_PATHS:
            path = Path.cwd() / search_path
            if path.exists():
                console.print(f"[dim]Using keywords from: {path}[/]")
                return cls._load_from_file(path)

        # 3. Embedded defaults
        return cls._load_from_file(DEFAULT_KEYWORDS_PATH)

    @classmethod
    def _load_from_file(cls, path: Path) -> "KeywordsConfig":
        """Load keywords from YAML file."""
        try:
            with open(path, encoding="utf-8") as f:
                data = yaml.safe_load(f)

            if not isinstance(data, dict):
                console.print(f"[yellow]Invalid keywords file format: {path}[/]")
                return cls._load_defaults()

            return cls(
                bug=data.get("bug", []),
                change=data.get("change", []),
                ui=data.get("ui", []),
            )

        except yaml.YAMLError as e:
            console.print(f"[yellow]Error parsing keywords file: {e}[/]")
            return cls._load_defaults()
        except OSError as e:
            console.print(f"[yellow]Error reading keywords file: {e}[/]")
            return cls._load_defaults()

    @classmethod
    def _load_defaults(cls) -> "KeywordsConfig":
        """Load embedded default keywords."""
        return cls._load_from_file(DEFAULT_KEYWORDS_PATH)

    def get_keywords(self, category: str) -> list[str]:
        """Get keywords for a specific category."""
        if category == "bug":
            return self.bug
        elif category == "change":
            return self.change
        elif category == "ui":
            return self.ui
        return []

    @property
    def total_keywords(self) -> int:
        """Total number of keywords across all categories."""
        return len(self.bug) + len(self.change) + len(self.ui)

    def summary(self) -> str:
        """Return a summary of loaded keywords."""
        return f"Keywords: {len(self.bug)} bug, {len(self.change)} change, {len(self.ui)} UI"


def save_default_keywords(path: Path) -> None:
    """
    Save default keywords to a file for user customization.

    Args:
        path: Path to save keywords file
    """
    import shutil

    shutil.copy(DEFAULT_KEYWORDS_PATH, path)
    console.print(f"[green]Default keywords saved to: {path}[/]")
