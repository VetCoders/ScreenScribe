"""Report generation for video review results."""

import json
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .detect import Detection, format_timestamp

console = Console()


def print_report(
    detections: list[Detection], screenshots: list[tuple[Detection, Path]], video_path: Path
) -> None:
    """Print a rich console report of findings."""
    console.print()
    console.print(
        Panel(
            f"[bold]Video Review Report[/]\n{video_path.name}",
            subtitle=f"Generated {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        )
    )
    console.print()

    # Summary table
    table = Table(title="Findings Summary")
    table.add_column("Category", style="cyan")
    table.add_column("Count", justify="right")

    bugs = sum(1 for d in detections if d.category == "bug")
    changes = sum(1 for d in detections if d.category == "change")
    ui = sum(1 for d in detections if d.category == "ui")

    table.add_row("Bugs", str(bugs))
    table.add_row("Change Requests", str(changes))
    table.add_row("UI Issues", str(ui))
    table.add_row("[bold]Total[/]", f"[bold]{len(detections)}[/]")

    console.print(table)
    console.print()

    # Detailed findings
    for i, (detection, screenshot_path) in enumerate(screenshots, 1):
        category_color = {"bug": "red", "change": "yellow", "ui": "blue"}.get(
            detection.category, "white"
        )

        console.print(
            Panel(
                f"[bold]{detection.segment.text}[/]\n\n"
                f"[dim]Context: {detection.context[:200]}...[/]\n\n"
                f"[dim]Screenshot: {screenshot_path}[/]",
                title=f"[{category_color}]#{i} {detection.category.upper()}[/] "
                f"@ {format_timestamp(detection.segment.start)}",
                border_style=category_color,
            )
        )
        console.print()


def save_json_report(
    detections: list[Detection],
    screenshots: list[tuple[Detection, Path]],
    video_path: Path,
    output_path: Path,
) -> Path:
    """Save report as JSON for further processing."""
    report = {
        "video": str(video_path),
        "generated_at": datetime.now().isoformat(),
        "summary": {
            "total": len(detections),
            "bugs": sum(1 for d in detections if d.category == "bug"),
            "changes": sum(1 for d in detections if d.category == "change"),
            "ui": sum(1 for d in detections if d.category == "ui"),
        },
        "findings": [],
    }

    for detection, screenshot_path in screenshots:
        report["findings"].append(
            {
                "id": detection.segment.id,
                "category": detection.category,
                "timestamp_start": detection.segment.start,
                "timestamp_end": detection.segment.end,
                "timestamp_formatted": format_timestamp(detection.segment.start),
                "text": detection.segment.text,
                "context": detection.context,
                "keywords": detection.keywords_found,
                "screenshot": str(screenshot_path),
            }
        )

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    console.print(f"[green]Report saved:[/] {output_path}")
    return output_path


def save_markdown_report(
    detections: list[Detection],
    screenshots: list[tuple[Detection, Path]],
    video_path: Path,
    output_path: Path,
) -> Path:
    """Save report as Markdown for documentation."""
    lines = [
        "# Video Review Report",
        "",
        f"**Video:** `{video_path.name}`",
        f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "## Summary",
        "",
        "| Category | Count |",
        "|----------|-------|",
        f"| Bugs | {sum(1 for d in detections if d.category == 'bug')} |",
        f"| Change Requests | {sum(1 for d in detections if d.category == 'change')} |",
        f"| UI Issues | {sum(1 for d in detections if d.category == 'ui')} |",
        f"| **Total** | **{len(detections)}** |",
        "",
        "## Findings",
        "",
    ]

    for i, (detection, screenshot_path) in enumerate(screenshots, 1):
        emoji = {"bug": "🐛", "change": "🔄", "ui": "🎨"}.get(detection.category, "📝")
        lines.extend(
            [
                f"### {emoji} #{i} {detection.category.upper()} @ {format_timestamp(detection.segment.start)}",
                "",
                f"> {detection.segment.text}",
                "",
                f"**Keywords:** {', '.join(detection.keywords_found)}",
                "",
                f"**Context:** {detection.context[:300]}...",
                "",
                f"![Screenshot]({screenshot_path.name})",
                "",
                "---",
                "",
            ]
        )

    lines.extend(
        [
            "",
            "---",
            "*Made with (งಠ_ಠ)ง by ⌜ScreenScribe⌟ © 2025 — Maciej & Monika + Klaudiusz (AI) + Mikserka (AI)*",
        ]
    )

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    console.print(f"[green]Markdown report saved:[/] {output_path}")
    return output_path


def save_enhanced_json_report(
    detections: list[Detection],
    screenshots: list[tuple[Detection, Path]],
    video_path: Path,
    output_path: Path,
    semantic_analyses: list | None = None,
    vision_analyses: list | None = None,
    executive_summary: str = "",
    errors: list[dict] | None = None,
) -> Path:
    """Save enhanced report with AI analyses as JSON."""
    report = {
        "video": str(video_path),
        "generated_at": datetime.now().isoformat(),
        "executive_summary": executive_summary,
        "summary": {
            "total": len(detections),
            "bugs": sum(1 for d in detections if d.category == "bug"),
            "changes": sum(1 for d in detections if d.category == "change"),
            "ui": sum(1 for d in detections if d.category == "ui"),
        },
        "severity_breakdown": {},
        "errors": errors or [],
        "findings": [],
    }

    # Build severity breakdown from semantic analyses
    if semantic_analyses:
        for severity in ["critical", "high", "medium", "low"]:
            count = sum(1 for a in semantic_analyses if a.severity == severity)
            report["severity_breakdown"][severity] = count

    # Build findings with AI enhancements
    semantic_by_id = {a.detection_id: a for a in (semantic_analyses or [])}
    vision_by_path = {str(v.screenshot_path): v for v in (vision_analyses or [])}

    for detection, screenshot_path in screenshots:
        finding = {
            "id": detection.segment.id,
            "category": detection.category,
            "timestamp_start": detection.segment.start,
            "timestamp_end": detection.segment.end,
            "timestamp_formatted": format_timestamp(detection.segment.start),
            "text": detection.segment.text,
            "context": detection.context,
            "keywords": detection.keywords_found,
            "screenshot": str(screenshot_path),
        }

        # Add semantic analysis if available
        if detection.segment.id in semantic_by_id:
            sem = semantic_by_id[detection.segment.id]
            finding["semantic_analysis"] = {
                "severity": sem.severity,
                "summary": sem.summary,
                "action_items": sem.action_items,
                "affected_components": sem.affected_components,
                "suggested_fix": sem.suggested_fix,
            }

        # Add vision analysis if available
        if str(screenshot_path) in vision_by_path:
            vis = vision_by_path[str(screenshot_path)]
            finding["vision_analysis"] = {
                "ui_elements": vis.ui_elements,
                "issues_detected": vis.issues_detected,
                "accessibility_notes": vis.accessibility_notes,
                "design_feedback": vis.design_feedback,
                "technical_observations": vis.technical_observations,
            }

        report["findings"].append(finding)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    console.print(f"[green]Enhanced report saved:[/] {output_path}")
    return output_path


def save_enhanced_markdown_report(
    detections: list[Detection],
    screenshots: list[tuple[Detection, Path]],
    video_path: Path,
    output_path: Path,
    semantic_analyses: list | None = None,
    vision_analyses: list | None = None,
    executive_summary: str = "",
    visual_summary: str = "",
    errors: list[dict] | None = None,
) -> Path:
    """Save enhanced report with AI analyses as Markdown."""
    lines = [
        "# Video Review Report",
        "",
        f"**Video:** `{video_path.name}`",
        f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "**Powered by:** LibraxisAI",
        "",
    ]

    # Executive Summary
    if executive_summary:
        lines.extend(
            [
                "## Executive Summary",
                "",
                executive_summary,
                "",
            ]
        )

    # Summary table
    lines.extend(
        [
            "## Summary",
            "",
            "| Category | Count |",
            "|----------|-------|",
            f"| Bugs | {sum(1 for d in detections if d.category == 'bug')} |",
            f"| Change Requests | {sum(1 for d in detections if d.category == 'change')} |",
            f"| UI Issues | {sum(1 for d in detections if d.category == 'ui')} |",
            f"| **Total** | **{len(detections)}** |",
            "",
        ]
    )

    # Severity breakdown
    if semantic_analyses:
        lines.extend(
            [
                "### By Severity",
                "",
                "| Severity | Count |",
                "|----------|-------|",
            ]
        )
        for severity in ["critical", "high", "medium", "low"]:
            count = sum(1 for a in semantic_analyses if a.severity == severity)
            emoji = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}.get(
                severity, "⚪"
            )
            lines.append(f"| {emoji} {severity.capitalize()} | {count} |")
        lines.append("")

    # Visual summary
    if visual_summary:
        lines.extend([visual_summary, ""])

    # Errors section (if any)
    if errors:
        lines.extend(
            [
                "## ⚠️ Processing Errors",
                "",
                "Some analysis steps encountered errors but processing continued:",
                "",
            ]
        )
        for error in errors:
            stage = error.get("stage", "unknown")
            message = error.get("message", "Unknown error")
            lines.append(f"- **{stage}:** {message}")
        lines.extend(["", "---", ""])

    # Detailed findings
    lines.extend(["## Findings", ""])

    semantic_by_id = {a.detection_id: a for a in (semantic_analyses or [])}
    vision_by_path = {str(v.screenshot_path): v for v in (vision_analyses or [])}

    for i, (detection, screenshot_path) in enumerate(screenshots, 1):
        emoji = {"bug": "🐛", "change": "🔄", "ui": "🎨"}.get(detection.category, "📝")

        # Get severity if available
        severity_badge = ""
        if detection.segment.id in semantic_by_id:
            sem = semantic_by_id[detection.segment.id]
            sev_emoji = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}.get(
                sem.severity, ""
            )
            severity_badge = f" {sev_emoji} [{sem.severity.upper()}]"

        lines.extend(
            [
                f"### {emoji} #{i} {detection.category.upper()}{severity_badge} @ {format_timestamp(detection.segment.start)}",
                "",
                f"> {detection.segment.text}",
                "",
            ]
        )

        # Semantic analysis
        if detection.segment.id in semantic_by_id:
            sem = semantic_by_id[detection.segment.id]
            lines.extend(
                [
                    "**AI Analysis:**",
                    f"- **Summary:** {sem.summary}",
                    f"- **Affected:** {', '.join(sem.affected_components) if sem.affected_components else 'N/A'}",
                    f"- **Fix:** {sem.suggested_fix}",
                    "",
                ]
            )
            if sem.action_items:
                lines.append("**Action Items:**")
                for item in sem.action_items:
                    lines.append(f"- [ ] {item}")
                lines.append("")

        # Vision analysis
        if str(screenshot_path) in vision_by_path:
            vis = vision_by_path[str(screenshot_path)]
            if vis.issues_detected:
                lines.extend(
                    [
                        "**Visual Issues:**",
                    ]
                )
                for issue in vis.issues_detected:
                    lines.append(f"- {issue}")
                lines.append("")
            if vis.design_feedback:
                lines.append(f"**Design Feedback:** {vis.design_feedback}")
                lines.append("")

        lines.extend(
            [
                f"![Screenshot]({screenshot_path.name})",
                "",
                "---",
                "",
            ]
        )

    lines.extend(
        [
            "",
            "---",
            "*Made with (งಠ_ಠ)ง by ⌜ScreenScribe⌟ © 2025 — Maciej & Monika + Klaudiusz (AI) + Mikserka (AI)*",
        ]
    )

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    console.print(f"[green]Enhanced Markdown report saved:[/] {output_path}")
    return output_path
