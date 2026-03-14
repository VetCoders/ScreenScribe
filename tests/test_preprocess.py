from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from screenscribe.cli import app
from screenscribe.config import ScreenScribeConfig
from screenscribe.preprocess import write_preprocess_bundle
from screenscribe.transcribe import Segment, TranscriptionResult


def _sample_transcription(language: str = "en") -> TranscriptionResult:
    return TranscriptionResult(
        text="Open the login screen and finish auth with the pasted code.",
        segments=[
            Segment(id=1, start=0.0, end=2.5, text="Open the login screen."),
            Segment(
                id=2,
                start=2.5,
                end=6.0,
                text="Finish auth with the pasted code.",
            ),
        ],
        language=language,
        response_id="resp_stt_test_123",
    )


def test_write_preprocess_bundle_creates_transcript_artifacts(tmp_path: Path) -> None:
    video_path = tmp_path / "demo.mov"
    video_path.write_bytes(b"video")

    audio_path = tmp_path / "source.mp3"
    audio_path.write_bytes(b"audio")

    output_dir = tmp_path / "demo_preprocess"
    transcription = _sample_transcription(language="en")

    artifacts = write_preprocess_bundle(
        video_path=video_path,
        output_dir=output_dir,
        transcription=transcription,
        duration_seconds=12.4,
        extracted_audio_path=audio_path,
        include_audio=True,
    )

    assert artifacts["transcript"].read_text(encoding="utf-8") == transcription.text
    timestamped = artifacts["timestamped_transcript"].read_text(encoding="utf-8")
    assert "[0.0s - 2.5s] Open the login screen." in timestamped

    segments_payload = json.loads(artifacts["segments_json"].read_text(encoding="utf-8"))
    assert segments_payload["language"] == "en"
    assert len(segments_payload["segments"]) == 2

    vtt = artifacts["webvtt"].read_text(encoding="utf-8")
    assert "WEBVTT" in vtt
    assert "Language: en" in vtt

    manifest = json.loads(artifacts["manifest"].read_text(encoding="utf-8"))
    assert manifest["mode"] == "preprocess"
    assert manifest["language"] == "en"
    assert manifest["duration_seconds"] == 12.4
    assert manifest["stats"]["segments"] == 2
    assert manifest["response_id"] == "resp_stt_test_123"
    assert Path(manifest["artifacts"]["audio"]).exists()


def test_preprocess_command_builds_bundle(monkeypatch, tmp_path: Path) -> None:
    runner = CliRunner()
    video_path = tmp_path / "auth-flow.mov"
    video_path.write_bytes(b"video")

    extracted_audio = tmp_path / "audio.mp3"
    extracted_audio.write_bytes(b"audio")
    output_dir = tmp_path / "artifacts"

    monkeypatch.setattr("screenscribe.cli.check_ffmpeg_installed", lambda: None)
    monkeypatch.setattr("screenscribe.cli.extract_audio", lambda _: extracted_audio)
    monkeypatch.setattr("screenscribe.cli.get_video_duration", lambda _: 64.2)
    monkeypatch.setattr(
        "screenscribe.cli.transcribe_audio",
        lambda *args, **kwargs: _sample_transcription(language="pl"),
    )
    monkeypatch.setattr(
        ScreenScribeConfig,
        "load",
        classmethod(lambda cls: ScreenScribeConfig(api_key="test-key")),
    )

    result = runner.invoke(app, ["preprocess", str(video_path), "-o", str(output_dir)])

    assert result.exit_code == 0, result.output
    assert (output_dir / "preprocess.json").exists()
    assert (output_dir / "transcript.txt").exists()
    assert (output_dir / "transcript.timestamped.txt").exists()
    assert (output_dir / "transcript.segments.json").exists()
    assert (output_dir / "transcript.vtt").exists()
    assert (output_dir / "audio.mp3").exists()
