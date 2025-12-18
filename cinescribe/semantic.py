"""Semantic analysis using LibraxisAI LLM models."""

from dataclasses import dataclass

import httpx
from rich.console import Console

from .config import CinescribeConfig
from .detect import Detection

console = Console()


@dataclass
class SemanticAnalysis:
    """Result of semantic analysis."""

    detection_id: int
    category: str
    severity: str  # "critical", "high", "medium", "low"
    summary: str
    action_items: list[str]
    affected_components: list[str]
    suggested_fix: str


ANALYSIS_PROMPT = """Jesteś ekspertem UX/UI i programistą analizującym feedback z nagrania screencast.

Przeanalizuj poniższy fragment transkrypcji, gdzie użytkownik opisuje problem lub zmianę w aplikacji.

Fragment:
{text}

Kontekst (otaczające wypowiedzi):
{context}

Kategoria wykryta automatycznie: {category}

Odpowiedz w formacie JSON:
{{
    "severity": "critical|high|medium|low",
    "summary": "Krótkie podsumowanie problemu (1-2 zdania)",
    "action_items": ["Lista konkretnych zadań do wykonania"],
    "affected_components": ["Lista komponentów UI/funkcji których dotyczy"],
    "suggested_fix": "Sugerowane rozwiązanie techniczne"
}}

Odpowiadaj tylko JSON, bez dodatkowego tekstu."""


def analyze_detection_semantically(
    detection: Detection, config: CinescribeConfig
) -> SemanticAnalysis | None:
    """
    Analyze a single detection using LLM.

    Args:
        detection: The detection to analyze
        config: Cinescribe configuration

    Returns:
        SemanticAnalysis result or None if failed
    """
    if not config.api_key:
        return None

    prompt = ANALYSIS_PROMPT.format(
        text=detection.segment.text, context=detection.context[:500], category=detection.category
    )

    try:
        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                config.llm_endpoint,
                headers={
                    "Authorization": f"Bearer {config.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": config.llm_model,
                    "input": [
                        {"role": "user", "content": [{"type": "input_text", "text": prompt}]}
                    ],
                },
            )

        if response.status_code != 200:
            console.print(
                f"[yellow]LLM API error: {response.status_code} - {response.text[:200]}[/]"
            )
            return None

        result = response.json()
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

        # Handle potential markdown code blocks
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        data = json.loads(content.strip())

        return SemanticAnalysis(
            detection_id=detection.segment.id,
            category=detection.category,
            severity=data.get("severity", "medium"),
            summary=data.get("summary", ""),
            action_items=data.get("action_items", []),
            affected_components=data.get("affected_components", []),
            suggested_fix=data.get("suggested_fix", ""),
        )

    except Exception as e:
        console.print(f"[yellow]Semantic analysis failed: {e}[/]")
        return None


def analyze_detections_semantically(
    detections: list[Detection], config: CinescribeConfig
) -> list[SemanticAnalysis]:
    """
    Analyze all detections using LLM.

    Args:
        detections: List of detections
        config: Cinescribe configuration

    Returns:
        List of semantic analyses
    """
    if not config.use_semantic_analysis:
        console.print("[dim]Semantic analysis disabled[/]")
        return []

    if not config.api_key:
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

    # Summary by severity
    critical = sum(1 for a in results if a.severity == "critical")
    high = sum(1 for a in results if a.severity == "high")
    medium = sum(1 for a in results if a.severity == "medium")
    low = sum(1 for a in results if a.severity == "low")

    console.print(
        f"[green]Semantic analysis complete:[/] "
        f"[red]{critical} critical[/], "
        f"[yellow]{high} high[/], "
        f"[blue]{medium} medium[/], "
        f"[dim]{low} low[/]"
    )

    return results


def generate_executive_summary(analyses: list[SemanticAnalysis], config: CinescribeConfig) -> str:
    """
    Generate executive summary of all findings.

    Args:
        analyses: List of semantic analyses
        config: Cinescribe configuration

    Returns:
        Executive summary text
    """
    if not analyses or not config.api_key:
        return ""

    # Prepare findings summary
    findings = []
    for a in analyses:
        findings.append(f"- [{a.severity.upper()}] {a.summary}")

    prompt = f"""Jesteś product managerem przygotowującym raport z przeglądu UX.

Na podstawie poniższych znalezisk, przygotuj krótkie podsumowanie wykonawcze (executive summary) dla zespołu developerskiego.

Znaleziska:
{chr(10).join(findings)}

Napisz podsumowanie w 3-5 zdaniach, skupiając się na:
1. Najważniejszych problemach do naprawienia
2. Ogólnym stanie UX aplikacji
3. Rekomendacji priorytetów

Odpowiadaj po polsku, zwięźle i konkretnie."""

    try:
        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                config.llm_endpoint,
                headers={
                    "Authorization": f"Bearer {config.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": config.llm_model,
                    "input": [
                        {"role": "user", "content": [{"type": "input_text", "text": prompt}]}
                    ],
                },
            )

        if response.status_code == 200:
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
