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

    @app.get("/", response_class=HTMLResponse)
    async def index() -> HTMLResponse:
        """Serve the analyze UI."""
        from .html_pro.assets import load_css, load_js_video_player

        # Load assets
        css = load_css()
        js_video = load_js_video_player()

        # Build analyze page (simplified version of report.html)
        html = f"""<!DOCTYPE html>
<html lang="pl">
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
        </div>
        <div class="export-buttons">
            <button onclick="exportFindings()" class="btn-secondary">Export JSON</button>
            <button onclick="generateFullReport()" class="btn-primary">Generate Full Report</button>
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
    const data = await response.json();

    const blob = new Blob([JSON.stringify(data, null, 2)], {{ type: 'application/json' }});
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'analyze_findings.json';
    a.click();
    URL.revokeObjectURL(url);
}}

// Generate full report (placeholder)
function generateFullReport() {{
    alert('Full report generation will process all marked frames through the complete pipeline.');
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
        session.markers[marker_id] = marker
        return JSONResponse(content={"marker_id": marker_id, "status": "pending"})

    @app.get("/api/markers")
    async def get_markers() -> JSONResponse:
        """Get all markers with their results."""
        markers_data = []
        for m in session.markers.values():
            data = {
                "marker_id": m.marker_id,
                "timestamp": m.timestamp,
                "transcript": m.transcript,
                "notes": m.notes,
                "status": m.status,
            }
            if m.marker_id in session.results:
                r = session.results[m.marker_id]
                data["result"] = {
                    "category": r.category,
                    "severity": r.severity,
                    "summary": r.summary,
                    "issues_detected": r.issues_detected,
                    "suggested_fix": r.suggested_fix,
                }
            markers_data.append(data)
        return JSONResponse(content=markers_data)

    @app.post("/api/analyze/{marker_id}")
    async def analyze_marked_frame(marker_id: str) -> JSONResponse:
        """Run VLM analysis on a marked frame."""
        from .detect import Detection
        from .transcribe import Segment
        from .unified_analysis import analyze_finding_unified

        if marker_id not in session.markers:
            raise HTTPException(status_code=404, detail="Marker not found")

        marker = session.markers[marker_id]
        marker.status = "analyzing"

        # Create a Detection object for the unified analysis
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

        # Save frame to temp file
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            frame_bytes = base64.b64decode(marker.frame_base64)
            tmp.write(frame_bytes)
            screenshot_path = Path(tmp.name)

        try:
            # Run VLM analysis
            finding = analyze_finding_unified(
                detection=detection,
                screenshot_path=screenshot_path,
                config=config,
                previous_response_id=session.last_response_id,
            )

            if finding:
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
                session.results[marker_id] = result
                session.last_response_id = finding.response_id
                marker.status = "completed"

                return JSONResponse(
                    content={
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
                )
            else:
                marker.status = "error"
                return JSONResponse(
                    content={"marker_id": marker_id, "status": "error", "error": "Analysis failed"}
                )
        finally:
            screenshot_path.unlink(missing_ok=True)

    @app.get("/api/export")
    async def export_findings() -> JSONResponse:
        """Export all findings as JSON."""
        markers_list: list[dict[str, Any]] = []
        export_data: dict[str, Any] = {
            "video": str(video_path),
            "markers": markers_list,
        }

        for m in session.markers.values():
            marker_data = {
                "marker_id": m.marker_id,
                "timestamp": m.timestamp,
                "transcript": m.transcript,
                "notes": m.notes,
            }
            if m.marker_id in session.results:
                r = session.results[m.marker_id]
                marker_data["analysis"] = {
                    "category": r.category,
                    "severity": r.severity,
                    "summary": r.summary,
                    "issues_detected": r.issues_detected,
                    "suggested_fix": r.suggested_fix,
                    "affected_components": r.affected_components,
                }
            export_data["markers"].append(marker_data)

        return JSONResponse(content=export_data)

    return app
