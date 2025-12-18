"""Vision analysis using LibraxisAI Vision models."""

import base64
from dataclasses import dataclass
from pathlib import Path

import httpx
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from .config import CinescribeConfig
from .detect import Detection

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


VISION_PROMPT = """Jesteś ekspertem UX/UI analizującym screenshot aplikacji desktopowej.

Kontekst z transkrypcji (co użytkownik mówił w tym momencie):
"{transcript_context}"

Przeanalizuj ten screenshot i odpowiedz w formacie JSON:
{{
    "ui_elements": ["Lista widocznych elementów UI (przyciski, formularze, itp.)"],
    "issues_detected": ["Lista problemów wizualnych/UX widocznych na screenshocie"],
    "accessibility_notes": ["Uwagi dotyczące dostępności"],
    "design_feedback": "Ogólna ocena designu i sugestie (1-2 zdania)",
    "technical_observations": "Obserwacje techniczne - błędy, artefakty, problemy z layoutem"
}}

Odpowiadaj tylko JSON, po polsku."""


def encode_image_base64(image_path: Path) -> str:
    """Encode image to base64 for API."""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def analyze_screenshot(
    screenshot_path: Path,
    detection: Detection,
    config: CinescribeConfig
) -> VisionAnalysis | None:
    """
    Analyze a screenshot using Vision model.

    Args:
        screenshot_path: Path to screenshot
        detection: Associated detection for context
        config: Cinescribe configuration

    Returns:
        VisionAnalysis result or None if failed
    """
    if not config.api_key:
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

    prompt = VISION_PROMPT.format(
        transcript_context=detection.segment.text[:200]
    )

    try:
        with httpx.Client(timeout=120.0) as client:
            response = client.post(
                config.vision_endpoint,
                headers={"Authorization": f"Bearer {config.api_key}", "Content-Type": "application/json"},
                json={
                    "model": config.vision_model,
                    "input": [
                        {
                            "role": "user",
                            "content": [
                                {"type": "input_text", "text": prompt},
                                {
                                    "type": "input_image",
                                    "image_url": f"data:{media_type};base64,{image_base64}",
                                    "detail": "high"
                                }
                            ]
                        }
                    ],
                }
            )

        if response.status_code != 200:
            console.print(f"[yellow]Vision API error: {response.status_code} - {response.text[:300]}[/]")
            return None

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
            technical_observations=data.get("technical_observations", "")
        )

    except Exception as e:
        console.print(f"[yellow]Vision analysis failed for {screenshot_path.name}: {e}[/]")
        return None


def analyze_screenshots(
    screenshots: list[tuple[Detection, Path]],
    config: CinescribeConfig
) -> list[VisionAnalysis]:
    """
    Analyze all screenshots using Vision model.

    Args:
        screenshots: List of (detection, screenshot_path) tuples
        config: Cinescribe configuration

    Returns:
        List of vision analyses
    """
    if not config.use_vision_analysis:
        console.print("[dim]Vision analysis disabled[/]")
        return []

    if not config.api_key:
        console.print("[yellow]No API key - skipping vision analysis[/]")
        return []

    results = []
    console.print(f"[blue]Running vision analysis on {len(screenshots)} screenshots...[/]")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Analyzing screenshots...", total=len(screenshots))

        for i, (detection, screenshot_path) in enumerate(screenshots, 1):
            console.print(f"[dim]  [{i}/{len(screenshots)}] {screenshot_path.name}...[/]")
            analysis = analyze_screenshot(screenshot_path, detection, config)
            if analysis:
                results.append(analysis)
                console.print(f"[green]  ✓[/] {screenshot_path.name}")
            else:
                console.print(f"[yellow]  ✗[/] {screenshot_path.name} - failed")
            progress.advance(task)

    console.print(f"[green]Vision analysis complete:[/] {len(results)} screenshots analyzed")

    return results


def generate_visual_summary(
    analyses: list[VisionAnalysis],
    config: CinescribeConfig
) -> str:
    """
    Generate summary of visual issues found.

    Args:
        analyses: List of vision analyses
        config: Cinescribe configuration

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
