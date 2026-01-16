"""Report generation for video review results."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .detect import Detection, format_timestamp
from .html_pro import render_html_report_pro
from .html_template import render_html_report
from .image_utils import encode_image_base64
from .transcribe import Segment

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
        lines.extend(
            [
                f"### #{i} [{detection.category.upper()}] @ {format_timestamp(detection.segment.start)}",
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
    unified_findings: list[Any] | None = None,
    executive_summary: str = "",
    errors: list[dict[str, str]] | None = None,
) -> Path:
    """Save enhanced report with unified VLM analysis as JSON.

    Args:
        detections: List of detections
        screenshots: List of (detection, screenshot_path) tuples
        video_path: Path to source video
        output_path: Path to save JSON report
        unified_findings: List of UnifiedFinding from unified VLM analysis
        executive_summary: Executive summary text
        errors: List of pipeline errors

    Returns:
        Path to saved report
    """
    # Use unified_findings for counts if available (respects deduplication)
    count_source = unified_findings if unified_findings else detections
    report: dict[str, Any] = {
        "video": str(video_path),
        "generated_at": datetime.now().isoformat(),
        "executive_summary": executive_summary,
        "summary": {
            "total": len(count_source),
            "bugs": sum(1 for d in count_source if d.category == "bug"),
            "changes": sum(1 for d in count_source if d.category == "change"),
            "ui": sum(1 for d in count_source if d.category in ("ui", "accessibility")),
        },
        "severity_breakdown": {},
        "errors": errors or [],
        "findings": [],
    }

    # Build severity breakdown from unified findings
    if unified_findings:
        for severity in ["critical", "high", "medium", "low"]:
            count = sum(1 for f in unified_findings if f.is_issue and f.severity == severity)
            report["severity_breakdown"][severity] = count

    # Build screenshot lookup by (detection_id, timestamp)
    screenshots_by_key = {(d.segment.id, d.segment.start): (d, p) for d, p in screenshots}

    # If unified_findings provided, use them as source of truth (respects deduplication)
    if unified_findings:
        for uf in unified_findings:
            # Get detection and screenshot for this finding
            key = (uf.detection_id, uf.timestamp)
            detection, screenshot_path = screenshots_by_key.get(key, (None, None))

            if detection is None:
                # Fallback: find by detection_id only (shouldn't happen normally)
                for d, p in screenshots:
                    if d.segment.id == uf.detection_id:
                        detection, screenshot_path = d, p
                        break

            if detection is None:
                continue  # Skip if no matching detection found

            finding = {
                "id": detection.segment.id,
                "category": detection.category,
                "timestamp_start": detection.segment.start,
                "timestamp_end": detection.segment.end,
                "timestamp_formatted": format_timestamp(detection.segment.start),
                "text": detection.segment.text,
                "context": detection.context,
                "keywords": detection.keywords_found,
                "screenshot": str(screenshot_path) if screenshot_path else None,
                # Combined analysis (semantic + vision in one)
                "unified_analysis": {
                    # Semantic fields
                    "is_issue": uf.is_issue,
                    "sentiment": uf.sentiment,
                    "severity": uf.severity,
                    "summary": uf.summary,
                    "action_items": uf.action_items,
                    "affected_components": uf.affected_components,
                    "suggested_fix": uf.suggested_fix,
                    # Vision fields
                    "ui_elements": uf.ui_elements,
                    "issues_detected": uf.issues_detected,
                    "accessibility_notes": uf.accessibility_notes,
                    "design_feedback": uf.design_feedback,
                    "technical_observations": uf.technical_observations,
                    # API tracking
                    "response_id": uf.response_id or None,
                },
            }
            report["findings"].append(finding)
    else:
        # Fallback: no unified analysis, just use screenshots/detections
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
    unified_findings: list[Any] | None = None,
    executive_summary: str = "",
    visual_summary: str = "",
    errors: list[dict[str, str]] | None = None,
    transcript: str = "",
) -> Path:
    """Save enhanced report with unified VLM analysis as Markdown.

    Format optimized for AI consumption:
    - Transcript at the top for full context
    - Sorted by severity (critical first)
    - Consolidated action items at top
    - No emoji clutter
    - Non-issues separated at end

    Args:
        detections: List of detections
        screenshots: List of (detection, screenshot_path) tuples
        video_path: Path to source video
        output_path: Path to save Markdown report
        unified_findings: List of UnifiedFinding from unified VLM analysis
        executive_summary: Executive summary text
        visual_summary: Visual summary text
        errors: List of pipeline errors
        transcript: Full transcript text (embedded at start for AI context)

    Returns:
        Path to saved report
    """
    findings_by_id = {f.detection_id: f for f in (unified_findings or [])}

    # Separate issues from non-issues and sort by severity
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "none": 4}
    issues: list[tuple[Detection, Path]] = []
    non_issues: list[tuple[Detection, Path]] = []

    for detection, screenshot_path in screenshots:
        uf = findings_by_id.get(detection.segment.id)
        if uf and not uf.is_issue:
            non_issues.append((detection, screenshot_path))
        else:
            issues.append((detection, screenshot_path))

    # Sort issues by severity
    def get_severity_rank(item: tuple[Detection, Path]) -> int:
        detection, _ = item
        uf = findings_by_id.get(detection.segment.id)
        if uf:
            return severity_order.get(uf.severity, 4)
        return 4

    issues.sort(key=get_severity_rank)

    # Collect all action items upfront
    all_action_items: list[tuple[str, str, list[str]]] = []  # (severity, summary, items)
    for detection, _ in issues:
        uf = findings_by_id.get(detection.segment.id)
        if uf and uf.action_items:
            all_action_items.append((uf.severity, uf.summary, uf.action_items))

    # Build components index: component -> [(finding_num, severity)]
    components_index: dict[str, list[tuple[int, str]]] = {}
    for i, (detection, _) in enumerate(issues, 1):
        uf = findings_by_id.get(detection.segment.id)
        if uf and uf.affected_components:
            severity = uf.severity if uf.is_issue else "ok"
            for component in uf.affected_components:
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

    if unified_findings:
        issues_only = [f for f in unified_findings if f.is_issue]
        crit = sum(1 for f in issues_only if f.severity == "critical")
        high = sum(1 for f in issues_only if f.severity == "high")
        med = sum(1 for f in issues_only if f.severity == "medium")
        low = sum(1 for f in issues_only if f.severity == "low")
        lines.append(
            f"**Stats:** {len(issues)} issues ({crit} critical, {high} high, {med} medium, {low} low) "
            f"| {bug_count} bugs, {change_count} changes, {ui_count} UI "
            f"| {len(non_issues)} non-issues filtered"
        )
    else:
        lines.append(
            f"**Stats:** {len(detections)} findings | {bug_count} bugs, {change_count} changes, {ui_count} UI"
        )
    lines.append("")

    # Transcript (at the top for AI context)
    if transcript:
        lines.extend(["## Transcript", "", transcript, ""])

    # Executive Summary
    if executive_summary:
        lines.extend(["## Summary", "", executive_summary, ""])

    # Consolidated Action Items (critical and high only for quick scan)
    if all_action_items:
        critical_high = [
            (s, summ, items) for s, summ, items in all_action_items if s in ("critical", "high")
        ]
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
            max_sev = max((severity_weight.get(sev, 0) for _, sev in findings), default=0)
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
        uf = findings_by_id.get(detection.segment.id)

        severity = (uf.severity if uf else "medium").upper()
        category = detection.category.upper()

        lines.append(
            f"### [{severity}] #{i} {category} @ {format_timestamp(detection.segment.start)}"
        )
        lines.append("")
        lines.append(f"> {detection.segment.text}")
        lines.append("")

        if uf:
            lines.append(f"**Summary:** {uf.summary}")
            if uf.affected_components:
                lines.append(f"**Components:** {', '.join(uf.affected_components)}")
            if uf.suggested_fix:
                lines.append(f"**Fix:** {uf.suggested_fix}")
            lines.append("")

            # Visual issues from unified analysis
            if uf.issues_detected:
                lines.append("**Visual issues:** " + "; ".join(uf.issues_detected))
                lines.append("")
        else:
            lines.append(f"**Summary:** {detection.segment.text}")
            lines.append("")

        lines.append(f"Screenshot: {screenshot_path.name}")
        lines.extend(["", "---", ""])

    # Non-issues (at the end, collapsed)
    if non_issues:
        lines.extend(
            [
                "## Non-Issues (Confirmed OK)",
                "",
                "These were flagged by detection but user confirmed they work correctly:",
                "",
            ]
        )
        for detection, _ in non_issues:
            uf = findings_by_id.get(detection.segment.id)
            summary = uf.summary if uf else detection.segment.text
            lines.append(f"- {format_timestamp(detection.segment.start)}: {summary}")
        lines.append("")

    lines.extend(
        [
            "---",
            "*Generated by ScreenScribe*",
        ]
    )

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    console.print(f"[green]Enhanced Markdown report saved:[/] {output_path}")
    return output_path


def save_html_report(
    detections: list[Detection],
    screenshots: list[tuple[Detection, Path]],
    video_path: Path,
    output_path: Path,
    unified_findings: list[Any] | None = None,
    executive_summary: str = "",
    errors: list[dict[str, str]] | None = None,
) -> Path:
    """Save report as interactive HTML with embedded screenshots.

    Args:
        detections: List of detections
        screenshots: List of (detection, screenshot_path) tuples
        video_path: Path to source video
        output_path: Path to save HTML report
        unified_findings: List of UnifiedFinding from unified VLM analysis
        executive_summary: Executive summary text
        errors: List of pipeline errors

    Returns:
        Path to saved report
    """
    # Build findings lookup from unified analysis
    findings_by_id = {f.detection_id: f for f in (unified_findings or [])}

    # Build findings data for template
    findings_data: list[dict[str, Any]] = []
    for detection, screenshot_path in screenshots:
        uf = findings_by_id.get(detection.segment.id)

        # Encode screenshot as base64 if exists
        screenshot_b64 = ""
        if screenshot_path.exists():
            screenshot_b64 = encode_image_base64(screenshot_path)

        finding: dict[str, Any] = {
            "id": detection.segment.id,
            "category": detection.category,
            "timestamp": format_timestamp(detection.segment.start),
            "timestamp_seconds": detection.segment.start,
            "text": detection.segment.text,
            "context": detection.context,
            "keywords": detection.keywords_found,
            "screenshot_b64": screenshot_b64,
            "thumbnail_b64": screenshot_b64,  # Use same image for thumbnail
        }

        # Add unified analysis fields if available
        if uf:
            finding.update(
                {
                    "is_issue": uf.is_issue,
                    "severity": uf.severity,
                    "summary": uf.summary,
                    "action_items": uf.action_items,
                    "affected_components": uf.affected_components,
                    "suggested_fix": uf.suggested_fix,
                    "ui_elements": uf.ui_elements,
                    "issues_detected": uf.issues_detected,
                    "accessibility_notes": uf.accessibility_notes,
                    "design_feedback": uf.design_feedback,
                }
            )
        else:
            # Fallback values if no UnifiedFinding
            finding.update(
                {
                    "is_issue": True,
                    "severity": "medium",
                    "summary": detection.segment.text,
                    "action_items": [],
                    "affected_components": [],
                    "suggested_fix": "",
                    "ui_elements": [],
                    "issues_detected": [],
                    "accessibility_notes": [],
                    "design_feedback": "",
                }
            )

        findings_data.append(finding)

    # Sort findings by severity (critical=0, high=1, medium=2, low=3)
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "none": 4}
    findings_data.sort(key=lambda f: severity_order.get(f.get("severity", "medium"), 4))

    # Render HTML using template
    html_content = render_html_report(
        video_name=video_path.name,
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
        findings=findings_data,
        executive_summary=executive_summary,
        errors=errors or [],
    )

    # Write HTML file
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    console.print(f"[green]HTML report saved:[/] {output_path}")
    return output_path


def save_html_report_pro(
    detections: list[Detection],
    screenshots: list[tuple[Detection, Path]],
    video_path: Path,
    output_path: Path,
    segments: list[Segment] | None = None,
    unified_findings: list[Any] | None = None,
    executive_summary: str = "",
    errors: list[dict[str, str]] | None = None,
    embed_video: bool = False,
) -> Path:
    """Save report as Pro HTML with video player and synchronized subtitles.

    Args:
        detections: List of detections
        screenshots: List of (detection, screenshot_path) tuples
        video_path: Path to source video
        output_path: Path to save HTML report
        segments: List of transcript segments for subtitle sync
        unified_findings: List of UnifiedFinding from unified VLM analysis
        executive_summary: Executive summary text
        errors: List of pipeline errors
        embed_video: Whether to embed video as base64 (for smaller files)

    Returns:
        Path to saved report
    """
    # Build findings lookup from unified analysis
    findings_by_id = {f.detection_id: f for f in (unified_findings or [])}

    # Build findings data for template
    findings_data: list[dict[str, Any]] = []
    for detection, screenshot_path in screenshots:
        uf = findings_by_id.get(detection.segment.id)

        # Encode screenshot as base64 if exists
        screenshot_b64 = ""
        if screenshot_path.exists():
            screenshot_b64 = encode_image_base64(screenshot_path)

        finding: dict[str, Any] = {
            "id": detection.segment.id,
            "category": detection.category,
            "timestamp_formatted": format_timestamp(detection.segment.start),
            "timestamp": detection.segment.start,
            "text": detection.segment.text,
            "context": detection.context,
            "keywords": detection.keywords_found,
            # Base64 for HTML display, file path for JSON export
            "screenshot": f"data:image/png;base64,{screenshot_b64}" if screenshot_b64 else "",
            "screenshot_path": str(screenshot_path) if screenshot_path.exists() else "",
        }

        # Add unified analysis fields if available
        if uf:
            finding["unified_analysis"] = {
                "is_issue": uf.is_issue,
                "severity": uf.severity,
                "summary": uf.summary,
                "action_items": uf.action_items,
                "affected_components": uf.affected_components,
                "suggested_fix": uf.suggested_fix,
                "ui_elements": uf.ui_elements,
                "issues_detected": uf.issues_detected,
                "accessibility_notes": uf.accessibility_notes,
                "design_feedback": uf.design_feedback,
            }
        else:
            # Fallback values if no UnifiedFinding
            finding["unified_analysis"] = {
                "is_issue": True,
                "severity": "medium",
                "summary": detection.segment.text,
                "action_items": [],
                "affected_components": [],
                "suggested_fix": "",
                "ui_elements": [],
                "issues_detected": [],
                "accessibility_notes": [],
                "design_feedback": "",
            }

        findings_data.append(finding)

    # Sort findings by severity (critical=0, high=1, medium=2, low=3)
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "none": 4}
    findings_data.sort(
        key=lambda f: severity_order.get(f.get("unified_analysis", {}).get("severity", "medium"), 4)
    )

    # Render HTML using Pro template
    html_content = render_html_report_pro(
        video_name=video_path.name,
        video_path=str(video_path),
        generated_at=datetime.now().isoformat(),
        executive_summary=executive_summary,
        findings=findings_data,
        segments=segments,
        errors=errors or [],
        embed_video=embed_video,
    )

    # Write HTML file
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    console.print(f"[green]HTML Pro report saved:[/] {output_path}")
    return output_path
