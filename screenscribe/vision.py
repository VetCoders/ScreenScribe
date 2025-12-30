"""Vision analysis using LibraxisAI Vision models."""

from __future__ import annotations

import base64
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import httpx
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from .api_utils import retry_request
from .config import ScreenScribeConfig
from .detect import Detection
from .prompts import get_vision_analysis_prompt

if TYPE_CHECKING:
    from .semantic import SemanticAnalysis

console = Console()


@dataclass
class VisionAnalysis:
    """Result of vision analysis on a screenshot."""

    screenshot_path: Path
    timestamp: float
    ui_elements: list[str]
    issues_detected: list[str]
    accessibility_notes: list[str]
    design_feedback: str
    technical_observations: str


def encode_image_base64(image_path: Path) -> str:
    """Encode image to base64 for API."""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def analyze_screenshot(
    screenshot_path: Path,
    detection: Detection,
    config: ScreenScribeConfig,
    previous_response_id: str | None = None,
) -> VisionAnalysis | None:
    """
    Analyze a screenshot using Vision model.

    Uses conversation chaining via previous_response_id to leverage
    context from semantic analysis, avoiding duplicate work.

    Args:
        screenshot_path: Path to screenshot
        detection: Associated detection for context
        config: ScreenScribe configuration
        previous_response_id: Response ID from semantic analysis for context chaining

    Returns:
        VisionAnalysis result or None if failed
    """
    if not config.get_vision_api_key():
        return None

    if not screenshot_path.exists():
        console.print(f"[yellow]Screenshot not found: {screenshot_path}[/]")
        return None

    # Encode image
    image_base64 = encode_image_base64(screenshot_path)

    # Determine image type
    suffix = screenshot_path.suffix.lower()
    media_type = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }.get(suffix, "image/jpeg")

    # Get localized prompt template
    prompt_template = get_vision_analysis_prompt(config.language)

    # Use shorter prompt when chaining (model already has context)
    if previous_response_id:
        prompt = (
            "Przeanalizuj ten screenshot w kontekście mojej poprzedniej analizy. "
            "Zidentyfikuj dodatkowe problemy wizualne widoczne na obrazie."
            if config.language.lower().startswith("pl")
            else "Analyze this screenshot in context of my previous analysis. "
            "Identify additional visual issues visible in the image."
        )
    else:
        prompt = prompt_template.format(transcript_context=detection.segment.text[:200])

    try:

        def do_vision_request() -> httpx.Response:
            with httpx.Client(timeout=120.0) as client:
                # Build request payload
                payload: dict[str, object] = {
                    "model": config.vision_model,
                    "input": [
                        {
                            "role": "user",
                            "content": [
                                {"type": "input_text", "text": prompt},
                                {
                                    "type": "input_image",
                                    "image_url": f"data:{media_type};base64,{image_base64}",
                                    "detail": "high",
                                },
                            ],
                        }
                    ],
                }

                # Add conversation chaining if we have semantic analysis context
                if previous_response_id:
                    payload["previous_response_id"] = previous_response_id

                response = client.post(
                    config.vision_endpoint,
                    headers={
                        "Authorization": f"Bearer {config.get_vision_api_key()}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
                response.raise_for_status()
                return response

        response = retry_request(
            do_vision_request,
            max_retries=3,
            operation_name=f"Vision analysis ({screenshot_path.name})",
        )

        result = response.json()
        # v1/responses format - handle both reasoning and message outputs
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

        # Parse JSON from response
        import json

        # Handle potential markdown code blocks
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        data = json.loads(content.strip())

        return VisionAnalysis(
            screenshot_path=screenshot_path,
            timestamp=detection.segment.start,
            ui_elements=data.get("ui_elements", []),
            issues_detected=data.get("issues_detected", []),
            accessibility_notes=data.get("accessibility_notes", []),
            design_feedback=data.get("design_feedback", ""),
            technical_observations=data.get("technical_observations", ""),
        )

    except Exception as e:
        console.print(f"[yellow]Vision analysis failed for {screenshot_path.name}: {e}[/]")
        return None


def analyze_screenshots(
    screenshots: list[tuple[Detection, Path]],
    config: ScreenScribeConfig,
    semantic_analyses: list[SemanticAnalysis] | None = None,
) -> list[VisionAnalysis]:
    """
    Analyze all screenshots using Vision model.

    Uses conversation chaining to leverage semantic analysis context,
    and skips non-issues to save API calls.

    Args:
        screenshots: List of (detection, screenshot_path) tuples
        config: ScreenScribe configuration
        semantic_analyses: Optional list of SemanticAnalysis for chaining and filtering

    Returns:
        List of vision analyses
    """
    if not config.use_vision_analysis:
        console.print("[dim]Vision analysis disabled[/]")
        return []

    if not config.get_vision_api_key():
        console.print("[yellow]No Vision API key - skipping vision analysis[/]")
        return []

    # Build lookup for semantic analyses
    semantic_by_id: dict[int, SemanticAnalysis] = {}
    if semantic_analyses:
        semantic_by_id = {a.detection_id: a for a in semantic_analyses}

    # Filter out non-issues (optimization: skip vision for confirmed OK items)
    filtered_screenshots = []
    skipped_count = 0
    for detection, screenshot_path in screenshots:
        sem = semantic_by_id.get(detection.segment.id)
        if sem and not sem.is_issue:
            skipped_count += 1
            continue
        filtered_screenshots.append((detection, screenshot_path))

    if skipped_count > 0:
        console.print(f"[dim]Skipping {skipped_count} non-issues (is_issue=False)[/]")

    results = []
    console.print(f"[blue]Running vision analysis on {len(filtered_screenshots)} screenshots...[/]")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Analyzing screenshots...", total=len(filtered_screenshots))

        for i, (detection, screenshot_path) in enumerate(filtered_screenshots, 1):
            console.print(f"[dim]  [{i}/{len(filtered_screenshots)}] {screenshot_path.name}...[/]")

            # Get response_id from semantic analysis for chaining
            sem = semantic_by_id.get(detection.segment.id)
            previous_response_id = None
            if sem and sem.response_id:
                previous_response_id = sem.response_id

            analysis = analyze_screenshot(
                screenshot_path, detection, config, previous_response_id=previous_response_id
            )
            if analysis:
                results.append(analysis)
                chained = " [chained]" if previous_response_id else ""
                console.print(f"[green]  ✓[/] {screenshot_path.name}{chained}")
            else:
                console.print(f"[yellow]  ✗[/] {screenshot_path.name} - failed")
            progress.advance(task)

    console.print(f"[green]Vision analysis complete:[/] {len(results)} screenshots analyzed")

    return results


def generate_visual_summary(analyses: list[VisionAnalysis], config: ScreenScribeConfig) -> str:
    """
    Generate summary of visual issues found.

    Args:
        analyses: List of vision analyses
        config: ScreenScribe configuration

    Returns:
        Visual summary text
    """
    if not analyses:
        return ""

    # Collect all issues
    all_issues = []
    for a in analyses:
        all_issues.extend(a.issues_detected)

    # Count unique issues
    from collections import Counter

    issue_counts = Counter(all_issues)

    # Format summary
    lines = ["## Podsumowanie analizy wizualnej", ""]
    lines.append("### Najczęstsze problemy:")
    for issue, count in issue_counts.most_common(10):
        lines.append(f"- {issue} ({count}x)")

    return "\n".join(lines)
