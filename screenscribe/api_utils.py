"""API utilities including retry logic with exponential backoff."""

import time
from collections.abc import Callable
from typing import TypeVar

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
                console.print(
                    f"[red]{operation_name} failed after {max_retries + 1} attempts[/]"
                )
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
    **kwargs: object,
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
        response = client.request(method, url, **kwargs)  # type: ignore[arg-type]
        response.raise_for_status()
        return response

    return retry_request(do_request, max_retries=max_retries, operation_name=operation_name)
