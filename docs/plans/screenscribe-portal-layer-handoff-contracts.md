# ScreenScribe Portal — Layer Handoff Contracts (Perception → Diagnosis → Direction)

**Version:** 0.1 (xhigh)
**Purpose:** This document defines the explicit contracts and handoff points between the major layers in a ScreenScribe AI Review job.

It is the "plumbing" spec that ensures the operator fleet can move information rigorously from raw multimodal input all the way to high-quality customer deliverables.

---

## 1. Why This Matters

In a normal vc-operator job, the plan is usually written by a human and is relatively clean.

In a ScreenScribe review job, the input is **noisy and ambiguous** (a screencast of real human frustration + a large codebase). The quality of the final output depends heavily on disciplined handoffs between layers.

Bad handoffs here are one of the fastest ways to produce beautiful but shallow or untrustworthy results.

---

## 2. The Three Core Layers

### 2.1 Perception Layer
**Goal:** Make the invisible visible with maximum fidelity and minimal interpretation.
**Primary outputs:**
- Screencast-derived artifacts (key moments, pain points, UI states)
- Loctree-derived artifacts (structural map, slices, impacts, twins, etc.)
- Cross-modal alignment artifacts (explicit links between visual moments and code structures)

**Exit criteria (what must be true before handing off):**
- Every significant pain moment from the screencast has been timestamped and described.
- Relevant structural findings have been extracted via loctree (not just "we read the code").
- Clear cross-references exist between the two.

### 2.2 Diagnosis Layer
**Goal:** Connect lived customer experience to structural code reality.
**Primary outputs:**
- Problem clusters (not flat lists)
- For each cluster: customer-visible symptoms + structural root causes + evidence from both modalities
- Prioritized problem map

**Exit criteria:**
- Every major problem cluster has traceable evidence from *both* the screencast and loctree (or explicitly marked as having only one type of evidence).
- Clear separation between "what the user feels" and "what the code structurally does".
- Some early hypotheses about why previous fixes didn't work (if visible).

### 2.3 Direction Layer
**Goal:** Turn diagnosis into actionable, phased engineering direction.
**Primary outputs:**
- Master Architectural Brief
- Wave Atlas
- Set of specialized worker briefs
- (Optional) starter implementation for highest-leverage items

**Exit criteria:**
- Every recommendation in the Direction layer can be traced back to a specific problem cluster in the Diagnosis layer.
- The Wave Atlas respects real technical dependencies.
- The worker briefs are specific enough that a competent team could execute them with limited additional discovery.

---

## 3. Recommended Handoff Artifacts & Contracts

### Handoff 1: Perception → Diagnosis

**What Diagnosis receives from Perception:**
- Curated set of high-signal screencast moments (not the entire transcript)
- High-signal loctree findings (not the entire atlas)
- Existing cross-modal alignments (with confidence levels)
- Explicit "open questions" from the perception specialists ("this moment in the video looks painful but we couldn't map it cleanly to code")

**Format recommendation:**
A single `perception-handoff.md` + structured `perception-artifacts/` folder. The handoff document should be written for a diagnostician, not for the customer.

**Quality bar:**
The diagnostician should be able to start forming strong hypotheses within 30-60 minutes of reading the handoff, without having to watch the entire original screencast or run their own loctree queries from scratch.

### Handoff 2: Diagnosis → Direction

**What Direction receives from Diagnosis:**
- The full Diagnosis report
- Prioritized problem clusters with evidence
- Any early architectural hypotheses the diagnosticians formed
- Explicit "we are confident about X but this part is still weak" notes

**Format recommendation:**
The Diagnosis report itself + a short `diagnosis-to-direction-handoff.md` that highlights the 3-5 clusters the Direction wave should focus on first.

**Quality bar:**
The architecture scaffolder should feel they have a clear "what is actually wrong" picture before they start designing solutions.

---

## 4. Anti-Patterns in Handoffs

- Throwing raw artifacts over the wall ("here's the full loctree atlas and the full transcript, good luck").
- Diagnosis teams starting to design solutions too early.
- Direction teams ignoring weak evidence and over-confidently recommending big changes.
- Not explicitly calling out what is still uncertain.

---

## 5. Tooling / Process Recommendations (Early)

- Every layer should produce a short "handoff note" (1-3 pages) in addition to the raw artifacts.
- The operator (or a dedicated synthesis agent) is responsible for curating what actually gets passed forward.
- We should track, over many jobs, which types of perception artifacts are most useful to diagnosticians. This data will let us improve the handoff discipline over time.

---

This document closes one of the most important remaining gaps in the current artifact system: how information actually flows rigorously through a real review job.

---

**Updated status of the core artifact set (xhigh effort):**

We now have a very complete first-cut foundation:

1. Product vision
2. Job model
3. Operator runbook
4. Specialized Iter-3 brief template
5. Review package spec
6. Perception layer spec
7. Full artifact manifest
8. Wave atlas template
9. Operator journal template
10. **This layer handoff contracts document**

This is now a genuinely strong, operator-grade definition of how the "we" in the tagline would actually operate at high quality.

What should we produce next at maximum depth? Strong remaining candidates:

- The **CLI / customer submission surface** spec (how someone actually triggers and tracks one of these jobs)
- First detailed integration thinking with the existing analysis engine (`unified_analysis.py`, `transcribe.py`, etc.)
- The **internal quality bar checklist** an operator should run before considering a package ready to deliver
- A first version of the **pricing / packaging** model tied to artifact depth and human review involvement

Your choice. I'm ready to go very deep.
