# ScreenScribe Portal — Specialized Wave Atlas Template

**Version:** 0.1 (xhigh)
**Purpose:** This is the canonical structure for the Wave Atlas produced during a ScreenScribe AI Review job.

It is an evolution of the standard vc-operator wave atlas concept, heavily specialized for the multimodal nature of the work (screencast of real user pain + deep structural code perception via loctree).

---

## 1. Philosophy

A Wave Atlas for a ScreenScribe review job must make the following brutally clear:

- Which problems are **real** (backed by evidence from the screencast **and/or** loctree).
- What the natural **dependency order** is.
- What can be attacked **in parallel**.
- Where the highest **leverage** exists (pain intensity × blast radius × confidence).
- What remains **genuinely ambiguous** and would require more input from the customer.

It is a planning and communication tool first, a task list second.

---

## 2. Top-Level Structure

```markdown
# Wave Atlas — ScreenScribe Review Job {job_id}

**Date:** ...
**Customer context:** ...
**Primary pain areas from screencast:** [list with timestamps]
**Key structural findings from loctree:** [summary]

## Overall Assessment

[2-4 paragraph synthesis]

## Prioritization Framework Used

[Explain the model: e.g. (User Friction Score × Structural Blast Radius × Implementation Confidence) / Effort]

## Wave Overview

| Wave | Theme | Goal | Estimated Effort | Parallelism | Confidence | Key Dependencies |
|------|-------|------|------------------|-------------|------------|------------------|
| A    | ...   | ...  | ...              | ...         | ...        | ...              |
| B    | ...   | ...  | ...              | ...         | ...        | ...              |
| C    | ...   | ...  | ...              | ...         | ...        | ...              |
| D    | ...   | ...  | ...              | ...         | ...        | ...              |

## Detailed Waves

### Wave A — [Theme]

**Goal:** ...
**Rationale (why this first):** ...

**Prompts / Work Items:**

1. **[Short title]**
   - Evidence: [screencast timestamp(s) + loctree finding(s)]
   - Type: Perception / Diagnosis / Direction / Execution
   - Recommended agent: ...
   - Depends on: -
   - Blocks: [later items]
   - Acceptance criteria: ...
   - Out of scope: ...

2. ...

**Success criteria for the wave as a whole:**
- ...

### Wave B — [Theme]

...
```

---

## 3. Key Sections Explained

### Evidence Tagging (Mandatory)

Every significant work item must carry explicit evidence tags:

- `screencast: 04:12 – "This loading state is confusing..."`
- `loctree: slice screenscribe/components/ReportDashboard.tsx showed 17 importers of useReportData with no memoization`
- `both`

This is what separates this from normal planning.

### Problem Cluster Mapping

It is often useful to have a section that maps high-level problem clusters (from the Diagnosis layer) to the waves that address them.

Example:
- Cluster "Reporting feels slow and unpredictable" → primarily addressed in Waves A-2, B-1, B-3, C-2

### Parallelism vs Sequencing

The atlas must be explicit about what can run in parallel and what truly cannot. This is one of the highest-leverage things a good operator does.

### Confidence Levels

Use simple, honest labels per wave or per item:
- High (we have strong evidence from both modalities)
- Medium
- Hypothesis (we think this is likely, but evidence is incomplete)

---

## 4. Anti-Patterns to Avoid

- Fake parallelism (items marked as parallel that actually have hidden dependencies).
- Over-planning Wave C and D before Wave A and B are solid.
- Hiding uncertainty to make the atlas look cleaner.
- Making the atlas too tactical too early (it should stay at the right level of abstraction for the current state of understanding).

---

## 5. Evolution

Early versions of the portal may produce simpler atlases (fewer waves, more manual curation). As the system matures and we accumulate data across many jobs, we can make the atlas generation itself more automated and higher quality.

---

This template, combined with the other artifacts already defined, gives a very complete picture of how a high-discipline, loctree-grounded, multimodal review engagement would be planned and executed.

---

**Current complete artifact set produced at xhigh effort:**

1. `screenscribe-ai-review-portal-vision.md`
2. `screenscribe-portal-job-model.md`
3. `screenscribe-portal-operator-runbook.md`
4. `screenscribe-portal-iter3-brief-template.md`
5. `screenscribe-review-package-spec.md`
6. `screenscribe-portal-perception-layer-spec.md`
7. `screenscribe-review-job-artifact-manifest.md`
8. `screenscribe-portal-wave-atlas-template.md` ← this one

We now have a very solid foundation for the core operational artifacts of the product.

What should we attack next with maximum depth? Strong options:

- The specialized **Operator Journal template** for these jobs
- First detailed spec of the **Perception → Diagnosis → Direction** data flow and handoff points between waves
- The **CLI / customer submission surface** (how someone actually triggers one of these reviews)
- A first cut of the **pricing / packaging** model tied to artifact depth (basic diagnosis vs full direction + briefs vs execution support)

Your call. I'm ready to go very deep on whichever one you choose.
