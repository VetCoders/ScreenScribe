"""HTML Pro report renderer.

Main rendering functions for the ScreenScribe Pro HTML report.
"""

from __future__ import annotations

import base64
import html
import json
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .assets import load_css, load_html_template, load_js_review_app, load_js_video_player
from .data import generate_report_id

if TYPE_CHECKING:
    from ..transcribe import Segment


def _render_stats(findings: list[dict[str, Any]]) -> str:
    """Render severity statistics cards."""
    severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}

    for f in findings:
        unified = f.get("unified_analysis", {})
        if unified.get("is_issue", True):
            severity = unified.get("severity", "medium")
            if severity in severity_counts:
                severity_counts[severity] += 1

    total = sum(severity_counts.values())

    return f"""
    <div class="stats">
        <div class="stat-card">
            <div class="label" data-i18n="total">Razem</div>
            <div class="value">{total}</div>
        </div>
        <div class="stat-card critical">
            <div class="label" data-i18n="critical">Krytyczne</div>
            <div class="value">{severity_counts["critical"]}</div>
        </div>
        <div class="stat-card high">
            <div class="label" data-i18n="high">Wysokie</div>
            <div class="value">{severity_counts["high"]}</div>
        </div>
        <div class="stat-card medium">
            <div class="label" data-i18n="medium">Srednie</div>
            <div class="value">{severity_counts["medium"]}</div>
        </div>
        <div class="stat-card low">
            <div class="label" data-i18n="low">Niskie</div>
            <div class="value">{severity_counts["low"]}</div>
        </div>
    </div>
    """


def _render_errors(errors: list[dict[str, str]]) -> str:
    """Render pipeline errors section."""
    if not errors:
        return ""

    lines = [
        '<div class="errors-section">',
        '<h3 data-i18n="pipelineErrors">Bledy Pipeline</h3>',
        "<ul>",
    ]

    for error in errors:
        stage = html.escape(error.get("stage", "unknown"))
        message = html.escape(error.get("message", ""))
        lines.append(f"<li><strong>{stage}:</strong> {message}</li>")

    lines.extend(["</ul>", "</div>"])
    return "\n".join(lines)


def _render_finding(f: dict[str, Any], index: int) -> str:
    """Render a single finding as an article element."""
    finding_id = f.get("id", index)
    category = f.get("category", "unknown")
    timestamp = f.get("timestamp_formatted", "00:00")
    timestamp_seconds = f.get("timestamp", 0)
    text = html.escape(f.get("text", ""))
    screenshot = f.get("screenshot", "")

    unified = f.get("unified_analysis", {})
    severity = unified.get("severity", "medium")
    summary = html.escape(unified.get("summary", ""))
    suggested_fix = html.escape(unified.get("suggested_fix", ""))
    affected_components = unified.get("affected_components", [])
    issues_detected = unified.get("issues_detected", [])
    action_items = unified.get("action_items", [])

    severity_class = f"severity-{severity}" if severity else "severity-none"

    details_html = ""
    if affected_components:
        components = ", ".join(html.escape(c) for c in affected_components)
        details_html += f"<dt>Dotknięte komponenty</dt><dd>{components}</dd>"
    if suggested_fix:
        details_html += f"<dt>Sugerowana poprawka</dt><dd>{suggested_fix}</dd>"
    if issues_detected:
        issues = "; ".join(html.escape(i) for i in issues_detected)
        details_html += f"<dt>Wizualne problemy</dt><dd>{issues}</dd>"

    screenshot_html = ""
    if screenshot:
        escaped_src = html.escape(screenshot)
        screenshot_html = f"""
        <div class="finding-screenshot">
            <div class="annotation-container" data-finding-id="{finding_id}">
                <img class="thumbnail" src="{escaped_src}" data-full="{escaped_src}"
                     alt="Screenshot @ {timestamp}" title="Kliknij aby powiekszye i adnotowac">
                <svg class="annotation-svg"></svg>
                <div class="annotation-hint">Kliknij aby adnotowac</div>
            </div>
        </div>
        """

    action_items_display = ", ".join(action_items) if action_items else ""

    return f"""
    <article class="finding" data-finding-id="{finding_id}" data-confirmed="">
        <div class="finding-header">
            <div>
                <span class="finding-title">
                    <span class="index">#{index}</span>
                    {html.escape(category.upper())}
                </span>
                <span class="finding-meta" onclick="seekToTimestamp({timestamp_seconds})"
                      title="Kliknij aby przejsc do tego momentu">@ {html.escape(timestamp)}</span>
            </div>
            <span class="severity-badge {severity_class}">{html.escape(severity)}</span>
        </div>

        <div class="finding-content">
            <div class="finding-transcript">{text}</div>
            {f'<div class="finding-summary"><strong>Podsumowanie:</strong> {summary}</div>' if summary else ""}
            <dl class="finding-details">
                {details_html}
            </dl>
            {screenshot_html}
        </div>

        <div class="human-review">
            <h4 data-i18n="review">Recenzja</h4>
            <div class="review-row">
                <div class="review-field">
                    <label data-i18n="confirmed">Potwierdzone?</label>
                    <div class="radio-group">
                        <label>
                            <input type="radio" name="confirmed-{finding_id}" value="true">
                            <span data-i18n="yes">Tak</span>
                        </label>
                        <label>
                            <input type="radio" name="confirmed-{finding_id}" value="false">
                            <span data-i18n="noFalseAlarm">Nie / Falszy alarm</span>
                        </label>
                    </div>
                </div>
                <div class="review-field">
                    <label data-i18n="changePriority">Zmien priorytet</label>
                    <select class="severity-select">
                        <option value="" data-i18n="noChange">-- Bez zmian --</option>
                        <option value="critical" data-i18n="critical">Krytyczny</option>
                        <option value="high" data-i18n="high">Wysoki</option>
                        <option value="medium" data-i18n="medium">Sredni</option>
                        <option value="low" data-i18n="low">Niski</option>
                    </select>
                </div>
            </div>
            <div class="review-field notes">
                <label data-i18n="notes">Notatki / Akcje</label>
                {f'<div class="ai-suggestions"><strong data-i18n="aiSuggestions">Sugestie AI:</strong> {html.escape(action_items_display)}</div>' if action_items_display else ''}
                <textarea placeholder="Twoje uwagi, akcje do podjęcia..." data-i18n="notesPlaceholder"></textarea>
            </div>
        </div>
    </article>
    """


def render_html_report_pro(
    video_name: str,
    video_path: str | None,
    generated_at: str,
    executive_summary: str,
    findings: list[dict[str, Any]],
    segments: list[Segment] | None = None,
    errors: list[dict[str, str]] | None = None,
    embed_video: bool = False,
) -> str:
    """Render complete HTML Pro report with video player and synchronized subtitles.

    Args:
        video_name: Name of the source video file
        video_path: Path to the video file (for embedding or reference)
        generated_at: ISO timestamp of report generation
        executive_summary: Executive summary text
        findings: List of finding dictionaries
        segments: Optional list of transcript segments for subtitle sync
        errors: Optional list of pipeline error dictionaries
        embed_video: Whether to embed video as base64 (for smaller files)

    Returns:
        Complete HTML document as string
    """
    errors = errors or []
    segments = segments or []

    # Generate unique report ID
    report_id = generate_report_id(video_name, generated_at)

    # Format timestamp
    try:
        dt = datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
        display_time = dt.strftime("%Y-%m-%d %H:%M")
    except (ValueError, AttributeError):
        display_time = generated_at

    # Video source handling
    video_src = ""
    if video_path:
        video_path_obj = Path(video_path)
        if embed_video and video_path_obj.exists():
            size_mb = video_path_obj.stat().st_size / (1024 * 1024)
            if size_mb < 50:  # Only embed if < 50MB
                with open(video_path_obj, "rb") as vf:
                    video_b64 = base64.b64encode(vf.read()).decode("ascii")
                video_src = f"data:video/mp4;base64,{video_b64}"
            else:
                video_src = f"file://{video_path_obj.resolve()}"
        else:
            if video_path_obj.exists():
                video_src = f"file://{video_path_obj.resolve()}"
            else:
                video_src = video_path

    # Generate VTT data URL for subtitles
    vtt_data_url = ""
    if segments:
        from ..vtt_generator import generate_vtt_data_url

        vtt_data_url = generate_vtt_data_url(segments)

    # Segments as JSON for JavaScript
    segments_json = json.dumps(
        [{"id": s.id, "start": s.start, "end": s.end, "text": s.text} for s in segments],
        ensure_ascii=False,
    )

    # Build findings HTML
    findings_html = "\n".join(_render_finding(f, i + 1) for i, f in enumerate(findings))

    # Embed findings as JSON for export
    findings_json = json.dumps(findings, ensure_ascii=False)

    # Load assets
    css_content = load_css()
    js_video_player = load_js_video_player()
    js_review_app = load_js_review_app()
    template = load_html_template()

    # Build video source attribute
    video_src_attr = f'src="{html.escape(video_src)}"' if video_src else ""

    # Build VTT track element
    vtt_track = (
        f'<track kind="subtitles" src="{vtt_data_url}" srclang="pl" label="Polski" default>'
        if vtt_data_url
        else ""
    )

    # Build executive summary HTML
    if executive_summary:
        executive_summary_html = f'<div class="executive-summary"><h3 data-i18n="executiveSummary">Streszczenie</h3><p>{html.escape(executive_summary)}</p></div>'
    else:
        executive_summary_html = (
            '<p class="text-muted" data-i18n="noSummary">Brak podsumowania AI</p>'
        )

    # Render template with all placeholders
    return template.format(
        video_name_escaped=html.escape(video_name),
        report_id=report_id,
        findings_count=len(findings),
        display_time_escaped=html.escape(display_time),
        video_src_attr=video_src_attr,
        vtt_track=vtt_track,
        errors_html=_render_errors(errors),
        executive_summary_html=executive_summary_html,
        findings_html=findings_html,
        stats_html=_render_stats(findings),
        findings_json=findings_json,
        segments_json=segments_json,
        css_content=css_content,
        js_video_player=js_video_player,
        js_review_app=js_review_app,
    )
