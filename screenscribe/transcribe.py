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
LOCAL_STT_URL = "http://localhost:7237/transcribe"


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

        # Detect MIME type from file extension
        mime_types = {
            ".mp3": "audio/mpeg",
            ".wav": "audio/wav",
            ".m4a": "audio/mp4",
            ".ogg": "audio/ogg",
            ".flac": "audio/flac",
            ".webm": "audio/webm",
        }
        mime_type = mime_types.get(audio_path.suffix.lower(), "audio/mpeg")
        # Local endpoints use 'audio' field, OpenAI-compatible use 'file'
        is_local_endpoint = url.startswith("http://127.0.0.1") or url.startswith("http://localhost")
        field_name = "audio" if is_local_endpoint else "file"
        files = {field_name: (audio_path.name, audio_content, mime_type)}
        data = {
            "model": stt_model,
            "language": language,
            "response_format": "verbose_json",
        }
        headers = {}
        if api_key and not use_local and not is_local_endpoint:
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

    # Fallback: if API returns text but no segments, create a single segment
    # This handles APIs that don't support verbose segment output
    full_text = result.get("text", "").strip()
    if not segments and full_text:
        console.print("[yellow]API returned text without segments, creating synthetic segment[/]")
        # Estimate duration from text length (~150 words/min in Polish)
        word_count = len(full_text.split())
        estimated_duration = (word_count / 150) * 60  # seconds
        segments.append(
            Segment(
                id=0,
                start=0.0,
                end=estimated_duration,
                text=full_text,
                no_speech_prob=0.0,
            )
        )

    console.print(f"[green]Transcription complete:[/] {len(segments)} segments")

    return TranscriptionResult(
        text=result.get("text", ""), segments=segments, language=result.get("language", language)
    )


def validate_audio_quality(result: TranscriptionResult) -> tuple[bool, str | None, bool]:
    """
    Validate that audio actually contains speech.

    Detects silent/near-silent recordings by analyzing no_speech_prob
    from Whisper and checking for repetitive hallucinations.

    Args:
        result: TranscriptionResult from transcribe_audio()

    Returns:
        Tuple of (is_valid, message, is_warning).
        If is_valid is False, message contains user-friendly feedback.
        If is_warning is True, pipeline should continue after showing the warning.
    """
    if not result.segments:
        return (
            False,
            "⚠️  No audio segments detected!\n   The audio file appears to be empty or corrupted.",
            False,
        )

    # Calculate average no_speech probability
    avg_no_speech = sum(s.no_speech_prob for s in result.segments) / len(result.segments)

    transcript_text = result.text.strip()
    if not transcript_text:
        transcript_text = " ".join(s.text for s in result.segments if s.text)
    word_count = len(transcript_text.split())

    suppress_warning_words = 150
    stop_words_threshold = 40
    stop_no_speech_threshold = 0.85
    warn_no_speech_threshold = 0.75

    # Only stop on very high no_speech + very short transcript.
    if avg_no_speech > stop_no_speech_threshold and word_count < stop_words_threshold:
        return (
            False,
            f"⚠️  Audio appears to contain little or no speech!\n"
            f"   Average no-speech probability: {avg_no_speech:.0%}\n"
            f"\n"
            f"   Common causes:\n"
            f"   • Microphone was not enabled during screen recording\n"
            f"   • Microphone input volume is too low (check System Settings > Sound > Input)\n"
            f"   • Wrong audio input device selected\n"
            f"\n"
            f"   Tip: When using Cmd+Shift+5, click 'Options' and select your microphone.",
            False,
        )

    # Suppress warning if transcript is long enough to be meaningful.
    if word_count >= suppress_warning_words:
        return True, None, False

    if avg_no_speech >= warn_no_speech_threshold:
        return (
            True,
            f"⚠️  High no-speech score detected, but transcript has content.\n"
            f"   Average no-speech probability: {avg_no_speech:.0%}\n"
            f"   Word count: {word_count}\n"
            f"\n"
            f"   Continuing anyway. If results look wrong, check mic settings.",
            True,
        )

    # Check for repetitive hallucinations (Whisper hallucinates on silence)
    texts = [s.text.strip().lower() for s in result.segments if s.text.strip()]
    if texts:
        unique_ratio = len(set(texts)) / len(texts)
        if unique_ratio < 0.3 and len(texts) > 3:
            # More than 70% duplicates with multiple segments = likely hallucination
            most_common = max(set(texts), key=texts.count)
            return (
                False,
                f"⚠️  Detected repetitive transcription (likely silent audio)!\n"
                f"   The same phrase '{most_common}' appears repeatedly.\n"
                f"   This typically happens when Whisper hallucinates on silent input.\n"
                f"\n"
                f"   Please check your microphone settings and re-record.",
                False,
            )

    return True, None, False
