"""Transcription using LibraxisAI STT API."""

from dataclasses import dataclass
from pathlib import Path

import httpx
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from .api_utils import retry_request

console = Console()

# Default LibraxisAI STT endpoint (used if not configured otherwise)
DEFAULT_STT_URL = "https://api.libraxis.cloud/v1/audio/transcriptions"
LOCAL_STT_URL = "http://localhost:8237/transcribe"


@dataclass
class Segment:
    """A transcription segment with timing info."""

    id: int
    start: float
    end: float
    text: str


@dataclass
class TranscriptionResult:
    """Full transcription result with segments."""

    text: str
    segments: list[Segment]
    language: str


def transcribe_audio(
    audio_path: Path,
    language: str = "pl",
    use_local: bool = False,
    api_key: str | None = None,
    stt_endpoint: str | None = None,
) -> TranscriptionResult:
    """
    Transcribe audio using LibraxisAI STT.

    Args:
        audio_path: Path to audio file
        language: Language code (default: pl)
        use_local: Use local STT server instead of cloud
        api_key: LibraxisAI API key
        stt_endpoint: Custom STT endpoint URL (overrides default)

    Returns:
        TranscriptionResult with full text and segments
    """
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    # Validate API key for cloud usage
    if not api_key and not use_local:
        raise ValueError(
            "API key required for cloud STT. Set it via config or use --local flag for local STT."
        )

    # Determine URL: local > custom endpoint > default cloud
    if use_local:
        url = LOCAL_STT_URL
    elif stt_endpoint:
        url = stt_endpoint
    else:
        url = DEFAULT_STT_URL

    console.print(f"[blue]Transcribing:[/] {audio_path.name}")
    console.print(f"[dim]Using {'local' if use_local else 'cloud'} STT[/]")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        progress.add_task("Transcribing audio...", total=None)

        with open(audio_path, "rb") as f:
            audio_content = f.read()

        files = {"file": (audio_path.name, audio_content, "audio/mpeg")}
        data = {
            "model": "whisper-1",
            "language": language,
            "response_format": "verbose_json",
        }
        headers = {}
        if api_key and not use_local:
            headers["Authorization"] = f"Bearer {api_key}"

        def do_transcribe() -> httpx.Response:
            # Long timeout for large files
            with httpx.Client(timeout=600.0) as client:
                response = client.post(url, files=files, data=data, headers=headers)
                response.raise_for_status()
                return response

        response = retry_request(
            do_transcribe,
            max_retries=3,
            operation_name="STT transcription",
        )

    result = response.json()

    # Parse segments
    segments = []
    for seg in result.get("segments", []):
        segments.append(
            Segment(
                id=seg.get("id", 0),
                start=seg.get("start", 0.0),
                end=seg.get("end", 0.0),
                text=seg.get("text", "").strip(),
            )
        )

    console.print(f"[green]Transcription complete:[/] {len(segments)} segments")

    return TranscriptionResult(
        text=result.get("text", ""), segments=segments, language=result.get("language", language)
    )
