"""Streaming unified analysis regression tests."""

import json
from pathlib import Path

from screenscribe.config import ScreenScribeConfig
from screenscribe.detect import Detection
from screenscribe.transcribe import Segment
from screenscribe.unified_analysis import analyze_finding_unified_streaming


class _FakeStreamResponse:
    def __init__(self, lines: list[str]) -> None:
        self._lines = lines

    def __enter__(self) -> "_FakeStreamResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False

    def raise_for_status(self) -> None:
        return None

    def iter_lines(self):
        yield from self._lines


class _FakeClient:
    def __init__(self, *args, **kwargs) -> None:
        pass

    def __enter__(self) -> "_FakeClient":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False

    def stream(self, *args, **kwargs) -> _FakeStreamResponse:
        final_text = "Not JSON but still useful fallback summary."
        response_payload = {
            "id": "resp_test_123",
            "output": [
                {
                    "type": "message",
                    "content": [{"type": "output_text", "text": final_text}],
                }
            ],
        }
        return _FakeStreamResponse(
            [
                "event: response.created",
                f"data: {json.dumps({'type': 'response.created', 'response': {'id': 'resp_test_123'}})}",
                f"data: {json.dumps({'type': 'response.output_text.done', 'text': final_text})}",
                f"data: {json.dumps({'type': 'response.completed', 'response': response_payload})}",
                "data: [DONE]",
            ]
        )


def test_streaming_unified_analysis_keeps_final_text_fallback(monkeypatch, tmp_path: Path) -> None:
    screenshot = tmp_path / "shot.jpg"
    screenshot.write_bytes(b"fake-image")

    detection = Detection(
        segment=Segment(id=1, start=12.5, end=15.0, text="Przycisk dalej nie działa poprawnie."),
        category="bug",
        keywords_found=["semantic:bug"],
        context="Użytkownik raportuje problem z przyciskiem na ekranie konfiguracji.",
    )

    config = ScreenScribeConfig(
        vision_api_key="test-key",
        vision_endpoint="https://api.example.com/v1/responses",
        vision_model="test-model",
    )

    monkeypatch.setattr("screenscribe.unified_analysis.httpx.Client", _FakeClient)

    result = analyze_finding_unified_streaming(detection, screenshot, config)

    assert result is not None
    assert result.response_id == "resp_test_123"
    assert result.summary == "Not JSON but still useful fallback summary."
    assert result.suggested_fix
