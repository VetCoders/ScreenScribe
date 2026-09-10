# ScreenScribe Portal — Specialized Iter-3 Worker Brief Template

**Version:** 0.2 (xhigh)
**Purpose:** This is the canonical contract template used when dispatching agents inside a ScreenScribe Portal review job.

This template is an evolution of the standard vc-operator Iter-3 format (from DISPATCH.md), heavily specialized for the unique input of this product:
- Screencast (visual + narrated pain)
- Repo + deep structural perception (loctree)
- Goal: High-signal engineering direction for real product friction

---

## YAML Frontmatter (Extended for Portal)

```yaml
---
# Standard vc-operator fields
prompt_id: screenscribe-portal-review-20260531-uuid
wave: B
position: 2
mandate: /vc-ownership          # or /vc-marbles, /vc-audit, etc.
recommended_agent: claude       # enforced by model parity
parent_branch: main@f1e6c45
result_branch: feature/portal-review-xxx

# Portal-specific fields (new)
review_job_id: "job_abc123"
source_screencast: "s3://.../pain-point-x.mov"
screencast_key_moments:
  - timestamp: "02:14"
    description: "User expresses frustration with loading state"
    linked_findings: ["slow-initial-render", "missing-skeleton"]
loctree_focus_areas:
  - "component-tree under Dashboard"
  - "data-fetching layer for reports"
  - "state management around filters"
priority: high
customer_segment: "technical founder, 3-8 person team"
---

depends_on: [...]
parallel_with: [...]
blocks: [...]
report_path: ~/.vibecrafted/artifacts/.../portal-reviews/job_abc123/reports/...
authored_by: ...
```

---

## 1. Mission

One paragraph, starting with the Emil-style imperative.

Example:

> You're tasked with deeply analyzing the specific friction the customer showed in the attached screencast around the reporting dashboard loading experience. You have full access to the repo and a rich loctree structural map. Your job is to produce a precise, evidence-based diagnosis that connects the user's lived pain (visible in the video) to concrete structural problems in the code. After this lands, the next wave can design the actual fix with high confidence that they are solving the real problem, not a symptom.

---

## 2. Context & Evidence (Multimodal)

This section is **much richer** than standard vc-operator briefs.

- Direct links/timestamps into the source screencast (with transcribed quotes).
- Key visual states the user went through.
- Relevant loctree slices and impact analyses (pre-computed or to be run).
- Existing architectural context from previous waves in this job.
- Business/product context if provided by the customer.

---

## 3. Files to Create / Explore / Modify

Strong emphasis on:

- **Explore first** (using loctree slice/impact/find).
- Clear distinction between "read for understanding" and "will modify".
- Living Tree warnings are even stricter because changes here affect real customer pain.

Example structure:
```
Explore (mandatory before any recommendation):
  - screenscribe/components/ReportDashboard.tsx (loct slice recommended)
  - ...

Create:
  ...

Modify:
  ...
```

---

## 4. Acceptance Criteria

Even more rigorous than usual, because the input was ambiguous (a screencast).

Must include:
- Every major claim must be traceable to either:
  - A specific moment/timestamp in the screencast, **or**
  - A specific, verifiable loctree structural finding.
- Clear separation between "what the user feels" and "what the code actually does".
- Prioritization that considers both technical blast radius and user pain intensity.

---

## 5. Gates

Standard + Portal-specific:

```bash
# Code quality
make check

# Structural sanity
loct impact <key files changed>

# For this job specifically
# (example) Validate that all findings have either screencast or loctree evidence
```

---

## 6. Out of Scope (Critical in this domain)

Very important because customers often have many pains in one video.

Explicitly list what we are **not** addressing in this specific wave/prompt, even if visible in the screencast.

---

## 7. Living Tree & Perception Discipline (Strengthened)

The standard Living Tree block + strong requirement to use loctree as primary perception tool.

Explicit instruction:

> Before forming any architectural opinion, you must run fresh loctree perception on the relevant areas. Memory of previous waves or general knowledge of the codebase is not sufficient.

---

## 8. Evidence Requirements (New Section)

This is the key specialization:

Every significant finding or recommendation **must** include:

- Type of evidence: `screencast` | `loctree_structural` | `both`
- For screencast: timestamp(s) + short quote or description of the moment.
- For loctree: specific command output or slice reference (e.g. "loct slice screenscribe/components/ReportDashboard.tsx showed 14 importers of the slow data hook").

This makes the output auditable and dramatically increases trust.

---

## 9–12. Remaining Sections

(Recovery, Dependencies, etc. — similar to standard Iter-3, possibly with portal-specific notes.)

---

## 13. Closing Rail (Adapted)

Must still have the emotional/kaomoji/suchar element, but tuned to the seriousness of reviewing someone's real product pain.

Example spirit:
> This person showed you where their product is hurting. Treat the evidence with respect. (ง •̀_•́)ง

---

This template is stricter, more evidence-oriented, and multimodal compared to generic vc-operator briefs. It is designed so that the output of the entire portal job feels like it was done by a very senior, very disciplined engineering team that actually watched the customer suffer and then read the code with x-ray vision.

---

**Next artifacts to define at xhigh effort (tell me the order):**

- Full `PortalJob` + session model spec
- Operator runbook / FLOW.md specific to ScreenScribe review jobs
- The exact structure of the final "Review Package" delivered to the customer
- Integration points with existing ScreenScribe analysis engine (`unified_analysis.py` etc.)

Where should we go deepest next?
