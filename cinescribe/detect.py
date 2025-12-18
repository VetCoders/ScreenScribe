"""Bug and change detection from transcripts."""

import re
from dataclasses import dataclass

from rich.console import Console

from .transcribe import Segment, TranscriptionResult

console = Console()


# Keywords indicating bugs, issues, or requested changes (PL + EN)
BUG_KEYWORDS = [
    # Polish
    r"nie działa",
    r"nie dziala",
    r"bug",
    r"błąd",
    r"blad",
    r"problem",
    r"zepsute",
    r"nie widać",
    r"nie widac",
    r"brakuje",
    r"złe",
    r"zle",
    r"straszne",
    r"tragedia",
    r"koszmar",
    r"potworek",
    r"bez sensu",
    r"nie podoba",
    # English
    r"broken",
    r"doesn't work",
    r"not working",
    r"issue",
    r"error",
    r"wrong",
    r"missing",
    r"bad",
]

CHANGE_KEYWORDS = [
    # Polish
    r"trzeba",
    r"powinno",
    r"powinien",
    r"powinniśmy",
    r"powinnismy",
    r"musimy",
    r"zmienić",
    r"zmienic",
    r"poprawić",
    r"poprawic",
    r"wyrzucić",
    r"wyrzucic",
    r"usunąć",
    r"usunac",
    r"dodać",
    r"dodac",
    r"przenieść",
    r"przeniesc",
    r"przeprojektować",
    r"przeprojektowac",
    r"zrobić",
    r"zrobic",
    r"ogarnąć",
    r"ogarnac",
    r"spłaszczyć",
    r"splaszczyc",
    r"wywalamy",
    r"wypierdala",
    # English
    r"should",
    r"must",
    r"need to",
    r"have to",
    r"fix",
    r"change",
    r"remove",
    r"add",
    r"move",
    r"redesign",
]

UI_KEYWORDS = [
    r"layout",
    r"ui",
    r"ux",
    r"button",
    r"przycisk",
    r"okno",
    r"modal",
    r"ekran",
    r"screen",
    r"animacj",
    r"scroll",
    r"glass",
    r"blur",
    r"vibrancy",
    r"border",
    r"rama",
    r"warstwa",
    r"layer",
]


@dataclass
class Detection:
    """A detected issue or change request."""
    segment: Segment
    category: str  # "bug", "change", "ui"
    keywords_found: list[str]
    context: str  # Extended context from surrounding segments


def detect_issues(
    transcription: TranscriptionResult,
    context_window: int = 2
) -> list[Detection]:
    """
    Detect bugs and change requests in transcription.

    Args:
        transcription: The transcription result
        context_window: Number of segments before/after to include as context

    Returns:
        List of detections with category and context
    """
    detections = []
    segments = transcription.segments

    console.print("[blue]Analyzing transcript for issues...[/]")

    for i, segment in enumerate(segments):
        text_lower = segment.text.lower()
        found_keywords = []
        category = None

        # Check for bugs
        for pattern in BUG_KEYWORDS:
            if re.search(pattern, text_lower):
                found_keywords.append(pattern)
                category = "bug"

        # Check for change requests
        for pattern in CHANGE_KEYWORDS:
            if re.search(pattern, text_lower):
                found_keywords.append(pattern)
                if category is None:
                    category = "change"

        # Check for UI-related
        for pattern in UI_KEYWORDS:
            if re.search(pattern, text_lower):
                found_keywords.append(pattern)
                if category is None:
                    category = "ui"

        if category and found_keywords:
            # Build context from surrounding segments
            start_idx = max(0, i - context_window)
            end_idx = min(len(segments), i + context_window + 1)
            context_segments = segments[start_idx:end_idx]
            context = " ".join(s.text for s in context_segments)

            detections.append(Detection(
                segment=segment,
                category=category,
                keywords_found=list(set(found_keywords)),
                context=context
            ))

    # Merge consecutive detections
    merged = merge_consecutive_detections(detections)

    console.print(
        f"[green]Found {len(merged)} issues:[/] "
        f"{sum(1 for d in merged if d.category == 'bug')} bugs, "
        f"{sum(1 for d in merged if d.category == 'change')} changes, "
        f"{sum(1 for d in merged if d.category == 'ui')} UI issues"
    )

    return merged


def merge_consecutive_detections(
    detections: list[Detection],
    max_gap: float = 5.0
) -> list[Detection]:
    """
    Merge consecutive detections that are close in time.

    Args:
        detections: List of detections
        max_gap: Maximum gap in seconds to merge

    Returns:
        Merged list of detections
    """
    if not detections:
        return []

    merged = []
    current = detections[0]

    for detection in detections[1:]:
        gap = detection.segment.start - current.segment.end

        if gap <= max_gap and detection.category == current.category:
            # Merge: extend end time, combine keywords and context
            current = Detection(
                segment=Segment(
                    id=current.segment.id,
                    start=current.segment.start,
                    end=detection.segment.end,
                    text=f"{current.segment.text} {detection.segment.text}"
                ),
                category=current.category,
                keywords_found=list(set(
                    current.keywords_found + detection.keywords_found
                )),
                context=f"{current.context} ... {detection.context}"
            )
        else:
            merged.append(current)
            current = detection

    merged.append(current)
    return merged


def format_timestamp(seconds: float) -> str:
    """Format seconds as MM:SS."""
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes:02d}:{secs:02d}"
