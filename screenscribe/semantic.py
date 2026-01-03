"""Semantic analysis using LibraxisAI LLM models."""

from dataclasses import dataclass

import httpx
from rich.console import Console

from .api_utils import retry_request
from .config import ScreenScribeConfig
from .detect import Detection
from .prompts import get_executive_summary_prompt, get_semantic_analysis_prompt

console = Console()


@dataclass
class SemanticAnalysis:
    """Result of semantic analysis."""

    detection_id: int
    category: str
    is_issue: bool  # True if user reports a problem, False if confirms OK
    sentiment: str  # "problem", "positive", "neutral"
    severity: str  # "critical", "high", "medium", "low", "none"
    summary: str
    action_items: list[str]
    affected_components: list[str]
    suggested_fix: str
    response_id: str = ""  # API response ID for conversation chaining


def analyze_detection_semantically(
    detection: Detection, config: ScreenScribeConfig
) -> SemanticAnalysis | None:
    """
    Analyze a single detection using LLM.

    Args:
        detection: The detection to analyze
        config: ScreenScribe configuration

    Returns:
        SemanticAnalysis result or None if failed
    """
    if not config.get_llm_api_key():
        return None

    # Get localized prompt template
    prompt_template = get_semantic_analysis_prompt(config.language)
    prompt = prompt_template.format(
        text=detection.segment.text, context=detection.context[:500], category=detection.category
    )

    try:

        def do_llm_request() -> httpx.Response:
            with httpx.Client(timeout=60.0) as client:
                response = client.post(
                    config.llm_endpoint,
                    headers={
                        "Authorization": f"Bearer {config.get_llm_api_key()}",
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
            do_llm_request,
            max_retries=3,
            operation_name="Semantic analysis",
        )

        # Debug: check raw response
        raw_text = response.text
        if not raw_text or raw_text.strip() == "":
            console.print(f"[yellow]Empty response from API (status {response.status_code})[/]")
            return None

        try:
            result = response.json()
        except Exception as e:
            console.print(f"[yellow]Failed to parse API response: {e}. Raw: {raw_text[:300]}...[/]")
            return None
        # v1/responses format - handle both reasoning and message outputs
        content = ""
        for item in result.get("output", []):
            item_type = item.get("type", "")
            # Handle reasoning blocks (new format with thinking)
            if item_type == "reasoning":
                for part in item.get("content", []):
                    if part.get("type") == "reasoning_text":
                        # Skip reasoning, look for actual output
                        pass
            # Handle message blocks
            elif item_type == "message":
                for part in item.get("content", []):
                    if part.get("type") == "output_text":
                        content += part.get("text", "")
                    elif part.get("type") == "text":
                        content += part.get("text", "")
            # Handle direct output_text
            elif item_type == "output_text":
                content += item.get("text", "")
            # Handle direct text
            elif item_type == "text":
                content += item.get("text", "")

        if not content:
            console.print(
                f"[yellow]No content found in response. Output types: {[i.get('type') for i in result.get('output', [])]}[/]"
            )
            return None

        # Parse JSON from response
        import json
        import re

        # Strip model control tokens (e.g. <|channel|>final <|constrain|>JSON<|message|>)
        # Remove all <|...|>tag patterns
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

        json_content = json_content.strip()

        # Debug: if parsing fails, show what we got
        if not json_content:
            console.print(f"[yellow]Empty JSON after parsing. Raw content: {content[:200]}...[/]")
            return None

        try:
            data = json.loads(json_content)
        except json.JSONDecodeError as e:
            console.print(f"[yellow]JSON parse error: {e}. Content: {json_content[:200]}...[/]")
            return None

        # Extract response_id for conversation chaining with vision
        response_id = result.get("id", "")

        return SemanticAnalysis(
            detection_id=detection.segment.id,
            category=detection.category,
            is_issue=data.get("is_issue", True),
            sentiment=data.get("sentiment", "problem"),
            severity=data.get("severity", "medium"),
            summary=data.get("summary", ""),
            action_items=data.get("action_items", []),
            affected_components=data.get("affected_components", []),
            suggested_fix=data.get("suggested_fix", ""),
            response_id=response_id,
        )

    except Exception as e:
        console.print(f"[yellow]Semantic analysis failed: {e}[/]")
        return None


def analyze_detections_semantically(
    detections: list[Detection],
    config: ScreenScribeConfig,
    previous_response_id: str = "",
) -> list[SemanticAnalysis]:
    """
    Analyze all detections using LLM.

    Args:
        detections: List of detections
        config: ScreenScribe configuration
        previous_response_id: Optional response ID from previous batch for context chaining
            (reserved for future use - enables cross-video context in batch mode)

    Returns:
        List of semantic analyses
    """
    # Note: previous_response_id is currently reserved for future conversation chaining
    # across videos in batch mode. Individual detections chain via response_id field.
    _ = previous_response_id  # Acknowledge parameter for future use
    if not config.use_semantic_analysis:
        console.print("[dim]Semantic analysis disabled[/]")
        return []

    if not config.get_llm_api_key():
        console.print("[yellow]No API key - skipping semantic analysis[/]")
        return []

    results = []
    console.print(f"[blue]Running semantic analysis on {len(detections)} detections...[/]")

    for i, detection in enumerate(detections, 1):
        console.print(
            f"[dim]  [{i}/{len(detections)}] Analyzing {detection.category} @ {detection.segment.start:.1f}s...[/]"
        )
        analysis = analyze_detection_semantically(detection, config)
        if analysis:
            results.append(analysis)
            console.print(f"[green]  ✓[/] [{analysis.severity}]")
        else:
            console.print("[yellow]  ✗[/] failed")

    # Summary by severity and issue status
    issues = [a for a in results if a.is_issue]
    non_issues = [a for a in results if not a.is_issue]
    critical = sum(1 for a in issues if a.severity == "critical")
    high = sum(1 for a in issues if a.severity == "high")
    medium = sum(1 for a in issues if a.severity == "medium")
    low = sum(1 for a in issues if a.severity == "low")

    console.print(
        f"[green]Semantic analysis complete:[/] "
        f"[red]{critical} critical[/], "
        f"[yellow]{high} high[/], "
        f"[blue]{medium} medium[/], "
        f"[dim]{low} low[/]"
    )
    if non_issues:
        console.print(f"[dim]  ({len(non_issues)} positive/neutral observations filtered)[/]")

    return results


def generate_executive_summary(analyses: list[SemanticAnalysis], config: ScreenScribeConfig) -> str:
    """
    Generate executive summary of all findings.

    Args:
        analyses: List of semantic analyses
        config: ScreenScribe configuration

    Returns:
        Executive summary text
    """
    if not analyses or not config.get_llm_api_key():
        return ""

    # Prepare findings summary
    findings_list = []
    for a in analyses:
        findings_list.append(f"- [{a.severity.upper()}] {a.summary}")

    # Get localized prompt template
    prompt_template = get_executive_summary_prompt(config.language)
    prompt = prompt_template.format(findings=chr(10).join(findings_list))

    try:

        def do_summary_request() -> httpx.Response:
            with httpx.Client(timeout=60.0) as client:
                response = client.post(
                    config.llm_endpoint,
                    headers={
                        "Authorization": f"Bearer {config.get_llm_api_key()}",
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
            do_summary_request,
            max_retries=3,
            operation_name="Executive summary",
        )

        result = response.json()
        # Extract text from v1/responses output format (handle reasoning + message)
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

    except Exception as e:
        console.print(f"[yellow]Executive summary failed: {e}[/]")

    return ""
