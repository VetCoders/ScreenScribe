"""Unified VLM-powered analysis combining semantic and vision analysis.

This module replaces the separate semantic.py + vision.py pipeline with a single
VLM call that analyzes both the screenshot AND full transcript context together.

Benefits:
- Single API call instead of two (LLM + VLM)
- VLM sees both image and full context simultaneously
- Better understanding of user intent by combining visual and verbal cues
- Reduced latency and API costs
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

import httpx
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from .api_utils import extract_llm_response_text, is_chat_completions_endpoint, retry_request
from .config import ScreenScribeConfig
from .detect import Detection
from .image_utils import encode_image_base64, get_media_type
from .prompts import get_unified_analysis_prompt

if TYPE_CHECKING:
    pass

console = Console()


@dataclass
class UnifiedFinding:
    """Combined semantic + visual analysis of a finding.

    This dataclass unifies SemanticAnalysis and VisionAnalysis into a single
    result, produced by a single VLM call that analyzes both the screenshot
    and transcript context together.
    """

    detection_id: int
    screenshot_path: Path | None
    timestamp: float

    # From semantic analysis
    category: str  # bug, change, ui, performance, accessibility, other
    is_issue: bool  # True if user reports a problem, False if confirms OK
    sentiment: str  # "problem", "positive", "neutral"
    severity: str  # "critical", "high", "medium", "low", "none"
    summary: str
    action_items: list[str]
    affected_components: list[str]
    suggested_fix: str

    # From vision analysis
    ui_elements: list[str]
    issues_detected: list[str]
    accessibility_notes: list[str]
    design_feedback: str
    technical_observations: str

    # API response tracking
    response_id: str = ""  # For conversation chaining between findings


def parse_json_response(content: str) -> dict[str, Any]:
    """Parse JSON from LLM response, handling various formats.

    Args:
        content: Raw response text from LLM

    Returns:
        Parsed JSON as dict

    Raises:
        json.JSONDecodeError: If JSON parsing fails
    """
    # Strip model control tokens (e.g. <|channel|>final <|constrain|>JSON<|message|>)
    content = re.sub(r"<\|[^|]+\|>\w*\s*", "", content)

    # If content starts with non-JSON, try to find JSON object
    if not content.strip().startswith("{"):
        json_match = re.search(r"\{.*\}", content, re.DOTALL)
        if json_match:
            content = json_match.group(0)

    # Handle potential markdown code blocks
    json_content = content
    if "```json" in content:
        json_content = content.split("```json")[1].split("```")[0]
    elif "```" in content:
        parts = content.split("```")
        if len(parts) >= 2:
            json_content = parts[1]

    json_candidates: list[str] = [json_content.strip()]

    # If we still fail, try to grab the largest {...} block
    json_match = re.search(r"\{.*\}", json_content, re.DOTALL)
    if json_match:
        json_candidates.append(json_match.group(0).strip())

    # Try to trim trailing ellipsis or stray characters
    if json_content.strip().endswith("..."):
        json_candidates.append(json_content.strip().rstrip("."))

    last_error: json.JSONDecodeError | None = None
    for candidate in json_candidates:
        try:
            return json.loads(candidate)
        except json.JSONDecodeError as e:
            last_error = e
            continue

    # Fallback: return sentinel payload instead of raising, so pipeline can continue
    return {
        "parse_error": str(last_error) if last_error else "Unknown JSON parse error",
        "raw_content": content,
    }


def _clean_summary_response(text: str) -> str:
    """Clean up LLM response that may contain markdown fences or JSON.

    Some models return JSON wrapped in markdown code fences even when asked
    for plain text. This function:
    1. Strips markdown code fences (```json ... ``` or ``` ... ```)
    2. If remaining content is JSON with a "summary" key, extracts it
    3. Otherwise returns the clean text

    Args:
        text: Raw response text from LLM

    Returns:
        Cleaned plain text
    """
    cleaned = text.strip()

    # Strip markdown code fences
    fence_pattern = re.compile(r"^```(?:json)?\s*\n?(.*?)\n?```$", re.DOTALL | re.IGNORECASE)
    match = fence_pattern.match(cleaned)
    if match:
        cleaned = match.group(1).strip()

    # Try to parse as JSON and extract summary if present
    if cleaned.startswith("{"):
        try:
            parsed = json.loads(cleaned)
            if isinstance(parsed, dict):
                # Look for summary field
                if "summary" in parsed:
                    return str(parsed["summary"])
                # Or return the whole thing as formatted text
                # Build readable output from known fields
                parts = []
                if parsed.get("summary"):
                    parts.append(parsed["summary"])
                if parsed.get("action_items"):
                    items = parsed["action_items"]
                    if isinstance(items, list):
                        parts.append("\n\nPriorytetowe akcje:")
                        for item in items[:5]:
                            parts.append(f"• {item}")
                if parts:
                    return "\n".join(parts)
        except json.JSONDecodeError:
            pass

    return cleaned


def extract_response_content(
    result: dict[str, Any], clean_summary: bool = False, endpoint: str = ""
) -> str:
    """Extract text content from API response (supports both formats).

    Handles both LibraxisAI v1/responses and OpenAI Chat Completions formats.

    Args:
        result: API response JSON
        clean_summary: If True, clean up markdown fences and extract from JSON
        endpoint: API endpoint URL (used to detect format)

    Returns:
        Extracted text content
    """
    # Use unified helper if endpoint provided
    if endpoint and is_chat_completions_endpoint(endpoint):
        content = extract_llm_response_text(result, endpoint)
    else:
        # LibraxisAI v1/responses format
        content = ""
        output_list = result.get("output", [])
        if not isinstance(output_list, list):
            return content
        for item in output_list:
            if not isinstance(item, dict):
                continue
            item_type = item.get("type", "")
            # Handle reasoning blocks (skip - look for actual output)
            if item_type == "reasoning":
                pass
            # Handle message blocks
            elif item_type == "message":
                item_content = item.get("content", [])
                if isinstance(item_content, list):
                    for part in item_content:
                        if isinstance(part, dict) and part.get("type") in ("output_text", "text"):
                            text = part.get("text", "")
                            if isinstance(text, str):
                                content += text
            # Handle direct output_text or text
            elif item_type in ("output_text", "text"):
                text = item.get("text", "")
                if isinstance(text, str):
                    content += text

    if clean_summary:
        content = _clean_summary_response(content)

    return content


def analyze_finding_unified(
    detection: Detection,
    screenshot_path: Path | None,
    config: ScreenScribeConfig,
    previous_response_id: str | None = None,
) -> UnifiedFinding | None:
    """
    Analyze a single finding using VLM with both image and full context.

    This is the core function that replaces separate semantic + vision analysis.
    It sends the screenshot AND full transcript context to VLM in a single call.

    Args:
        detection: The detection to analyze
        screenshot_path: Path to screenshot (can be None if extraction failed)
        config: ScreenScribe configuration
        previous_response_id: Response ID from previous finding for context chaining

    Returns:
        UnifiedFinding result or None if analysis failed
    """
    if not config.get_vision_api_key():
        console.print("[yellow]No Vision API key - skipping unified analysis[/]")
        return None

    # Determine if we have a screenshot
    has_screenshot = screenshot_path is not None and screenshot_path.exists()

    # Get appropriate prompt (with or without image)
    prompt_template = get_unified_analysis_prompt(config.language, text_only=not has_screenshot)

    # Build prompt with FULL context (not just 200 chars!)
    prompt = prompt_template.format(
        transcript_context=detection.segment.text,
        full_context=detection.context,  # Full context from surrounding segments
        category=detection.category,
    )

    try:

        def do_unified_request() -> httpx.Response:
            with httpx.Client(timeout=120.0) as client:
                # Build content array based on API format
                use_chat_completions = is_chat_completions_endpoint(config.vision_endpoint)

                if use_chat_completions:
                    # OpenAI Chat Completions format
                    content: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
                    if has_screenshot and screenshot_path:
                        image_base64 = encode_image_base64(screenshot_path)
                        media_type = get_media_type(screenshot_path)
                        content.append(
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:{media_type};base64,{image_base64}"},
                            }
                        )
                    payload: dict[str, object] = {
                        "model": config.vision_model,
                        "messages": [{"role": "user", "content": content}],
                    }
                else:
                    # LibraxisAI Responses API format
                    content_libraxis: list[dict[str, str]] = [
                        {"type": "input_text", "text": prompt}
                    ]
                    if has_screenshot and screenshot_path:
                        image_base64 = encode_image_base64(screenshot_path)
                        media_type = get_media_type(screenshot_path)
                        content_libraxis.append(
                            {
                                "type": "input_image",
                                "image_url": f"data:{media_type};base64,{image_base64}",
                                "detail": "high",
                            }
                        )
                    payload = {
                        "model": config.vision_model,
                        "input": [{"role": "user", "content": content_libraxis}],
                    }
                    # Add conversation chaining if we have previous context (LibraxisAI only)
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
            do_unified_request,
            max_retries=3,
            operation_name=f"Unified analysis ({detection.segment.start:.1f}s)",
        )

        # Parse response
        raw_text = response.text
        if not raw_text or raw_text.strip() == "":
            console.print(f"[yellow]Empty response from API (status {response.status_code})[/]")
            return None

        try:
            result = response.json()
        except Exception as e:
            console.print(f"[yellow]Failed to parse API response: {e}[/]")
            return None

        # Extract content from response (supports both API formats)
        content_text = extract_response_content(result, endpoint=config.vision_endpoint)

        if not content_text:
            console.print(
                f"[yellow]No content in response. Output types: "
                f"{[i.get('type') for i in result.get('output', [])]}[/]"
            )
            return None

        # Parse JSON from content
        data = parse_json_response(content_text)
        if "parse_error" in data:
            console.print(
                f"[yellow]JSON parse error: {data['parse_error']}. "
                f"Content (truncated): {data.get('raw_content','')[:200]}...[/]"
            )

        # Extract response_id for conversation chaining
        response_id = result.get("id", "")

        return UnifiedFinding(
            detection_id=detection.segment.id,
            screenshot_path=screenshot_path,
            timestamp=detection.segment.start,
            # Semantic fields
            category=detection.category,
            is_issue=data.get("is_issue", "parse_error" not in data),
            sentiment=data.get("sentiment", "problem"),
            severity=data.get("severity", "medium"),
            summary=data.get("summary", data.get("raw_content", "")),
            action_items=data.get("action_items", []),
            affected_components=data.get("affected_components", []),
            suggested_fix=data.get("suggested_fix", data.get("parse_error", "")),
            # Vision fields
            ui_elements=data.get("ui_elements", []),
            issues_detected=data.get("issues_detected", []),
            accessibility_notes=data.get("accessibility_notes", []),
            design_feedback=data.get("design_feedback", ""),
            technical_observations=data.get("technical_observations", ""),
            # API tracking
            response_id=response_id,
        )

    except Exception as e:
        console.print(f"[yellow]Unified analysis failed: {e}[/]")
        return None


def analyze_all_findings_unified(
    screenshots: list[tuple[Detection, Path]],
    config: ScreenScribeConfig,
    previous_response_id: str = "",
) -> list[UnifiedFinding]:
    """
    Analyze all findings using unified VLM pipeline.

    Replaces the separate analyze_detections_semantically() + analyze_screenshots()
    pipeline with a single pass that analyzes each finding with VLM.

    Args:
        screenshots: List of (detection, screenshot_path) tuples
        config: ScreenScribe configuration
        previous_response_id: Optional response ID from previous batch for context chaining

    Returns:
        List of UnifiedFinding results
    """
    if not config.get_vision_api_key():
        console.print("[yellow]No Vision API key - skipping unified analysis[/]")
        return []

    results = []
    console.print(f"[blue]Running unified VLM analysis on {len(screenshots)} findings...[/]")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Analyzing findings...", total=len(screenshots))

        # Chain context between findings
        chain_response_id = previous_response_id

        for i, (detection, screenshot_path) in enumerate(screenshots, 1):
            console.print(
                f"[dim]  [{i}/{len(screenshots)}] "
                f"{detection.category} @ {detection.segment.start:.1f}s...[/]"
            )

            finding = analyze_finding_unified(
                detection,
                screenshot_path,
                config,
                previous_response_id=chain_response_id,
            )

            if finding:
                results.append(finding)
                # Update chain for next finding
                if finding.response_id:
                    chain_response_id = finding.response_id

                # Show result indicator
                severity = finding.severity if finding.is_issue else "ok"
                chained = " [chained]" if chain_response_id else ""
                console.print(f"[green]  ok[/] [{severity}]{chained}")
            else:
                console.print("[yellow]  x[/] failed")

            progress.advance(task)

    # Summary
    issues = [f for f in results if f.is_issue]
    non_issues = [f for f in results if not f.is_issue]
    critical = sum(1 for f in issues if f.severity == "critical")
    high = sum(1 for f in issues if f.severity == "high")
    medium = sum(1 for f in issues if f.severity == "medium")
    low = sum(1 for f in issues if f.severity == "low")

    console.print(
        f"[green]Unified analysis complete:[/] "
        f"[red]{critical} critical[/], "
        f"[yellow]{high} high[/], "
        f"[blue]{medium} medium[/], "
        f"[dim]{low} low[/]"
    )
    if non_issues:
        console.print(f"[dim]  ({len(non_issues)} positive/neutral observations filtered)[/]")

    return results


def generate_unified_summary(findings: list[UnifiedFinding], config: ScreenScribeConfig) -> str:
    """
    Generate executive summary from unified findings.

    Args:
        findings: List of UnifiedFinding results
        config: ScreenScribe configuration

    Returns:
        Executive summary text
    """
    if not findings or not config.get_vision_api_key():
        return ""

    # Filter to issues only
    issues = [f for f in findings if f.is_issue]
    if not issues:
        return "No issues found - all observations confirmed as working correctly."

    # Build findings summary for prompt
    from .prompts import get_executive_summary_prompt

    findings_list = []
    for f in issues:
        findings_list.append(f"- [{f.severity.upper()}] {f.summary}")

    prompt_template = get_executive_summary_prompt(config.language)
    prompt = prompt_template.format(findings=chr(10).join(findings_list))

    try:

        def do_summary_request() -> httpx.Response:
            with httpx.Client(timeout=60.0) as client:
                # Build request body based on API format
                from .api_utils import build_llm_request_body

                response = client.post(
                    config.vision_endpoint,  # Use vision endpoint (same model)
                    headers={
                        "Authorization": f"Bearer {config.get_vision_api_key()}",
                        "Content-Type": "application/json",
                    },
                    json=build_llm_request_body(
                        config.vision_model, prompt, config.vision_endpoint
                    ),
                )
                response.raise_for_status()
                return response

        response = retry_request(
            do_summary_request,
            max_retries=3,
            operation_name="Executive summary",
        )

        result = response.json()
        return extract_response_content(result, clean_summary=True, endpoint=config.vision_endpoint)

    except Exception as e:
        console.print(f"[yellow]Executive summary failed: {e}[/]")
        return ""


def generate_visual_summary_unified(findings: list[UnifiedFinding]) -> str:
    """
    Generate summary of visual issues found.

    Args:
        findings: List of UnifiedFinding results

    Returns:
        Visual summary text in Markdown
    """
    if not findings:
        return ""

    # Collect all visual issues
    all_issues = []
    for f in findings:
        if f.is_issue:
            all_issues.extend(f.issues_detected)

    if not all_issues:
        return ""

    # Count unique issues
    from collections import Counter

    issue_counts = Counter(all_issues)

    # Format summary
    lines = ["## Podsumowanie analizy wizualnej", ""]
    lines.append("### Najczęstsze problemy:")
    for issue, count in issue_counts.most_common(10):
        lines.append(f"- {issue} ({count}x)")

    return "\n".join(lines)
