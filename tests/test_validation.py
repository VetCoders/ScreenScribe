"""Tests for model validation (fail fast)."""

from unittest.mock import MagicMock, patch

import httpx
import pytest

from screenscribe.config import ScreenScribeConfig
from screenscribe.validation import (
    APIKeyError,
    ModelValidationError,
    _check_llm_model,
    _check_stt_model,
    validate_models,
)

# --- Fixtures ---


@pytest.fixture
def config() -> ScreenScribeConfig:
    """Basic config with API key."""
    cfg = ScreenScribeConfig()
    cfg.api_key = "test-api-key"
    cfg.stt_model = "whisper-1"
    cfg.llm_model = "ai-suggestions"
    cfg.vision_model = "ai-suggestions"
    return cfg


@pytest.fixture
def config_no_key() -> ScreenScribeConfig:
    """Config without API key."""
    cfg = ScreenScribeConfig()
    cfg.api_key = ""
    return cfg


# --- API Key Tests ---


class TestAPIKeyValidation:
    """Tests for API key presence validation."""

    def test_missing_api_key_raises_error(self, config_no_key: ScreenScribeConfig) -> None:
        """Missing API key should raise APIKeyError."""
        with pytest.raises(APIKeyError) as exc_info:
            validate_models(config_no_key, use_semantic=True, use_vision=True)
        assert "No API key configured" in str(exc_info.value)

    def test_api_key_present_passes(self, config: ScreenScribeConfig) -> None:
        """Present API key should not raise on key check."""
        # Mock HTTP responses to avoid actual API calls
        with patch("screenscribe.validation.httpx.Client") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_client.return_value.__enter__.return_value.post.return_value = mock_response

            # Should not raise
            validate_models(config, use_semantic=False, use_vision=False)


# --- LLM Model Tests ---


class TestLLMModelValidation:
    """Tests for LLM model availability check."""

    def test_model_available_200(self, config: ScreenScribeConfig) -> None:
        """200 response means model is available."""
        with patch("screenscribe.validation.httpx.Client") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_client.return_value.__enter__.return_value.post.return_value = mock_response

            result = _check_llm_model(config, config.llm_model, "LLM")
            assert result is True

    def test_model_available_400(self, config: ScreenScribeConfig) -> None:
        """400 response means model exists (bad input but model recognized)."""
        with patch("screenscribe.validation.httpx.Client") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 400
            mock_client.return_value.__enter__.return_value.post.return_value = mock_response

            result = _check_llm_model(config, config.llm_model, "LLM")
            assert result is True

    def test_model_not_found_404(self, config: ScreenScribeConfig) -> None:
        """404 response means model not found."""
        with patch("screenscribe.validation.httpx.Client") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 404
            mock_client.return_value.__enter__.return_value.post.return_value = mock_response

            with pytest.raises(ModelValidationError) as exc_info:
                _check_llm_model(config, "nonexistent-model", "LLM")

            assert "nonexistent-model" in str(exc_info.value)
            assert exc_info.value.model_type == "LLM"
            assert exc_info.value.model_name == "nonexistent-model"

    def test_bad_api_key_401(self, config: ScreenScribeConfig) -> None:
        """401 response means bad API key."""
        with patch("screenscribe.validation.httpx.Client") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 401
            mock_client.return_value.__enter__.return_value.post.return_value = mock_response

            with pytest.raises(APIKeyError) as exc_info:
                _check_llm_model(config, config.llm_model, "LLM")

            assert "Invalid API key" in str(exc_info.value)

    def test_timeout_is_optimistic(self, config: ScreenScribeConfig) -> None:
        """Timeout should return True (optimistic - let pipeline try)."""
        with patch("screenscribe.validation.httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.post.side_effect = (
                httpx.TimeoutException("timeout")
            )

            result = _check_llm_model(config, config.llm_model, "LLM")
            assert result is True

    def test_connection_error_raises(self, config: ScreenScribeConfig) -> None:
        """Connection error should raise ModelValidationError."""
        with patch("screenscribe.validation.httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.post.side_effect = httpx.ConnectError(
                "connection refused"
            )

            with pytest.raises(ModelValidationError) as exc_info:
                _check_llm_model(config, config.llm_model, "LLM")

            assert "Cannot connect" in str(exc_info.value)


# --- STT Model Tests ---


class TestSTTModelValidation:
    """Tests for STT endpoint availability check."""

    def test_stt_endpoint_available_400(self, config: ScreenScribeConfig) -> None:
        """400 response means endpoint works (expected with empty file)."""
        with patch("screenscribe.validation.httpx.Client") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 400
            mock_client.return_value.__enter__.return_value.post.return_value = mock_response

            result = _check_stt_model(config)
            assert result is True

    def test_stt_bad_api_key_401(self, config: ScreenScribeConfig) -> None:
        """401 response means bad API key for STT."""
        with patch("screenscribe.validation.httpx.Client") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 401
            mock_client.return_value.__enter__.return_value.post.return_value = mock_response

            with pytest.raises(APIKeyError):
                _check_stt_model(config)


# --- Full Validation Tests ---


class TestValidateModels:
    """Tests for the main validate_models function."""

    def test_validates_stt_only_when_no_ai(self, config: ScreenScribeConfig) -> None:
        """When semantic=False and vision=False, only STT is validated."""
        with patch("screenscribe.validation._check_stt_model") as mock_stt:
            with patch("screenscribe.validation._check_llm_model") as mock_llm:
                mock_stt.return_value = True
                mock_llm.return_value = True

                validate_models(config, use_semantic=False, use_vision=False)

                mock_stt.assert_called_once()
                mock_llm.assert_not_called()

    def test_validates_llm_when_semantic(self, config: ScreenScribeConfig) -> None:
        """When semantic=True, LLM model is validated."""
        with patch("screenscribe.validation._check_stt_model") as mock_stt:
            with patch("screenscribe.validation._check_llm_model") as mock_llm:
                mock_stt.return_value = True
                mock_llm.return_value = True

                validate_models(config, use_semantic=True, use_vision=False)

                mock_stt.assert_called_once()
                assert mock_llm.call_count == 1
                # Check it was called with LLM model
                call_args = mock_llm.call_args
                assert call_args[0][1] == config.llm_model
                assert call_args[0][2] == "LLM"

    def test_validates_vision_when_enabled(self, config: ScreenScribeConfig) -> None:
        """When vision=True, Vision model is validated."""
        with patch("screenscribe.validation._check_stt_model") as mock_stt:
            with patch("screenscribe.validation._check_llm_model") as mock_llm:
                mock_stt.return_value = True
                mock_llm.return_value = True

                validate_models(config, use_semantic=False, use_vision=True)

                mock_stt.assert_called_once()
                assert mock_llm.call_count == 1
                # Check it was called with Vision model
                call_args = mock_llm.call_args
                assert call_args[0][1] == config.vision_model
                assert call_args[0][2] == "Vision"

    def test_validates_all_when_full_pipeline(self, config: ScreenScribeConfig) -> None:
        """Full pipeline validates STT, LLM, and Vision."""
        with patch("screenscribe.validation._check_stt_model") as mock_stt:
            with patch("screenscribe.validation._check_llm_model") as mock_llm:
                mock_stt.return_value = True
                mock_llm.return_value = True

                validate_models(config, use_semantic=True, use_vision=True)

                mock_stt.assert_called_once()
                # LLM called twice: once for LLM, once for Vision
                assert mock_llm.call_count == 2
