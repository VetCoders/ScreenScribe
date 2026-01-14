"""API utilities including retry logic with exponential backoff."""

import time
from collections.abc import Callable
from typing import Any, TypeVar

import httpx
from rich.console import Console

console = Console()

T = TypeVar("T")

# Status codes that should trigger a retry
RETRIABLE_STATUS_CODES = {
    408,  # Request Timeout
    429,  # Too Many Requests (rate limit)
    500,  # Internal Server Error
    502,  # Bad Gateway
    503,  # Service Unavailable
    504,  # Gateway Timeout
}


class APIError(Exception):
    """API request error with details."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


def is_retriable_error(error: Exception) -> bool:
    """Check if an error should trigger a retry."""
    # Timeout errors are always retriable
    if isinstance(error, httpx.TimeoutException):
        return True

    # Connection errors are retriable
    if isinstance(error, httpx.ConnectError):
        return True

    # HTTP status errors - check the status code
    if isinstance(error, httpx.HTTPStatusError):
        return error.response.status_code in RETRIABLE_STATUS_CODES

    return False


def retry_request(
    fn: Callable[[], T],
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    operation_name: str = "API request",
) -> T:
    """
    Execute a function with exponential backoff retry.

    Args:
        fn: Function to execute (should raise httpx exceptions on failure)
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay in seconds
        max_delay: Maximum delay between retries
        operation_name: Name of operation for logging

    Returns:
        Result of fn()

    Raises:
        The last exception if all retries fail
    """
    last_error: Exception | None = None

    for attempt in range(max_retries + 1):
        try:
            return fn()
        except Exception as e:
            last_error = e

            # Check if this error is retriable
            if not is_retriable_error(e):
                # Non-retriable error (e.g., 400, 401, 404) - fail immediately
                raise

            # Check if we have retries left
            if attempt >= max_retries:
                console.print(f"[red]{operation_name} failed after {max_retries + 1} attempts[/]")
                raise

            # Calculate delay with exponential backoff
            delay = min(base_delay * (2**attempt), max_delay)

            # Add jitter to prevent thundering herd
            import random

            delay = delay * (0.5 + random.random())  # noqa: S311

            console.print(
                f"[yellow]{operation_name} failed (attempt {attempt + 1}/{max_retries + 1}), "
                f"retrying in {delay:.1f}s...[/]"
            )
            console.print(f"[dim]  Error: {e}[/]")

            time.sleep(delay)

    # This shouldn't happen, but just in case
    if last_error:
        raise last_error
    raise RuntimeError("Unexpected retry loop exit")


def make_api_request(
    client: httpx.Client,
    method: str,
    url: str,
    *,
    max_retries: int = 3,
    operation_name: str = "API request",
    **kwargs: Any,
) -> httpx.Response:
    """
    Make an HTTP request with automatic retry on transient failures.

    Args:
        client: httpx.Client instance
        method: HTTP method (GET, POST, etc.)
        url: Request URL
        max_retries: Maximum retry attempts
        operation_name: Name for logging
        **kwargs: Additional arguments passed to client.request()

    Returns:
        httpx.Response on success

    Raises:
        httpx.HTTPStatusError: On non-retriable HTTP errors
        httpx.TimeoutException: If all retries fail due to timeout
    """

    def do_request() -> httpx.Response:
        response = client.request(method, url, **kwargs)
        response.raise_for_status()
        return response

    return retry_request(do_request, max_retries=max_retries, operation_name=operation_name)


def is_chat_completions_endpoint(endpoint: str) -> bool:
    """Check if endpoint uses Chat Completions API format."""
    return "chat/completions" in endpoint or "api.openai.com" in endpoint


def build_llm_request_body(
    model: str,
    prompt: str,
    endpoint: str,
    image_base64: str | None = None,
) -> dict[str, Any]:
    """Build request body for either Responses API or Chat Completions API.

    Args:
        model: Model name
        prompt: Text prompt
        endpoint: API endpoint URL (used to detect format)
        image_base64: Optional base64-encoded image for vision

    Returns:
        Request body dict
    """
    if is_chat_completions_endpoint(endpoint):
        # OpenAI Chat Completions format
        if image_base64:
            content: list[dict[str, Any]] = [
                {"type": "text", "text": prompt},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"},
                },
            ]
        else:
            content = prompt  # type: ignore[assignment]
        return {
            "model": model,
            "messages": [{"role": "user", "content": content}],
        }
    else:
        # LibraxisAI Responses API format
        if image_base64:
            input_content: list[dict[str, Any]] = [
                {"type": "input_text", "text": prompt},
                {"type": "input_image", "image_url": f"data:image/jpeg;base64,{image_base64}"},
            ]
        else:
            input_content = [{"type": "input_text", "text": prompt}]
        return {
            "model": model,
            "input": [{"role": "user", "content": input_content}],
        }


def extract_llm_response_text(response_json: dict[str, Any], endpoint: str) -> str:
    """Extract text content from LLM response (either API format).

    Args:
        response_json: Parsed JSON response
        endpoint: API endpoint URL (used to detect format)

    Returns:
        Extracted text content
    """
    if is_chat_completions_endpoint(endpoint):
        # OpenAI Chat Completions format
        choices = response_json.get("choices", [])
        if choices:
            message = choices[0].get("message", {})
            content = message.get("content", "")
            return content if isinstance(content, str) else ""
        return ""
    else:
        # LibraxisAI Responses API format
        content = ""
        for item in response_json.get("output", []):
            item_type = item.get("type", "")
            if item_type == "reasoning":
                # Skip reasoning blocks
                pass
            elif item_type == "message":
                for part in item.get("content", []):
                    if part.get("type") in ("output_text", "text"):
                        text = part.get("text", "")
                        content += text if isinstance(text, str) else ""
            elif item_type in ("output_text", "text"):
                text = item.get("text", "")
                content += text if isinstance(text, str) else ""
        return content
