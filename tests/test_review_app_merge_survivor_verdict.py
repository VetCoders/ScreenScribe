"""Survivor verdict preservation on human-merge (P2, finding #5).

``mergeFindings`` sets the surviving finding's verdict to ``accepted`` (the
reviewer deliberately kept it) and reverts absorbed members to ``none``. The
member-reset loop compared a raw ``id === merged.id``: member ids arrive from the
DOM as STRINGS (``dataset.findingId`` -> ``"17"``) while ``merged.id`` is the
INTEGER parsed from the report JSON (``17``). ``"17" === 17`` is false, so the
survivor was not skipped and its just-set ``accepted`` verdict was overwritten
back to ``none`` — a human-merge silently dropped the survivor's acceptance.

The fix compares normalized ids (``normId(id) === normId(merged.id)``) so the
survivor is skipped regardless of id type. This test drives the real
``mergeFindings`` from ``review_app.js`` in a node sandbox with an INTEGER
survivor id and asserts the survivor keeps ``accepted``.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
I18N_JS = REPO_ROOT / "screenscribe/html_pro_assets/scripts/i18n.js"
LANGUAGE_CONTROL_JS = REPO_ROOT / "screenscribe/html_pro_assets/scripts/lib/language-control.js"
STT_TRANSPORT_JS = REPO_ROOT / "screenscribe/html_pro_assets/scripts/lib/stt-transport.js"
TAB_KEYBOARD_JS = REPO_ROOT / "screenscribe/html_pro_assets/scripts/lib/tab-keyboard.js"
REVIEW_APP_JS = REPO_ROOT / "screenscribe/html_pro_assets/scripts/review_app.js"


def _finding(fid: int, ts: float, summary: str) -> dict:
    return {
        "id": fid,
        "timestamp": ts,
        "timestamp_formatted": f"{int(ts) // 60:02d}:{int(ts) % 60:02d}",
        "category": "ui",
        "text": f"transcript line for finding {fid}",
        "screenshot": "data:image/jpeg;base64,QUJD",
        "unified_analysis": {
            "summary": summary,
            "severity": "low",
            "action_items": [f"do thing {fid}"],
            "affected_components": [f"Component{fid}"],
            "issues_detected": [f"issue {fid}"],
        },
    }


# INTEGER ids, exactly as JSON.parse yields them in the browser.
_FINDINGS = [
    _finding(17, 17.0, "survivor of the merge"),
    _finding(18, 18.0, "absorbed member"),
]


def _run(driver_body: str) -> None:
    node = shutil.which("node")
    if not node:
        pytest.skip("node is required for review_app.js merge tests")

    runner = textwrap.dedent(
        f"""
        const fs = require('fs');
        const vm = require('vm');

        const findings = {json.dumps(_FINDINGS)};
        const findingsEl = {{ textContent: JSON.stringify(findings) }};

        function makeEl() {{
            return {{
                className: '', textContent: '', hidden: false, href: '', download: '',
                style: {{}}, dataset: {{}},
                classList: {{ add() {{}}, remove() {{}}, toggle() {{}}, contains() {{ return false; }} }},
                appendChild() {{}}, removeChild() {{}}, remove() {{}}, click() {{}},
                querySelector() {{ return null; }}, querySelectorAll() {{ return []; }},
                addEventListener() {{}}, setAttribute() {{}}, insertBefore() {{}},
            }};
        }}

        const documentStub = {{
            body: {{
                dataset: {{ videoName: 'demo.mp4', reportLanguage: 'en' }},
                classList: {{ add() {{}}, remove() {{}} }},
                contains() {{ return true; }},
                appendChild() {{}}, removeChild() {{}},
            }},
            documentElement: {{ lang: 'en' }},
            addEventListener() {{}},
            querySelector() {{ return null; }},
            querySelectorAll() {{ return []; }},
            getElementById(id) {{ return id === 'original-findings' ? findingsEl : null; }},
            createElement() {{ return makeEl(); }},
        }};

        const sandbox = {{
            console, setTimeout, clearTimeout, Math, Date, JSON, Promise,
            window: {{
                location: {{ search: '' }},
                addEventListener() {{}}, removeEventListener() {{}},
                TRANSCRIPT_SEGMENTS: [],
            }},
            document: documentStub,
            localStorage: {{ getItem() {{ return null; }}, setItem() {{}}, removeItem() {{}} }},
            navigator: {{ mediaDevices: {{}} }},
            Blob: class Blob {{ constructor(c, o = {{}}) {{ this.chunks = c; this.type = o.type || ''; }} }},
            ResizeObserver: class ResizeObserver {{ observe() {{}} disconnect() {{}} }},
            Image: class Image {{}},
            process, confirm() {{ return true; }},
            fetch() {{ throw new Error('no network in test'); }},
        }};
        sandbox.window.document = sandbox.document;
        sandbox.window.navigator = sandbox.navigator;
        sandbox.globalThis = sandbox;

        const i18nSource = fs.readFileSync({str(I18N_JS)!r}, 'utf8');
        const languageControlSource = fs.readFileSync({str(LANGUAGE_CONTROL_JS)!r}, 'utf8');
        const sttTransportSource = fs.readFileSync({str(STT_TRANSPORT_JS)!r}, 'utf8');
        const tabKeyboardSource = fs.readFileSync({str(TAB_KEYBOARD_JS)!r}, 'utf8');
        const source = fs.readFileSync({str(REVIEW_APP_JS)!r}, 'utf8');

        const driver = `
            reportState.reviewer = 'qa';
            reportState.manualFrames = [];
            {driver_body}
        `;

        const script = new vm.Script(
            i18nSource + "\\n" + languageControlSource + "\\n" + sttTransportSource + "\\n" +
            tabKeyboardSource + "\\n" + source + "\\n" + driver,
            {{ filename: 'review_app.js' }}
        );
        script.runInNewContext(sandbox);
        """
    )
    result = subprocess.run([node, "-e", runner], capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr or result.stdout


def test_human_merge_preserves_survivor_accepted_verdict() -> None:
    """A human-merge with a numeric survivor id keeps the survivor ``accepted``.

    RED before the fix: ``"17" === 17`` is false, so the survivor falls through
    the member-reset loop and its verdict is clobbered to ``none``.
    """
    _run(
        textwrap.dedent(
            """
            // The reviewer accepted BOTH findings before merging.
            reportState.findings = {
                '17': { verdict: 'accepted' },
                '18': { verdict: 'accepted' },
            };
            // member ids come from the DOM as STRINGS; the survivor (17) is numeric
            // in the report JSON.
            const merged = mergeFindings(['17', '18']);
            if (!merged) throw new Error('mergeFindings returned null');
            const survivor = reportState.findings['17'];
            if (!survivor) throw new Error('survivor review state missing');
            if (survivor.verdict !== 'accepted')
                throw new Error('survivor verdict clobbered: ' + survivor.verdict + ' (want accepted)');
            // The absorbed member must still revert to none.
            const member = reportState.findings['18'];
            if (!member || member.verdict !== 'none')
                throw new Error('absorbed member verdict wrong: ' + (member && member.verdict));
            """
        )
    )


def test_legacy_unmerge_preserves_survivor_verdict_without_snapshot() -> None:
    """Legacy merge data without member snapshots keeps the survivor verdict."""
    _run(
        textwrap.dedent(
            """
            reportState.findings = {
                '17': {
                    verdict: 'rejected', severity: 'high', notes: 'keep survivor', annotations: [],
                },
                '18': {
                    verdict: 'none', severity: null, notes: '', annotations: [],
                },
            };
            reportState.merges = [{
                id: 17,
                member_ids: [17, 18],
                // Saved before merged_member_reviews/member_reviews existed.
                member_reviews: {},
            }];

            if (!unmergeFindings('17')) throw new Error('legacy group did not unmerge');
            const survivor = reportState.findings['17'];
            if (survivor.verdict !== 'rejected'
                || survivor.severity !== 'high'
                || survivor.notes !== 'keep survivor') {
                throw new Error('legacy survivor state was overwritten: ' + JSON.stringify(survivor));
            }
            if (reportState.findings['18'].verdict !== 'none') {
                throw new Error('legacy absorbed member did not use the unreviewed fallback');
            }
            """
        )
    )


def test_cold_reload_unmerge_does_not_copy_member_union_to_survivor() -> None:
    """Hydrated union notes/priority must not become survivor-owned on unmerge."""
    _run(
        textwrap.dedent(
            """
            const originalSurvivor = {
                verdict: 'none', severity: 'low', notes: 'survivor note', annotations: [],
            };
            const originalMember = {
                verdict: 'accepted', severity: 'high', notes: 'member note', annotations: [],
            };
            reportState.findings = {
                '17': {
                    verdict: 'accepted', severity: 'high',
                    notes: 'survivor note\\\\n\\\\nmember note', annotations: [],
                    merged_from_ids: [18],
                    merged_member_reviews: {
                        '17': originalSurvivor,
                        '18': originalMember,
                    },
                    merged_survivor_review: originalSurvivor,
                    merged_review_baseline: {
                        verdict: 'accepted', severity: 'high',
                        notes: 'survivor note\\\\n\\\\nmember note', annotations: [],
                    },
                },
            };
            const merged = { id: 17, merged_from_ids: [18] };
            ensureMergeEntry(merged);
            if (!unmergeFindings('17')) throw new Error('cold merge did not unmerge');

            const survivor = reportState.findings['17'];
            const member = reportState.findings['18'];
            if (survivor.verdict !== 'none' || survivor.severity !== 'low'
                || survivor.notes !== 'survivor note') {
                throw new Error('member union leaked onto survivor: ' + JSON.stringify(survivor));
            }
            if (member.verdict !== 'accepted' || member.severity !== 'high'
                || member.notes !== 'member note') {
                throw new Error('absorbed member was not restored: ' + JSON.stringify(member));
            }
            """
        )
    )


def test_cold_reload_unmerge_keeps_real_post_reload_survivor_edits() -> None:
    """Fields changed after hydration still belong to the survivor on unmerge."""
    _run(
        textwrap.dedent(
            """
            const originalSurvivor = {
                verdict: 'none', severity: 'low', notes: 'survivor note', annotations: [],
            };
            const originalMember = {
                verdict: 'accepted', severity: 'high', notes: 'member note', annotations: [],
            };
            reportState.findings = {
                '17': {
                    verdict: 'accepted', severity: 'high',
                    notes: 'survivor note\\\\n\\\\nmember note', annotations: [],
                    merged_from_ids: [18],
                    merged_member_reviews: {
                        '17': originalSurvivor,
                        '18': originalMember,
                    },
                    merged_survivor_review: originalSurvivor,
                    merged_review_baseline: {
                        verdict: 'accepted', severity: 'high',
                        notes: 'survivor note\\\\n\\\\nmember note', annotations: [],
                    },
                },
            };
            const merged = { id: 17, merged_from_ids: [18] };
            ensureMergeEntry(merged);
            reportState.findings['17'].notes = 'edited merged survivor';
            reportState.findings['17'].severity = 'critical';
            reportState.findings['17'].annotations = [{ type: 'rect', x: 0.4 }];
            if (!unmergeFindings('17')) throw new Error('cold merge did not unmerge');

            const survivor = reportState.findings['17'];
            if (survivor.verdict !== 'none' || survivor.severity !== 'critical'
                || survivor.notes !== 'edited merged survivor'
                || survivor.annotations[0]?.type !== 'rect') {
                throw new Error('real survivor edits were lost: ' + JSON.stringify(survivor));
            }
            """
        )
    )


def test_cold_reload_legacy_empty_metadata_keeps_hydrated_survivor() -> None:
    """Server-projected empty additive fields do not erase a legacy survivor."""
    _run(
        textwrap.dedent(
            """
            reportState.findings = {
                '17': {
                    verdict: 'rejected', severity: 'high', notes: 'legacy union', annotations: [],
                    merged_from_ids: [18],
                    merged_member_reviews: {},
                    merged_survivor_review: {},
                    merged_review_baseline: {},
                },
            };
            ensureMergeEntry({ id: 17, merged_from_ids: [18] });
            if (!unmergeFindings('17')) throw new Error('legacy cold merge did not unmerge');

            const survivor = reportState.findings['17'];
            if (survivor.verdict !== 'rejected' || survivor.severity !== 'high'
                || survivor.notes !== 'legacy union') {
                throw new Error('empty metadata erased survivor: ' + JSON.stringify(survivor));
            }
            """
        )
    )
