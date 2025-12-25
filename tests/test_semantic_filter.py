"""Tests for semantic filtering pipeline."""

import json

import pytest

from screenscribe.detect import Detection
from screenscribe.semantic_filter import (
    PointOfInterest,
    SemanticFilterLevel,
    _extract_content_from_response,
    _parse_prefilter_response,
    format_transcript_with_timestamps,
    get_semantic_prefilter_prompt,
    merge_pois_with_detections,
    poi_to_detection,
    pois_to_detections,
)
from screenscribe.transcribe import Segment, TranscriptionResult


# --- Fixtures ---


@pytest.fixture
def sample_transcription() -> TranscriptionResult:
    """Sample transcription for testing."""
    return TranscriptionResult(
        text="Przycisk nie działa. Trzeba to naprawić. Layout wygląda dobrze.",
        segments=[
            Segment(id=0, start=0.0, end=3.0, text="Przycisk nie działa."),
            Segment(id=1, start=3.5, end=6.0, text="Trzeba to naprawić."),
            Segment(id=2, start=7.0, end=10.0, text="Layout wygląda dobrze."),
        ],
        language="pl",
    )


@pytest.fixture
def sample_poi() -> PointOfInterest:
    """Sample point of interest for testing."""
    return PointOfInterest(
        timestamp_start=0.0,
        timestamp_end=3.0,
        category="bug",
        confidence=0.85,
        reasoning="User says button doesn't work",
        transcript_excerpt="Przycisk nie działa.",
        segment_ids=[0],
    )


@pytest.fixture
def sample_detection() -> Detection:
    """Sample detection for testing."""
    return Detection(
        segment=Segment(id=0, start=0.0, end=3.0, text="Przycisk nie działa."),
        category="bug",
        keywords_found=["nie działa"],
        context="Przycisk nie działa. Trzeba to naprawić.",
    )


# --- Test SemanticFilterLevel ---


class TestSemanticFilterLevel:
    """Tests for SemanticFilterLevel enum."""

    def test_keywords_level_value(self) -> None:
        """Keywords level has correct string value."""
        assert SemanticFilterLevel.KEYWORDS.value == "keywords"

    def test_base_level_value(self) -> None:
        """Base level has correct string value."""
        assert SemanticFilterLevel.BASE.value == "base"

    def test_combined_level_value(self) -> None:
        """Combined level has correct string value."""
        assert SemanticFilterLevel.COMBINED.value == "combined"

    def test_from_string_keywords(self) -> None:
        """Can create KEYWORDS from string."""
        level = SemanticFilterLevel("keywords")
        assert level == SemanticFilterLevel.KEYWORDS

    def test_from_string_base(self) -> None:
        """Can create BASE from string."""
        level = SemanticFilterLevel("base")
        assert level == SemanticFilterLevel.BASE

    def test_from_string_combined(self) -> None:
        """Can create COMBINED from string."""
        level = SemanticFilterLevel("combined")
        assert level == SemanticFilterLevel.COMBINED

    def test_invalid_string_raises(self) -> None:
        """Invalid string raises ValueError."""
        with pytest.raises(ValueError):
            SemanticFilterLevel("invalid")

    def test_all_levels_exist(self) -> None:
        """All expected levels exist."""
        levels = list(SemanticFilterLevel)
        assert len(levels) == 3
        assert SemanticFilterLevel.KEYWORDS in levels
        assert SemanticFilterLevel.BASE in levels
        assert SemanticFilterLevel.COMBINED in levels


# --- Test PointOfInterest ---


class TestPointOfInterest:
    """Tests for PointOfInterest dataclass."""

    def test_midpoint_calculation(self, sample_poi: PointOfInterest) -> None:
        """Midpoint is correctly calculated."""
        assert sample_poi.midpoint == 1.5  # (0.0 + 3.0) / 2

    def test_midpoint_with_offset(self) -> None:
        """Midpoint works with non-zero start."""
        poi = PointOfInterest(
            timestamp_start=10.0,
            timestamp_end=20.0,
            category="ui",
            confidence=0.7,
            reasoning="Test",
            transcript_excerpt="Test",
            segment_ids=[],
        )
        assert poi.midpoint == 15.0

    def test_category_types(self) -> None:
        """All category types are valid."""
        categories = ["bug", "change", "ui", "performance", "accessibility", "other"]
        for cat in categories:
            poi = PointOfInterest(
                timestamp_start=0.0,
                timestamp_end=1.0,
                category=cat,
                confidence=0.5,
                reasoning="Test",
                transcript_excerpt="Test",
            )
            assert poi.category == cat

    def test_default_segment_ids(self) -> None:
        """Segment IDs default to empty list."""
        poi = PointOfInterest(
            timestamp_start=0.0,
            timestamp_end=1.0,
            category="bug",
            confidence=0.5,
            reasoning="Test",
            transcript_excerpt="Test",
        )
        assert poi.segment_ids == []

    def test_confidence_range(self, sample_poi: PointOfInterest) -> None:
        """Confidence is within expected range."""
        assert 0.0 <= sample_poi.confidence <= 1.0


# --- Test format_transcript_with_timestamps ---


class TestFormatTranscriptWithTimestamps:
    """Tests for format_transcript_with_timestamps function."""

    def test_empty_transcription(self) -> None:
        """Empty transcription returns empty string."""
        transcription = TranscriptionResult(text="", segments=[], language="pl")
        result = format_transcript_with_timestamps(transcription)
        assert result == ""

    def test_single_segment(self) -> None:
        """Single segment is formatted correctly."""
        transcription = TranscriptionResult(
            text="Hello",
            segments=[Segment(id=0, start=0.0, end=2.0, text="Hello")],
            language="en",
        )
        result = format_transcript_with_timestamps(transcription)
        assert "[0.0s - 2.0s]" in result
        assert "Hello" in result

    def test_multiple_segments(self, sample_transcription: TranscriptionResult) -> None:
        """Multiple segments are each on separate lines."""
        result = format_transcript_with_timestamps(sample_transcription)
        lines = result.strip().split("\n")
        assert len(lines) == 3

    def test_timestamp_format(self, sample_transcription: TranscriptionResult) -> None:
        """Timestamps are formatted with brackets."""
        result = format_transcript_with_timestamps(sample_transcription)
        assert "[0.0s - 3.0s]" in result
        assert "[3.5s - 6.0s]" in result
        assert "[7.0s - 10.0s]" in result

    def test_text_included(self, sample_transcription: TranscriptionResult) -> None:
        """Segment text is included."""
        result = format_transcript_with_timestamps(sample_transcription)
        assert "Przycisk nie działa." in result
        assert "Trzeba to naprawić." in result
        assert "Layout wygląda dobrze." in result


# --- Test get_semantic_prefilter_prompt ---


class TestGetSemanticPrefilterPrompt:
    """Tests for get_semantic_prefilter_prompt function."""

    def test_polish_prompt(self) -> None:
        """Polish prompt is returned for 'pl'."""
        prompt = get_semantic_prefilter_prompt("pl")
        assert "Jesteś ekspertem" in prompt
        assert "transkrypcję" in prompt

    def test_english_prompt(self) -> None:
        """English prompt is returned for 'en'."""
        prompt = get_semantic_prefilter_prompt("en")
        assert "You are a UX/UI expert" in prompt
        assert "transcript" in prompt

    def test_default_to_english(self) -> None:
        """Unknown language defaults to English."""
        prompt = get_semantic_prefilter_prompt("de")
        assert "You are a UX/UI expert" in prompt

    def test_polish_variants(self) -> None:
        """Polish language variants return Polish prompt."""
        for lang in ["pl", "pl-pl", "polish", "polski"]:
            prompt = get_semantic_prefilter_prompt(lang)
            assert "Jesteś ekspertem" in prompt

    def test_prompt_contains_placeholder(self) -> None:
        """Prompt contains transcript placeholder."""
        prompt = get_semantic_prefilter_prompt("pl")
        assert "{transcript_with_timestamps}" in prompt


# --- Test _extract_content_from_response ---


class TestExtractContentFromResponse:
    """Tests for _extract_content_from_response function."""

    def test_empty_response(self) -> None:
        """Empty response returns empty string."""
        result = _extract_content_from_response({})
        assert result == ""

    def test_output_text_type(self) -> None:
        """Extracts content from output_text type."""
        response = {"output": [{"type": "output_text", "text": "Hello"}]}
        result = _extract_content_from_response(response)
        assert result == "Hello"

    def test_text_type(self) -> None:
        """Extracts content from text type."""
        response = {"output": [{"type": "text", "text": "World"}]}
        result = _extract_content_from_response(response)
        assert result == "World"

    def test_message_with_output_text(self) -> None:
        """Extracts content from message with output_text."""
        response = {
            "output": [
                {
                    "type": "message",
                    "content": [{"type": "output_text", "text": "Content"}],
                }
            ]
        }
        result = _extract_content_from_response(response)
        assert result == "Content"

    def test_message_with_text(self) -> None:
        """Extracts content from message with text."""
        response = {
            "output": [
                {
                    "type": "message",
                    "content": [{"type": "text", "text": "Content"}],
                }
            ]
        }
        result = _extract_content_from_response(response)
        assert result == "Content"

    def test_skips_reasoning(self) -> None:
        """Skips reasoning blocks."""
        response = {
            "output": [
                {"type": "reasoning", "content": [{"type": "reasoning_text", "text": "Thinking..."}]},
                {"type": "output_text", "text": "Result"},
            ]
        }
        result = _extract_content_from_response(response)
        assert "Thinking" not in result
        assert result == "Result"

    def test_concatenates_multiple(self) -> None:
        """Concatenates multiple content items."""
        response = {
            "output": [
                {"type": "text", "text": "Part1"},
                {"type": "text", "text": "Part2"},
            ]
        }
        result = _extract_content_from_response(response)
        assert result == "Part1Part2"


# --- Test _parse_prefilter_response ---


class TestParsePrefilterResponse:
    """Tests for _parse_prefilter_response function."""

    @pytest.fixture
    def transcription(self) -> TranscriptionResult:
        """Simple transcription for parsing tests."""
        return TranscriptionResult(
            text="Test",
            segments=[
                Segment(id=0, start=0.0, end=5.0, text="Test segment"),
                Segment(id=1, start=5.0, end=10.0, text="Another segment"),
            ],
            language="pl",
        )

    def test_valid_json_response(self, transcription: TranscriptionResult) -> None:
        """Parses valid JSON response correctly."""
        content = json.dumps(
            {
                "points_of_interest": [
                    {
                        "timestamp_start": 0.0,
                        "timestamp_end": 5.0,
                        "category": "bug",
                        "confidence": 0.9,
                        "reasoning": "Test reason",
                        "transcript_excerpt": "Test",
                    }
                ],
                "total_issues_found": 1,
                "analysis_notes": "Test notes",
            }
        )
        result = _parse_prefilter_response(content, transcription)
        assert len(result) == 1
        assert result[0].category == "bug"
        assert result[0].confidence == 0.9

    def test_json_in_markdown_block(self, transcription: TranscriptionResult) -> None:
        """Parses JSON wrapped in markdown code block."""
        content = '```json\n{"points_of_interest": []}\n```'
        result = _parse_prefilter_response(content, transcription)
        assert result == []

    def test_json_with_prefix_text(self, transcription: TranscriptionResult) -> None:
        """Parses JSON with prefix text."""
        content = 'Here is the result:\n{"points_of_interest": []}'
        result = _parse_prefilter_response(content, transcription)
        assert result == []

    def test_invalid_json_returns_empty(self, transcription: TranscriptionResult) -> None:
        """Invalid JSON returns empty list."""
        result = _parse_prefilter_response("not valid json", transcription)
        assert result == []

    def test_strips_control_tokens(self, transcription: TranscriptionResult) -> None:
        """Strips model control tokens."""
        content = '<|channel|>final {"points_of_interest": []}'
        result = _parse_prefilter_response(content, transcription)
        assert result == []

    def test_matches_segment_ids(self, transcription: TranscriptionResult) -> None:
        """Matches segment IDs within time range."""
        content = json.dumps(
            {
                "points_of_interest": [
                    {
                        "timestamp_start": 0.0,
                        "timestamp_end": 5.0,
                        "category": "bug",
                        "confidence": 0.8,
                        "reasoning": "Test",
                        "transcript_excerpt": "Test",
                    }
                ]
            }
        )
        result = _parse_prefilter_response(content, transcription)
        assert len(result) == 1
        assert 0 in result[0].segment_ids

    def test_multiple_pois(self, transcription: TranscriptionResult) -> None:
        """Parses multiple points of interest."""
        content = json.dumps(
            {
                "points_of_interest": [
                    {
                        "timestamp_start": 0.0,
                        "timestamp_end": 5.0,
                        "category": "bug",
                        "confidence": 0.8,
                        "reasoning": "Bug",
                        "transcript_excerpt": "Bug",
                    },
                    {
                        "timestamp_start": 5.0,
                        "timestamp_end": 10.0,
                        "category": "ui",
                        "confidence": 0.7,
                        "reasoning": "UI issue",
                        "transcript_excerpt": "UI",
                    },
                ]
            }
        )
        result = _parse_prefilter_response(content, transcription)
        assert len(result) == 2
        assert result[0].category == "bug"
        assert result[1].category == "ui"


# --- Test merge_pois_with_detections ---


class TestMergePoisWithDetections:
    """Tests for merge_pois_with_detections function."""

    def test_empty_inputs(self) -> None:
        """Empty inputs return empty list."""
        result = merge_pois_with_detections([], [])
        assert result == []

    def test_pois_only(self, sample_poi: PointOfInterest) -> None:
        """POIs without detections are returned."""
        result = merge_pois_with_detections([sample_poi], [])
        assert len(result) == 1
        assert result[0].category == "bug"

    def test_detections_only(self, sample_detection: Detection) -> None:
        """Detections without POIs are converted."""
        result = merge_pois_with_detections([], [sample_detection])
        assert len(result) == 1
        assert result[0].confidence == 0.7  # Keyword detection confidence

    def test_overlapping_boosts_confidence(
        self, sample_poi: PointOfInterest, sample_detection: Detection
    ) -> None:
        """Overlapping POI and detection boosts confidence."""
        original_confidence = sample_poi.confidence
        result = merge_pois_with_detections([sample_poi], [sample_detection])
        # Should boost confidence but not create duplicate
        assert len(result) == 1
        assert result[0].confidence >= original_confidence

    def test_non_overlapping_creates_both(self) -> None:
        """Non-overlapping items create separate entries."""
        poi = PointOfInterest(
            timestamp_start=0.0,
            timestamp_end=3.0,
            category="bug",
            confidence=0.8,
            reasoning="Bug",
            transcript_excerpt="Bug",
        )
        detection = Detection(
            segment=Segment(id=1, start=10.0, end=13.0, text="Change needed"),
            category="change",
            keywords_found=["trzeba"],
            context="Change needed",
        )
        result = merge_pois_with_detections([poi], [detection])
        assert len(result) == 2

    def test_sorted_by_timestamp(self) -> None:
        """Results are sorted by timestamp."""
        poi1 = PointOfInterest(
            timestamp_start=10.0,
            timestamp_end=12.0,
            category="ui",
            confidence=0.7,
            reasoning="UI",
            transcript_excerpt="UI",
        )
        poi2 = PointOfInterest(
            timestamp_start=0.0,
            timestamp_end=3.0,
            category="bug",
            confidence=0.8,
            reasoning="Bug",
            transcript_excerpt="Bug",
        )
        result = merge_pois_with_detections([poi1, poi2], [])
        assert result[0].timestamp_start < result[1].timestamp_start

    def test_merges_overlapping_pois(self) -> None:
        """Overlapping POIs are merged."""
        poi1 = PointOfInterest(
            timestamp_start=0.0,
            timestamp_end=5.0,
            category="bug",
            confidence=0.8,
            reasoning="Bug 1",
            transcript_excerpt="Bug 1",
        )
        poi2 = PointOfInterest(
            timestamp_start=4.0,
            timestamp_end=8.0,
            category="bug",
            confidence=0.7,
            reasoning="Bug 2",
            transcript_excerpt="Bug 2",
        )
        result = merge_pois_with_detections([poi1, poi2], [])
        # Should merge overlapping POIs
        assert len(result) == 1
        assert result[0].timestamp_start == 0.0
        assert result[0].timestamp_end == 8.0

    def test_confidence_cap(self) -> None:
        """Confidence boost is capped at 1.0."""
        poi = PointOfInterest(
            timestamp_start=0.0,
            timestamp_end=3.0,
            category="bug",
            confidence=0.95,
            reasoning="Bug",
            transcript_excerpt="Bug",
        )
        detection = Detection(
            segment=Segment(id=0, start=0.0, end=3.0, text="Bug"),
            category="bug",
            keywords_found=["bug"],
            context="Bug",
        )
        result = merge_pois_with_detections([poi], [detection])
        assert result[0].confidence <= 1.0


# --- Test poi_to_detection ---


class TestPoiToDetection:
    """Tests for poi_to_detection function."""

    def test_basic_conversion(
        self, sample_poi: PointOfInterest, sample_transcription: TranscriptionResult
    ) -> None:
        """POI is converted to Detection correctly."""
        result = poi_to_detection(sample_poi, sample_transcription)
        assert isinstance(result, Detection)
        assert result.category == "bug"
        assert result.segment.start == sample_poi.timestamp_start
        assert result.segment.end == sample_poi.timestamp_end

    def test_segment_text_from_excerpt(
        self, sample_poi: PointOfInterest, sample_transcription: TranscriptionResult
    ) -> None:
        """Detection segment text comes from POI excerpt."""
        result = poi_to_detection(sample_poi, sample_transcription)
        assert result.segment.text == sample_poi.transcript_excerpt

    def test_keywords_include_semantic_marker(
        self, sample_poi: PointOfInterest, sample_transcription: TranscriptionResult
    ) -> None:
        """Keywords include semantic marker."""
        result = poi_to_detection(sample_poi, sample_transcription)
        assert any("semantic:" in kw for kw in result.keywords_found)

    def test_context_includes_surrounding(
        self, sample_poi: PointOfInterest, sample_transcription: TranscriptionResult
    ) -> None:
        """Context includes surrounding segment text."""
        result = poi_to_detection(sample_poi, sample_transcription)
        # Context should include text from nearby segments
        assert len(result.context) > 0

    def test_category_normalization(self, sample_transcription: TranscriptionResult) -> None:
        """Non-standard categories are normalized."""
        poi = PointOfInterest(
            timestamp_start=0.0,
            timestamp_end=3.0,
            category="performance",  # Not in bug/change/ui
            confidence=0.8,
            reasoning="Slow",
            transcript_excerpt="Slow",
        )
        result = poi_to_detection(poi, sample_transcription)
        # Should be normalized to "ui" as fallback
        assert result.category in ("bug", "change", "ui")

    def test_segment_id_from_poi(
        self, sample_poi: PointOfInterest, sample_transcription: TranscriptionResult
    ) -> None:
        """Segment ID is taken from POI segment_ids."""
        result = poi_to_detection(sample_poi, sample_transcription)
        assert result.segment.id == sample_poi.segment_ids[0]


# --- Test pois_to_detections ---


class TestPoisToDetections:
    """Tests for pois_to_detections function."""

    def test_empty_list(self, sample_transcription: TranscriptionResult) -> None:
        """Empty POI list returns empty detection list."""
        result = pois_to_detections([], sample_transcription)
        assert result == []

    def test_multiple_pois(self, sample_transcription: TranscriptionResult) -> None:
        """Multiple POIs are all converted."""
        pois = [
            PointOfInterest(
                timestamp_start=0.0,
                timestamp_end=3.0,
                category="bug",
                confidence=0.8,
                reasoning="Bug",
                transcript_excerpt="Bug",
                segment_ids=[0],
            ),
            PointOfInterest(
                timestamp_start=3.5,
                timestamp_end=6.0,
                category="change",
                confidence=0.7,
                reasoning="Change",
                transcript_excerpt="Change",
                segment_ids=[1],
            ),
        ]
        result = pois_to_detections(pois, sample_transcription)
        assert len(result) == 2
        assert all(isinstance(d, Detection) for d in result)

    def test_preserves_order(self, sample_transcription: TranscriptionResult) -> None:
        """Order of POIs is preserved."""
        pois = [
            PointOfInterest(
                timestamp_start=3.5,
                timestamp_end=6.0,
                category="change",
                confidence=0.7,
                reasoning="Change",
                transcript_excerpt="Change",
                segment_ids=[1],
            ),
            PointOfInterest(
                timestamp_start=0.0,
                timestamp_end=3.0,
                category="bug",
                confidence=0.8,
                reasoning="Bug",
                transcript_excerpt="Bug",
                segment_ids=[0],
            ),
        ]
        result = pois_to_detections(pois, sample_transcription)
        assert result[0].category == "change"
        assert result[1].category == "bug"
