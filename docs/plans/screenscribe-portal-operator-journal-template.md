# ScreenScribe Portal — Specialized Operator Journal Template

**Version:** 0.1 (xhigh)
**Purpose:** This is the recommended structure and discipline for the `journal.md` maintained by the operator agent while processing a ScreenScribe AI Review job.

It is an evolution of the standard vc-operator journal, heavily specialized for the unique demands of multimodal (screencast + loctree) review work.

---

## 1. Core Principles for This Journal

- **Append-only.** Never edit or delete previous entries.
- **Evidence-obsessed.** Almost every entry should reference either a specific screencast timestamp or a specific loctree finding.
- **Decision hygiene.** Every significant scoping, prioritization, or recovery decision must be recorded with the reasoning at the time.
- **Emotional tone tracking.** Because the input is a human being showing real pain, it is useful to occasionally note the emotional tone of the work (e.g., "this moment in the video hit hard — we need to treat the loading experience with respect").

---

## 2. Recommended Entry Format

```markdown
## <ISO-8601 timestamp> — <event-kind>

**Wave / Prompt:** B-3 or "Intake" / "Perception Wave A" etc.
**Agent(s):** claude / gemini / ...
**Run ID:** ...

**Context / Trigger:**
[What just happened or what decision is being made]

**Key Evidence:**
- Screencast: 07:42 – "I keep clicking this and nothing happens for 4 seconds..."
- Loctree: `loct slice screenscribe/hooks/useReportData.ts` showed 23 importers, 0 memoization, heavy re-renders on filter change
- Both: The visual hesitation at 07:42 maps directly to the structural anti-pattern found in the hook.

**Decision / Action:**
[What was decided or done]

**Rationale (at the time):**
[Why]

**Open Questions / Risks:**
- ...

**Next move:**
...
```

---

## 3. Recommended Event Kinds (use these tags)

- `intake` — job received, initial reading of screencast + repo
- `perception-pass` — major loctree or multimodal analysis run
- `cross-modal-alignment` — important moment where screencast evidence and code structure were explicitly linked
- `diagnosis-insight` — a significant "aha" connecting user pain to structural cause
- `scope-decision` — what is in / out for this wave or the overall job
- `wave-planning` — building or adjusting the wave atlas
- `brief-authoring` — creating or refining worker briefs
- `recovery` — something went wrong, how we responded
- `quality-gate` — running gates, findings, fixes
- `human-escalation` — decision to involve a senior human reviewer
- `synthesis` — pulling everything together for the final package
- `stop-point` — reaching a natural handoff point
- `customer-communication` — any direct output or recommendation to the customer

You don't have to use only these tags — they are just strong defaults.

---

## 4. Special Sections (use when relevant)

### 4.1 "This moment in the video matters" entries

When a particular part of the screencast reveals something structurally important that might have been missed in normal code review, call it out explicitly.

### 4.2 "Loctree revealed something the video didn't show" entries

Conversely, when structural analysis surfaces problems the customer hasn't consciously articulated yet (this is often where the highest leverage lives).

### 4.3 "We were wrong about X" entries

Honest corrections of earlier hypotheses. These are gold for improving the system over time.

---

## 5. Anti-Patterns in Journaling for This Product

- Treating the journal as just "what the agents did" instead of "what we learned about the customer's actual experience + the code".
- Being too polite or high-level. The journal is internal — it can (and should) contain sharp, sometimes uncomfortable observations.
- Forgetting to link back to specific evidence. "The dashboard feels slow" is weak. "At 04:11 the user waits 3.8s with a spinner while filters are applied. This maps to 14 re-renders of ReportTable caused by..." is strong.

---

## 6. Relationship to Other Artifacts

The journal is **not** the customer-facing story. It is the operator's working memory and audit trail.

It feeds:
- The quality and honesty of the Diagnosis and Direction layers.
- The stop-point handoff.
- Future improvements to the portal (this journal is extremely valuable training data).

---

This template, combined with the rest of the artifact system we've defined, gives a very complete picture of how to run these review jobs with genuine discipline and respect for both the customer's lived experience and the structural reality of their codebase.

---

**Current state of the core artifact set (xhigh effort):**

We now have a quite solid foundation:

- Product vision
- Job model
- Operator runbook
- Specialized worker brief template
- Review package spec
- Perception layer spec
- Full artifact manifest
- Wave atlas template
- **This journal template**

This is already a very strong "zestaw artefaktów" for the operator layer of the portal.

What should we produce next at maximum depth? Some of the strongest remaining candidates:

- The **Perception → Diagnosis → Direction** data flow and handoff contracts (how artifacts actually move between waves)
- First version of the **customer submission / CLI surface** spec
- The **internal quality bar checklist** an operator should run before considering a review package ready for delivery
- Deeper integration thinking with the existing `unified_analysis.py` + analysis engine

Your move. I'm ready to go very deep on whichever one you choose.
