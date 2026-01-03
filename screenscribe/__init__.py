"""
ScreenScribe - Video review automation for screencast commentary analysis.

Extract bugs, changes, and action items from video walkthroughs.
Made with (งಠ_ಠ)ง by ⌜ScreenScribe⌟ © 2025 — Maciej & Monika + Klaudiusz (AI) + Mikserka (AI)
"""

__version__ = "0.1.3"

# Export key modules for external use
from .html_template_pro import render_html_report_pro
from .vtt_generator import (
    SubtitleEntry,
    format_display_timestamp,
    generate_vtt_data_url,
    generate_webvtt,
    generate_webvtt_with_cue_settings,
    seconds_to_vtt_timestamp,
    segments_to_subtitle_entries,
)

__all__ = [
    "SubtitleEntry",
    "__version__",
    "format_display_timestamp",
    "generate_vtt_data_url",
    "generate_webvtt",
    "generate_webvtt_with_cue_settings",
    "render_html_report_pro",
    "seconds_to_vtt_timestamp",
    "segments_to_subtitle_entries",
]
