"""Integration tests for ScreenScribe with real API calls.

These tests require:
- LIBRAXIS_API_KEY environment variable
- Network access to api.libraxis.cloud

Run with: make test-integration
Or: LIBRAXIS_API_KEY=xxx pytest tests/test_integration.py -v -m integration
"""

import os

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


def get_api_key() -> str:
    """Get API key from environment."""
    key = os.environ.get("LIBRAXIS_API_KEY", "")
    if not key:
        pytest.skip("LIBRAXIS_API_KEY not set")
    return key


@pytest.fixture
def config_with_api() -> ScreenScribeConfig:
    """Config with API key from environment."""
    api_key = get_api_key()
    config = ScreenScribeConfig.load()
    config.api_key = api_key
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

        pois = semantic_prefilter(sample_transcription_pl, config_with_api)

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

        pois = semantic_prefilter(sample_transcription_en, config_with_api)

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

        pois = semantic_prefilter(sample_transcription_pl, config_with_api)

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

        pois = semantic_prefilter(sample_transcription_pl, config_with_api)

        # Get transcript time range
        min_time = min(s.start for s in sample_transcription_pl.segments)
        max_time = max(s.end for s in sample_transcription_pl.segments)

        for poi in pois:
            # Allow some tolerance for LLM timestamp estimation
            assert poi.timestamp_start >= min_time - 1.0, (
                f"Start {poi.timestamp_start} before transcript"
            )
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
        assert result.severity in ("critical", "high"), (
            f"Crash should be critical/high, got {result.severity}"
        )


# ============================================================================
# Config Integration Tests
# ============================================================================


class TestConfigIntegration:
    """Integration tests for configuration with API."""

    def test_config_loads_api_key_from_env(self) -> None:
        """Config correctly loads API key from environment."""
        api_key = get_api_key()

        config = ScreenScribeConfig.load()

        assert config.api_key == api_key

    def test_config_has_correct_endpoints(self) -> None:
        """Config has correct LibraxisAI endpoints."""
        get_api_key()  # Skip if no key

        config = ScreenScribeConfig.load()

        assert "libraxis.cloud" in config.api_base
        assert "libraxis.cloud" in config.llm_endpoint
        assert "/v1/responses" in config.llm_endpoint


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
        pois = semantic_prefilter(sample_transcription_pl, config_with_api)
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
        pois = semantic_prefilter(sample_transcription_pl, config_with_api)

        # Step 3: Merge
        if pois:
            merged_pois = merge_pois_with_detections(pois, keyword_detections)
            detections = pois_to_detections(merged_pois, sample_transcription_pl)

            # Combined should find at least as many as keywords alone
            assert len(detections) >= len(keyword_detections), "Combined should not lose findings"
