"""Interactive analysis server for reversed review flow.

This module creates a FastAPI server that enables human-first video analysis:
1. Human watches video in browser
2. Marks frames and records voice comments
3. Voice -> STT -> becomes context for VLM analysis
4. Results appear in real-time

Created by M&K (c)2026 VetCoders
"""

from __future__ import annotations

import base64
import tempfile
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from pydantic import BaseModel

if TYPE_CHECKING:
    from .config import ScreenScribeConfig


class MarkFrameRequest(BaseModel):
    """Request body for marking a frame."""

    timestamp: float
    frame_base64: str
    transcript: str = ""
    notes: str = ""


@dataclass
class FrameMarker:
    """A marked frame with optional voice comment."""

    marker_id: str
    timestamp: float
    frame_base64: str
    transcript: str = ""
    notes: str = ""
    status: str = "pending"  # pending, analyzing, completed, error


@dataclass
class AnalysisResult:
    """VLM analysis result for a marked frame."""

    marker_id: str
    timestamp: float
    category: str = "unknown"
    severity: str = "medium"
    summary: str = ""
    issues_detected: list[str] = field(default_factory=list)
    suggested_fix: str = ""
    affected_components: list[str] = field(default_factory=list)
    response_id: str = ""


@dataclass
class AnalyzeSession:
    """Session state for analyze mode."""

    video_path: Path
    markers: dict[str, FrameMarker] = field(default_factory=dict)
    results: dict[str, AnalysisResult] = field(default_factory=dict)
    last_response_id: str = ""
    finalize_jobs: dict[str, FinalizeJob] = field(default_factory=dict)
    lock: threading.RLock = field(default_factory=threading.RLock)


@dataclass
class FinalizeJob:
    """Background job state for finalize/analyze-all flow."""

    job_id: str
    total: int = 0
    processed: int = 0
    completed: int = 0
    errors: int = 0
    skipped: int = 0
    status: str = "running"  # running, completed, error
    last_error: str = ""
    started_at: float = field(default_factory=time.time)
    finished_at: float | None = None
    export_payload: dict[str, Any] | None = None


def create_analyze_app(video_path: Path, config: ScreenScribeConfig) -> FastAPI:
    """Create FastAPI app for analyze mode.

    Args:
        video_path: Path to video file to analyze
        config: ScreenScribe configuration

    Returns:
        FastAPI application instance
    """
    app = FastAPI(
        title="ScreenScribe Analyze",
        description="Interactive video analysis with human-in-the-loop",
        version="0.1.0",
    )

    # Session state (in-memory, single user)
    session = AnalyzeSession(video_path=video_path)

    def build_markers_payload() -> list[dict[str, Any]]:
        """Build current marker list enriched with analysis results."""
        markers_data: list[dict[str, Any]] = []
        with session.lock:
            markers = list(session.markers.values())
        for marker in markers:
            marker_data: dict[str, Any] = {
                "marker_id": marker.marker_id,
                "timestamp": marker.timestamp,
                "transcript": marker.transcript,
                "notes": marker.notes,
                "status": marker.status,
            }
            with session.lock:
                result = session.results.get(marker.marker_id)
            if result:
                marker_data["result"] = {
                    "category": result.category,
                    "severity": result.severity,
                    "summary": result.summary,
                    "issues_detected": result.issues_detected,
                    "suggested_fix": result.suggested_fix,
                }
            markers_data.append(marker_data)
        return markers_data

    def build_export_payload() -> dict[str, Any]:
        """Build exported JSON payload for all markers."""
        markers_list: list[dict[str, Any]] = []
        export_data: dict[str, Any] = {
            "video": str(video_path),
            "markers": markers_list,
        }
        with session.lock:
            markers = list(session.markers.values())
        for marker in markers:
            marker_data: dict[str, Any] = {
                "marker_id": marker.marker_id,
                "timestamp": marker.timestamp,
                "transcript": marker.transcript,
                "notes": marker.notes,
            }
            with session.lock:
                result = session.results.get(marker.marker_id)
            if result:
                marker_data["analysis"] = {
                    "category": result.category,
                    "severity": result.severity,
                    "summary": result.summary,
                    "issues_detected": result.issues_detected,
                    "suggested_fix": result.suggested_fix,
                    "affected_components": result.affected_components,
                }
            markers_list.append(marker_data)
        return export_data

    def analyze_single_marker(marker_id: str) -> dict[str, Any]:
        """Run unified AI analysis for one marker and persist status/result."""
        from .detect import Detection
        from .transcribe import Segment
        from .unified_analysis import analyze_finding_unified

        with session.lock:
            if marker_id not in session.markers:
                raise HTTPException(status_code=404, detail="Marker not found")
            marker = session.markers[marker_id]
            marker.status = "analyzing"

        segment = Segment(
            id=0,
            start=marker.timestamp,
            end=marker.timestamp + 1.0,
            text=marker.transcript or marker.notes or "User marked this frame",
        )
        detection = Detection(
            segment=segment,
            category="user_marked",
            keywords_found=[],
            context=f"User comment: {marker.transcript}\nNotes: {marker.notes}",
        )

        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            frame_bytes = base64.b64decode(marker.frame_base64)
            tmp.write(frame_bytes)
            screenshot_path = Path(tmp.name)

        try:
            with session.lock:
                previous_response_id = session.last_response_id

            finding = analyze_finding_unified(
                detection=detection,
                screenshot_path=screenshot_path,
                config=config,
                previous_response_id=previous_response_id,
            )

            if not finding:
                with session.lock:
                    marker.status = "error"
                return {"marker_id": marker_id, "status": "error", "error": "Analysis failed"}

            result = AnalysisResult(
                marker_id=marker_id,
                timestamp=marker.timestamp,
                category=finding.category,
                severity=finding.severity,
                summary=finding.summary,
                issues_detected=finding.issues_detected,
                suggested_fix=finding.suggested_fix,
                affected_components=finding.affected_components,
                response_id=finding.response_id,
            )
            with session.lock:
                session.results[marker_id] = result
                session.last_response_id = finding.response_id
                marker.status = "completed"

            return {
                "marker_id": marker_id,
                "status": "completed",
                "result": {
                    "category": result.category,
                    "severity": result.severity,
                    "summary": result.summary,
                    "issues_detected": result.issues_detected,
                    "suggested_fix": result.suggested_fix,
                },
            }
        except Exception as exc:  # defensive guard for batch finalize
            with session.lock:
                marker.status = "error"
            return {"marker_id": marker_id, "status": "error", "error": str(exc)}
        finally:
            screenshot_path.unlink(missing_ok=True)

    def analyze_all_pending_markers(job: FinalizeJob | None = None) -> dict[str, Any]:
        """Analyze all markers that are pending/error/no-result."""
        with session.lock:
            markers = list(session.markers.values())
            result_ids = set(session.results.keys())

        marker_ids = [
            marker.marker_id
            for marker in markers
            if marker.status in {"pending", "error"} or marker.marker_id not in result_ids
        ]

        completed = 0
        errors = 0
        skipped = max(0, len(markers) - len(marker_ids))
        results: list[dict[str, Any]] = []

        if job:
            with session.lock:
                job.total = len(marker_ids)
                job.skipped = skipped

        for marker_id in marker_ids:
            outcome = analyze_single_marker(marker_id)
            results.append(outcome)
            if outcome.get("status") == "completed":
                completed += 1
            elif outcome.get("status") == "error":
                errors += 1
            if job:
                with session.lock:
                    job.processed += 1
                    job.completed = completed
                    job.errors = errors

        return {
            "total_markers": len(markers),
            "processed": len(marker_ids),
            "completed": completed,
            "errors": errors,
            "skipped": skipped,
            "results": results,
        }

    def get_finalize_job(job_id: str) -> FinalizeJob:
        """Get finalize job by id or raise HTTP 404."""
        with session.lock:
            job = session.finalize_jobs.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Finalize job not found")
        return job

    def serialize_finalize_job(job: FinalizeJob) -> dict[str, Any]:
        """Serialize finalize job for frontend polling."""
        with session.lock:
            total = job.total
            processed = job.processed
            status = job.status
            completed = job.completed
            errors = job.errors
            skipped = job.skipped
            finished_at = job.finished_at
            started_at = job.started_at
            last_error = job.last_error

        progress = (
            1.0
            if total == 0 and status == "completed"
            else ((processed / total) if total > 0 else 0.0)
        )
        return {
            "job_id": job.job_id,
            "status": status,
            "total": total,
            "processed": processed,
            "completed": completed,
            "errors": errors,
            "skipped": skipped,
            "progress": progress,
            "started_at": started_at,
            "finished_at": finished_at,
            "last_error": last_error,
        }

    def run_finalize_job(job_id: str) -> None:
        """Run async finalize job in background thread."""
        job = get_finalize_job(job_id)
        try:
            analysis_summary = analyze_all_pending_markers(job=job)
            payload = {
                "analysis": analysis_summary,
                "markers": build_markers_payload(),
                "export": build_export_payload(),
            }
            with session.lock:
                job.status = "completed"
                job.finished_at = time.time()
                job.export_payload = payload
        except Exception as exc:  # pragma: no cover - defensive
            with session.lock:
                job.status = "error"
                job.last_error = str(exc)
                job.finished_at = time.time()

    @app.get("/", response_class=HTMLResponse)
    async def index() -> HTMLResponse:
        """Serve the analyze UI."""
        from .html_pro.assets import load_css, load_js_video_player

        # Load assets
        css = load_css()
        js_video = load_js_video_player()

        # Build analyze page (simplified version of report.html)
        lang = config.language[:2].lower()  # "pl" or "en"
        html = f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ScreenScribe Analyze - {video_path.name}</title>
    <style>{css}</style>
    <style>
        /* Analyze mode specific styles */
        .capture-controls {{
            display: flex;
            gap: var(--space-lg);
            align-items: center;
            padding: var(--space-md);
            background: var(--surface-card);
            border-radius: var(--radius-md);
            margin-top: var(--space-md);
        }}

        .mic-button {{
            width: 64px;
            height: 64px;
            border-radius: 50%;
            border: 3px solid var(--border-default);
            background: var(--surface-card);
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all var(--motion-fast);
            flex-shrink: 0;
        }}

        .mic-button:hover {{
            border-color: var(--vista-mint);
            background: var(--surface-hover);
        }}

        .mic-button.recording {{
            border-color: var(--color-critical);
            background: color-mix(in srgb, var(--color-critical) 20%, transparent);
            animation: pulse-recording 1s infinite;
        }}

        @keyframes pulse-recording {{
            0%, 100% {{ transform: scale(1); }}
            50% {{ transform: scale(1.05); }}
        }}

        .mic-button svg {{
            width: 28px;
            height: 28px;
            fill: currentColor;
        }}

        .recording-indicator {{
            display: none;
            align-items: center;
            gap: var(--space-sm);
            padding: var(--space-sm) var(--space-md);
            background: color-mix(in srgb, var(--color-critical) 20%, transparent);
            border-radius: var(--radius-sm);
            color: var(--color-critical);
            font-weight: 600;
        }}

        .recording-indicator.active {{
            display: flex;
        }}

        .recording-indicator::before {{
            content: '';
            width: 12px;
            height: 12px;
            background: var(--color-critical);
            border-radius: 50%;
            animation: pulse-dot 1s infinite;
        }}

        @keyframes pulse-dot {{
            0%, 100% {{ opacity: 1; }}
            50% {{ opacity: 0.4; }}
        }}

        .transcript-input {{
            flex: 1;
            display: flex;
            flex-direction: column;
            gap: var(--space-sm);
        }}

        .transcript-preview {{
            background: var(--surface-primary);
            border: 1px solid var(--border-default);
            border-radius: var(--radius-sm);
            padding: var(--space-md);
            min-height: 60px;
            font-style: italic;
            color: var(--text-secondary);
        }}

        .transcript-preview.has-text {{
            font-style: normal;
            color: var(--text-primary);
        }}

        .notes-input {{
            width: 100%;
            padding: var(--space-sm);
            background: var(--surface-card);
            border: 1px solid var(--border-default);
            border-radius: var(--radius-sm);
            color: var(--text-primary);
            font-family: var(--font-sans);
            resize: vertical;
        }}

        .mark-frame-btn {{
            padding: var(--space-md) var(--space-xl);
            background: var(--quantum-green);
            color: var(--crt-black);
            border: none;
            border-radius: var(--radius-sm);
            font-weight: 600;
            cursor: pointer;
            transition: all var(--motion-fast);
            flex-shrink: 0;
        }}

        .mark-frame-btn:hover {{
            background: var(--vista-mint);
            box-shadow: var(--shadow-glow);
        }}

        .mark-frame-btn:disabled {{
            opacity: 0.5;
            cursor: not-allowed;
        }}

        .markers-list {{
            margin-top: var(--space-lg);
        }}

        .marker-item {{
            background: var(--surface-card);
            border: 1px solid var(--border-default);
            border-radius: var(--radius-md);
            padding: var(--space-md);
            margin-bottom: var(--space-md);
        }}

        .marker-item.analyzing {{
            border-color: var(--quantum-amber);
        }}

        .marker-item.completed {{
            border-color: var(--quantum-green);
        }}

        .marker-item.error {{
            border-color: var(--color-critical);
        }}

        .marker-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: var(--space-sm);
        }}

        .marker-time {{
            font-family: var(--font-mono);
            color: var(--quantum-cyan);
        }}

        .marker-status {{
            font-size: 0.85rem;
            padding: var(--space-xs) var(--space-sm);
            border-radius: var(--radius-sm);
            background: var(--surface-hover);
        }}

        .marker-transcript {{
            color: var(--text-secondary);
            font-size: 0.9rem;
        }}

        .marker-result {{
            margin-top: var(--space-md);
            padding-top: var(--space-md);
            border-top: 1px solid var(--border-default);
        }}

        .spinner {{
            display: inline-block;
            width: 16px;
            height: 16px;
            border: 2px solid var(--border-default);
            border-top-color: var(--quantum-green);
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
        }}

        @keyframes spin {{
            to {{ transform: rotate(360deg); }}
        }}

        .empty-state {{
            text-align: center;
            padding: var(--space-xl);
            color: var(--text-muted);
        }}

        .finalize-progress {{
            min-width: 280px;
            display: flex;
            flex-direction: column;
            gap: var(--space-xs);
        }}

        .finalize-progress[hidden] {{
            display: none;
        }}

        .finalize-progress-meta {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 0.82rem;
            color: var(--text-secondary);
        }}

        .finalize-progress-track {{
            width: 100%;
            height: 8px;
            border-radius: 999px;
            background: var(--surface-hover);
            overflow: hidden;
            border: 1px solid var(--border-default);
        }}

        .finalize-progress-fill {{
            width: 0%;
            height: 100%;
            background: var(--quantum-green);
            transition: width var(--motion-fast);
        }}
    </style>
</head>
<body data-mode="analyze" data-video-name="{video_path.name}">

    <header class="app-header">
        <div class="header-left">
            <h1>ScreenScribe Analyze</h1>
        </div>
        <nav class="header-tabs">
            <button class="tab-btn active" data-tab="capture">Capture</button>
            <button class="tab-btn" data-tab="findings">Findings (<span id="findings-count">0</span>)</button>
        </nav>
        <div class="meta">
            {video_path.name} | Interactive Mode
        </div>
    </header>

    <div class="app-container">
        <main class="video-section">
            <div class="video-container">
                <video id="videoPlayer" controls preload="metadata" src="/video">
                    Your browser does not support HTML5 video.
                </video>
            </div>

            <div id="tab-capture" class="tab-content active">
                <div class="capture-controls">
                    <button class="mic-button" id="micBtn" title="Hold to record voice comment">
                        <!-- Phosphor microphone icon (monochrome) -->
                        <svg viewBox="0 0 256 256" xmlns="http://www.w3.org/2000/svg">
                            <path d="M128,176a48,48,0,0,0,48-48V64a48,48,0,0,0-96,0v64A48,48,0,0,0,128,176ZM96,64a32,32,0,0,1,64,0v64a32,32,0,0,1-64,0Zm40,143.6V232a8,8,0,0,1-16,0V207.6A80.11,80.11,0,0,1,48,128a8,8,0,0,1,16,0,64,64,0,0,0,128,0,8,8,0,0,1,16,0A80.11,80.11,0,0,1,136,207.6Z"/>
                        </svg>
                    </button>

                    <div class="transcript-input">
                        <div id="recordingStatus" class="recording-indicator">
                            Recording...
                        </div>
                        <div id="transcriptPreview" class="transcript-preview">
                            Hold mic button to record, or type below
                        </div>
                        <textarea id="notesInput" class="notes-input" rows="2"
                                  placeholder="Additional notes (optional)..."></textarea>
                    </div>

                    <button class="mark-frame-btn" id="markFrameBtn">
                        Mark Frame
                    </button>
                </div>
            </div>
        </main>

        <aside class="sidebar">
            <div class="sidebar-panel">
                <div class="sidebar-scroll">
                    <div id="tab-findings" class="tab-content active">
                        <section class="findings-section">
                            <div id="markersList" class="markers-list">
                                <div class="empty-state">
                                    No frames marked yet.<br>
                                    Watch the video and mark interesting frames.
                                </div>
                            </div>
                        </section>
                    </div>
                </div>
            </div>
        </aside>
    </div>

    <div class="export-bar">
        <div class="export-options">
            <span id="statusText">Ready</span>
            <div id="finalizeProgress" class="finalize-progress" hidden>
                <div class="finalize-progress-meta">
                    <span id="finalizeProgressLabel">0/0</span>
                    <span id="finalizeProgressErrors">0 errors</span>
                </div>
                <div class="finalize-progress-track">
                    <div id="finalizeProgressFill" class="finalize-progress-fill"></div>
                </div>
            </div>
        </div>
        <div class="export-buttons">
            <button onclick="exportFindings()" class="btn-secondary">Export JSON</button>
            <button id="finalizeBtn" onclick="generateFullReport()" class="btn-primary">Generate Full Report</button>
        </div>
    </div>

    <script>
{js_video}
    </script>

    <script>
// =============================================================================
// ANALYZE MODE - Voice Recording & Frame Marking
// =============================================================================

class VoiceRecorder {{
    constructor(onTranscript) {{
        this.mediaRecorder = null;
        this.audioChunks = [];
        this.isRecording = false;
        this.onTranscript = onTranscript;
        this.stream = null;
    }}

    async init() {{
        try {{
            this.stream = await navigator.mediaDevices.getUserMedia({{
                audio: {{
                    echoCancellation: true,
                    noiseSuppression: true,
                    sampleRate: 16000
                }}
            }});
            return true;
        }} catch (e) {{
            console.error('Microphone access denied:', e);
            return false;
        }}
    }}

    async start() {{
        if (!this.stream) {{
            const ok = await this.init();
            if (!ok) {{
                alert('Microphone access denied. Please allow microphone access.');
                return false;
            }}
        }}

        this.audioChunks = [];
        this.mediaRecorder = new MediaRecorder(this.stream, {{
            mimeType: 'audio/webm;codecs=opus'
        }});

        this.mediaRecorder.ondataavailable = (e) => {{
            if (e.data.size > 0) {{
                this.audioChunks.push(e.data);
            }}
        }};

        this.mediaRecorder.onstop = async () => {{
            const audioBlob = new Blob(this.audioChunks, {{ type: 'audio/webm' }});
            await this.transcribe(audioBlob);
        }};

        this.mediaRecorder.start();
        this.isRecording = true;
        return true;
    }}

    stop() {{
        if (this.mediaRecorder && this.isRecording) {{
            this.mediaRecorder.stop();
            this.isRecording = false;
        }}
    }}

    async transcribe(audioBlob) {{
        const formData = new FormData();
        formData.append('audio', audioBlob, 'recording.webm');

        try {{
            document.getElementById('statusText').textContent = 'Transcribing...';
            const response = await fetch('/api/stt', {{
                method: 'POST',
                body: formData
            }});

            if (!response.ok) {{
                throw new Error('STT failed: ' + response.status);
            }}

            const result = await response.json();
            if (this.onTranscript) {{
                this.onTranscript(result.text);
            }}
            document.getElementById('statusText').textContent = 'Ready';
        }} catch (e) {{
            console.error('Transcription failed:', e);
            document.getElementById('statusText').textContent = 'Transcription failed';
        }}
    }}

    destroy() {{
        if (this.stream) {{
            this.stream.getTracks().forEach(track => track.stop());
            this.stream = null;
        }}
    }}
}}

class FrameMarker {{
    constructor(video) {{
        this.video = video;
    }}

    async captureFrame() {{
        const canvas = document.createElement('canvas');
        canvas.width = this.video.videoWidth;
        canvas.height = this.video.videoHeight;

        const ctx = canvas.getContext('2d');
        ctx.drawImage(this.video, 0, 0);

        // Get base64 without data URL prefix
        const dataUrl = canvas.toDataURL('image/jpeg', 0.9);
        const base64 = dataUrl.split(',')[1];

        return {{
            timestamp: this.video.currentTime,
            frame_base64: base64
        }};
    }}

    async markCurrentFrame(transcript = '', notes = '') {{
        const frameData = await this.captureFrame();

        const marker = {{
            ...frameData,
            transcript,
            notes
        }};

        document.getElementById('statusText').textContent = 'Marking frame...';

        const response = await fetch('/api/mark', {{
            method: 'POST',
            headers: {{ 'Content-Type': 'application/json' }},
            body: JSON.stringify(marker)
        }});

        const result = await response.json();
        document.getElementById('statusText').textContent = 'Ready';

        return result;
    }}
}}

// Format timestamp as MM:SS
function formatTime(seconds) {{
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return m.toString().padStart(2, '0') + ':' + s.toString().padStart(2, '0');
}}

// Update markers list UI
function updateMarkersList(markers) {{
    const container = document.getElementById('markersList');
    const countEl = document.getElementById('findings-count');

    if (markers.length === 0) {{
        container.innerHTML = '<div class="empty-state">No frames marked yet.<br>Watch the video and mark interesting frames.</div>';
        countEl.textContent = '0';
        return;
    }}

    countEl.textContent = markers.length.toString();

    container.innerHTML = markers.map(m => `
        <div class="marker-item ${{m.status}}">
            <div class="marker-header">
                <span class="marker-time">${{formatTime(m.timestamp)}}</span>
                <span class="marker-status">
                    ${{m.status === 'analyzing' ? '<span class="spinner"></span> Analyzing...' :
                      m.status === 'completed' ? 'Analyzed' :
                      m.status === 'error' ? 'Error' : 'Pending'}}
                </span>
            </div>
            <div class="marker-transcript">${{m.transcript || '(no transcript)'}}</div>
            ${{m.result ? `
                <div class="marker-result">
                    <strong>${{m.result.category}}</strong> (${{m.result.severity}})<br>
                    ${{m.result.summary}}
                </div>
            ` : ''}}
            ${{m.status === 'pending' ? `
                <button onclick="analyzeMarker('${{m.marker_id}}')" style="margin-top: var(--space-sm);">
                    Analyze
                </button>
            ` : ''}}
        </div>
    `).join('');
}}

// Fetch and refresh markers
async function refreshMarkers() {{
    const response = await fetch('/api/markers');
    const markers = await response.json();
    updateMarkersList(markers);
}}

// Analyze a specific marker
async function analyzeMarker(markerId) {{
    document.getElementById('statusText').textContent = 'Analyzing...';

    const response = await fetch('/api/analyze/' + markerId, {{
        method: 'POST'
    }});

    if (response.ok) {{
        await refreshMarkers();
    }}
    document.getElementById('statusText').textContent = 'Ready';
}}

// Export findings as JSON
async function exportFindings() {{
    const response = await fetch('/api/export');
    if (!response.ok) {{
        document.getElementById('statusText').textContent = 'Export failed';
        return;
    }}
    const data = await response.json();
    downloadJson(data, 'analyze_findings.json');
}}

function downloadJson(data, filename) {{
    const blob = new Blob([JSON.stringify(data, null, 2)], {{ type: 'application/json' }});
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
}}

function updateFinalizeProgress(state) {{
    const wrap = document.getElementById('finalizeProgress');
    const fill = document.getElementById('finalizeProgressFill');
    const label = document.getElementById('finalizeProgressLabel');
    const errors = document.getElementById('finalizeProgressErrors');

    if (!wrap || !fill || !label || !errors) return;

    wrap.hidden = false;
    const total = Number(state.total || 0);
    const processed = Number(state.processed || 0);
    const ratio = total > 0 ? (processed / total) : (state.status === 'completed' ? 1 : 0);

    fill.style.width = `${{Math.max(0, Math.min(100, ratio * 100))}}%`;
    label.textContent = `${{processed}}/${{total}}`;
    errors.textContent = `${{Number(state.errors || 0)}} errors`;
}}

function hideFinalizeProgress() {{
    const wrap = document.getElementById('finalizeProgress');
    if (wrap) wrap.hidden = true;
}}

function sleep(ms) {{
    return new Promise(resolve => setTimeout(resolve, ms));
}}

// Finalize annotations -> analyze all -> export JSON
async function generateFullReport() {{
    const statusEl = document.getElementById('statusText');
    const finalizeBtn = document.getElementById('finalizeBtn');
    if (finalizeBtn) finalizeBtn.disabled = true;
    hideFinalizeProgress();

    statusEl.textContent = 'Finalizing annotations...';
    try {{
        const startResponse = await fetch('/api/finalize/start', {{
            method: 'POST'
        }});
        if (!startResponse.ok) {{
            throw new Error('Finalize start failed: ' + startResponse.status);
        }}

        let state = await startResponse.json();
        const jobId = state.job_id;
        if (!jobId) {{
            throw new Error('Finalize job id missing');
        }}

        updateFinalizeProgress(state);

        while (state.status === 'running') {{
            await sleep(250);
            const statusResponse = await fetch('/api/finalize/status/' + jobId);
            if (!statusResponse.ok) {{
                throw new Error('Finalize status failed: ' + statusResponse.status);
            }}
            state = await statusResponse.json();
            updateFinalizeProgress(state);
            statusEl.textContent = `Finalizing... ${{state.processed || 0}}/${{state.total || 0}}`;
        }}

        if (state.status !== 'completed') {{
            throw new Error(state.last_error || 'Finalize failed');
        }}

        const resultResponse = await fetch('/api/finalize/result/' + jobId);
        if (!resultResponse.ok) {{
            throw new Error('Finalize result failed: ' + resultResponse.status);
        }}
        const payload = await resultResponse.json();
        await refreshMarkers();
        downloadJson(payload.export, 'analyze_findings.json');

        const summary = payload.analysis || {{}};
        statusEl.textContent = `Done: ${{summary.completed || 0}} completed, ${{summary.errors || 0}} errors`;
    }} catch (error) {{
        console.error(error);
        statusEl.textContent = 'Finalize failed';
    }} finally {{
        if (finalizeBtn) finalizeBtn.disabled = false;
    }}
}}

// Initialize
document.addEventListener('DOMContentLoaded', () => {{
    const video = document.getElementById('videoPlayer');
    const micBtn = document.getElementById('micBtn');
    const recordingStatus = document.getElementById('recordingStatus');
    const transcriptPreview = document.getElementById('transcriptPreview');
    const notesInput = document.getElementById('notesInput');
    const markFrameBtn = document.getElementById('markFrameBtn');

    const recorder = new VoiceRecorder((text) => {{
        transcriptPreview.textContent = text;
        transcriptPreview.classList.add('has-text');
    }});

    const frameMarker = new FrameMarker(video);

    // Mic button - hold to record
    micBtn.addEventListener('mousedown', async () => {{
        const started = await recorder.start();
        if (started) {{
            micBtn.classList.add('recording');
            recordingStatus.classList.add('active');
        }}
    }});

    micBtn.addEventListener('mouseup', () => {{
        recorder.stop();
        micBtn.classList.remove('recording');
        recordingStatus.classList.remove('active');
    }});

    micBtn.addEventListener('mouseleave', () => {{
        if (recorder.isRecording) {{
            recorder.stop();
            micBtn.classList.remove('recording');
            recordingStatus.classList.remove('active');
        }}
    }});

    // Mark frame button
    markFrameBtn.addEventListener('click', async () => {{
        const transcript = transcriptPreview.classList.contains('has-text')
            ? transcriptPreview.textContent
            : '';
        const notes = notesInput.value;

        await frameMarker.markCurrentFrame(transcript, notes);

        // Clear inputs
        transcriptPreview.textContent = 'Hold mic button to record, or type below';
        transcriptPreview.classList.remove('has-text');
        notesInput.value = '';

        // Refresh list
        await refreshMarkers();
    }});

    // Tab switching
    document.querySelectorAll('.tab-btn').forEach(btn => {{
        btn.addEventListener('click', () => {{
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
        }});
    }});

    // Initial load
    refreshMarkers();
}});
    </script>

</body>
</html>"""
        return HTMLResponse(content=html)

    @app.get("/video")
    async def serve_video() -> FileResponse:
        """Serve the video file."""
        if not video_path.exists():
            raise HTTPException(status_code=404, detail="Video not found")
        return FileResponse(
            video_path,
            media_type="video/mp4",
            filename=video_path.name,
        )

    @app.post("/api/stt")
    async def transcribe_voice(audio: Annotated[UploadFile, File()]) -> JSONResponse:
        """Transcribe voice recording to text."""
        from .transcribe import transcribe_audio

        # Save to temp file
        with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as tmp:
            content = await audio.read()
            tmp.write(content)
            tmp_path = Path(tmp.name)

        try:
            result = transcribe_audio(
                tmp_path,
                language=config.language,
                api_key=config.get_stt_api_key(),
                stt_endpoint=config.stt_endpoint,
                stt_model=config.stt_model,
            )
            with session.lock:
                session.last_response_id = result.response_id
            return JSONResponse(
                content={
                    "text": result.text,
                    "segments": [
                        {"start": s.start, "end": s.end, "text": s.text} for s in result.segments
                    ],
                    "response_id": result.response_id,
                }
            )
        finally:
            tmp_path.unlink(missing_ok=True)

    @app.post("/api/mark")
    async def mark_frame(request: MarkFrameRequest) -> JSONResponse:
        """Mark a frame for analysis."""
        marker_id = str(uuid.uuid4())[:8]
        marker = FrameMarker(
            marker_id=marker_id,
            timestamp=request.timestamp,
            frame_base64=request.frame_base64,
            transcript=request.transcript,
            notes=request.notes,
            status="pending",
        )
        with session.lock:
            session.markers[marker_id] = marker
        return JSONResponse(content={"marker_id": marker_id, "status": "pending"})

    @app.get("/api/markers")
    async def get_markers() -> JSONResponse:
        """Get all markers with their results."""
        return JSONResponse(content=build_markers_payload())

    @app.post("/api/analyze/{marker_id}")
    async def analyze_marked_frame(marker_id: str) -> JSONResponse:
        """Run VLM analysis on a marked frame."""
        return JSONResponse(content=analyze_single_marker(marker_id))

    @app.post("/api/analyze-all")
    async def analyze_all_marked_frames() -> JSONResponse:
        """Run VLM analysis for all pending markers."""
        return JSONResponse(content=analyze_all_pending_markers())

    @app.post("/api/finalize/start")
    async def start_finalize_job() -> JSONResponse:
        """Start async finalize job and return job metadata for polling."""
        with session.lock:
            running_job = next(
                (job for job in session.finalize_jobs.values() if job.status == "running"),
                None,
            )
            if running_job:
                return JSONResponse(content=serialize_finalize_job(running_job))

            job_id = str(uuid.uuid4())[:12]
            job = FinalizeJob(job_id=job_id)
            session.finalize_jobs[job_id] = job

        thread = threading.Thread(target=run_finalize_job, args=(job_id,), daemon=True)
        thread.start()
        return JSONResponse(content=serialize_finalize_job(job))

    @app.get("/api/finalize/status/{job_id}")
    async def get_finalize_job_status(job_id: str) -> JSONResponse:
        """Get current async finalize job status/progress."""
        job = get_finalize_job(job_id)
        return JSONResponse(content=serialize_finalize_job(job))

    @app.get("/api/finalize/result/{job_id}")
    async def get_finalize_job_result(job_id: str) -> JSONResponse:
        """Get final payload for completed finalize job."""
        job = get_finalize_job(job_id)
        with session.lock:
            status = job.status
            payload = job.export_payload
            last_error = job.last_error

        if status == "running":
            raise HTTPException(status_code=409, detail="Finalize job still running")
        if status == "error":
            raise HTTPException(status_code=500, detail=last_error or "Finalize job failed")
        if not payload:
            raise HTTPException(status_code=500, detail="Finalize result missing")
        return JSONResponse(content=payload)

    @app.post("/api/finalize")
    async def finalize_marked_frames() -> JSONResponse:
        """Finalize annotation session: analyze all markers and return export payload."""
        analysis_summary = analyze_all_pending_markers()
        payload = {
            "analysis": analysis_summary,
            "markers": build_markers_payload(),
            "export": build_export_payload(),
        }
        return JSONResponse(content=payload)

    @app.get("/api/export")
    async def export_findings() -> JSONResponse:
        """Export all findings as JSON."""
        return JSONResponse(content=build_export_payload())

    return app
