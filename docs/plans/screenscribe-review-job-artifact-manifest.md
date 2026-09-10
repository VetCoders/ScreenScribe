# ScreenScribe AI Review Job — Complete Artifact Manifest

**Version:** 0.1 (xhigh)
**Purpose:** This is the single source of truth describing every artifact produced during the processing of one customer review job in the ScreenScribe Portal.

It serves as the operational contract between the platform, the operator fleet, and the final customer deliverable.

---

## 1. Job Lifecycle Overview

A single `PortalJob` moves through these high-level stages:

1. **Intake** — screencast + repo submitted, initial job record created.
2. **Perception** — deep multimodal + structural ground truth is built.
3. **Diagnosis** — pain is connected to structural reality.
4. **Direction** — architecture, wave planning, and executable briefs are produced.
5. **Synthesis & Packaging** — everything is curated into the customer-facing Review Package.
6. **Delivery + Optional Human Review** — package is delivered; stop-point handoff is written.

---

## 2. Core Artifact Inventory

### 2.1 Job-Level Artifacts (always produced)

| Artifact | Path (relative to job) | Owner | Produced in stage | Purpose | Customer-visible? |
|----------|------------------------|-------|-------------------|---------|-------------------|
| `job.json` | `job.json` | Platform | Intake | Canonical job record, metadata, status, links to all other artifacts | Yes (summary view) |
| `screencasts/` | `screencasts/` | Platform | Intake | Original uploaded video files + basic metadata | Yes (with timestamps) |
| `repo-snapshot/` | `repo-snapshot/` | Platform | Intake | Manifest of what was cloned/indexed + commit SHA | Yes |
| `journal.md` | `journal.md` | Operator | Entire lifecycle | Append-only operator diary (decisions, observations, pivots) | No (internal) |
| `tracker.md` | `tracker.md` | Operator | Entire lifecycle | Wave status table, run IDs, SHAs, gate results | Partial (high-level progress) |
| `provenance.json` | `provenance.json` | Platform + Operator | Synthesis | Complete audit trail of every agent run, model, prompt_id, inputs, outputs | Yes (for trust) |

### 2.2 Perception Layer Artifacts

| Artifact | Path | Owner | Stage | Purpose | Customer-visible? |
|----------|------|-------|-------|---------|-------------------|
| `perception/screencast-analysis.md` | `perception/screencast-analysis.md` | Screencast Perception Specialist | Perception | Key moments, transcribed pain points, emotional intensity, UI states | Yes (curated) |
| `perception/loctree-atlas/` | `perception/loctree-atlas/` | Structural Perception Specialist | Perception | Full or scoped loctree context + key slices/impacts/finds | Yes (relevant excerpts) |
| `perception/cross-modal-alignment.md` | `perception/cross-modal-alignment.md` | Cross-Modal Synthesizer | Perception | Explicit mappings between screencast moments and code structures | Yes (core value) |
| `perception/raw/` | `perception/raw/` | Specialists | Perception | Raw loctree outputs, full transcripts, etc. | No (available on request) |

### 2.3 Diagnosis Layer Artifacts

| Artifact | Path | Owner | Stage | Purpose | Customer-visible? |
|----------|------|-------|-------|---------|-------------------|
| `diagnosis/diagnosis-report.md` | `diagnosis/diagnosis-report.md` | Diagnostic Synthesizer | Diagnosis | Problem clusters with evidence from both modalities | Yes |
| `diagnosis/evidence-index.json` | `diagnosis/evidence-index.json` | Diagnostic Synthesizer | Diagnosis | Machine-readable mapping of every claim to evidence | Yes (for power users) |

### 2.4 Direction Layer Artifacts (Highest Value)

| Artifact | Path | Owner | Stage | Purpose | Customer-visible? |
|----------|------|-------|-------|---------|-------------------|
| `direction/master-brief.md` | `direction/master-brief.md` | Architecture Scaffolder | Direction | SCAFFOLD-style architectural diagnosis + recommendations | Yes (primary document) |
| `direction/wave-atlas.md` | `direction/wave-atlas.md` | Architecture Scaffolder | Direction | Phased, parallelizable execution plan with dependencies | Yes |
| `direction/briefs/` | `direction/briefs/` | Brief Authors | Direction | Full set of specialized Iter-3 worker briefs | Yes (raw + curated) |
| `direction/implementation-starters/` | `direction/implementation-starters/` (optional) | Executor Agents | Direction | Starter code for highest-leverage Wave A items (higher tier) | Yes (in premium packages) |

### 2.5 Synthesis & Delivery Artifacts

| Artifact | Path | Owner | Stage | Purpose | Customer-visible? |
|----------|------|-------|-------|---------|-------------------|
| `package/` | `package/` | Operator + Platform | Synthesis | The final curated Review Package (see separate spec) | **Primary customer deliverable** |
| `stop-point-handoff.md` | `stop-point-handoff.md` | Operator | Close-out | Explicit handoff: what was done, what remains, recommended next actions, open questions | Yes |
| `customer-summary.md` | `package/00-Executive-Summary.md` | Operator | Synthesis | The one document most stakeholders will actually read | Yes |

---

## 3. Internal vs Customer-Facing

- **Internal-only** (operator working memory): full `journal.md`, raw perception outputs, intermediate drafts, full tracker with every run ID.
- **Customer-visible** (curated): the contents of `package/`, plus selected high-signal excerpts from perception and diagnosis.
- **Available on request**: deeper raw artifacts (full loctree atlas, complete journal, raw briefs, etc.).

This separation is important for product experience and trust.

---

## 4. Provenance Requirements

Every significant artifact must contain or link to `provenance.json` entries that include at minimum:

- Which agent(s) produced it
- Model(s) used
- Prompt / brief ID
- Input artifacts it depended on
- Timestamp + git SHA of the operator session at time of creation
- Any loctree commands that were run as part of its creation

This is non-negotiable for a credible paid review service.

---

## 5. Evolution Notes

This manifest is expected to grow as the product matures:

- v0.x: Mostly the artifacts listed above.
- Later versions will likely add: execution artifacts (actual code changes from higher-tier packages), comparative analysis across multiple jobs for the same customer, etc.

---

This document, together with the previous ones (`vision.md`, `job-model.md`, `operator-runbook.md`, `iter3-brief-template.md`, `review-package-spec.md`, `perception-layer-spec.md`), gives a very complete picture of the operational artifact system required to deliver on the ScreenScribe Portal promise at high quality.

---

**Current status of the full artifact set (xhigh effort):**

Already written:

- `screenscribe-ai-review-portal-vision.md`
- `screenscribe-portal-job-model.md`
- `screenscribe-portal-operator-runbook.md`
- `screenscribe-portal-iter3-brief-template.md`
- `screenscribe-review-package-spec.md`
- `screenscribe-portal-perception-layer-spec.md`
- `screenscribe-review-job-artifact-manifest.md` ← **this one**

This is now a quite complete first-cut definition of the core operator-grade artifact system for the product.

What would you like to deepen or add next at maximum effort? Some strong candidates:

- The specialized **Wave Atlas template** for these jobs
- The **Operator Journal template** tailored to multimodal review work
- First version of the **CLI / submission interface** spec
- How the existing `unified_analysis.py` + other analysis code actually gets called from the new perception/direction layers
- The **storage, retention, and access control model** for all these artifacts

Tell me the priority. I'm ready to go very deep on whichever one you choose.
