"""Model validation - fail fast before pipeline starts."""

import httpx
from rich.console import Console

from screenscribe.config import ScreenScribeConfig

console = Console()

# Validation timeout - short, just checking availability
VALIDATION_TIMEOUT = 10.0


class ModelValidationError(Exception):
    """Raised when model validation fails."""

    def __init__(self, message: str, model_type: str, model_name: str) -> None:
        super().__init__(message)
        self.model_type = model_type
        self.model_name = model_name


class APIKeyError(Exception):
    """Raised when API key is missing or invalid."""


def _check_llm_model(config: ScreenScribeConfig, model: str, model_type: str) -> bool:
    """Check if LLM/Vision model is available via minimal request.

    Returns True if model is available, raises on definitive failure.
    """
    try:
        with httpx.Client(timeout=VALIDATION_TIMEOUT) as client:
            # Minimal request - empty input will fail but model will be validated
            response = client.post(
                config.llm_endpoint,
                headers={
                    "x-api-key": config.api_key,
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "input": [
                        {"role": "user", "content": [{"type": "input_text", "text": "ping"}]}
                    ],
                    "max_tokens": 1,
                },
            )

            # 200 = model works
            if response.status_code == 200:
                return True

            # 400 = bad request but model recognized
            if response.status_code == 400:
                return True

            # 401 = bad API key
            if response.status_code == 401:
                raise APIKeyError("Invalid API key")

            # 404 = model not found
            if response.status_code == 404:
                raise ModelValidationError(
                    f"{model_type} model '{model}' not found",
                    model_type=model_type,
                    model_name=model,
                )

            # 503 = service unavailable (might be model issue or server issue)
            if response.status_code == 503:
                # Try to parse error message
                try:
                    error_data = response.json()
                    error_msg = error_data.get("error", {}).get("message", "")
                    if "model" in error_msg.lower():
                        raise ModelValidationError(
                            f"{model_type} model '{model}' unavailable: {error_msg}",
                            model_type=model_type,
                            model_name=model,
                        )
                except (ValueError, KeyError):
                    pass
                # Generic 503 - could be temporary
                console.print("[yellow]  Warning: API returned 503, model status unclear[/]")
                return True  # Optimistic - let pipeline try

            # Other errors - log but continue
            console.print(f"[yellow]  Warning: Unexpected status {response.status_code}[/]")
            return True

    except httpx.TimeoutException:
        console.print(f"[yellow]  Warning: Timeout checking {model_type} model[/]")
        return True  # Optimistic - let pipeline try

    except httpx.ConnectError as e:
        raise ModelValidationError(
            f"Cannot connect to API: {e}",
            model_type=model_type,
            model_name=model,
        ) from e


def _check_stt_model(config: ScreenScribeConfig) -> bool:
    """Check if STT endpoint is reachable.

    STT validation is limited - we can't easily test without audio.
    Just verify the endpoint responds.
    """
    try:
        with httpx.Client(timeout=VALIDATION_TIMEOUT) as client:
            # POST with empty file to check endpoint responds (400 expected)
            response = client.post(
                config.stt_endpoint,
                headers={"Authorization": f"Bearer {config.api_key}"},
                data={"model": config.stt_model},
                files={"file": ("test.mp3", b"", "audio/mpeg")},
            )

            # 400 = endpoint works, just bad input (expected)
            if response.status_code == 400:
                return True

            # 401 = bad API key
            if response.status_code == 401:
                raise APIKeyError("Invalid API key for STT endpoint")

            # 200 would be weird with empty file, but OK
            if response.status_code == 200:
                return True

            # Other - optimistic
            return True

    except httpx.TimeoutException:
        console.print("[yellow]  Warning: Timeout checking STT endpoint[/]")
        return True

    except httpx.ConnectError as e:
        raise ModelValidationError(
            f"Cannot connect to STT API: {e}",
            model_type="STT",
            model_name=config.stt_model,
        ) from e


def validate_models(
    config: ScreenScribeConfig,
    use_semantic: bool = True,
    use_vision: bool = True,
) -> None:
    """Validate model availability before pipeline starts.

    Args:
        config: ScreenScribe configuration
        use_semantic: Whether semantic analysis will be used
        use_vision: Whether vision analysis will be used

    Raises:
        APIKeyError: If API key is missing or invalid
        ModelValidationError: If a required model is not available
    """
    console.print("[dim]Validating configuration...[/]")

    # Check API key presence
    if not config.api_key:
        raise APIKeyError(
            "API key not configured. "
            "Set LIBRAXIS_API_KEY or run: screenscribe config --set-key YOUR_KEY"
        )

    validation_results: list[tuple[str, str, bool]] = []

    # Always validate STT (transcription is required)
    try:
        stt_ok = _check_stt_model(config)
        validation_results.append(("STT", config.stt_model, stt_ok))
    except (APIKeyError, ModelValidationError):
        raise

    # Validate LLM if semantic analysis enabled
    if use_semantic:
        try:
            llm_ok = _check_llm_model(config, config.llm_model, "LLM")
            validation_results.append(("LLM", config.llm_model, llm_ok))
        except (APIKeyError, ModelValidationError):
            raise

    # Validate Vision if vision analysis enabled
    if use_vision:
        try:
            vision_ok = _check_llm_model(config, config.vision_model, "Vision")
            validation_results.append(("Vision", config.vision_model, vision_ok))
        except (APIKeyError, ModelValidationError):
            raise

    # Print results
    for model_type, model_name, _ok in validation_results:
        console.print(f"  [green]\u2713[/] {model_type} model ({model_name})")

    console.print()
