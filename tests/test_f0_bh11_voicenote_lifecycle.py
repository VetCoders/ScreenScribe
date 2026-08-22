"""W1-1 BH11 — voice-note recognizer lifecycle canary.

``recognition.onend`` nulled the GLOBAL ``voiceNoteRuntime.recognition``. When a
second note starts before the first recognizer's onend fires, that late onend
wiped the new session's recognition/button/findingId. The fix only clears the
shared runtime when the firing recognizer is still the active one. Revert the
``=== recognition`` guard and this canary goes red.
"""

from __future__ import annotations

from tests.test_f0_js_runtime_smoke import _run_review_app_smoke


def test_bh11_old_recognizer_onend_does_not_clobber_new_session() -> None:
    """A late onend from a replaced recognizer must not wipe the new session."""
    _run_review_app_smoke(
        """
        const instances = [];
        function FakeRecognition() {
            this.continuous = false; this.interimResults = false; this.lang = '';
            this.onresult = null; this.onerror = null; this.onend = null;
            this.start = () => {};
            this.stop = () => {};
            instances.push(this);
        }
        window.SpeechRecognition = FakeRecognition;

        const mkBtn = () => ({ classList: { toggle() {} }, textContent: '' });
        const btn1 = mkBtn(), btn2 = mkBtn();

        startVoiceNoteCapture(btn1, 'f1');
        const rec1 = instances[0];
        startVoiceNoteCapture(btn2, 'f2');   // new session replaces the old
        const rec2 = instances[1];

        if (voiceNoteRuntime.recognition !== rec2) {
            console.error('new session did not become active');
            process.exitCode = 1;
        }

        // The OLD recognizer fires onend late (the browser delivers it after the
        // new session already started).
        rec1.onend();

        if (voiceNoteRuntime.recognition !== rec2) {
            console.error('late onend from old recognizer wiped the new recognition');
            process.exitCode = 1;
        }
        if (voiceNoteRuntime.activeFindingId !== 'f2') {
            console.error('late onend cleared the new findingId: ' + voiceNoteRuntime.activeFindingId);
            process.exitCode = 1;
        }
        if (voiceNoteRuntime.activeButton !== btn2) {
            console.error('late onend cleared the new active button');
            process.exitCode = 1;
        }

        // The active session's own onend still cleans up the shared runtime.
        rec2.onend();
        if (voiceNoteRuntime.recognition !== null
            || voiceNoteRuntime.activeButton !== null
            || voiceNoteRuntime.activeFindingId !== null) {
            console.error('active-session onend did not clear runtime: '
                + JSON.stringify({
                    rec: voiceNoteRuntime.recognition,
                    fid: voiceNoteRuntime.activeFindingId,
                }));
            process.exitCode = 1;
        }
        """
    )


def test_reset_hydration_aborts_voice_note_and_ignores_queued_result() -> None:
    """Reset invalidates an active recognizer and any already queued transcript."""
    _run_review_app_smoke(
        """
        const instances = [];
        function FakeRecognition() {
            this.continuous = false; this.interimResults = false; this.lang = '';
            this.onresult = null; this.onerror = null; this.onend = null;
            this.abortCalls = 0;
            this.start = () => {};
            this.stop = () => {};
            this.abort = () => { this.abortCalls += 1; };
            instances.push(this);
        }
        window.SpeechRecognition = FakeRecognition;

        restoreUIFromState = () => {};
        restoreMergesToDom = () => {};
        renderManualFrames = () => {};
        initAnnotationTools = () => {};
        let appended = 0;
        appendVoiceTextToNotes = () => { appended += 1; };

        const button = { classList: { toggle() {} }, textContent: '' };
        reportState.resetGeneration = 0;
        startVoiceNoteCapture(button, 'f1');
        const recognition = instances[0];
        const queuedResult = recognition.onresult;

        hydrateReportState({
            findings: {}, manualFrames: [], reviewer: '', resetGeneration: 1,
        });

        if (recognition.abortCalls !== 1) {
            console.error('reset did not abort recognition: ' + recognition.abortCalls);
            process.exitCode = 1;
        }
        if (voiceNoteRuntime.recognition !== null
            || voiceNoteRuntime.activeButton !== null
            || voiceNoteRuntime.activeFindingId !== null) {
            console.error('reset left voice runtime active');
            process.exitCode = 1;
        }

        // Simulate a browser callback that was queued before handlers were
        // detached. Its captured generation/session guards must still reject it.
        queuedResult({
            resultIndex: 0,
            results: [{ isFinal: true, 0: { transcript: 'stale voice note' } }],
        });
        if (appended !== 0) {
            console.error('queued voice result recreated notes after reset');
            process.exitCode = 1;
        }
        """
    )
