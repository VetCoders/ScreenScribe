"""Unified VLM-powered analysis combining semantic and vision analysis.

This module replaces the separate semantic.py + vision.py pipeline with a single
VLM call that analyzes both the screenshot AND full transcript context together.

Benefits:
- Single API call instead of two (LLM + VLM)
- VLM sees both image and full context simultaneously
- Better understanding of user intent by combining visual and verbal cues
- Reduced latency and API costs
- Parallel processing with staggered starts for better throughput
"""

from __future__ import annotations

import json
import re
import threading
import time
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

import httpx
from rich.console import Console
from rich.live import Live
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskID, TextColumn

from .api_utils import extract_llm_response_text, is_chat_completions_endpoint, retry_request
from .config import ScreenScribeConfig
from .detect import Detection
from .image_utils import encode_image_base64, get_media_type
from .prompts import get_unified_analysis_prompt

if TYPE_CHECKING:
    pass

console = Console()

# Constants for parallel processing
MAX_WORKERS = 5
STAGGER_DELAY = 0.5  # seconds between task starts


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

    # Deduplication tracking - stores (detection_id, timestamp) of merged findings
    merged_from_ids: list[tuple[int, float]] = field(default_factory=list)


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
            result: dict[str, Any] = json.loads(candidate)
            return result
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


def _extract_reasoning_delta(chunk: dict[str, Any]) -> str:
    """Extract reasoning summary delta from SSE chunk."""
    chunk_type = chunk.get("type", "")

    if chunk_type == "response.reasoning_summary_text.delta":
        return str(chunk.get("delta", ""))
    elif chunk_type == "response.reasoning_summary_text.done":
        return str(chunk.get("text", ""))

    return ""


def _extract_response_id_from_stream(chunk: dict[str, Any]) -> str:
    """Extract response ID from streaming chunk."""
    chunk_type = chunk.get("type", "")

    # response.done contains the final response with ID
    if chunk_type == "response.done":
        response = chunk.get("response", {})
        return str(response.get("id", ""))

    # Some formats include ID at chunk level
    return str(chunk.get("id", "") or chunk.get("response_id", ""))


def analyze_finding_unified_streaming(
    detection: Detection,
    screenshot_path: Path | None,
    config: ScreenScribeConfig,
    previous_response_id: str | None = None,
    on_reasoning: Callable[[str], None] | None = None,
    on_content: Callable[[str], None] | None = None,
) -> UnifiedFinding | None:
    """
    Analyze a single finding using VLM with streaming SSE response.

    This is the streaming version that provides real-time feedback
    via callbacks for reasoning and content deltas.

    Args:
        detection: The detection to analyze
        screenshot_path: Path to screenshot (can be None if extraction failed)
        config: ScreenScribe configuration
        previous_response_id: Response ID from previous finding for context chaining
        on_reasoning: Callback for reasoning summary deltas
        on_content: Callback for content deltas

    Returns:
        UnifiedFinding result or None if analysis failed
    """
    if not config.get_vision_api_key():
        return None

    # Determine if we have a screenshot
    has_screenshot = screenshot_path is not None and screenshot_path.exists()

    # Get appropriate prompt (with or without image)
    prompt_template = get_unified_analysis_prompt(config.language, text_only=not has_screenshot)

    # Build prompt with FULL context
    prompt = prompt_template.format(
        transcript_context=detection.segment.text,
        full_context=detection.context,
        category=detection.category,
    )

    try:
        # Build request body based on API format
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
                "stream": True,
            }
        else:
            # Responses API format (OpenAI + LibraxisAI)
            content_responses: list[dict[str, Any]] = [{"type": "input_text", "text": prompt}]
            if has_screenshot and screenshot_path:
                image_b64 = encode_image_base64(screenshot_path)
                media_type = get_media_type(screenshot_path)
                content_responses.append(
                    {
                        "type": "input_image",
                        "image_url": f"data:{media_type};base64,{image_b64}",
                    }
                )
            payload = {
                "model": config.vision_model,
                "input": [{"role": "user", "content": content_responses}],
                "reasoning": {"summary": "auto"},
                "stream": True,
            }
            if previous_response_id:
                payload["previous_response_id"] = previous_response_id

        # Stream the response
        collected_content = ""
        response_id = ""

        with httpx.Client(timeout=120.0) as client:
            with client.stream(
                "POST",
                config.vision_endpoint,
                headers={
                    "Authorization": f"Bearer {config.get_vision_api_key()}",
                    "Content-Type": "application/json",
                    "Accept": "text/event-stream",
                },
                json=payload,
            ) as response:
                response.raise_for_status()

                for line in response.iter_lines():
                    if not line:
                        continue

                    # Handle SSE format
                    if line.startswith("event:"):
                        continue

                    if line.startswith("data:"):
                        line_data = line[5:].strip()
                        if line_data == "[DONE]":
                            break

                        try:
                            chunk = json.loads(line_data)

                            # Extract reasoning delta
                            reasoning_delta = _extract_reasoning_delta(chunk)
                            if reasoning_delta and on_reasoning:
                                on_reasoning(reasoning_delta)

                            # Extract content delta
                            content_delta = _extract_stream_delta(chunk)
                            if content_delta:
                                collected_content += content_delta
                                if on_content:
                                    on_content(content_delta)

                            # Extract response ID
                            chunk_response_id = _extract_response_id_from_stream(chunk)
                            if chunk_response_id:
                                response_id = chunk_response_id

                        except json.JSONDecodeError:
                            continue

        if not collected_content:
            return None

        # Parse JSON from content
        try:
            data = parse_json_response(collected_content)
        except json.JSONDecodeError:
            return None

        return UnifiedFinding(
            detection_id=detection.segment.id,
            screenshot_path=screenshot_path,
            timestamp=detection.segment.start,
            category=detection.category,
            is_issue=data.get("is_issue", True),
            sentiment=data.get("sentiment", "problem"),
            severity=data.get("severity", "medium"),
            summary=data.get("summary", ""),
            action_items=data.get("action_items", []),
            affected_components=data.get("affected_components", []),
            suggested_fix=data.get("suggested_fix", ""),
            ui_elements=data.get("ui_elements", []),
            issues_detected=data.get("issues_detected", []),
            accessibility_notes=data.get("accessibility_notes", []),
            design_feedback=data.get("design_feedback", ""),
            technical_observations=data.get("technical_observations", ""),
            response_id=response_id,
        )

    except Exception as e:
        if config.verbose:
            console.print(f"[dim]Streaming analysis failed: {e}[/]")
        return None


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
                    # Responses API format (OpenAI + LibraxisAI)
                    content_responses: list[dict[str, Any]] = [
                        {"type": "input_text", "text": prompt}
                    ]
                    if has_screenshot and screenshot_path:
                        image_b64 = encode_image_base64(screenshot_path)
                        media_type = get_media_type(screenshot_path)
                        # OpenAI Responses API uses image_url with data URI
                        content_responses.append(
                            {
                                "type": "input_image",
                                "image_url": f"data:{media_type};base64,{image_b64}",
                            }
                        )
                    payload = {
                        "model": config.vision_model,
                        "input": [{"role": "user", "content": content_responses}],
                        "reasoning": {"summary": "auto"},  # Enable reasoning summaries
                    }
                    # Add conversation chaining if we have previous context
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


@dataclass
class _TaskState:
    """State for a parallel analysis task."""

    idx: int
    detection: Detection
    screenshot_path: Path
    status: str = "pending"  # pending, running, done, failed
    reasoning_preview: str = ""
    severity: str = ""
    task_id: TaskID | None = None


def analyze_all_findings_unified(
    screenshots: list[tuple[Detection, Path]],
    config: ScreenScribeConfig,
    previous_response_id: str = "",
) -> list[UnifiedFinding]:
    """
    Analyze all findings using unified VLM pipeline with parallel streaming.

    Uses ThreadPoolExecutor to run up to MAX_WORKERS concurrent VLM requests,
    with staggered starts (STAGGER_DELAY between each) to avoid rate limits.
    Response IDs are chained between streams using a shared lock.

    Args:
        screenshots: List of (detection, screenshot_path) tuples
        config: ScreenScribe configuration
        previous_response_id: Optional response ID from previous batch for context chaining

    Returns:
        List of UnifiedFinding results (ordered by original index)
    """
    if not config.get_vision_api_key():
        console.print("[yellow]No Vision API key - skipping unified analysis[/]")
        return []

    if not screenshots:
        return []

    console.print(
        f"[blue]Running parallel VLM analysis on {len(screenshots)} findings "
        f"(max {MAX_WORKERS} concurrent, {STAGGER_DELAY}s stagger)...[/]"
    )

    # Shared state for response_id chaining
    response_id_lock = threading.Lock()
    shared_response_id = previous_response_id

    # Track task states for display
    task_states: dict[int, _TaskState] = {}
    for idx, (detection, screenshot_path) in enumerate(screenshots):
        task_states[idx] = _TaskState(idx=idx, detection=detection, screenshot_path=screenshot_path)

    # Results storage (indexed by original position)
    results_by_idx: dict[int, UnifiedFinding | None] = {}
    completed_count = 0

    def analyze_one(idx: int, delay: float) -> tuple[int, UnifiedFinding | None]:
        """Analyze a single finding with staggered start and response_id chaining."""
        nonlocal shared_response_id, completed_count

        # Staggered start
        if delay > 0:
            time.sleep(delay)

        state = task_states[idx]
        state.status = "running"

        # Get latest response_id for chaining
        with response_id_lock:
            prev_id = shared_response_id

        # Create callbacks for live display
        reasoning_buffer = ""

        def on_reasoning(delta: str) -> None:
            nonlocal reasoning_buffer
            reasoning_buffer = (reasoning_buffer + delta)[-50:]
            state.reasoning_preview = reasoning_buffer

        # Run streaming analysis
        finding = analyze_finding_unified_streaming(
            state.detection,
            state.screenshot_path,
            config,
            previous_response_id=prev_id,
            on_reasoning=on_reasoning,
        )

        # Update shared response_id for next task
        if finding and finding.response_id:
            with response_id_lock:
                shared_response_id = finding.response_id

        # Update state
        if finding:
            state.status = "done"
            state.severity = finding.severity if finding.is_issue else "ok"
        else:
            state.status = "failed"

        with response_id_lock:
            completed_count += 1
        return (idx, finding)

    # Build progress display
    progress = Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=20),
        TextColumn("{task.completed}/{task.total}"),
        TextColumn("[dim]{task.fields[stream]}[/]"),
        console=console,
        transient=True,
    )

    with Live(progress, console=console, refresh_per_second=10):
        # Add main progress task
        main_task = progress.add_task(
            f"Analyzing {len(screenshots)} findings",
            total=len(screenshots),
            stream="starting...",
        )

        # Submit all tasks with staggered delays
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures: dict[Future[tuple[int, UnifiedFinding | None]], int] = {}

            for idx in range(len(screenshots)):
                delay = idx * STAGGER_DELAY
                future = executor.submit(analyze_one, idx, delay)
                futures[future] = idx

            # Process completions as they arrive
            for future in as_completed(futures):
                idx = futures[future]
                try:
                    result_idx, finding = future.result()
                    results_by_idx[result_idx] = finding

                    # Update progress display
                    state = task_states[result_idx]
                    if finding:
                        status_str = f"[green]ok[/] #{result_idx+1} [{state.severity}]"
                    else:
                        status_str = f"[yellow]x[/] #{result_idx+1} failed"

                    # Show active tasks reasoning
                    active_reasoning = ""
                    for s in task_states.values():
                        if s.status == "running" and s.reasoning_preview:
                            active_reasoning = s.reasoning_preview[:30]
                            break

                    progress.update(
                        main_task,
                        advance=1,
                        stream=active_reasoning or status_str,
                    )

                except Exception as e:
                    results_by_idx[idx] = None
                    progress.update(main_task, advance=1, stream=f"[red]error: {e}[/]")

    # Collect results in original order
    results: list[UnifiedFinding] = []
    for idx in range(len(screenshots)):
        finding = results_by_idx.get(idx)
        if finding:
            results.append(finding)

    # Print completion status for each task
    for idx in range(len(screenshots)):
        state = task_states[idx]
        finding = results_by_idx.get(idx)
        timestamp = state.detection.segment.start

        if finding:
            chained = " [chained]" if finding.response_id else ""
            severity_color = {
                "critical": "red",
                "high": "yellow",
                "medium": "blue",
                "low": "dim",
                "ok": "green",
            }.get(state.severity, "white")
            console.print(
                f"[dim]  [{idx+1}/{len(screenshots)}][/] "
                f"{state.detection.category} @ {timestamp:.1f}s "
                f"[{severity_color}]{state.severity}[/]{chained}"
            )
        else:
            console.print(
                f"[dim]  [{idx+1}/{len(screenshots)}][/] "
                f"{state.detection.category} @ {timestamp:.1f}s "
                f"[yellow]failed[/]"
            )

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


def _normalize_text_for_similarity(text: str) -> set[str]:
    """Normalize text for similarity comparison.

    Removes stopwords, normalizes numbers, and extracts meaningful words.

    Args:
        text: Input text

    Returns:
        Set of normalized words
    """
    # Polish and English stopwords
    stopwords = {
        # Polish
        "i",
        "w",
        "z",
        "na",
        "do",
        "że",
        "to",
        "jest",
        "się",
        "nie",
        "tak",
        "ale",
        "jak",
        "co",
        "ten",
        "ta",
        "te",
        "za",
        "od",
        "po",
        "o",
        "a",
        "oraz",
        "lub",
        "by",
        "być",
        "aby",
        "już",
        "też",
        "tylko",
        "czy",
        "tego",
        "tej",
        "tym",
        "tę",
        "tych",
        "które",
        "który",
        "która",
        "których",
        "którzy",
        "której",
        "którą",
        "chce",
        "chciałabym",
        "chciałaby",
        "mówi",
        "prosi",
        "sugeruje",
        "uważa",
        "wskazuje",
        "użytkownik",
        "użytkowniczka",
        "najlepiej",
        "około",
        "ok",
        "ok.",
        # English
        "the",
        "an",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "have",
        "has",
        "had",
        "does",
        "did",
        "will",
        "would",
        "could",
        "should",
        "may",
        "might",
        "must",
        "shall",
        "can",
        "need",
        "dare",
        "ought",
        "used",
        "of",
        "in",
        "for",
        "on",
        "with",
        "at",
        "from",
        "as",
        "into",
        "through",
        "during",
        "before",
        "after",
        "above",
        "below",
        "between",
        "under",
        "again",
        "further",
        "then",
        "once",
        "here",
        "there",
        "when",
        "where",
        "why",
        "how",
        "all",
        "each",
        "few",
        "more",
        "most",
        "other",
        "some",
        "such",
        "no",
        "nor",
        "not",
        "only",
        "own",
        "same",
        "so",
        "than",
        "too",
        "very",
        "just",
        "and",
        "but",
        "if",
        "or",
        "because",
        "until",
        "while",
        "this",
        "that",
        "these",
        "those",
        "user",
        "wants",
        "says",
        "suggests",
    }

    # Number normalization: map Polish number words to digits
    number_map = {
        "jeden": "1",
        "jedna": "1",
        "jedno": "1",
        "jednego": "1",
        "dwa": "2",
        "dwie": "2",
        "dwóch": "2",
        "dwu": "2",
        "trzy": "3",
        "trzech": "3",
        "cztery": "4",
        "czterech": "4",
        "pięć": "5",
        "pięciu": "5",
        "pieciu": "5",
        "sześć": "6",
        "sześciu": "6",
        "siedem": "7",
        "siedmiu": "7",
        "osiem": "8",
        "ośmiu": "8",
        "dziewięć": "9",
        "dziewięciu": "9",
        "dziesięć": "10",
        "dziesięciu": "10",
    }

    # Simple Polish stemming: normalize common word forms
    stem_map = {
        # lista (list)
        "listy": "lista",
        "liście": "lista",
        "liscie": "lista",
        "listę": "lista",
        "liste": "lista",
        "liści": "lista",
        # krótki/skrócić (short/shorten)
        "krótsza": "krotki",
        "krotsza": "krotki",
        "krótszy": "krotki",
        "skrócić": "krotki",
        "skrocic": "krotki",
        "skrócona": "krotki",
        # pozycja (position/item)
        "pozycji": "pozycja",
        "pozycje": "pozycja",
        "pozycją": "pozycja",
        # pacjent (patient)
        "pacjenta": "pacjent",
        "pacjentów": "pacjent",
        "pacjentow": "pacjent",
        "pacjenci": "pacjent",
        "pacjentem": "pacjent",
        # dodać (add)
        "dodaj": "dodac",
        "dodać": "dodac",
        "dodania": "dodac",
        # nagłówek (header)
        "nagłówka": "naglowek",
        "naglowka": "naglowek",
        "nagłówku": "naglowek",
        # sekcja (section)
        "sekcji": "sekcja",
        "sekcję": "sekcja",
        "sekcje": "sekcja",
    }

    # Normalize: lowercase, remove punctuation, split
    import re

    text_lower = text.lower()
    # Remove punctuation except numbers
    text_clean = re.sub(r"[^\w\s]", " ", text_lower)
    words = text_clean.split()

    # Process words
    result = set()
    for word in words:
        # Normalize numbers first so digits survive length filter
        if word in number_map:
            result.add(number_map[word])
            continue

        # Allow key short tokens like UI/UX/AI and digits
        if len(word) <= 2 and not word.isdigit() and word not in {"ui", "ux", "ai"}:
            continue
        if word in stopwords:
            continue

        # Apply stemming
        if word in stem_map:
            result.add(stem_map[word])
        else:
            result.add(word)

    return result


def _text_similarity(text1: str, text2: str) -> float:
    """Calculate concept-based similarity between two texts.

    Uses normalized text and focuses on key concept overlap rather than
    pure Jaccard similarity. This works better for Polish text with
    different phrasings of the same concept.

    Args:
        text1: First text
        text2: Second text

    Returns:
        Similarity score between 0.0 and 1.0
    """
    words1 = _normalize_text_for_similarity(text1)
    words2 = _normalize_text_for_similarity(text2)

    if not words1 or not words2:
        return 0.0

    # Key concepts that indicate similar topics
    key_concepts = {
        "lista",
        "pozycja",
        "krotki",
        "sekcja",
        "naglowek",
        "pacjent",
        "dodac",
        "przycisk",
        "button",
        "dropdown",
        "menu",
        "modal",
        "okno",
        "formularz",
        "pole",
        "input",
        "wybor",
        "opcja",
        "1",
        "2",
        "3",
        "4",
        "5",
        "6",
        "7",
        "8",
        "9",
        "10",
    }

    # Find shared key concepts
    concepts1 = words1 & key_concepts
    concepts2 = words2 & key_concepts
    shared_concepts = concepts1 & concepts2

    # If they share 2+ key concepts, consider them similar
    if len(shared_concepts) >= 2:
        # Score based on concept overlap
        concept_score = len(shared_concepts) / max(len(concepts1), len(concepts2), 1)

        # Also factor in overall word overlap (Jaccard)
        intersection = words1 & words2
        union = words1 | words2
        jaccard = len(intersection) / len(union) if union else 0.0

        # Weighted: 60% concept match, 40% jaccard
        return 0.6 * concept_score + 0.4 * jaccard

    # Fallback to pure Jaccard for non-concept matches
    intersection = words1 & words2
    union = words1 | words2

    return len(intersection) / len(union) if union else 0.0


def deduplicate_findings(
    findings: list[UnifiedFinding],
    similarity_threshold: float = 0.4,
) -> list[UnifiedFinding]:
    """Deduplicate similar findings by merging them.

    Two-stage deduplication:
    1. Group findings with IDENTICAL summaries (cross-category, always merge)
    2. Group SIMILAR findings only if same category AND within 30s timestamp

    The merged finding keeps:
    - Highest severity
    - Combined action items (deduplicated)
    - First screenshot (earliest timestamp)
    - Combined affected components

    Args:
        findings: List of UnifiedFinding objects
        similarity_threshold: Minimum similarity (0-1) to consider as duplicate

    Returns:
        Deduplicated list of UnifiedFinding objects
    """
    if not findings or len(findings) <= 1:
        return findings

    def normalize_text(text: str) -> str:
        """Normalize text for comparison: lowercase and collapse whitespace."""
        return " ".join(text.lower().split())

    def extract_similarity_text(finding: UnifiedFinding) -> str:
        """Extract text from finding for similarity comparison."""
        if finding.summary.strip():
            return finding.summary
        parts = []
        parts.extend(finding.action_items or [])
        parts.extend(finding.affected_components or [])
        parts.extend(finding.issues_detected or [])
        parts.extend(finding.ui_elements or [])
        return " ".join(part.strip() for part in parts if part and part.strip())

    # Severity ranking for comparison
    severity_rank = {"critical": 4, "high": 3, "medium": 2, "low": 1, "none": 0}

    # Stage 1: Group identical summaries first (stable, cross-category)
    summary_groups: dict[str, list[int]] = {}
    for idx, finding in enumerate(findings):
        key = normalize_text(finding.summary)
        if key:
            summary_groups.setdefault(key, []).append(idx)

    # Stage 2: Group similar findings
    groups: list[list[UnifiedFinding]] = []
    used: set[int] = set()

    for i, finding in enumerate(findings):
        # Check if this finding has identical summary duplicates
        key = normalize_text(finding.summary)
        if key and len(summary_groups.get(key, [])) > 1:
            if i in used:
                continue
            group = [findings[idx] for idx in summary_groups[key]]
            groups.append(group)
            used.update(summary_groups[key])
            continue

        if i in used:
            continue

        # Start new group with this finding
        group = [finding]
        used.add(i)

        # Find similar findings (same category + close timestamp)
        for j, other in enumerate(findings):
            if j in used:
                continue

            # Only compare within same category and 30s window
            if finding.category == other.category:
                if abs(finding.timestamp - other.timestamp) > 30:
                    continue
                similarity = _text_similarity(
                    extract_similarity_text(finding), extract_similarity_text(other)
                )
            else:
                similarity = 0.0

            if similarity >= similarity_threshold:
                group.append(other)
                used.add(j)

        groups.append(group)

    # Merge each group into single finding
    result: list[UnifiedFinding] = []

    for group in groups:
        if len(group) == 1:
            result.append(group[0])
            continue

        # Sort by timestamp to get earliest
        group.sort(key=lambda f: f.timestamp)
        base = group[0]

        # Find highest severity
        best_severity = max(group, key=lambda f: severity_rank.get(f.severity, 0)).severity

        # Combine action items (deduplicate)
        all_actions: list[str] = []
        seen_actions: set[str] = set()
        for f in group:
            for action in f.action_items:
                action_lower = action.lower()
                if action_lower not in seen_actions:
                    all_actions.append(action)
                    seen_actions.add(action_lower)

        # Combine affected components
        all_components: list[str] = []
        seen_components: set[str] = set()
        for f in group:
            for comp in f.affected_components:
                comp_lower = comp.lower()
                if comp_lower not in seen_components:
                    all_components.append(comp)
                    seen_components.add(comp_lower)

        # Track original (detection_id, timestamp) pairs that were merged into base
        merged_ids = [(f.detection_id, f.timestamp) for f in group if f is not base]

        # Create merged finding
        merged = UnifiedFinding(
            detection_id=base.detection_id,
            screenshot_path=base.screenshot_path,
            timestamp=base.timestamp,
            # Use best values
            category=base.category,
            is_issue=any(f.is_issue for f in group),
            sentiment=base.sentiment,
            severity=best_severity,
            summary=base.summary,  # Keep first (earliest) summary
            action_items=all_actions[:5],  # Limit to 5 actions
            affected_components=all_components,
            suggested_fix=base.suggested_fix,
            # Vision fields from first
            ui_elements=base.ui_elements,
            issues_detected=base.issues_detected,
            accessibility_notes=base.accessibility_notes,
            design_feedback=base.design_feedback,
            technical_observations=base.technical_observations,
            response_id=base.response_id,
            # Track all original IDs for screenshot filtering
            merged_from_ids=merged_ids,
        )

        result.append(merged)

        # Log merge
        if len(group) > 1:
            console.print(
                f"[dim]  Merged {len(group)} similar findings → " f"'{base.summary[:50]}...'[/]"
            )

    return result
