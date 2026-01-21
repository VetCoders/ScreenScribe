"""Integration tests for ScreenScribe with real API calls.

These tests require:
- API key configured in ~/.config/screenscribe/config.env
- Or LIBRAXIS_API_KEY environment variable
- Network access to api.libraxis.cloud

Run with: make test-integration
"""

from pathlib import Path

import pytest

from screenscribe.config import ScreenScribeConfig
from screenscribe.detect import Detection
from screenscribe.semantic import SemanticAnalysis, analyze_detection_semantically
from screenscribe.semantic_filter import (
    PointOfInterest,
    semantic_prefilter,
)
from screenscribe.transcribe import Segment, TranscriptionResult

# Skip all tests if no API key
pytestmark = pytest.mark.integration


@pytest.fixture
def config_with_api() -> ScreenScribeConfig:
    """Config with API key from config file or environment."""
    config = ScreenScribeConfig.load()
    if not config.get_llm_api_key():
        pytest.skip("No API key configured (set in ~/.config/screenscribe/config.env)")
    return config


@pytest.fixture
def sample_transcription_pl() -> TranscriptionResult:
    """Sample Polish transcription for testing."""
    return TranscriptionResult(
        text=(
            "Tutaj widzę problem z przyciskiem. Nie reaguje na kliknięcie. "
            "Trzeba to naprawić. Layout wygląda dobrze ale kolory są za ciemne. "
            "Formularz rejestracji ma błąd walidacji."
        ),
        segments=[
            Segment(id=0, start=0.0, end=4.0, text="Tutaj widzę problem z przyciskiem."),
            Segment(id=1, start=4.5, end=7.0, text="Nie reaguje na kliknięcie."),
            Segment(id=2, start=7.5, end=10.0, text="Trzeba to naprawić."),
            Segment(
                id=3, start=11.0, end=16.0, text="Layout wygląda dobrze ale kolory są za ciemne."
            ),
            Segment(id=4, start=17.0, end=21.0, text="Formularz rejestracji ma błąd walidacji."),
        ],
        language="pl",
    )


@pytest.fixture
def sample_transcription_en() -> TranscriptionResult:
    """Sample English transcription for testing."""
    return TranscriptionResult(
        text=(
            "I see a bug with the submit button. It doesn't respond to clicks. "
            "We need to fix this. The layout looks good but colors are too dark. "
            "The registration form has a validation error."
        ),
        segments=[
            Segment(id=0, start=0.0, end=4.0, text="I see a bug with the submit button."),
            Segment(id=1, start=4.5, end=7.0, text="It doesn't respond to clicks."),
            Segment(id=2, start=7.5, end=10.0, text="We need to fix this."),
            Segment(
                id=3, start=11.0, end=16.0, text="The layout looks good but colors are too dark."
            ),
            Segment(
                id=4, start=17.0, end=21.0, text="The registration form has a validation error."
            ),
        ],
        language="en",
    )


@pytest.fixture
def sample_detection() -> Detection:
    """Sample detection for semantic analysis."""
    return Detection(
        segment=Segment(id=0, start=0.0, end=4.0, text="Tutaj widzę problem z przyciskiem."),
        category="bug",
        keywords_found=["problem"],
        context="Tutaj widzę problem z przyciskiem. Nie reaguje na kliknięcie.",
    )


# ============================================================================
# Semantic Pre-filter Integration Tests
# ============================================================================


class TestSemanticPrefilterIntegration:
    """Integration tests for semantic_prefilter with real API."""

    @pytest.mark.slow
    def test_prefilter_polish_transcription(
        self,
        config_with_api: ScreenScribeConfig,
        sample_transcription_pl: TranscriptionResult,
    ) -> None:
        """Semantic pre-filter identifies issues in Polish transcription."""
        config_with_api.language = "pl"

        result = semantic_prefilter(sample_transcription_pl, config_with_api)
        pois = result.pois

        # Should identify at least some issues
        assert len(pois) >= 1, "Should identify at least one point of interest"

        # All POIs should be valid
        for poi in pois:
            assert isinstance(poi, PointOfInterest)
            assert poi.timestamp_start >= 0
            assert poi.timestamp_end > poi.timestamp_start
            assert poi.category in ("bug", "change", "ui", "performance", "accessibility", "other")
            assert 0.0 <= poi.confidence <= 1.0
            assert poi.reasoning  # Should have reasoning

    @pytest.mark.slow
    def test_prefilter_english_transcription(
        self,
        config_with_api: ScreenScribeConfig,
        sample_transcription_en: TranscriptionResult,
    ) -> None:
        """Semantic pre-filter identifies issues in English transcription."""
        config_with_api.language = "en"

        result = semantic_prefilter(sample_transcription_en, config_with_api)
        pois = result.pois

        # Should identify at least some issues
        assert len(pois) >= 1, "Should identify at least one point of interest"

        # Check categories make sense
        categories = {poi.category for poi in pois}
        assert len(categories) >= 1

    @pytest.mark.slow
    def test_prefilter_finds_bug_category(
        self,
        config_with_api: ScreenScribeConfig,
        sample_transcription_pl: TranscriptionResult,
    ) -> None:
        """Pre-filter should identify bug category from problem description."""
        config_with_api.language = "pl"

        result = semantic_prefilter(sample_transcription_pl, config_with_api)
        pois = result.pois

        # At least one should be bug-related
        bug_pois = [p for p in pois if p.category == "bug"]
        assert len(bug_pois) >= 1, "Should identify bug from 'problem z przyciskiem'"

    @pytest.mark.slow
    def test_prefilter_returns_valid_timestamps(
        self,
        config_with_api: ScreenScribeConfig,
        sample_transcription_pl: TranscriptionResult,
    ) -> None:
        """Pre-filter timestamps should be within transcript range."""
        config_with_api.language = "pl"

        result = semantic_prefilter(sample_transcription_pl, config_with_api)
        pois = result.pois

        # Get transcript time range
        min_time = min(s.start for s in sample_transcription_pl.segments)
        max_time = max(s.end for s in sample_transcription_pl.segments)

        for poi in pois:
            # Allow some tolerance for LLM timestamp estimation
            assert (
                poi.timestamp_start >= min_time - 1.0
            ), f"Start {poi.timestamp_start} before transcript"
            assert poi.timestamp_end <= max_time + 1.0, f"End {poi.timestamp_end} after transcript"


# ============================================================================
# Semantic Analysis Integration Tests
# ============================================================================


class TestSemanticAnalysisIntegration:
    """Integration tests for semantic analysis with real API."""

    @pytest.mark.slow
    def test_analyze_detection_returns_result(
        self,
        config_with_api: ScreenScribeConfig,
        sample_detection: Detection,
    ) -> None:
        """Semantic analysis returns valid result."""
        config_with_api.language = "pl"

        result = analyze_detection_semantically(sample_detection, config_with_api)

        assert result is not None, "Should return analysis result"
        assert isinstance(result, SemanticAnalysis)
        assert result.detection_id == sample_detection.segment.id
        assert result.category == sample_detection.category
        assert result.severity in ("critical", "high", "medium", "low")
        assert result.summary  # Should have summary
        assert isinstance(result.action_items, list)
        assert isinstance(result.affected_components, list)

    @pytest.mark.slow
    def test_analyze_detection_severity_assessment(
        self,
        config_with_api: ScreenScribeConfig,
    ) -> None:
        """Semantic analysis assesses severity appropriately."""
        # Create a critical-sounding detection
        critical_detection = Detection(
            segment=Segment(
                id=0,
                start=0.0,
                end=5.0,
                text="Aplikacja się crashuje przy każdym otwarciu. Użytkownicy tracą dane.",
            ),
            category="bug",
            keywords_found=["crashuje"],
            context="Aplikacja się crashuje przy każdym otwarciu. Użytkownicy tracą dane.",
        )
        config_with_api.language = "pl"

        result = analyze_detection_semantically(critical_detection, config_with_api)

        assert result is not None
        # Critical crash should be high or critical severity
        assert result.severity in (
            "critical",
            "high",
        ), f"Crash should be critical/high, got {result.severity}"


# ============================================================================
# Config Integration Tests
# ============================================================================


class TestConfigIntegration:
    """Integration tests for configuration with API."""

    def test_config_loads_api_key(self, config_with_api: ScreenScribeConfig) -> None:
        """Config correctly loads API key from config file or environment."""
        assert config_with_api.get_llm_api_key()

    def test_config_has_valid_endpoints(self, config_with_api: ScreenScribeConfig) -> None:
        """Config has valid API endpoints."""
        # Endpoints should be HTTPS URLs with proper paths
        assert config_with_api.llm_endpoint.startswith("https://")
        assert "/v1/" in config_with_api.llm_endpoint
        assert config_with_api.stt_endpoint.startswith("https://")
        assert "/v1/" in config_with_api.stt_endpoint


# ============================================================================
# End-to-End Workflow Tests
# ============================================================================


class TestEndToEndWorkflow:
    """End-to-end workflow tests."""

    @pytest.mark.slow
    def test_full_semantic_pipeline_polish(
        self,
        config_with_api: ScreenScribeConfig,
        sample_transcription_pl: TranscriptionResult,
    ) -> None:
        """Full semantic pipeline: prefilter -> convert -> analyze."""
        from screenscribe.semantic_filter import pois_to_detections

        config_with_api.language = "pl"

        # Step 1: Semantic pre-filter
        result = semantic_prefilter(sample_transcription_pl, config_with_api)
        pois = result.pois
        assert len(pois) >= 1, "Pre-filter should find issues"

        # Step 2: Convert to detections
        detections = pois_to_detections(pois, sample_transcription_pl)
        assert len(detections) == len(pois)

        # Step 3: Semantic analysis on first detection
        if detections:
            analysis = analyze_detection_semantically(detections[0], config_with_api)
            assert analysis is not None, "Analysis should succeed"
            assert analysis.summary, "Should have summary"

    @pytest.mark.slow
    def test_combined_mode_workflow(
        self,
        config_with_api: ScreenScribeConfig,
        sample_transcription_pl: TranscriptionResult,
    ) -> None:
        """Combined mode: keywords + semantic pre-filter."""
        from screenscribe.detect import detect_issues
        from screenscribe.semantic_filter import merge_pois_with_detections, pois_to_detections

        config_with_api.language = "pl"

        # Step 1: Keyword detection
        keyword_detections = detect_issues(sample_transcription_pl)

        # Step 2: Semantic pre-filter
        result = semantic_prefilter(sample_transcription_pl, config_with_api)
        pois = result.pois

        # Step 3: Merge
        if pois:
            merged_pois = merge_pois_with_detections(pois, keyword_detections)
            detections = pois_to_detections(merged_pois, sample_transcription_pl)

            # Combined mode should produce results (semantic may group multiple keyword findings)
            assert len(detections) >= 1, "Combined should produce at least one finding"
            # Verify the merge worked - should have some detections
            assert len(merged_pois) >= 1, "Merge should produce POIs"


# ============================================================================
# Analyze Server Tests
# ============================================================================


class TestAnalyzeServer:
    """Integration tests for analyze server."""

    @pytest.fixture
    def sample_video(self, tmp_path: Path) -> Path:
        """Create a minimal valid video file for testing."""
        # Create a tiny valid MP4 (ftyp box only - enough for server to accept)
        video_path = tmp_path / "test_video.mp4"
        # Minimal ftyp box that makes file recognizable as MP4
        ftyp = b"\x00\x00\x00\x14ftypmp42\x00\x00\x00\x00mp42"
        video_path.write_bytes(ftyp)
        return video_path

    def test_analyze_app_creates(
        self, config_with_api: ScreenScribeConfig, sample_video: Path
    ) -> None:
        """Analyze app is created successfully."""
        from screenscribe.analyze_server import create_analyze_app

        app = create_analyze_app(sample_video, config_with_api)

        assert app is not None
        assert app.title == "ScreenScribe Analyze"

    def test_analyze_index_returns_html(
        self, config_with_api: ScreenScribeConfig, sample_video: Path
    ) -> None:
        """Index endpoint returns HTML page."""
        from fastapi.testclient import TestClient

        from screenscribe.analyze_server import create_analyze_app

        app = create_analyze_app(sample_video, config_with_api)
        client = TestClient(app)

        response = client.get("/")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "ScreenScribe Analyze" in response.text

    def test_analyze_markers_empty_initially(
        self, config_with_api: ScreenScribeConfig, sample_video: Path
    ) -> None:
        """Markers endpoint returns empty list initially."""
        from fastapi.testclient import TestClient

        from screenscribe.analyze_server import create_analyze_app

        app = create_analyze_app(sample_video, config_with_api)
        client = TestClient(app)

        response = client.get("/api/markers")

        assert response.status_code == 200
        assert response.json() == []

    def test_analyze_mark_frame(
        self, config_with_api: ScreenScribeConfig, sample_video: Path
    ) -> None:
        """Mark frame endpoint creates marker."""
        from fastapi.testclient import TestClient

        from screenscribe.analyze_server import create_analyze_app

        app = create_analyze_app(sample_video, config_with_api)
        client = TestClient(app)

        # Mark a frame
        response = client.post(
            "/api/mark",
            json={
                "timestamp": 5.0,
                "frame_base64": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
                "transcript": "Test transcript",
                "notes": "Test notes",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "marker_id" in data
        assert data["status"] == "pending"

        # Verify marker exists
        markers = client.get("/api/markers").json()
        assert len(markers) == 1
        assert markers[0]["timestamp"] == 5.0

    def test_analyze_page_respects_language_setting(
        self, config_with_api: ScreenScribeConfig, sample_video: Path
    ) -> None:
        """Page sets HTML lang attribute based on config."""
        from fastapi.testclient import TestClient

        from screenscribe.analyze_server import create_analyze_app

        # Test PL
        config_with_api.language = "pl"
        app = create_analyze_app(sample_video, config_with_api)
        client = TestClient(app)
        response = client.get("/")
        assert 'lang="pl"' in response.text

        # Test EN
        config_with_api.language = "en"
        app = create_analyze_app(sample_video, config_with_api)
        client = TestClient(app)
        response = client.get("/")
        assert 'lang="en"' in response.text

    def test_analyze_page_has_ui_controls(
        self, config_with_api: ScreenScribeConfig, sample_video: Path
    ) -> None:
        """Page has Mark Frame and Record controls."""
        from fastapi.testclient import TestClient

        from screenscribe.analyze_server import create_analyze_app

        app = create_analyze_app(sample_video, config_with_api)
        client = TestClient(app)

        response = client.get("/")
        html = response.text

        # UI control buttons
        assert "Mark Frame" in html or "markFrame" in html
        assert "Record" in html or "record" in html.lower()

    def test_analyze_page_has_video_player(
        self, config_with_api: ScreenScribeConfig, sample_video: Path
    ) -> None:
        """Page contains video player element."""
        from fastapi.testclient import TestClient

        from screenscribe.analyze_server import create_analyze_app

        app = create_analyze_app(sample_video, config_with_api)
        client = TestClient(app)

        response = client.get("/")
        html = response.text

        # Video player
        assert "<video" in html
        assert 'id="videoPlayer"' in html or 'id="video"' in html

    def test_analyze_page_has_mic_button(
        self, config_with_api: ScreenScribeConfig, sample_video: Path
    ) -> None:
        """Page contains microphone button for voice recording."""
        from fastapi.testclient import TestClient

        from screenscribe.analyze_server import create_analyze_app

        app = create_analyze_app(sample_video, config_with_api)
        client = TestClient(app)

        response = client.get("/")
        html = response.text

        # Mic button (Phosphor icon SVG or button)
        assert "mic" in html.lower() or "microphone" in html.lower() or "record" in html.lower()

    def test_analyze_page_has_theme_support(
        self, config_with_api: ScreenScribeConfig, sample_video: Path
    ) -> None:
        """Page has CSS variables for theming (light/dark mode support)."""
        from fastapi.testclient import TestClient

        from screenscribe.analyze_server import create_analyze_app

        app = create_analyze_app(sample_video, config_with_api)
        client = TestClient(app)

        response = client.get("/")
        html = response.text

        # CSS custom properties for theming
        assert "--bg" in html or "--background" in html or "prefers-color-scheme" in html

    def test_analyze_page_has_voicerecorder_js(
        self, config_with_api: ScreenScribeConfig, sample_video: Path
    ) -> None:
        """Page contains VoiceRecorder JavaScript class."""
        from fastapi.testclient import TestClient

        from screenscribe.analyze_server import create_analyze_app

        app = create_analyze_app(sample_video, config_with_api)
        client = TestClient(app)

        response = client.get("/")
        html = response.text

        # VoiceRecorder class and MediaRecorder API usage
        assert "VoiceRecorder" in html
        assert "MediaRecorder" in html
