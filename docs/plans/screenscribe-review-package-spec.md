# ScreenScribe AI Review Package — Customer Deliverable Specification

**Version:** 0.2 (xhigh)
**Purpose:** This document defines exactly what a customer receives as the "resztę" when they submit a screencast + repo to the ScreenScribe Portal.

This is the **final output artifact** of a completed review job. Everything the operator fleet does is in service of producing a high-quality version of this package.

---

## 1. Philosophy of the Package

The package must feel like it was produced by a **very senior, very disciplined engineering team** that:

- Actually watched the screencast (multiple times)
- Read the codebase with structural x-ray vision (loctree + sourcemaps)
- Thought rigorously about trade-offs
- Delivered something immediately actionable, not vague "consider refactoring X"

Tone: Professional, direct, respectful of the customer's pain, zero hype, zero hand-waving.

---

## 2. Package Structure (v1)

The customer receives a single, well-organized bundle (e.g. ZIP + web view, or a private repo + Notion/linear export).

### Root

```
ScreenScribe-Review-{JobID}-{Date}/
├── 00-Executive-Summary.md
├── 01-Perception/
├── 02-Diagnosis/
├── 03-Direction/
│   ├── Master-Architectural-Brief.md
│   ├── Wave-Atlas.md
│   └── Worker-Briefs/
├── 04-Evidence/
├── 05-Recommendations/
├── 06-Appendices/
└── provenance.json
```

---

## 3. Detailed Contents

### 00-Executive-Summary.md (2-4 pages max)

The only document many stakeholders will read.

Must contain:
- One-paragraph synthesis of the core problem (in the customer's language + technical translation)
- Top 3-5 highest-leverage opportunities, ranked by (pain intensity × blast radius × effort)
- Rough effort/size estimate for the top waves
- Clear "what you should do next" recommendation
- Honest statement of what remains ambiguous or would require more input

### 01-Perception/

This section proves that the system actually looked at what the customer showed.

**Contents:**
- Key moments from the screencast (timestamped, with transcribed quotes + short description of what is visible)
- Relevant loctree structural findings (with direct references to slices, impacts, etc.)
- Cross-references: "At 03:47 in the video the user struggles with X. Structurally this maps to Y (see loct slice Z)"

This section is what makes the whole thing feel different from generic AI code review.

### 02-Diagnosis/

The "what is actually wrong" layer.

- Problem clusters (not a flat list)
- For each cluster:
  - Customer-visible symptoms (with screencast evidence)
  - Structural root causes (with loctree evidence)
  - Why previous attempts to fix it probably didn't work (if visible)
- Prioritization framework used

### 03-Direction/

This is the highest-value part.

**Master-Architectural-Brief.md**
- Similar to a high-quality SCAFFOLD.md
- Clear architectural decisions with trade-offs
- Boundaries and interfaces
- Non-goals

**Wave-Atlas.md**
- Phased, parallelizable plan
- Dependencies made explicit
- Rough sizing per wave

**Worker-Briefs/**
- The actual Iter-3 (or enhanced ScreenScribe variant) briefs that a team could pick up and execute
- These are the real "work orders"

### 04-Evidence/

All raw supporting material, properly organized:
- Full loctree context atlas (or relevant subsets)
- Key screencast timestamps + transcripts
- Specific code excerpts when helpful
- Any other artifacts generated during the job

The goal is full auditability.

### 05-Recommendations/

- Immediate next steps (what to do in the next 2-4 weeks)
- Medium-term direction
- Things the customer should consider investing in (tooling, process, hiring, etc.)
- Honest risks and unknowns

### 06-Appendices/

Anything that didn't fit cleanly above but might be useful.

---

## 4. Non-Negotiable Quality Bars

The package must satisfy all of the following:

- Every significant claim has traceable evidence (screencast timestamp or loctree structural reference).
- The tone is respectful of the customer's actual experience (no "just add caching" dismissiveness when the video shows deeper confusion).
- The recommendations are specific enough that a competent team could start executing without another discovery phase.
- The Wave Atlas actually respects real technical dependencies (not fake parallelism).
- It is clear what is high-confidence vs what is educated hypothesis.

---

## 5. Delivery Formats (v1)

The customer should be able to consume the package in at least two ways:

1. **Human-readable web view** (best for stakeholders)
2. **Machine-readable structured export** (for importing into Linear/Jira/Notion + GitHub)

The raw artifacts (master brief, briefs, etc.) must also be available as clean Markdown so they can be versioned in the customer's own repo if desired.

---

## 6. Relationship to vc-operator Artifacts

This package is the **customer-facing synthesis** of the internal operator artifacts produced during the job:

- The internal `journal.md` + `tracker.md` + wave briefs are used to *create* this package.
- The final package is a curated, polished, customer-appropriate view.
- Some internal artifacts (especially the detailed worker briefs) may be included as appendices or offered as "raw materials" for teams that want to go very deep.

The operator's job is not just to run the analysis — it is also to **translate** the internal high-discipline process into something the customer can actually use.

---

This is one of the most important artifacts to get right, because this is what the customer judges the entire product on.

---

**Status of the artifact set so far (what exists in `docs/plans/`):**

- `screenscribe-ai-review-portal-vision.md` — overall product vision
- `screenscribe-portal-iter3-brief-template.md` — specialized worker brief contract
- `screenscribe-portal-job-model.md` — job/session model
- `screenscribe-portal-operator-runbook.md` — how an operator agent runs such a job
- `screenscribe-review-package-spec.md` — **this document** (what the customer actually receives)

Next high-leverage ones I can produce immediately at xhigh effort:

- The detailed **Perception Layer Specification** (how screencast + loctree actually get fused)
- The **Wave Atlas template** specialized for this domain
- A first version of the **internal operator journal template** for these jobs
- The **CLI / submission interface** spec for how customers actually trigger these jobs

Tell me which one (or combination) to lock in next with maximum depth. Or if you want me to go back and significantly deepen any of the existing ones.
