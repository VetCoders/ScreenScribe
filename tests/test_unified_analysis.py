"""Tests for unified analysis helpers."""

from screenscribe.unified_analysis import UnifiedFinding, deduplicate_findings


def _make_finding(
    detection_id: int,
    summary: str,
    *,
    category: str = "bug",
    timestamp: float = 0.0,
    severity: str = "low",
) -> UnifiedFinding:
    return UnifiedFinding(
        detection_id=detection_id,
        screenshot_path=None,
        timestamp=timestamp,
        category=category,
        is_issue=True,
        sentiment="problem",
        severity=severity,
        summary=summary,
        action_items=[],
        affected_components=[],
        suggested_fix="",
        ui_elements=[],
        issues_detected=[],
        accessibility_notes=[],
        design_feedback="",
        technical_observations="",
        response_id="",
    )


def test_deduplicate_findings_merges_identical_summary() -> None:
    """Identical summaries should always merge."""
    f1 = _make_finding(1, "Same summary", category="bug", timestamp=10.0)
    f2 = _make_finding(2, "Same summary", category="change", timestamp=50.0)

    result = deduplicate_findings([f1, f2])

    assert len(result) == 1


def test_deduplicate_findings_with_close_timestamps() -> None:
    """Similar summaries in same category should merge."""
    f1 = _make_finding(
        1,
        "Lista jest za długa, ograniczyć do 5 pozycji.",
        category="change",
        timestamp=10.0,
    )
    f2 = _make_finding(
        2,
        "Skrócić listę do 5 pozycji w dropdownie.",
        category="change",
        timestamp=25.0,
    )

    result = deduplicate_findings([f1, f2])

    assert len(result) == 1


def test_deduplicate_findings_requires_category_match() -> None:
    """Similar summaries in different categories should not merge."""
    f1 = _make_finding(
        1,
        "Lista jest za długa, ograniczyć do 5 pozycji.",
        category="change",
        timestamp=10.0,
    )
    f2 = _make_finding(
        2,
        "Skrócić listę do 5 pozycji w dropdownie.",
        category="ui",
        timestamp=25.0,
    )

    result = deduplicate_findings([f1, f2])

    assert len(result) == 2
