"""HTML report template with interactive human review functionality.

This module generates standalone HTML reports with:
- Inline CSS for styling with severity-based color coding
- Inline JavaScript for interactive review features
- LocalStorage-based draft saving
- Export to reviewed JSON format
- Lightbox for screenshot viewing
"""

from __future__ import annotations

import hashlib
import html
import json
from datetime import datetime
from typing import Any

CSS_STYLES = """
:root {
    --color-critical: #dc2626;
    --color-high: #ea580c;
    --color-medium: #ca8a04;
    --color-low: #16a34a;
    --color-bg: #f8fafc;
    --color-card: #ffffff;
    --color-border: #e2e8f0;
    --color-text: #1e293b;
    --color-text-muted: #64748b;
    --shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
    --shadow-lg: 0 4px 6px rgba(0, 0, 0, 0.1);
}

* { box-sizing: border-box; }

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
    max-width: 1200px;
    margin: 0 auto;
    padding: 2rem;
    background: var(--color-bg);
    color: var(--color-text);
    line-height: 1.6;
}

header { margin-bottom: 2rem; }
header h1 { margin: 0 0 0.5rem 0; }
header .meta { color: var(--color-text-muted); font-size: 0.875rem; }

.stats { display: flex; gap: 1rem; flex-wrap: wrap; margin-bottom: 2rem; }
.stat-card {
    background: var(--color-card);
    border: 1px solid var(--color-border);
    border-radius: 0.5rem;
    padding: 1rem 1.5rem;
    box-shadow: var(--shadow);
}
.stat-card .label { font-size: 0.75rem; text-transform: uppercase; color: var(--color-text-muted); }
.stat-card .value { font-size: 1.5rem; font-weight: 600; }
.stat-card.critical .value { color: var(--color-critical); }
.stat-card.high .value { color: var(--color-high); }
.stat-card.medium .value { color: var(--color-medium); }
.stat-card.low .value { color: var(--color-low); }

.executive-summary {
    background: var(--color-card);
    border: 1px solid var(--color-border);
    border-radius: 0.5rem;
    padding: 1.5rem;
    margin-bottom: 2rem;
    box-shadow: var(--shadow);
}

.finding {
    background: var(--color-card);
    border: 1px solid var(--color-border);
    border-radius: 0.5rem;
    padding: 1.5rem;
    margin-bottom: 1.5rem;
    box-shadow: var(--shadow);
    border-left: 4px solid var(--color-border);
}

.finding[data-confirmed="true"] { border-left-color: var(--color-low); }
.finding[data-confirmed="false"] { opacity: 0.6; border-left-color: #9ca3af; }

.finding-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 1rem;
    flex-wrap: wrap;
    gap: 0.5rem;
}

.finding-title { font-weight: 600; font-size: 1.125rem; }
.finding-meta { font-size: 0.875rem; color: var(--color-text-muted); }

.severity-badge {
    display: inline-block;
    padding: 0.25rem 0.75rem;
    border-radius: 9999px;
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    color: white;
}
.severity-critical { background: var(--color-critical); }
.severity-high { background: var(--color-high); }
.severity-medium { background: var(--color-medium); }
.severity-low { background: var(--color-low); }
.severity-none { background: #6b7280; }

.finding-content { margin-bottom: 1rem; }
.finding-transcript {
    background: #f1f5f9;
    border-radius: 0.375rem;
    padding: 1rem;
    margin-bottom: 1rem;
    font-style: italic;
    border-left: 3px solid var(--color-border);
}

.finding-summary { margin-bottom: 1rem; }
.finding-details { font-size: 0.875rem; color: var(--color-text-muted); }
.finding-details dt { font-weight: 600; color: var(--color-text); margin-top: 0.5rem; }
.finding-details dd { margin: 0.25rem 0 0 0; }

.thumbnail {
    max-width: 200px;
    border-radius: 0.375rem;
    cursor: zoom-in;
    transition: transform 0.2s ease;
    border: 1px solid var(--color-border);
}
.thumbnail:hover { transform: scale(1.05); box-shadow: var(--shadow-lg); }

.lightbox {
    display: none;
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(0, 0, 0, 0.9);
    z-index: 1000;
    justify-content: center;
    align-items: center;
    cursor: pointer;
}
.lightbox.active { display: flex; }
.lightbox img { max-width: 95%; max-height: 95%; object-fit: contain; }

.human-review {
    border-top: 2px dashed var(--color-border);
    margin-top: 1.5rem;
    padding-top: 1.5rem;
}
.human-review h4 { margin: 0 0 1rem 0; font-size: 0.875rem; text-transform: uppercase; color: var(--color-text-muted); }

.review-row { display: flex; gap: 1.5rem; flex-wrap: wrap; margin-bottom: 1rem; }
.review-field { flex: 1; min-width: 200px; }
.review-field label { display: block; font-size: 0.75rem; font-weight: 600; margin-bottom: 0.25rem; color: var(--color-text-muted); }
.review-field select { width: 100%; padding: 0.5rem; border: 1px solid var(--color-border); border-radius: 0.375rem; }

.radio-group { display: flex; gap: 1rem; }
.radio-group label { display: flex; align-items: center; gap: 0.375rem; cursor: pointer; }

.notes textarea {
    width: 100%;
    min-height: 60px;
    padding: 0.75rem;
    border: 1px solid var(--color-border);
    border-radius: 0.375rem;
    resize: vertical;
    font-family: inherit;
}

[contenteditable]:focus { outline: 2px solid #3b82f6; outline-offset: 2px; }
[contenteditable] { padding: 0.25rem; border-radius: 0.25rem; }

.action-items-input {
    width: 100%;
    padding: 0.75rem;
    border: 1px solid var(--color-border);
    border-radius: 0.375rem;
    font-family: inherit;
    font-size: 0.875rem;
}

.errors-section {
    background: #fef2f2;
    border: 1px solid #fecaca;
    border-radius: 0.5rem;
    padding: 1rem 1.5rem;
    margin-bottom: 2rem;
}
.errors-section h3 { color: var(--color-critical); margin: 0 0 0.5rem 0; }
.errors-section ul { margin: 0; padding-left: 1.5rem; }

.actions-summary {
    background: #fefce8;
    border: 1px solid #fef08a;
    border-radius: 0.5rem;
    padding: 1.5rem;
    margin-bottom: 2rem;
}
.actions-summary h3 { margin: 0 0 1rem 0; color: var(--color-high); }
.actions-summary ul { margin: 0; padding-left: 1.5rem; }

.export-bar {
    position: sticky;
    bottom: 0;
    background: var(--color-card);
    border-top: 1px solid var(--color-border);
    padding: 1rem;
    margin: 2rem -2rem -2rem -2rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
    box-shadow: 0 -2px 4px rgba(0, 0, 0, 0.1);
}
.export-bar input { padding: 0.5rem; border: 1px solid var(--color-border); border-radius: 0.375rem; width: 200px; }
.export-bar button {
    padding: 0.5rem 1.5rem;
    background: #3b82f6;
    color: white;
    border: none;
    border-radius: 0.375rem;
    cursor: pointer;
    font-weight: 600;
}
.export-bar button:hover { background: #2563eb; }

.toast {
    position: fixed;
    bottom: 5rem;
    right: 2rem;
    background: #1e293b;
    color: white;
    padding: 0.75rem 1.5rem;
    border-radius: 0.5rem;
    box-shadow: var(--shadow-lg);
    animation: fadeInOut 3s ease;
    z-index: 1001;
}
@keyframes fadeInOut {
    0% { opacity: 0; transform: translateY(1rem); }
    10% { opacity: 1; transform: translateY(0); }
    90% { opacity: 1; transform: translateY(0); }
    100% { opacity: 0; transform: translateY(-1rem); }
}

footer {
    margin-top: 3rem;
    padding-top: 1rem;
    border-top: 1px solid var(--color-border);
    text-align: center;
    color: var(--color-text-muted);
    font-size: 0.875rem;
}
"""

JS_SCRIPT = """
const reportState = {
    findings: {},
    reviewer: '',
    modified: false,
    reportId: ''
};

function initState() {
    reportState.reportId = document.body.dataset.reportId || '';

    // Try to restore draft from localStorage (with error handling for private mode)
    try {
        const savedDraft = localStorage.getItem('screenscribe_draft_' + reportState.reportId);
        if (savedDraft) {
            const parsed = JSON.parse(savedDraft);
            reportState.findings = parsed.findings || {};
            reportState.reviewer = parsed.reviewer || '';
            restoreUIFromState();
            showNotification('Draft restored from local storage');
        }
    } catch (e) {
        console.warn('localStorage not available:', e);
    }

    // Use event delegation for better input handling
    document.addEventListener('input', handleInputEvent);
    document.addEventListener('change', handleChangeEvent);

    // Initialize finding states
    document.querySelectorAll('.finding').forEach(article => {
        const findingId = article.dataset.findingId;
        if (!reportState.findings[findingId]) {
            reportState.findings[findingId] = {
                confirmed: null,
                severity: null,
                notes: '',
                actionItems: ''
            };
        }
    });

    const reviewerInput = document.getElementById('reviewer-name');
    if (reviewerInput) {
        reviewerInput.value = reportState.reviewer;
    }

    setInterval(saveDraft, 30000);

    window.addEventListener('beforeunload', (e) => {
        if (reportState.modified) {
            e.preventDefault();
            e.returnValue = 'You have unsaved changes. Are you sure you want to leave?';
        }
    });

    // ESC key to close lightbox
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            closeLightbox();
        }
    });

    document.querySelectorAll('.thumbnail').forEach(img => {
        img.addEventListener('click', () => openLightbox(img));
    });

    const lightbox = document.getElementById('lightbox');
    if (lightbox) {
        lightbox.addEventListener('click', closeLightbox);
    }
}

function handleInputEvent(e) {
    const target = e.target;
    const article = target.closest('.finding');

    // Reviewer name input
    if (target.id === 'reviewer-name') {
        reportState.reviewer = target.value;
        reportState.modified = true;
        return;
    }

    if (!article) return;
    const findingId = article.dataset.findingId;
    if (!reportState.findings[findingId]) {
        reportState.findings[findingId] = { confirmed: null, severity: null, notes: '', actionItems: '' };
    }

    // Notes textarea
    if (target.matches('.notes textarea')) {
        reportState.findings[findingId].notes = target.value;
        reportState.modified = true;
    }

    // Action items input
    if (target.matches('.action-items-input')) {
        reportState.findings[findingId].actionItems = target.value;
        reportState.modified = true;
    }
}

function handleChangeEvent(e) {
    const target = e.target;
    const article = target.closest('.finding');

    if (!article) return;
    const findingId = article.dataset.findingId;
    if (!reportState.findings[findingId]) {
        reportState.findings[findingId] = { confirmed: null, severity: null, notes: '', actionItems: '' };
    }

    // Radio buttons for confirmed
    if (target.matches('input[type="radio"]') && target.name.startsWith('confirmed-')) {
        const value = target.value === 'true';
        reportState.findings[findingId].confirmed = value;
        article.dataset.confirmed = value.toString();
        reportState.modified = true;
    }

    // Severity select
    if (target.matches('.severity-select')) {
        reportState.findings[findingId].severity = target.value;
        reportState.modified = true;
    }
}


function openLightbox(img) {
    const lightbox = document.getElementById('lightbox');
    const lightboxImg = document.getElementById('lightbox-img');
    const fullSrc = img.dataset.full || img.src;
    lightboxImg.src = fullSrc;
    lightbox.classList.add('active');
}

function closeLightbox() {
    const lightbox = document.getElementById('lightbox');
    lightbox.classList.remove('active');
}

function saveDraft() {
    if (!reportState.modified) return;
    try {
        const data = {
            findings: reportState.findings,
            reviewer: reportState.reviewer,
            savedAt: new Date().toISOString()
        };
        localStorage.setItem('screenscribe_draft_' + reportState.reportId, JSON.stringify(data));
        showNotification('Draft saved');
        reportState.modified = false;
    } catch (e) {
        console.warn('Could not save draft to localStorage:', e);
    }
}

function restoreUIFromState() {
    Object.entries(reportState.findings).forEach(([findingId, state]) => {
        const article = document.querySelector(`[data-finding-id="${findingId}"]`);
        if (!article) return;

        if (state.confirmed !== null) {
            article.dataset.confirmed = state.confirmed.toString();
            const radio = article.querySelector(`input[value="${state.confirmed}"]`);
            if (radio) radio.checked = true;
        }

        if (state.severity) {
            const select = article.querySelector('.severity-select');
            if (select) select.value = state.severity;
        }

        if (state.notes) {
            const textarea = article.querySelector('.notes textarea');
            if (textarea) textarea.value = state.notes;
        }

        if (state.actionItems) {
            const input = article.querySelector('.action-items-input');
            if (input) input.value = state.actionItems;
        }
    });
}

function exportReviewedJSON() {
    // Validate reviewer name
    if (!reportState.reviewer.trim()) {
        showNotification('Please enter your name before exporting');
        document.getElementById('reviewer-name').focus();
        return;
    }

    // Check if at least one finding was reviewed
    const reviewedCount = Object.values(reportState.findings).filter(f => f.confirmed !== null).length;
    if (reviewedCount === 0) {
        if (!confirm('No findings have been reviewed yet. Export anyway?')) {
            return;
        }
    }

    const originalFindings = JSON.parse(document.getElementById('original-findings').textContent);
    const reviewedFindings = originalFindings.map(f => {
        const review = reportState.findings[f.id] || {};
        return {
            ...f,
            human_review: {
                confirmed: review.confirmed,
                severity_override: review.severity || null,
                notes: review.notes || '',
                action_items: review.actionItems ? review.actionItems.split(',').map(s => s.trim()).filter(Boolean) : [],
                reviewer: reportState.reviewer,
                reviewed_at: new Date().toISOString()
            }
        };
    });

    const output = {
        video: document.body.dataset.videoName,
        reviewed_at: new Date().toISOString(),
        reviewer: reportState.reviewer,
        findings: reviewedFindings
    };

    const blob = new Blob([JSON.stringify(output, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'reviewed_' + (document.body.dataset.videoName || 'report') + '.json';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    try {
        localStorage.removeItem('screenscribe_draft_' + reportState.reportId);
    } catch (e) {
        console.warn('Could not clear draft from localStorage:', e);
    }
    reportState.modified = false;
    showNotification('Review exported successfully');
}

function showNotification(msg) {
    const existing = document.querySelector('.toast');
    if (existing) existing.remove();

    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.textContent = msg;
    document.body.appendChild(toast);

    setTimeout(() => {
        if (toast.parentNode) toast.remove();
    }, 3000);
}

document.addEventListener('DOMContentLoaded', initState);
"""


def _render_stats(findings: list[dict[str, Any]]) -> str:
    """Render severity statistics cards.

    Args:
        findings: List of finding dictionaries

    Returns:
        HTML string for stats section
    """
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
            <div class="label">Total Issues</div>
            <div class="value">{total}</div>
        </div>
        <div class="stat-card critical">
            <div class="label">Critical</div>
            <div class="value">{severity_counts["critical"]}</div>
        </div>
        <div class="stat-card high">
            <div class="label">High</div>
            <div class="value">{severity_counts["high"]}</div>
        </div>
        <div class="stat-card medium">
            <div class="label">Medium</div>
            <div class="value">{severity_counts["medium"]}</div>
        </div>
        <div class="stat-card low">
            <div class="label">Low</div>
            <div class="value">{severity_counts["low"]}</div>
        </div>
    </div>
    """


def _render_action_items_summary(findings: list[dict[str, Any]]) -> str:
    """Render consolidated action items for critical and high severity findings.

    Args:
        findings: List of finding dictionaries

    Returns:
        HTML string for action items summary section
    """
    action_items: list[tuple[str, str, list[str]]] = []

    for f in findings:
        unified = f.get("unified_analysis", {})
        if not unified.get("is_issue", True):
            continue
        severity = unified.get("severity", "medium")
        if severity not in ("critical", "high"):
            continue
        items = unified.get("action_items", [])
        if items:
            summary = unified.get("summary", f.get("text", "")[:100])
            action_items.append((severity, summary, items))

    if not action_items:
        return ""

    lines = [
        '<div class="actions-summary">',
        "<h3>Action Items (Critical/High Priority)</h3>",
        "<ul>",
    ]

    for severity, summary, items in action_items:
        lines.append(
            f"<li><strong>[{html.escape(severity.upper())}]</strong> {html.escape(summary)}"
        )
        lines.append("<ul>")
        for item in items:
            lines.append(f"<li>{html.escape(item)}</li>")
        lines.append("</ul></li>")

    lines.extend(["</ul>", "</div>"])
    return "\n".join(lines)


def _render_errors(errors: list[dict[str, str]]) -> str:
    """Render pipeline errors section.

    Args:
        errors: List of error dictionaries with 'stage' and 'message' keys

    Returns:
        HTML string for errors section
    """
    if not errors:
        return ""

    lines = ['<div class="errors-section">', "<h3>Pipeline Errors</h3>", "<ul>"]

    for error in errors:
        stage = html.escape(error.get("stage", "unknown"))
        message = html.escape(error.get("message", ""))
        lines.append(f"<li><strong>{stage}:</strong> {message}</li>")

    lines.extend(["</ul>", "</div>"])
    return "\n".join(lines)


def _render_finding(f: dict[str, Any], index: int) -> str:
    """Render a single finding as an article element.

    Args:
        f: Finding dictionary
        index: Finding index (1-based)

    Returns:
        HTML string for the finding article
    """
    finding_id = f.get("id", index)
    category = f.get("category", "unknown")
    timestamp = f.get("timestamp_formatted", "00:00")
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

    # Build details section
    details_html = ""
    if affected_components:
        components = ", ".join(html.escape(c) for c in affected_components)
        details_html += f"<dt>Affected Components</dt><dd>{components}</dd>"
    if suggested_fix:
        details_html += f"<dt>Suggested Fix</dt><dd>{suggested_fix}</dd>"
    if issues_detected:
        issues = "; ".join(html.escape(i) for i in issues_detected)
        details_html += f"<dt>Visual Issues</dt><dd>{issues}</dd>"

    # Screenshot thumbnail
    screenshot_html = ""
    if screenshot:
        escaped_src = html.escape(screenshot)
        screenshot_html = f"""
        <div class="finding-screenshot">
            <img class="thumbnail" src="{escaped_src}" data-full="{escaped_src}"
                 alt="Screenshot at {timestamp}">
        </div>
        """

    # Action items display
    action_items_display = ", ".join(action_items) if action_items else ""

    return f"""
    <article class="finding" data-finding-id="{finding_id}" data-confirmed="">
        <div class="finding-header">
            <div>
                <span class="finding-title">#{index} {html.escape(category.upper())}</span>
                <span class="finding-meta">@ {html.escape(timestamp)}</span>
            </div>
            <span class="severity-badge {severity_class}">{html.escape(severity)}</span>
        </div>

        <div class="finding-content">
            <div class="finding-transcript">{text}</div>
            {f'<div class="finding-summary"><strong>Summary:</strong> {summary}</div>' if summary else ""}
            <dl class="finding-details">
                {details_html}
            </dl>
            {screenshot_html}
        </div>

        <div class="human-review">
            <h4>Human Review</h4>
            <div class="review-row">
                <div class="review-field">
                    <label>Confirmed Issue?</label>
                    <div class="radio-group">
                        <label>
                            <input type="radio" name="confirmed-{finding_id}" value="true">
                            Yes
                        </label>
                        <label>
                            <input type="radio" name="confirmed-{finding_id}" value="false">
                            No / False Positive
                        </label>
                    </div>
                </div>
                <div class="review-field">
                    <label>Override Severity</label>
                    <select class="severity-select">
                        <option value="">-- Keep Original --</option>
                        <option value="critical">Critical</option>
                        <option value="high">High</option>
                        <option value="medium">Medium</option>
                        <option value="low">Low</option>
                    </select>
                </div>
            </div>
            <div class="review-row">
                <div class="review-field">
                    <label>Additional Action Items (comma-separated)</label>
                    <input type="text" class="action-items-input"
                           placeholder="e.g., verify fix, add test, update docs"
                           value="{html.escape(action_items_display)}">
                </div>
            </div>
            <div class="notes">
                <label>Notes</label>
                <textarea placeholder="Add your review notes here..."></textarea>
            </div>
        </div>
    </article>
    """


def render_html_report(
    video_name: str,
    generated_at: str,
    executive_summary: str,
    findings: list[dict[str, Any]],
    errors: list[dict[str, str]] | None = None,
) -> str:
    """Render complete HTML report with interactive review functionality.

    Args:
        video_name: Name of the source video file
        generated_at: ISO timestamp of report generation
        executive_summary: Executive summary text
        findings: List of finding dictionaries from enhanced JSON report
        errors: Optional list of pipeline error dictionaries

    Returns:
        Complete HTML document as string
    """
    errors = errors or []

    # Generate unique report ID for localStorage (not cryptographic, just a unique key)
    report_id = hashlib.sha256(f"{video_name}:{generated_at}".encode()).hexdigest()[:12]

    # Format timestamp for display
    try:
        dt = datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
        display_time = dt.strftime("%Y-%m-%d %H:%M")
    except (ValueError, AttributeError):
        display_time = generated_at

    # Build findings HTML
    findings_html = "\n".join(_render_finding(f, i + 1) for i, f in enumerate(findings))

    # Embed original findings as JSON for export
    findings_json = json.dumps(findings, ensure_ascii=False)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Video Review Report - {html.escape(video_name)}</title>
    <style>
{CSS_STYLES}
    </style>
</head>
<body data-report-id="{report_id}" data-video-name="{html.escape(video_name)}">
    <header>
        <h1>Video Review Report</h1>
        <div class="meta">
            <strong>Video:</strong> {html.escape(video_name)} |
            <strong>Generated:</strong> {html.escape(display_time)}
        </div>
    </header>

    {_render_stats(findings)}

    {_render_errors(errors)}

    {_render_action_items_summary(findings)}

    {f'<div class="executive-summary"><h3>Executive Summary</h3><p>{html.escape(executive_summary)}</p></div>' if executive_summary else ""}

    <section class="findings">
        <h2>Findings</h2>
        {findings_html}
    </section>

    <div id="lightbox" class="lightbox">
        <img id="lightbox-img" src="" alt="Full size screenshot">
    </div>

    <script id="original-findings" type="application/json">
{findings_json}
    </script>

    <div class="export-bar">
        <div>
            <label>Reviewer Name:
                <input type="text" id="reviewer-name" placeholder="Your name">
            </label>
        </div>
        <button onclick="exportReviewedJSON()">Export Reviewed JSON</button>
    </div>

    <footer>
        <p>Generated by ScreenScribe</p>
    </footer>

    <script>
{JS_SCRIPT}
    </script>
</body>
</html>
"""
