# ScreenScribe Portal — Review Tracker Template (Specialized TRACKER.md)

**Version:** 0.1 (xhigh)
**Canonical Role:** This is the `tracker.md` equivalent for ScreenScribe AI Review jobs.

It is the single source of truth for the current state of all waves in one customer review job. It answers the question: "What has actually landed, what is in flight, and what is the objective status?"

---

## 1. Purpose (Why This Artifact Exists)

In vc-operator:

- `journal.md` = **why** we made decisions.
- `tracker.md` = **what** actually happened and its verifiable status.

For a ScreenScribe review job, the tracker is especially critical because:

- The work is long-running and multi-wave.
- Multiple specialist agents (perception, diagnosis, direction) are involved.
- There is a customer-facing deliverable at the end whose quality depends on the internal waves completing properly.
- We need clear, auditable evidence that certain perception and diagnosis steps actually happened before direction work began.

---

## 2. File Location (Recommended Convention)

Inside a job's artifact directory:

```
<job-artifact-root>/
├── tracker.md                     ← this file
├── journal.md
├── master-dispatch.md             (or wave-atlas.md)
├── briefs/
├── perception/
├── diagnosis/
├── direction/
└── package/
```

We recommend keeping the filename `tracker.md` for direct compatibility with the vc-operator runtime and tooling, even if the product calls the overall concept "Review Tracker" internally.

---

## 3. Recommended Structure

```markdown
# Review Tracker — Job {job_id}

**Customer:** ...
**Job created:** ...
**Current overall status:** [PERCEPTION | DIAGNOSIS | DIRECTION | SYNTHESIS | COMPLETED | BLOCKED]

**Last updated:** <timestamp> by <operator-agent>

## Summary Table

| Wave | Theme | Status | Key Deliverable | Agent | Run ID | Branch / SHA | Gates | Evidence Links | Notes |
|------|-------|--------|------------------|-------|--------|--------------|-------|----------------|-------|
| A    | ...   | [x]    | ...              | ...   | ...    | ...          | Green | ...            | ...   |
| B-1  | ...   | [x]    | ...              | ...   | ...    | ...          | Green | ...            | ...   |
| B-2  | ...   | [ ]    | ...              | ...   | ...    | ...          | -     | ...            | ...   |
| C    | ...   | [ ]    | ...              | ...   | ...    | ...          | -     | ...            | ...   |

## Detailed Wave Status

### Wave A — [Theme]

- **Status:** Completed
- **Goal:** ...
- **Completed prompts:**
  - A-1: ...
  - A-2: ...
- **Deliverables produced:**
  - `perception/screencast-analysis.md`
  - `perception/loctree-atlas/`
  - `perception/cross-modal-alignment.md`
- **Gates passed:** ...
- **Key evidence:** [links or references]
- **Operator notes:** ...

### Wave B — Diagnosis

...

## Open Risks & Blockers

- [ ] ...
- [ ] ...

## Next Wave Readiness

- Wave X is ready to fire when:
  - [ ] All of Wave Y is green
  - [ ] Perception handoff reviewed
  - [ ] ...

## Stop Point Status

- Current planned stop point: ...
- Conditions for reaching it: ...
```

---

## 4. Key Columns / Fields Explained

- **Status**: Use simple, unambiguous states: `[ ]` (not started), `[~]` (in progress), `[x]` (completed), `[!]` (blocked/failed).
- **Evidence Links**: This column is mandatory for this product. Every completed wave should have direct links to the screencast moments and/or loctree findings that justified the work.
- **Gates**: Explicit reference to which quality gates were run and their result (not just "green").
- **Deliverables produced**: Concrete paths to the artifacts created by that wave.

---

## 5. Rules Specific to ScreenScribe Review Jobs

1. **Perception waves must be visibly complete** in the tracker before any serious Diagnosis wave is marked ready.
2. **Diagnosis must be visibly complete** before Direction waves that produce customer-facing recommendations are fired.
3. The tracker is the single place where "has this actually been done with proper evidence?" can be answered quickly.
4. The operator should update the tracker **before** firing the next wave, not after (this forces discipline).

---

## 6. Relationship to Other Artifacts

- The `tracker.md` is the **source of truth** for what the `journal.md` is commenting on.
- The final `stop-point-handoff.md` and the customer `Review Package` should be able to reference specific rows in the tracker for credibility.
- When a human reviewer is brought in, the tracker is usually the first document they are asked to read.

---

## 7. Anti-Patterns

- Treating the tracker as a todo list instead of a **verifiable status** document.
- Marking waves complete without linking evidence.
- Letting the tracker get out of date with reality (this is one of the fastest ways to lose operator discipline).
- Hiding blocked waves instead of surfacing them clearly.

---

This template, together with the journal template and wave atlas, gives a complete, vc-operator-native set of living operator-side artifacts specialized for the ScreenScribe review use case.

---

**Current state of the core artifact set (as of this document):**

We now have a very strong foundation:

- Vision
- Job model
- Operator runbook
- Specialized brief template
- Review package spec
- Perception layer spec
- Full artifact manifest
- Wave atlas template
- Journal template
- Layer handoff contracts
- **This tracker template**

The three canonical vc-operator living artifacts (`master-dispatch`/`wave-atlas`, `journal`, `tracker`) now all have specialized versions for this product.

What would you like to deepen or add next at xhigh effort?

Strong remaining candidates:
- The **customer submission / CLI surface** spec
- The detailed **data contracts** between layers (what exactly flows from Perception to Diagnosis, etc.)
- The **internal pre-delivery quality checklist**
- Integration points with the existing analysis engine

Your call.
