"""Transcription using LibraxisAI STT API."""

import os
from dataclasses import dataclass
from pathlib import Path

import httpx
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()

# Default LibraxisAI STT endpoints (used only as fallback)
DEFAULT_LIBRAXIS_STT_URL = "https://api.libraxis.cloud/v1/audio/transcriptions"
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
        api_key: LibraxisAI API key (reads from LIBRAXIS_API_KEY env if not provided)
        stt_endpoint: Custom STT endpoint URL (overrides default)

    Returns:
        TranscriptionResult with full text and segments
    """
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    # Get API key
    if api_key is None:
        api_key = os.environ.get("LIBRAXIS_API_KEY")
        if api_key is None and not use_local:
            raise ValueError(
                "LIBRAXIS_API_KEY environment variable not set. "
                "Set it or use --local flag for local STT."
            )

    # Determine URL: local > custom endpoint > default cloud
    if use_local:
        url = LOCAL_STT_URL
    elif stt_endpoint:
        url = stt_endpoint
    else:
        url = DEFAULT_LIBRAXIS_STT_URL

    console.print(f"[blue]Transcribing:[/] {audio_path.name}")
    console.print(f"[dim]Using {'local' if use_local else 'cloud'} STT[/]")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        progress.add_task("Transcribing audio...", total=None)

        with open(audio_path, "rb") as f:
            files = {"file": (audio_path.name, f, "audio/mpeg")}
            data = {
                "model": "whisper-1",
                "language": language,
                "response_format": "verbose_json",
            }
            headers = {}
            if api_key and not use_local:
                headers["Authorization"] = f"Bearer {api_key}"

            # Long timeout for large files
            with httpx.Client(timeout=600.0) as client:
                response = client.post(url, files=files, data=data, headers=headers)

    if response.status_code != 200:
        raise RuntimeError(f"STT API error ({response.status_code}): {response.text}")

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
