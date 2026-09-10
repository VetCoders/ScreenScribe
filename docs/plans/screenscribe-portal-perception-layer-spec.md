# ScreenScribe Portal — Perception Layer Specification

**Version:** 0.1 (xhigh)
**Status:** Draft

This is the foundation that everything else in the portal builds upon. If the perception layer is weak or shallow, the entire value proposition collapses.

---

## 1. Purpose of the Perception Layer

The Perception Layer's only job is to make the invisible visible with maximum fidelity and minimal interpretation.

It must produce ground truth from two very different modalities:

1. **Human experience** (the screencast — what the user actually felt, saw, and struggled with)
2. **Code reality** (the structural truth of the system via loctree + sourcemaps + static/dynamic analysis)

These two must be cross-referenced at a very fine grain.

---

## 2. Inputs to Perception

For a single review job:

- One or more screencasts (primary narrative + visual evidence)
- Repo at a specific commit (or range)
- Optional: customer notes, specific areas of concern, sourcemaps, build artifacts, etc.

---

## 3. Required Outputs of the Perception Layer

### 3.1 Screencast-Derived Artifacts

- Full transcription with timestamps (high quality, speaker-aware if possible)
- Key moment extraction:
  - Moments of explicit frustration/confusion ("why is this so slow?", "I don't understand what just happened")
  - Moments of surprising behavior
  - Long pauses / hesitation
  - Repeated actions (user trying the same thing multiple ways)
- UI state reconstruction (what screens/views were visible at key moments)
- Emotional intensity / frustration scoring per segment (crude but useful)

### 3.2 Code-Derived Artifacts (Loctree-first)

- Full loctree context atlas for the repo (or intelligently scoped subset)
- Targeted deep slices on areas that appear relevant from the screencast
- Impact analysis on key files/components
- Identification of twins, dead code, high fan-in modules, cycles, etc. that are likely contributing to the observed pain
- Data flow and control flow analysis (especially around the features shown in the video)

### 3.3 Cross-Modal Alignment (The Magic)

This is the unique part:

- Explicit mappings between:
  - Specific timestamp in screencast → specific structural finding in the code
  - User mental model visible in narration → actual architectural reality
- "Friction heatmaps": which parts of the UI flow correspond to which parts of the codebase, ranked by observed user struggle

---

## 4. Quality Standards for Perception

- **No premature diagnosis.** The perception agents must not jump to "the problem is X". Their job is evidence, not conclusions.
- **Maximum provenance.** Every claim must be traceable to a specific timestamp or specific loctree command/output.
- **Honest uncertainty.** If something in the screencast cannot be mapped to code (or vice versa), this must be explicitly noted rather than forced.
- **Depth over breadth.** Better to deeply understand 2-3 key flows with loctree than to superficially touch the entire repo.

---

## 5. Agent Specialization in Perception

For a high-quality perception pass on a ScreenScribe review job, we typically want at least these specialist roles (which can be parallelized):

- **Screencast Perception Specialist** — multimodal understanding of the video + audio
- **Structural Perception Specialist** — heavy loctree + sourcemap work
- **Cross-Modal Synthesizer** — the agent that actually does the alignment between the two (this one is hardest and highest leverage)

These specialists produce raw PerceptionArtifacts that later diagnostic and direction waves consume.

---

## 6. Anti-Patterns in Perception for This Product

- Watching the video once and then mostly doing "normal" code review on the repo.
- Treating loctree as a nice-to-have instead of the primary structural perception tool.
- Over-indexing on what the customer *named* as the problem instead of what they actually showed.
- Shallow loctree usage (only repo-view instead of deep slice/impact/find/follow work on the relevant subgraphs).

---

This layer is what makes the product genuinely different. Everything downstream (diagnosis, direction, the quality of the briefs) is gated by how well this is executed.

---

**Status of the full artifact set (as of this moment):**

Already produced at xhigh effort:

- `screenscribe-ai-review-portal-vision.md`
- `screenscribe-portal-iter3-brief-template.md`
- `screenscribe-portal-job-model.md`
- `screenscribe-portal-operator-runbook.md`
- `screenscribe-review-package-spec.md`
- `screenscribe-portal-perception-layer-spec.md` ← **this one**

Next candidates (tell me priority or suggest others):

- The full **Review Job Artifact Manifest** (every single artifact produced during one job, with purpose and owner)
- Specialized **Wave Atlas template** for these multimodal review jobs
- The **internal operator journal template** for ScreenScribe review work
- First cut of the **CLI / submission surface** for triggering these jobs from the outside

What should we lock in next with maximum depth?
