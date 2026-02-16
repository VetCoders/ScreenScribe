"""Regression tests for report artifact completeness and review UI wiring."""

from pathlib import Path

from screenscribe.detect import Detection
from screenscribe.html_pro.renderer import render_html_report_pro
from screenscribe.report import (
    save_enhanced_json_report,
    save_enhanced_markdown_report,
    save_html_report_pro,
)
from screenscribe.transcribe import Segment


def _sample_detection() -> Detection:
    return Detection(
        segment=Segment(id=1, start=12.5, end=15.0, text="Przycisk dalej nie działa poprawnie."),
        category="bug",
        keywords_found=["semantic:bug"],
        context="Użytkownik raportuje problem z przyciskiem na ekranie konfiguracji.",
    )


def _sample_segments() -> list[Segment]:
    return [
        Segment(id=1, start=12.5, end=15.0, text="Przycisk dalej nie działa poprawnie."),
        Segment(id=2, start=15.2, end=18.1, text="Kliknięcie nic nie robi i brak informacji."),
    ]


def test_enhanced_json_report_persists_timestamped_transcript(tmp_path: Path) -> None:
    detection = _sample_detection()
    screenshot = tmp_path / "shot.jpg"
    screenshot.write_bytes(b"fake")
    output = tmp_path / "report.json"

    save_enhanced_json_report(
        detections=[detection],
        screenshots=[(detection, screenshot)],
        video_path=tmp_path / "video.mov",
        output_path=output,
        transcript="Przycisk dalej nie działa poprawnie. Kliknięcie nic nie robi.",
        transcript_segments=_sample_segments(),
    )

    data = output.read_text(encoding="utf-8")
    assert '"transcript_timestamped"' in data
    assert "[12.5s - 15.0s] Przycisk dalej nie działa poprawnie." in data
    assert '"transcript_segments"' in data


def test_enhanced_markdown_report_includes_timestamped_transcript(tmp_path: Path) -> None:
    detection = _sample_detection()
    screenshot = tmp_path / "shot.jpg"
    screenshot.write_bytes(b"fake")
    output = tmp_path / "report.md"

    save_enhanced_markdown_report(
        detections=[detection],
        screenshots=[(detection, screenshot)],
        video_path=tmp_path / "video.mov",
        output_path=output,
        transcript="Przycisk dalej nie działa poprawnie. Kliknięcie nic nie robi.",
        transcript_segments=_sample_segments(),
    )

    md = output.read_text(encoding="utf-8")
    assert "## Timestamped Transcript" in md
    assert "[12.5s - 15.0s] Przycisk dalej nie działa poprawnie." in md


def test_html_pro_report_contains_precision_controls_and_voice_note_action() -> None:
    findings = [
        {
            "id": 1,
            "category": "bug",
            "timestamp_formatted": "00:12",
            "timestamp": 12.5,
            "text": "Przycisk dalej nie działa poprawnie.",
            "context": "Kontekst testowy",
            "keywords": ["semantic:bug"],
            "screenshot": "",
            "screenshot_path": "",
            "unified_analysis": {
                "is_issue": True,
                "severity": "high",
                "summary": "Problem z CTA",
                "action_items": ["Naprawić handler kliknięcia"],
                "affected_components": ["CTA button"],
                "suggested_fix": "Sprawdzić event listener",
                "ui_elements": [],
                "issues_detected": [],
                "accessibility_notes": [],
                "design_feedback": "",
            },
        }
    ]
    html = render_html_report_pro(
        video_name="test.mov",
        video_path=None,
        generated_at="2026-02-15T17:31:26",
        executive_summary="",
        findings=findings,
        segments=_sample_segments(),
        errors=[],
    )

    assert 'id="frameSweep"' in html
    assert 'id="stepBackBtn"' in html
    assert 'data-action="voice-note"' in html
    assert 'class="notes-mic-btn"' in html


def test_html_pro_report_uses_relative_video_source_without_file_scheme(tmp_path: Path) -> None:
    detection = _sample_detection()
    screenshot = tmp_path / "shot.jpg"
    screenshot.write_bytes(b"fake")
    video = tmp_path / "source" / "sample.mov"
    video.parent.mkdir(parents=True, exist_ok=True)
    video.write_bytes(b"fake-video")
    output = tmp_path / "out" / "sample_report.html"
    output.parent.mkdir(parents=True, exist_ok=True)

    save_html_report_pro(
        detections=[detection],
        screenshots=[(detection, screenshot)],
        video_path=video,
        output_path=output,
        segments=_sample_segments(),
    )

    html = output.read_text(encoding="utf-8")
    assert 'src="sample.mov"' in html
    assert "file://" not in html
    assert (output.parent / "sample.mov").exists()
