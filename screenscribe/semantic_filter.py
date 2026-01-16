"""Semantic filtering pipeline for transcript analysis.

This module provides semantic pre-filtering capabilities that analyze
the entire transcript using LLM before frame extraction, allowing
the vision model to analyze more potential findings.
"""

import json
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Literal

import httpx
from rich.console import Console
from rich.live import Live
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn

from .api_utils import build_llm_request_body
from .config import ScreenScribeConfig
from .text_similarity import _text_similarity
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


@dataclass
class SemanticFilterResult:
    """Result of semantic pre-filtering with response_id for conversation chaining.

    The response_id enables context chaining to VLM analysis - the vision model
    will understand thematic context from the transcript analysis (e.g., knowing
    the user discussed "UI bugs" helps VLM better interpret screenshots).
    """

    pois: list[PointOfInterest]
    response_id: str = ""  # API response ID for conversation chaining to VLM


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
    previous_response_id: str = "",
) -> SemanticFilterResult:
    """
    Perform semantic pre-filtering on entire transcript.

    This analyzes the full transcript using LLM to identify points
    of interest BEFORE frame extraction, allowing more comprehensive
    analysis by the vision model.

    Args:
        transcription: Full transcription result with segments
        config: ScreenScribe configuration
        previous_response_id: Response ID from STT for conversation chaining

    Returns:
        SemanticFilterResult with POIs and response_id for VLM context chaining
    """
    if not config.get_llm_api_key():
        console.print("[yellow]No API key - skipping semantic pre-filter[/]")
        return SemanticFilterResult(pois=[], response_id="")

    # Format transcript for analysis
    transcript_text = format_transcript_with_timestamps(transcription)

    # Get localized prompt
    prompt_template = get_semantic_prefilter_prompt(config.language)
    prompt = prompt_template.format(transcript_with_timestamps=transcript_text)

    console.print("[blue]Running semantic pre-filter on entire transcript...[/]")

    if config.verbose:
        console.print(f"[dim]  Endpoint: {config.llm_endpoint}[/]")
        console.print(f"[dim]  Model: {config.llm_model}[/]")
        console.print(f"[dim]  Segments: {len(transcription.segments)}[/]")
        console.print(f"[dim]  Transcript length: {len(transcript_text)} chars[/]")

    try:
        # Build request with streaming enabled
        request_body = build_llm_request_body(config.llm_model, prompt, config.llm_endpoint)
        request_body["stream"] = True
        # Enable reasoning summaries in stream (for thinking models)
        request_body["reasoning"] = {"summary": "auto"}
        # Chain from STT response for thematic context
        if previous_response_id:
            request_body["previous_response_id"] = previous_response_id
            console.print(f"[dim]  Chaining from STT: {previous_response_id[:20]}...[/]")

        content = ""
        stream_preview = ""  # Last ~40 chars of output for live display
        reasoning_text = ""
        poi_count = 0
        response_id = ""  # Capture for conversation chaining to VLM

        # Create progress display with spinner + status + live stream
        progress = Progress(
            SpinnerColumn(),
            TextColumn("[cyan]{task.description}"),
            BarColumn(bar_width=15),
            TextColumn("[dim]{task.fields[stream]}[/]"),
            transient=True,
        )

        with Live(progress, console=console, refresh_per_second=15):
            task_id = progress.add_task(
                f"Analyzing {len(transcription.segments)} segments",
                total=100,
                stream="...",
            )

            with httpx.Client(timeout=120.0) as client:
                with client.stream(
                    "POST",
                    config.llm_endpoint,
                    headers={
                        "Authorization": f"Bearer {config.get_llm_api_key()}",
                        "Content-Type": "application/json",
                        "Accept": "text/event-stream",
                    },
                    json=request_body,
                ) as response:
                    response.raise_for_status()

                    line_count = 0
                    for line in response.iter_lines():
                        line_count += 1
                        if not line:
                            continue

                        # Verbose SSE logging - outside Live context
                        # (disabled to not interfere with progress display)

                        # Handle SSE format: "event: xxx" or "data: xxx"
                        if line.startswith("event:"):
                            continue  # Skip event lines, we parse data

                        if line.startswith("data:"):
                            data = line[5:].strip()  # Strip "data:" prefix
                            if data == "[DONE]":
                                progress.update(task_id, completed=100, stream="done")
                                break

                            try:
                                chunk = json.loads(data)
                                chunk_type = chunk.get("type", "")

                                # Capture response_id for conversation chaining
                                if chunk_type in ("response.created", "response.completed"):
                                    chunk_id = chunk.get("response", {}).get("id", "")
                                    if not chunk_id:
                                        chunk_id = chunk.get("id", "")
                                    if chunk_id:
                                        response_id = chunk_id

                                # Show reasoning summaries in real-time
                                if chunk_type == "response.reasoning_summary_text.delta":
                                    # Streaming reasoning summary delta
                                    delta = chunk.get("delta", "")
                                    if delta:
                                        reasoning_text = (reasoning_text + delta)[-60:]
                                        progress.update(task_id, stream=reasoning_text)
                                elif chunk_type == "response.reasoning_summary_text.done":
                                    # Full reasoning summary completed
                                    full_text = chunk.get("text", "")
                                    if full_text:
                                        reasoning_text = full_text[-60:]
                                        progress.update(task_id, stream=reasoning_text)

                                # Extract delta text from streaming response
                                delta_text = _extract_stream_delta(chunk, verbose=False)
                                if delta_text:
                                    content += delta_text
                                    # Update stream preview with last chars
                                    stream_preview = (stream_preview + delta_text)[-40:]
                                    # Clean for display (remove newlines, JSON noise)
                                    display_text = stream_preview.replace("\n", " ").replace(
                                        '"', ""
                                    )

                                    # Count POIs found so far
                                    new_poi_count = content.count('"timestamp_start"')
                                    if new_poi_count != poi_count:
                                        poi_count = new_poi_count
                                        progress.update(
                                            task_id,
                                            description=f"Found {poi_count} POI",
                                            completed=min(poi_count * 5, 95),
                                            stream=f"...{display_text}",
                                        )
                                    else:
                                        # Just update stream preview
                                        progress.update(task_id, stream=f"...{display_text}")

                            except json.JSONDecodeError:
                                continue

        if not content:
            console.print("[yellow]Empty response from semantic pre-filter[/]")
            return SemanticFilterResult(pois=[], response_id=response_id)

        # Parse JSON from content
        pois = _parse_prefilter_response(content, transcription)

        console.print(
            f"[green]Semantic pre-filter complete:[/] identified {len(pois)} points of interest"
        )
        if response_id:
            console.print(f"[dim]  Response ID for VLM chaining: {response_id[:20]}...[/]")

        # Summary by category
        categories: dict[str, int] = {}
        for poi in pois:
            categories[poi.category] = categories.get(poi.category, 0) + 1

        for cat, count in sorted(categories.items()):
            console.print(f"[dim]  • {cat}: {count}[/]")

        return SemanticFilterResult(pois=pois, response_id=response_id)

    except Exception as e:
        console.print(f"[yellow]Semantic pre-filter failed: {e}[/]")
        return SemanticFilterResult(pois=[], response_id="")


def _extract_stream_delta(chunk: dict[str, Any], verbose: bool = False) -> str:
    """Extract text delta from SSE streaming chunk.

    Supports Responses API streaming formats from OpenAI/LibraxisAI.
    """
    chunk_type = chunk.get("type", "")

    if verbose and chunk_type:
        console.print(f"[dim]  chunk type: {chunk_type}[/]")

    # Responses API: response.output_text.delta
    if chunk_type == "response.output_text.delta":
        return str(chunk.get("delta", ""))

    # Responses API: response.content_part.delta (alternative format)
    if chunk_type == "response.content_part.delta":
        delta = chunk.get("delta", {})
        if isinstance(delta, dict):
            return str(delta.get("text", ""))
        return str(delta) if delta else ""

    # Responses API: content.delta
    if chunk_type == "content.delta":
        delta = chunk.get("delta", {})
        if isinstance(delta, dict):
            return str(delta.get("text", ""))
        return str(delta) if delta else ""

    # Responses API: response.text.delta (yet another variant)
    if chunk_type == "response.text.delta":
        return str(chunk.get("delta", "") or chunk.get("text", ""))

    # Chat Completions API streaming format (legacy fallback)
    choices = chunk.get("choices", [])
    if choices:
        delta = choices[0].get("delta", {})
        return str(delta.get("content", ""))

    return ""


def _extract_content_from_response(result: dict[str, Any]) -> str:
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


def _poi_similarity_text(poi: PointOfInterest) -> str:
    """Extract text for similarity comparison from a POI."""
    parts = []
    if poi.transcript_excerpt:
        parts.append(poi.transcript_excerpt)
    if poi.reasoning:
        parts.append(poi.reasoning)
    return " ".join(parts)


def deduplicate_pois(
    pois: list[PointOfInterest],
    similarity_threshold: float = 0.45,
) -> list[PointOfInterest]:
    """Deduplicate similar POIs by transcript excerpt and reasoning.

    Groups POIs with similarity above threshold, then merges each group
    into a single POI with combined time range and best confidence.

    Args:
        pois: List of PointOfInterest objects
        similarity_threshold: Minimum similarity (0-1) to consider as duplicate

    Returns:
        Deduplicated list of PointOfInterest objects
    """
    if not pois or len(pois) <= 1:
        return pois

    groups: list[list[PointOfInterest]] = []
    used: set[int] = set()

    for i, poi in enumerate(pois):
        if i in used:
            continue

        group = [poi]
        used.add(i)
        poi_text = _poi_similarity_text(poi)

        for j, other in enumerate(pois):
            if j in used:
                continue

            similarity = _text_similarity(poi_text, _poi_similarity_text(other))
            if similarity >= similarity_threshold:
                group.append(other)
                used.add(j)

        groups.append(group)

    result: list[PointOfInterest] = []

    for group in groups:
        if len(group) == 1:
            result.append(group[0])
            continue

        group.sort(key=lambda p: p.timestamp_start)
        best = max(group, key=lambda p: p.confidence)

        excerpts = [p.transcript_excerpt.strip() for p in group if p.transcript_excerpt.strip()]
        reasoning_parts = []
        seen_reasoning: set[str] = set()
        for p in group:
            if not p.reasoning:
                continue
            key = p.reasoning.strip().lower()
            if key in seen_reasoning:
                continue
            seen_reasoning.add(key)
            reasoning_parts.append(p.reasoning.strip())

        merged = PointOfInterest(
            timestamp_start=min(p.timestamp_start for p in group),
            timestamp_end=max(p.timestamp_end for p in group),
            category=best.category,
            confidence=max(p.confidence for p in group),
            reasoning=" | ".join(reasoning_parts) if reasoning_parts else group[0].reasoning,
            transcript_excerpt=max(excerpts, key=len) if excerpts else group[0].transcript_excerpt,
            segment_ids=sorted({sid for p in group for sid in p.segment_ids}),
        )
        result.append(merged)

    return result


def merge_pois_with_detections(
    pois: list[PointOfInterest],
    keyword_detections: list[Any],  # list[Detection] - avoiding circular import
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


def poi_to_detection(poi: PointOfInterest, transcription: TranscriptionResult) -> Any:
    """
    Convert a PointOfInterest to a Detection object for compatibility.

    This allows the semantic pre-filter to integrate with existing
    screenshot extraction and analysis pipeline.

    Returns:
        Detection object (typed as object to avoid circular import)
    """
    from .detect import Detection

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
) -> list[Any]:
    """Convert list of POIs to Detection objects."""
    return [poi_to_detection(poi, transcription) for poi in pois]
