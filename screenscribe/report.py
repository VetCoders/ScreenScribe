"""Report generation for video review results."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

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
    report: dict[str, Any] = {
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
    semantic_analyses: list[Any] | None = None,
    vision_analyses: list[Any] | None = None,
    executive_summary: str = "",
    errors: list[dict[str, str]] | None = None,
) -> Path:
    """Save enhanced report with AI analyses as JSON."""
    report: dict[str, Any] = {
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
                "is_issue": sem.is_issue,
                "sentiment": sem.sentiment,
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
    semantic_analyses: list[Any] | None = None,
    vision_analyses: list[Any] | None = None,
    executive_summary: str = "",
    visual_summary: str = "",
    errors: list[dict[str, str]] | None = None,
) -> Path:
    """Save enhanced report with AI analyses as Markdown.

    Format optimized for AI consumption:
    - Sorted by severity (critical first)
    - Consolidated action items at top
    - No emoji clutter
    - Non-issues separated at end
    """
    semantic_by_id = {a.detection_id: a for a in (semantic_analyses or [])}
    vision_by_path = {str(v.screenshot_path): v for v in (vision_analyses or [])}

    # Separate issues from non-issues and sort by severity
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "none": 4}
    issues: list[tuple[Detection, Path]] = []
    non_issues: list[tuple[Detection, Path]] = []

    for detection, screenshot_path in screenshots:
        sem = semantic_by_id.get(detection.segment.id)
        if sem and not sem.is_issue:
            non_issues.append((detection, screenshot_path))
        else:
            issues.append((detection, screenshot_path))

    # Sort issues by severity
    def get_severity_rank(item: tuple[Detection, Path]) -> int:
        detection, _ = item
        sem = semantic_by_id.get(detection.segment.id)
        if sem:
            return severity_order.get(sem.severity, 4)
        return 4

    issues.sort(key=get_severity_rank)

    # Collect all action items upfront
    all_action_items: list[tuple[str, str, list[str]]] = []  # (severity, summary, items)
    for detection, _ in issues:
        sem = semantic_by_id.get(detection.segment.id)
        if sem and sem.action_items:
            all_action_items.append((sem.severity, sem.summary, sem.action_items))

    # Build components index: component -> [(finding_num, severity)]
    components_index: dict[str, list[tuple[int, str]]] = {}
    for i, (detection, _) in enumerate(issues, 1):
        sem = semantic_by_id.get(detection.segment.id)
        if sem and sem.affected_components:
            severity = sem.severity if sem.is_issue else "ok"
            for component in sem.affected_components:
                if component not in components_index:
                    components_index[component] = []
                components_index[component].append((i, severity))

    # Build report
    lines = [
        "# Video Review Report",
        "",
        f"Video: `{video_path.name}`",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
    ]

    # Quick stats - one line
    bug_count = sum(1 for d in detections if d.category == "bug")
    change_count = sum(1 for d in detections if d.category == "change")
    ui_count = sum(1 for d in detections if d.category == "ui")

    if semantic_analyses:
        issues_only = [a for a in semantic_analyses if a.is_issue]
        crit = sum(1 for a in issues_only if a.severity == "critical")
        high = sum(1 for a in issues_only if a.severity == "high")
        med = sum(1 for a in issues_only if a.severity == "medium")
        low = sum(1 for a in issues_only if a.severity == "low")
        lines.append(
            f"**Stats:** {len(issues)} issues ({crit} critical, {high} high, {med} medium, {low} low) "
            f"| {bug_count} bugs, {change_count} changes, {ui_count} UI "
            f"| {len(non_issues)} non-issues filtered"
        )
    else:
        lines.append(f"**Stats:** {len(detections)} findings | {bug_count} bugs, {change_count} changes, {ui_count} UI")
    lines.append("")

    # Executive Summary
    if executive_summary:
        lines.extend(["## Summary", "", executive_summary, ""])

    # Consolidated Action Items (critical and high only for quick scan)
    if all_action_items:
        critical_high = [(s, summ, items) for s, summ, items in all_action_items if s in ("critical", "high")]
        if critical_high:
            lines.extend(["## Action Items (Critical/High)", ""])
            for severity, summary, items in critical_high:
                lines.append(f"**[{severity.upper()}]** {summary}")
                for item in items:
                    lines.append(f"- [ ] {item}")
                lines.append("")

    # Components Index - shows which components have issues
    if components_index:
        # Sort by number of issues (most affected first), then by max severity
        severity_weight = {"critical": 4, "high": 3, "medium": 2, "low": 1, "ok": 0, "none": 0}

        def component_score(item: tuple[str, list[tuple[int, str]]]) -> tuple[int, int]:
            _, findings = item
            max_sev = max(severity_weight.get(sev, 0) for _, sev in findings)
            return (-len(findings), -max_sev)

        sorted_components = sorted(components_index.items(), key=component_score)

        lines.extend(["## Components Affected", ""])
        for component, findings in sorted_components:
            finding_nums = [f"#{num}" for num, _ in findings]
            severities = [sev for _, sev in findings]
            sev_counts = []
            for sev in ["critical", "high", "medium", "low"]:
                count = severities.count(sev)
                if count:
                    sev_counts.append(f"{count} {sev}")
            sev_summary = f" ({', '.join(sev_counts)})" if sev_counts else ""
            lines.append(f"- **{component}**: {', '.join(finding_nums)}{sev_summary}")
        lines.append("")

    # Errors section
    if errors:
        lines.extend(["## Errors", ""])
        for error in errors:
            lines.append(f"- {error.get('stage', 'unknown')}: {error.get('message', '')}")
        lines.append("")

    # Visual summary
    if visual_summary:
        lines.extend(["## Visual Summary", "", visual_summary, ""])

    # Issues (sorted by severity)
    lines.extend(["## Issues", ""])

    for i, (detection, screenshot_path) in enumerate(issues, 1):
        sem = semantic_by_id.get(detection.segment.id)
        vis = vision_by_path.get(str(screenshot_path))

        severity = sem.severity.upper() if sem else "UNKNOWN"
        category = detection.category.upper()

        lines.append(f"### [{severity}] #{i} {category} @ {format_timestamp(detection.segment.start)}")
        lines.append("")
        lines.append(f"> {detection.segment.text}")
        lines.append("")

        if sem:
            lines.append(f"**Summary:** {sem.summary}")
            if sem.affected_components:
                lines.append(f"**Components:** {', '.join(sem.affected_components)}")
            if sem.suggested_fix:
                lines.append(f"**Fix:** {sem.suggested_fix}")
            lines.append("")

        if vis and vis.issues_detected:
            lines.append("**Visual issues:** " + "; ".join(vis.issues_detected))
            lines.append("")

        lines.append(f"Screenshot: {screenshot_path.name}")
        lines.extend(["", "---", ""])

    # Non-issues (at the end, collapsed)
    if non_issues:
        lines.extend([
            "## Non-Issues (Confirmed OK)",
            "",
            "These were flagged by detection but user confirmed they work correctly:",
            "",
        ])
        for detection, _ in non_issues:
            sem = semantic_by_id.get(detection.segment.id)
            summary = sem.summary if sem else detection.segment.text
            lines.append(f"- {format_timestamp(detection.segment.start)}: {summary}")
        lines.append("")

    lines.extend([
        "---",
        "*Generated by ScreenScribe*",
    ])

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    console.print(f"[green]Enhanced Markdown report saved:[/] {output_path}")
    return output_path
