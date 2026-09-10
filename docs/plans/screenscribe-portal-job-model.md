# ScreenScribe Portal — Job & Session Model (v0.2 xhigh)

This document defines the core domain model for how work is tracked inside the ScreenScribe AI Review Portal.

It is designed to support the unique multimodal nature of the product (screencast + repo + deep structural perception via loctree) while being compatible with (and an evolution of) the job/session thinking we started in `screenscribe/server/jobs.py`.

---

## Core Principles

1. **One Job = One Customer Pain Story**
   - A job is tied to a specific screencast (or set of related screencasts) + a specific repo snapshot.
   - It represents one coherent "review engagement."

2. **Jobs are long-lived and observable**
   - They go through multiple waves of agent work.
   - Customers (and internal reviewers) need visibility into progress.

3. **Strong provenance**
   - Every significant output must be traceable back to either:
     - Specific evidence in the screencast(s), or
     - Specific structural findings from loctree/sourcemaps.

4. **Compatible with vc-operator discipline**
   - The job model must naturally support wave atlases, tracker.md, journal.md, and stop-point handoffs.

---

## Entity Model

### PortalJob (top-level entity)

```ts
interface PortalJob {
  id: string;                    // e.g. "job_20260531_abc123"

  // Customer input
  customerId: string;
  screencastUrls: string[];      // One or more screencasts for this pain story
  repoAccess: RepoAccess;        // Git URL + token/scope + commit SHA at time of submission

  // Lifecycle
  status: JobStatus;             // uploaded | perception | diagnosis | direction | completed | failed
  createdAt: Date;
  updatedAt: Date;

  // Human context
  customerNotes?: string;        // Optional free-text from the customer
  priority: 'normal' | 'high' | 'urgent';
  targetDeliveryDate?: Date;

  // Results (populated over time)
  perceptionReportId?: string;   // Reference to rich perception artifact
  diagnosisReportId?: string;
  masterBriefId?: string;        // The main SCAFFOLD-style deliverable

  // Internal
  assignedOperatorRunId?: string; // For tracking the main vc-operator session handling this job
  metadata: Record<string, any>;
}

type JobStatus =
  | 'uploaded'          // Just received
  | 'perception'        // Running loctree + multimodal screencast analysis
  | 'diagnosis'         // Connecting visual pain to structural reality
  | 'direction'         // Building wave atlas + briefs
  | 'review'            // Optional human senior review
  | 'completed'
  | 'failed';
```

### Sub-Entities

**PerceptionArtifact**
- Contains the "ground truth" layer.
- Loctree full atlas + focused slices/impacts.
- Multimodal extraction from screencast (key moments, transcribed pain points, UI states).
- Cross-references between visual moments and code locations.

**DiagnosisArtifact**
- The "what is actually wrong" layer.
- Problem clusters ranked by (user pain intensity × technical blast radius).
- Clear separation: "What the user experiences" vs "What the code structurally does".

**DirectionArtifact** (the highest value output)
- Master Architectural Brief (SCAFFOLD-style).
- Wave Atlas.
- Set of Iter-3 worker briefs (using the specialized template).
- Optional starter implementation for Wave A.

**Wave / OperatorRun**
- Internal execution tracking.
- Maps to one `master-dispatch.md` + its `tracker.md` + `journal.md`.
- One PortalJob can have multiple OperatorRuns over time (e.g. initial review + follow-up waves).

---

## State Machine (Simplified)

```
uploaded
   │
   ▼
perception  ──(loctree + screencast analysis)──▶
   │
   ▼
diagnosis   ──(synthesis + prioritization)──▶
   │
   ▼
direction   ──(architecture + wave planning + brief writing)──▶
   │
   ▼ (optional)
human_review
   │
   ▼
completed  ──(package delivered to customer)
```

Failure states can branch off any stage.

---

## Key Design Decisions

### 1. Job ≠ One Analysis Run

A single customer pain story may require multiple waves of work over days/weeks. The `PortalJob` is the long-lived container. Individual `OperatorRun`s are the executions.

### 2. Strong Evidence Linking

Every major claim in Diagnosis and Direction artifacts must carry evidence references (screencast timestamps and/or loctree structural references). This is non-negotiable for trust in a paid review service.

### 3. Progressive Enrichment

A job can start with partial perception and be enriched later (e.g. customer uploads additional screencast, or we do deeper loctree on a specific module after initial diagnosis).

### 4. Human-in-the-Loop Points

Explicit stages where a senior human reviewer can be injected (especially valuable in early days of the product for quality and learning).

---

## Open Questions (to be resolved in later phases)

- How do we handle very large repos? (smart scoping, incremental loctree indexing)
- Retention policy for screencasts and generated artifacts?
- Pricing tiers based on job complexity / depth of analysis / human review involvement?
- Can one job spawn "child jobs" for very large scopes?

---

This model is deliberately designed to feel like a senior engineering engagement that was conducted with extreme discipline and structural perception — because that is exactly what the product promises.

Next high-value artifact to define at xhigh effort (tell me the order or suggest new ones):

- Full spec of the final "Review Package" delivered to the customer
- Operator Runbook / FLOW for processing one PortalJob end-to-end
- Integration architecture between the portal job system and the existing ScreenScribe analysis engine (`unified_analysis.py`, etc.)
- Storage & retention model

What should we lock in next?
