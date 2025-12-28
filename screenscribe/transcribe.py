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
    no_speech_prob: float = 0.0  # Probability that segment contains no speech (0.0-1.0)


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
    stt_model: str = "whisper-1",
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
            "model": stt_model,
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
                no_speech_prob=seg.get("no_speech_prob", 0.0),
            )
        )

    console.print(f"[green]Transcription complete:[/] {len(segments)} segments")

    return TranscriptionResult(
        text=result.get("text", ""), segments=segments, language=result.get("language", language)
    )


def validate_audio_quality(result: TranscriptionResult) -> tuple[bool, str | None]:
    """
    Validate that audio actually contains speech.

    Detects silent/near-silent recordings by analyzing no_speech_prob
    from Whisper and checking for repetitive hallucinations.

    Args:
        result: TranscriptionResult from transcribe_audio()

    Returns:
        Tuple of (is_valid, error_message).
        If is_valid is False, error_message contains user-friendly feedback.
    """
    if not result.segments:
        return False, (
            "⚠️  No audio segments detected!\n"
            "   The audio file appears to be empty or corrupted."
        )

    # Calculate average no_speech probability
    avg_no_speech = sum(s.no_speech_prob for s in result.segments) / len(result.segments)

    # Check for high no_speech probability (silent audio)
    if avg_no_speech > 0.6:
        return False, (
            f"⚠️  Audio appears to contain little or no speech!\n"
            f"   Average no-speech probability: {avg_no_speech:.0%}\n"
            f"\n"
            f"   Common causes:\n"
            f"   • Microphone was not enabled during screen recording\n"
            f"   • Microphone input volume is too low (check System Settings > Sound > Input)\n"
            f"   • Wrong audio input device selected\n"
            f"\n"
            f"   Tip: When using Cmd+Shift+5, click 'Options' and select your microphone."
        )

    # Check for repetitive hallucinations (Whisper hallucinates on silence)
    texts = [s.text.strip().lower() for s in result.segments if s.text.strip()]
    if texts:
        unique_ratio = len(set(texts)) / len(texts)
        if unique_ratio < 0.3 and len(texts) > 3:
            # More than 70% duplicates with multiple segments = likely hallucination
            most_common = max(set(texts), key=texts.count)
            return False, (
                f"⚠️  Detected repetitive transcription (likely silent audio)!\n"
                f"   The same phrase '{most_common}' appears repeatedly.\n"
                f"   This typically happens when Whisper hallucinates on silent input.\n"
                f"\n"
                f"   Please check your microphone settings and re-record."
            )

    return True, None
