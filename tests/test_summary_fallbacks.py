"""Regression tests for AI summary fallbacks and unified preflight behavior."""

from pathlib import Path

from screenscribe.config import ScreenScribeConfig
from screenscribe.detect import Detection
from screenscribe.semantic import generate_detection_executive_summary
from screenscribe.transcribe import Segment
from screenscribe.unified_analysis import analyze_all_findings_unified


def _sample_detection() -> Detection:
    return Detection(
        segment=Segment(
            id=1,
            start=12.5,
            end=15.0,
            text="Przycisk dalej nie działa poprawnie.",
        ),
        category="bug",
        keywords_found=["semantic:bug"],
        context="Użytkownik raportuje problem z przyciskiem na ekranie konfiguracji.",
    )


class _FakeSummaryResponse:
    def raise_for_status(self) -> None:
        return None

    def json(self):
        return {
            "output": [
                {
                    "type": "message",
                    "content": [
                        {
                            "type": "output_text",
                            "text": "Najważniejszym problemem jest niedziałający przycisk dalej. Ogólnie UX wymaga dopracowania przepływu konfiguracji.",
                        }
                    ],
                }
            ]
        }


class _FakeSummaryClient:
    def __init__(self, *args, **kwargs) -> None:
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False

    def post(self, *args, **kwargs):
        return _FakeSummaryResponse()


def test_generate_detection_executive_summary_returns_text(monkeypatch) -> None:
    config = ScreenScribeConfig(
        llm_api_key="test-key",
        llm_endpoint="https://api.example.com/v1/responses",
        llm_model="test-model",
    )
    monkeypatch.setattr("screenscribe.semantic.httpx.Client", _FakeSummaryClient)

    summary = generate_detection_executive_summary([_sample_detection()], config)

    assert "niedziałający przycisk dalej" in summary


def test_analyze_all_findings_unified_fast_fails_when_preflight_returns_none(
    monkeypatch, tmp_path: Path
) -> None:
    screenshot = tmp_path / "shot.jpg"
    screenshot.write_bytes(b"fake-image")
    detection = _sample_detection()
    config = ScreenScribeConfig(
        vision_api_key="test-key",
        vision_endpoint="https://api.example.com/v1/responses",
        vision_model="test-model",
    )

    monkeypatch.setattr(
        "screenscribe.unified_analysis.analyze_finding_unified", lambda *args, **kwargs: None
    )

    results = analyze_all_findings_unified([(detection, screenshot)], config)

    assert results == []
