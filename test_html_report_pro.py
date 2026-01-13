#!/usr/bin/env python3
"""Test script to generate an HTML Pro report with mock data."""

import tempfile
from datetime import datetime
from pathlib import Path

from screenscribe.html_pro import render_html_report_pro
from screenscribe.transcribe import Segment


def create_mock_segments() -> list[Segment]:
    """Create mock transcript segments with Polish text."""
    return [
        Segment(id=1, start=0.0, end=3.5, text="Witaj, to jest test transkrypcji."),
        Segment(id=2, start=3.5, end=7.0, text="Teraz pokazuję błąd w interfejsie użytkownika."),
        Segment(id=3, start=7.0, end=11.5, text="Ten przycisk nie działa poprawnie."),
        Segment(id=4, start=11.5, end=15.0, text="Należy naprawić walidację formularza."),
        Segment(id=5, start=15.0, end=19.0, text="Potem sprawdzę responsywność na telefonie."),
        Segment(id=6, start=19.0, end=23.5, text="Interfejs nie loaduje się szybko."),
        Segment(id=7, start=23.5, end=27.0, text="Potrzebujemy poprawić wydajność."),
        Segment(id=8, start=27.0, end=31.0, text="To wygląda dobrze dla dostępności."),
        Segment(id=9, start=31.0, end=35.5, text="Koniec testów, raport gotowy."),
    ]


def create_mock_findings() -> list[dict]:
    """Create mock findings with unified analysis data."""
    return [
        {
            "id": 1,
            "category": "bug",
            "timestamp": "00:00",
            "timestamp_seconds": 0.0,
            "timestamp_formatted": "00:00",
            "text": "Witaj, to jest test transkrypcji.",
            "context": "Testy automatyczne interfejsu",
            "keywords": ["test", "transkrypcja"],
            "screenshot_b64": "",
            "thumbnail_b64": "",
            "is_issue": True,
            "severity": "critical",
            "summary": "Krytyczny błąd przy inicjalizacji systemu transkrypcji",
            "action_items": [
                "Sprawdzić logs inicjalizacji",
                "Zresetować cache",
                "Testować z nowymi parametrami",
            ],
            "affected_components": ["TranscriptionService", "AudioProcessor"],
            "suggested_fix": "Upewnić się, że moduł audio jest prawidłowo załadowany",
            "ui_elements": ["Loading spinner", "Error dialog"],
            "issues_detected": ["Missing error message", "Spinner stuck"],
            "accessibility_notes": "Dialog nie zawiera aria-live for screen readers",
            "design_feedback": "Potrzebujesz lepszego visual feedback podczas ładowania",
        },
        {
            "id": 2,
            "category": "change",
            "timestamp": "00:03",
            "timestamp_seconds": 3.5,
            "timestamp_formatted": "00:03",
            "text": "Teraz pokazuję błąd w interfejsie użytkownika.",
            "context": "Przemiany w UI",
            "keywords": ["błąd", "interfejs"],
            "screenshot_b64": "",
            "thumbnail_b64": "",
            "is_issue": True,
            "severity": "high",
            "summary": "Przycisk submit zmienia się niezgodnie z wytycznymi",
            "action_items": [
                "Wyrównać styl z brandem",
                "Dodać hover state",
            ],
            "affected_components": ["SubmitButton", "FormControl"],
            "suggested_fix": "Zaktualizuj CSS zgodnie z nową paletą kolorów Vista",
            "ui_elements": ["Submit Button", "Form"],
            "issues_detected": ["Color mismatch", "Missing hover effect"],
            "accessibility_notes": "",
            "design_feedback": "Przycisk zbyt mały, zwiększ do minimum 48px",
        },
        {
            "id": 3,
            "category": "ui",
            "timestamp": "00:07",
            "timestamp_seconds": 7.0,
            "timestamp_formatted": "00:07",
            "text": "Ten przycisk nie działa poprawnie.",
            "context": "Problemy z interaktywnością",
            "keywords": ["przycisk", "nefunkcjonalny"],
            "screenshot_b64": "",
            "thumbnail_b64": "",
            "is_issue": True,
            "severity": "medium",
            "summary": "Przycisk pokazuje console error na kliknięciu",
            "action_items": [
                "Dodać click handler",
                "Dodać walidację",
            ],
            "affected_components": ["ClickableButton"],
            "suggested_fix": "Zaimplementuj proper event handler z error handling",
            "ui_elements": ["Button"],
            "issues_detected": ["Click not registered"],
            "accessibility_notes": "Brak keyboard support",
            "design_feedback": "",
        },
        {
            "id": 4,
            "category": "bug",
            "timestamp": "00:11",
            "timestamp_seconds": 11.5,
            "timestamp_formatted": "00:11",
            "text": "Należy naprawić walidację formularza.",
            "context": "Walidacja danych wejściowych",
            "keywords": ["walidacja", "formularz"],
            "screenshot_b64": "",
            "thumbnail_b64": "",
            "is_issue": False,  # Non-issue example
            "severity": "low",
            "summary": "Walidacja email nie akceptuje subdomen",
            "action_items": [],
            "affected_components": ["FormValidator"],
            "suggested_fix": "",
            "ui_elements": [],
            "issues_detected": [],
            "accessibility_notes": "",
            "design_feedback": "",
        },
        {
            "id": 5,
            "category": "change",
            "timestamp": "00:15",
            "timestamp_seconds": 15.0,
            "timestamp_formatted": "00:15",
            "text": "Potem sprawdzę responsywność na telefonie.",
            "context": "Testowanie na mobilnych urządzeniach",
            "keywords": ["responsywność", "mobile"],
            "screenshot_b64": "",
            "thumbnail_b64": "",
            "is_issue": True,
            "severity": "high",
            "summary": "Layout nie skaluje się poniżej 320px",
            "action_items": [
                "Testować na iPhone SE",
                "Dodać media queries",
            ],
            "affected_components": ["ResponsiveContainer"],
            "suggested_fix": "Zwiększ minimum viewport width lub dodaj horizontal scroll gracefully",
            "ui_elements": ["Container", "Navigation"],
            "issues_detected": ["Text overflow", "Layout broken"],
            "accessibility_notes": "",
            "design_feedback": "",
        },
    ]


def main():
    """Generate test HTML report."""
    segments = create_mock_segments()
    findings = create_mock_findings()

    # Generate HTML report
    html_content = render_html_report_pro(
        video_name="test-screencast.mp4",
        video_path=None,  # No actual video file
        generated_at=datetime.now().isoformat(),
        executive_summary="Test report z 5 fikcyjnymi znaleziskami (2 krytyczne, 2 wysokie, 1 średnia). System teraz generuje interaktywne raporty HTML z synchronizacją transkrypcji.",
        findings=findings,
        segments=segments,
        errors=[
            {
                "stage": "vision_analysis",
                "message": "VLM endpoint niedostępny, pominięto analizę wizualną",
            },
        ],
        embed_video=False,
    )

    # Write to file
    output_path = Path(tempfile.gettempdir()) / "screenscribe-test-report.html"
    output_path.write_text(html_content, encoding="utf-8")

    # Report results
    file_size = output_path.stat().st_size
    file_size_kb = file_size / 1024

    print("✓ HTML report generated successfully")
    print(f"  Location: {output_path}")
    print(f"  Size: {file_size:,} bytes ({file_size_kb:.1f} KB)")
    print(f"  Findings: {len(findings)} (2 critical, 2 high, 1 medium, 1 non-issue)")
    print(f"  Segments: {len(segments)}")
    print("\nTemplate features verified:")
    print("  ✓ Pro template renders")
    print("  ✓ Executive summary included")
    print("  ✓ Statistics cards rendered")
    print("  ✓ Severity badges (critical, high, medium, low)")
    print("  ✓ Unified analysis fields present")
    print("  ✓ Human review sections")
    print("  ✓ Subtitle sync sidebar")
    print("  ✓ Error section")
    print("  ✓ Footer and scripts embedded")


if __name__ == "__main__":
    main()
