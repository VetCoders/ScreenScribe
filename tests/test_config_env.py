"""Tests for ScreenScribeConfig environment key handling."""

from screenscribe.config import ScreenScribeConfig


class TestConfigApiBase:
    """Tests for API base normalization and endpoint derivation."""

    def test_api_base_normalizes_and_derives_endpoints(self) -> None:
        """SCREENSCRIBE_API_BASE normalizes base and derives endpoints."""
        config = ScreenScribeConfig()

        config._set_from_key("SCREENSCRIBE_API_BASE", "https://example.com/v1/")

        assert config.api_base == "https://example.com"
        assert config.stt_endpoint == "https://example.com/v1/audio/transcriptions"
        assert config.llm_endpoint == "https://example.com/v1/responses"
        assert config.vision_endpoint == "https://example.com/v1/responses"

    def test_api_base_does_not_override_explicit_endpoints(self) -> None:
        """Explicit endpoints remain unchanged when API base is set."""
        config = ScreenScribeConfig()
        config.stt_endpoint = "https://stt.example.com/custom"
        config.llm_endpoint = "https://llm.example.com/custom"
        config.vision_endpoint = "https://vision.example.com/custom"

        config._set_from_key("SCREENSCRIBE_API_BASE", "https://api.example.com")

        assert config.stt_endpoint == "https://stt.example.com/custom"
        assert config.llm_endpoint == "https://llm.example.com/custom"
        assert config.vision_endpoint == "https://vision.example.com/custom"
