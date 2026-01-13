"""Data preparation for HTML Pro template.

Functions for preparing findings, segments, and other data for the template.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..transcribe import Segment


def generate_report_id(video_name: str, timestamp: str) -> str:
    """Generate a unique report ID based on video name and timestamp.

    Args:
        video_name: Name of the video file
        timestamp: Generation timestamp

    Returns:
        12-character hex hash
    """
    hash_input = f"{video_name}:{timestamp}"
    return hashlib.sha256(hash_input.encode()).hexdigest()[:12]


def prepare_findings_json(findings: list[dict[str, Any]]) -> str:
    """Prepare findings data as JSON for embedding in HTML.

    Args:
        findings: List of finding dictionaries

    Returns:
        JSON string (escaped for HTML embedding)
    """
    return json.dumps(findings, ensure_ascii=False, indent=2)


def prepare_segments_json(segments: list[Segment] | None) -> str:
    """Prepare transcript segments as JSON for the video player.

    Args:
        segments: List of transcript Segment objects (or None)

    Returns:
        JSON array of segment objects with start, end, text
    """
    if not segments:
        return "[]"

    segment_data = [
        {
            "start": seg.start,
            "end": seg.end,
            "text": seg.text,
        }
        for seg in segments
    ]
    return json.dumps(segment_data, ensure_ascii=False)


def format_timestamp(timestamp: datetime | None = None) -> str:
    """Format a timestamp for display.

    Args:
        timestamp: Datetime object (defaults to now)

    Returns:
        Formatted string like "2026-01-13 07:45"
    """
    if timestamp is None:
        timestamp = datetime.now()
    return timestamp.strftime("%Y-%m-%d %H:%M")
