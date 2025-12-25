"""Semantic filtering pipeline for transcript analysis.

This module provides semantic pre-filtering capabilities that analyze
the entire transcript using LLM before frame extraction, allowing
the vision model to analyze more potential findings.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Literal

import httpx
from rich.console import Console

from .api_utils import retry_request
from .config import ScreenScribeConfig
from .transcribe import Segment, TranscriptionResult

console = Console()


class SemanticFilterLevel(str, Enum):
    """Semantic filtering levels for the pipeline.

    - KEYWORDS: Legacy keyword-based detection only (fastest, least findings)
    - BASE: LLM pre-filter on entire transcript before frame extraction
    - COMBINED: Keywords + semantic pre-filter (most comprehensive)
    """

    KEYWORDS = "keywords"  # Level 0: Original keyword-based approach
    BASE = "base"  # Level 1: Semantic pre-filter on full transcript
    COMBINED = "combined"  # Level 2: Keywords + semantic pre-filter


@dataclass
class PointOfInterest:
    """A point of interest identified by semantic pre-filtering.

    Represents a moment in the video that may contain a finding,
    identified by analyzing the transcript semantically before
    any frame extraction occurs.
    """

    timestamp_start: float
    timestamp_end: float
    category: Literal["bug", "change", "ui", "performance", "accessibility", "other"]
    confidence: float  # 0.0 - 1.0
    reasoning: str  # Why this was flagged
    transcript_excerpt: str  # The relevant text
    segment_ids: list[int] = field(default_factory=list)  # Source segment IDs

    @property
    def midpoint(self) -> float:
        """Get the midpoint timestamp for screenshot extraction."""
        return (self.timestamp_start + self.timestamp_end) / 2


# Prompts for semantic pre-filtering
SEMANTIC_PREFILTER_PROMPTS: dict[str, str] = {
    "pl": """Jesteś ekspertem UX/UI analizującym transkrypcję nagrania przeglądu aplikacji.

Przeanalizuj CAŁĄ poniższą transkrypcję i zidentyfikuj WSZYSTKIE momenty, w których użytkownik:
- Opisuje błąd, problem lub coś co nie działa
- Sugeruje zmianę lub ulepszenie
- Komentuje elementy UI/UX (przyciski, formularze, layout)
- Wspomina o problemach z wydajnością
- Porusza kwestie dostępności
- Opisuje cokolwiek co może wymagać uwagi developera

WAŻNE: Bądź LIBERALNY w identyfikacji - lepiej oznaczyć więcej momentów niż przegapić potencjalne problemy.
Model wizyjny później zweryfikuje każdy z nich analizując screenshot.

Transkrypcja z timestampami:
{transcript_with_timestamps}

Odpowiedz w formacie JSON:
{{
    "points_of_interest": [
        {{
            "timestamp_start": 12.5,
            "timestamp_end": 18.0,
            "category": "bug|change|ui|performance|accessibility|other",
            "confidence": 0.85,
            "reasoning": "Użytkownik mówi że przycisk nie reaguje na kliknięcie",
            "transcript_excerpt": "ten przycisk tutaj jakoś nie działa"
        }}
    ],
    "total_issues_found": 5,
    "analysis_notes": "Krótkie podsumowanie znalezionych obszarów"
}}

Odpowiadaj tylko JSON.""",
    "en": """You are a UX/UI expert analyzing a transcript from an application review recording.

Analyze the ENTIRE transcript below and identify ALL moments where the user:
- Describes a bug, problem, or something that doesn't work
- Suggests a change or improvement
- Comments on UI/UX elements (buttons, forms, layout)
- Mentions performance issues
- Raises accessibility concerns
- Describes anything that may require developer attention

IMPORTANT: Be LIBERAL in identification - it's better to flag more moments than to miss potential issues.
The vision model will later verify each one by analyzing the screenshot.

Transcript with timestamps:
{transcript_with_timestamps}

Respond in JSON format:
{{
    "points_of_interest": [
        {{
            "timestamp_start": 12.5,
            "timestamp_end": 18.0,
            "category": "bug|change|ui|performance|accessibility|other",
            "confidence": 0.85,
            "reasoning": "User says button doesn't respond to clicking",
            "transcript_excerpt": "this button here doesn't seem to work"
        }}
    ],
    "total_issues_found": 5,
    "analysis_notes": "Brief summary of identified areas"
}}

Respond only with JSON.""",
}


def get_semantic_prefilter_prompt(language: str = "pl") -> str:
    """Get the semantic pre-filter prompt for specified language."""
    lang = language.lower().strip()
    if lang in ("pl", "pl-pl", "polish", "polski"):
        return SEMANTIC_PREFILTER_PROMPTS["pl"]
    return SEMANTIC_PREFILTER_PROMPTS["en"]


def format_transcript_with_timestamps(transcription: TranscriptionResult) -> str:
    """Format transcript with timestamps for LLM analysis."""
    lines = []
    for segment in transcription.segments:
        timestamp = f"[{segment.start:.1f}s - {segment.end:.1f}s]"
        lines.append(f"{timestamp} {segment.text}")
    return "\n".join(lines)


def semantic_prefilter(
    transcription: TranscriptionResult,
    config: ScreenScribeConfig,
) -> list[PointOfInterest]:
    """
    Perform semantic pre-filtering on entire transcript.

    This analyzes the full transcript using LLM to identify points
    of interest BEFORE frame extraction, allowing more comprehensive
    analysis by the vision model.

    Args:
        transcription: Full transcription result with segments
        config: ScreenScribe configuration

    Returns:
        List of PointOfInterest objects for frame extraction
    """
    if not config.api_key:
        console.print("[yellow]No API key - skipping semantic pre-filter[/]")
        return []

    # Format transcript for analysis
    transcript_text = format_transcript_with_timestamps(transcription)

    # Get localized prompt
    prompt_template = get_semantic_prefilter_prompt(config.language)
    prompt = prompt_template.format(transcript_with_timestamps=transcript_text)

    console.print("[blue]Running semantic pre-filter on entire transcript...[/]")
    console.print(f"[dim]Analyzing {len(transcription.segments)} segments[/]")

    try:

        def do_prefilter_request() -> httpx.Response:
            with httpx.Client(timeout=120.0) as client:  # Longer timeout for full transcript
                response = client.post(
                    config.llm_endpoint,
                    headers={
                        "x-api-key": config.api_key,
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": config.llm_model,
                        "input": [
                            {"role": "user", "content": [{"type": "input_text", "text": prompt}]}
                        ],
                    },
                )
                response.raise_for_status()
                return response

        response = retry_request(
            do_prefilter_request,
            max_retries=3,
            operation_name="Semantic pre-filter",
        )

        # Parse response
        result = response.json()
        content = _extract_content_from_response(result)

        if not content:
            console.print("[yellow]Empty response from semantic pre-filter[/]")
            return []

        # Parse JSON from content
        pois = _parse_prefilter_response(content, transcription)

        console.print(
            f"[green]Semantic pre-filter complete:[/] "
            f"identified {len(pois)} points of interest"
        )

        # Summary by category
        categories = {}
        for poi in pois:
            categories[poi.category] = categories.get(poi.category, 0) + 1

        for cat, count in sorted(categories.items()):
            console.print(f"[dim]  • {cat}: {count}[/]")

        return pois

    except Exception as e:
        console.print(f"[yellow]Semantic pre-filter failed: {e}[/]")
        return []


def _extract_content_from_response(result: dict) -> str:
    """Extract text content from API response."""
    content = ""
    for item in result.get("output", []):
        item_type = item.get("type", "")
        if item_type == "reasoning":
            pass  # Skip reasoning blocks
        elif item_type == "message":
            for part in item.get("content", []):
                if part.get("type") in ("output_text", "text"):
                    content += part.get("text", "")
        elif item_type in ("output_text", "text"):
            content += item.get("text", "")
    return content


def _parse_prefilter_response(
    content: str, transcription: TranscriptionResult
) -> list[PointOfInterest]:
    """Parse the pre-filter response into PointOfInterest objects."""
    import json
    import re

    # Strip model control tokens
    content = re.sub(r"<\|[^|]+\|>\w*\s*", "", content)

    # Find JSON in content
    if not content.strip().startswith("{"):
        json_match = re.search(r"\{.*\}", content, re.DOTALL)
        if json_match:
            content = json_match.group(0)

    # Handle markdown code blocks
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0]
    elif "```" in content:
        parts = content.split("```")
        if len(parts) >= 2:
            content = parts[1]

    content = content.strip()

    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        console.print(f"[yellow]Failed to parse pre-filter response: {e}[/]")
        return []

    pois = []
    for item in data.get("points_of_interest", []):
        # Find matching segment IDs for this time range
        segment_ids = []
        for seg in transcription.segments:
            if seg.start >= item.get("timestamp_start", 0) - 1.0:
                if seg.end <= item.get("timestamp_end", 0) + 1.0:
                    segment_ids.append(seg.id)

        poi = PointOfInterest(
            timestamp_start=item.get("timestamp_start", 0.0),
            timestamp_end=item.get("timestamp_end", 0.0),
            category=item.get("category", "other"),
            confidence=item.get("confidence", 0.5),
            reasoning=item.get("reasoning", ""),
            transcript_excerpt=item.get("transcript_excerpt", ""),
            segment_ids=segment_ids,
        )
        pois.append(poi)

    return pois


def merge_pois_with_detections(
    pois: list[PointOfInterest],
    keyword_detections: list,  # list[Detection] - avoiding circular import
    max_gap: float = 3.0,
) -> list[PointOfInterest]:
    """
    Merge semantic POIs with keyword detections.

    Used in COMBINED mode to get the best of both approaches.

    Args:
        pois: Points of interest from semantic pre-filter
        keyword_detections: Detections from keyword matching
        max_gap: Maximum gap in seconds to consider overlapping

    Returns:
        Merged and deduplicated list of POIs
    """
    # Convert keyword detections to POIs
    for det in keyword_detections:
        # Check if there's already a POI covering this time range
        covered = False
        for poi in pois:
            if abs(poi.timestamp_start - det.segment.start) < max_gap:
                # Boost confidence for POIs that also have keyword matches
                poi.confidence = min(1.0, poi.confidence + 0.2)
                covered = True
                break

        if not covered:
            # Add as new POI from keyword detection
            new_poi = PointOfInterest(
                timestamp_start=det.segment.start,
                timestamp_end=det.segment.end,
                category=det.category,
                confidence=0.7,  # Keyword matches have decent confidence
                reasoning=f"Keyword detection: {', '.join(det.keywords_found)}",
                transcript_excerpt=det.segment.text[:100],
                segment_ids=[det.segment.id],
            )
            pois.append(new_poi)

    # Sort by timestamp
    pois.sort(key=lambda p: p.timestamp_start)

    # Merge overlapping POIs
    if not pois:
        return []

    merged = []
    current = pois[0]

    for poi in pois[1:]:
        if poi.timestamp_start <= current.timestamp_end + max_gap:
            # Merge: extend time range, keep higher confidence
            current = PointOfInterest(
                timestamp_start=current.timestamp_start,
                timestamp_end=max(current.timestamp_end, poi.timestamp_end),
                category=current.category if current.confidence >= poi.confidence else poi.category,
                confidence=max(current.confidence, poi.confidence),
                reasoning=f"{current.reasoning} | {poi.reasoning}",
                transcript_excerpt=f"{current.transcript_excerpt} ... {poi.transcript_excerpt}",
                segment_ids=list(set(current.segment_ids + poi.segment_ids)),
            )
        else:
            merged.append(current)
            current = poi

    merged.append(current)
    return merged


def poi_to_detection(poi: PointOfInterest, transcription: TranscriptionResult):
    """
    Convert a PointOfInterest to a Detection object for compatibility.

    This allows the semantic pre-filter to integrate with existing
    screenshot extraction and analysis pipeline.
    """
    from .detect import Detection
    from .transcribe import Segment

    # Build context from surrounding segments
    context_segments = []
    for seg in transcription.segments:
        if seg.start >= poi.timestamp_start - 5.0 and seg.end <= poi.timestamp_end + 5.0:
            context_segments.append(seg.text)
    context = " ".join(context_segments)

    # Create synthetic segment for the POI
    segment = Segment(
        id=poi.segment_ids[0] if poi.segment_ids else 0,
        start=poi.timestamp_start,
        end=poi.timestamp_end,
        text=poi.transcript_excerpt,
    )

    return Detection(
        segment=segment,
        category=poi.category if poi.category in ("bug", "change", "ui") else "ui",
        keywords_found=[f"semantic:{poi.category}"],
        context=context,
    )


def pois_to_detections(
    pois: list[PointOfInterest], transcription: TranscriptionResult
) -> list:
    """Convert list of POIs to Detection objects."""
    return [poi_to_detection(poi, transcription) for poi in pois]
