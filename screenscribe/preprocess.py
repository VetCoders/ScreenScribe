"""Artifact-first preprocessing helpers for transcript-driven review workflows."""

from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from rich.console import Console

from .checkpoint import serialize_transcription
from .transcribe import TranscriptionResult
from .vtt_generator import generate_webvtt

console = Console()


def format_timestamped_transcript(transcription: TranscriptionResult) -> str:
    """Format transcript into stable timestamped lines."""
    return "\n".join(
        f"[{segment.start:.1f}s - {segment.end:.1f}s] {segment.text}"
        for segment in transcription.segments
    )


def write_preprocess_bundle(
    *,
    video_path: Path,
    output_dir: Path,
    transcription: TranscriptionResult,
    duration_seconds: float | None,
    extracted_audio_path: Path | None = None,
    include_audio: bool = True,
) -> dict[str, Path]:
    """Write transcript-first preprocessing artifacts for downstream model work."""
    output_dir.mkdir(parents=True, exist_ok=True)

    transcript_txt = output_dir / "transcript.txt"
    transcript_timestamped = output_dir / "transcript.timestamped.txt"
    segments_json = output_dir / "transcript.segments.json"
    transcript_vtt = output_dir / "transcript.vtt"
    manifest_json = output_dir / "preprocess.json"
    audio_output = output_dir / "audio.mp3"

    transcript_txt.write_text(transcription.text, encoding="utf-8")
    transcript_timestamped.write_text(
        format_timestamped_transcript(transcription),
        encoding="utf-8",
    )
    segments_json.write_text(
        json.dumps(serialize_transcription(transcription), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    transcript_vtt.write_text(
        generate_webvtt(transcription.segments, language=transcription.language),
        encoding="utf-8",
    )

    audio_path_for_manifest: str | None = None
    if include_audio and extracted_audio_path and extracted_audio_path.exists():
        shutil.copy2(extracted_audio_path, audio_output)
        audio_path_for_manifest = str(audio_output)

    manifest: dict[str, Any] = {
        "video": str(video_path),
        "generated_at": datetime.now().isoformat(),
        "mode": "preprocess",
        "language": transcription.language,
        "duration_seconds": duration_seconds,
        "response_id": transcription.response_id or None,
        "stats": {
            "segments": len(transcription.segments),
            "words": len(transcription.text.split()),
        },
        "artifacts": {
            "transcript": str(transcript_txt),
            "timestamped_transcript": str(transcript_timestamped),
            "segments_json": str(segments_json),
            "webvtt": str(transcript_vtt),
            "audio": audio_path_for_manifest,
        },
    }
    manifest_json.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    console.print(
        f"[green]Preprocess bundle saved:[/] [link=file://{output_dir}]{output_dir}[/link]"
    )

    return {
        "transcript": transcript_txt,
        "timestamped_transcript": transcript_timestamped,
        "segments_json": segments_json,
        "webvtt": transcript_vtt,
        "manifest": manifest_json,
        **({"audio": audio_output} if audio_path_for_manifest else {}),
    }
