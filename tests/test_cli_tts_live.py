"""CLI surfaces for xAI TTS (``screenscribe tts``) and live STT (``transcribe --live``)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

import screenscribe.cli as cli
from screenscribe.cli import app
from screenscribe.config import ScreenScribeConfig
from screenscribe.stt_stream import TranscriptEvent

runner = CliRunner()


def _use_config(monkeypatch: pytest.MonkeyPatch, config: ScreenScribeConfig) -> None:
    monkeypatch.setattr(cli.ScreenScribeConfig, "load", classmethod(lambda _cls: config))


def test_tts_writes_audio_file_via_xai(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    secret = "xai-" + "tts-secret"  # pragma: allowlist secret
    _use_config(monkeypatch, ScreenScribeConfig.provider_preset("xai", secret))
    seen: dict[str, Any] = {}

    def fake_tts(text: str, **kwargs: Any) -> tuple[bytes, str]:
        seen["text"] = text
        seen.update(kwargs)
        return b"ID3-bytes", "audio/mpeg"

    monkeypatch.setattr(cli, "synthesize_speech_xai", fake_tts)
    out = tmp_path / "nested" / "hello.mp3"

    result = runner.invoke(
        app, ["tts", "Dzień dobry", "--out", str(out), "--voice", "ara", "--language", "pl"]
    )

    assert result.exit_code == 0, result.output
    assert out.read_bytes() == b"ID3-bytes"
    assert seen["text"] == "Dzień dobry"
    assert seen["voice_id"] == "ara"
    assert seen["language"] == "pl"
    assert seen["codec"] == "mp3"
    assert seen["api_key"] == secret
    assert seen["endpoint"] == "https://api.x.ai/v1/tts"
    assert secret not in result.output
    assert "Audio saved" in result.output and "hello.mp3" in result.output


def test_tts_defaults_voice_and_language_from_config(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config = ScreenScribeConfig.provider_preset("xai", "k")
    config.language = "pl"
    config.tts_voice = "eve"
    _use_config(monkeypatch, config)
    seen: dict[str, Any] = {}

    def fake_tts(text: str, **kwargs: Any) -> tuple[bytes, str]:
        seen.update(kwargs)
        return b"RIFF", "audio/wav"

    monkeypatch.setattr(cli, "synthesize_speech_xai", fake_tts)
    out = tmp_path / "x.wav"

    result = runner.invoke(app, ["tts", "test", "--out", str(out)])

    assert result.exit_code == 0, result.output
    assert seen["voice_id"] == "eve"
    assert seen["language"] == "pl"
    assert seen["codec"] == "wav"  # derived from the output suffix


def test_tts_without_tts_provider_exits_with_guidance(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _use_config(monkeypatch, ScreenScribeConfig.provider_preset("libraxis", "lx"))
    monkeypatch.setattr(cli, "synthesize_speech_xai", lambda *a, **k: pytest.fail("no request"))

    result = runner.invoke(app, ["tts", "hi", "--out", str(tmp_path / "a.mp3")])

    assert result.exit_code == 1
    assert "SCREENSCRIBE_TTS_ENDPOINT" in result.output


class _FakeStream:
    def __init__(self, events: list[TranscriptEvent], record: dict[str, Any]) -> None:
        self._events = events
        self._record = record
        self._record["pcm"] = b""
        self._record["finished"] = False

    def __enter__(self) -> _FakeStream:
        return self

    def __exit__(self, *exc: object) -> None:
        return None

    def send_pcm(self, pcm: bytes) -> None:
        self._record["pcm"] += pcm

    def finish(self) -> None:
        self._record["finished"] = True

    def __iter__(self) -> Any:
        return iter(self._events)


def test_transcribe_live_streams_stdin_pcm_and_prints_lines(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = ScreenScribeConfig.provider_preset("xai", "xai-" + "k")
    _use_config(monkeypatch, config)
    record: dict[str, Any] = {}
    events = [
        TranscriptEvent(kind="partial", text="hel"),
        TranscriptEvent(kind="final", text="hello there", start_ms=0, end_ms=900),
        TranscriptEvent(kind="ended"),
    ]

    def fake_factory(endpoint: str, **kwargs: Any) -> _FakeStream:
        record["endpoint"] = endpoint
        record.update(kwargs)
        return _FakeStream(events, record)

    monkeypatch.setattr(cli, "stream_client_for_endpoint", fake_factory)
    pcm = b"\x01\x00" * 4000

    result = runner.invoke(app, ["transcribe", "--live", "--lang", "en"], input=pcm)

    assert result.exit_code == 0, result.output
    assert record["endpoint"] == "wss://api.x.ai/v1/stt"
    assert record["api_key"] == "xai-k"  # pragma: allowlist secret
    assert record["sample_rate"] == 16000
    assert record["language"] == "en"
    assert record["pcm"] == pcm
    assert record["finished"] is True
    assert "hel" in result.output
    assert "hello there" in result.output
    assert "xai-k" not in result.output


def test_transcribe_live_error_event_exits_nonzero(monkeypatch: pytest.MonkeyPatch) -> None:
    _use_config(monkeypatch, ScreenScribeConfig.provider_preset("xai", "k"))
    record: dict[str, Any] = {}
    events = [TranscriptEvent(kind="error", text="invalid api key", code="error")]
    monkeypatch.setattr(
        cli, "stream_client_for_endpoint", lambda endpoint, **kw: _FakeStream(events, record)
    )

    result = runner.invoke(app, ["transcribe", "--live"], input=b"\x00\x00")

    assert result.exit_code == 1
    assert "invalid api key" in result.output


def test_transcribe_without_video_or_live_is_a_usage_error() -> None:
    result = runner.invoke(app, ["transcribe"])
    assert result.exit_code != 0
    assert "--live" in result.output or "VIDEO" in result.output


def test_config_setup_offers_xai(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    secret = "xai-" + "setup-secret"  # pragma: allowlist secret

    result = runner.invoke(app, ["config", "setup"], input=f"4\n{secret}\n")

    assert result.exit_code == 0, result.output
    assert "xAI" in result.output
    assert secret not in result.output
    text = (tmp_path / ".config" / "screenscribe" / "config.env").read_text()
    assert "SCREENSCRIBE_PROVIDER=xai" in text
    assert "SCREENSCRIBE_STT_ENDPOINT=https://api.x.ai/v1/stt" in text
    assert "SCREENSCRIBE_LLM_MODEL=grok-4.6" in text


def test_config_show_labels_xai(monkeypatch: pytest.MonkeyPatch) -> None:
    _use_config(monkeypatch, ScreenScribeConfig.provider_preset("xai", "k"))
    result = runner.invoke(app, ["config", "--show"])
    assert result.exit_code == 0, result.output
    assert "xAI" in result.output
    assert "READY" in result.output
