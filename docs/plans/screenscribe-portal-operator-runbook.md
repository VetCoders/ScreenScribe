# ScreenScribe Portal — Operator Runbook (Specialized for Review Jobs)

**Version:** 0.2 (xhigh effort)
**Status:** Draft for the new product vision

This document defines how an agent operating in (an enhanced) vc-operator posture would actually process one customer job in the ScreenScribe AI Review Portal.

It is the "conductor's score" for this specific type of work: turning a screencast of real product pain + a repo into high-signal, loctree-grounded engineering direction.

---

## 1. Job Intake & Framing (Step 0)

When a new PortalJob arrives:

1. **Declare posture** (mandatory, single line):
   > "Operator mode active — ScreenScribe Review Job {job_id}"

2. **Read the full inputs** (no shortcuts):
   - All screencast(s) — watch them (or have multimodal perception layer transcribe + extract key moments).
   - The repo at the provided commit (via loctree indexing).
   - Any customer-provided notes.
   - Previous waves on this job (if this is a follow-up).

3. **Initial Perception Pass** (non-negotiable):
   - Run fresh `loct context --full` on the repo.
   - Identify the structural "hotspots" that seem related to the pain shown in the video.
   - Extract key moments from the screencast (timestamps + transcribed quotes + visible UI state).

**Output of this step:** Initial "Perception Notes" attached to the job (raw material for later artifacts).

---

## 2. Build the Wave Atlas (The Most Important Step)

This is where vc-operator discipline shines.

Using the multimodal input (screencast pain + structural map), the operator must produce a **Wave Atlas** that answers:

- What are the real problems here? (not just what the customer named)
- Which ones have the highest (user pain × technical blast radius)?
- What is the natural dependency order?
- Which parts can be worked on in parallel?

The atlas should have clear:
- **Wave A** (Foundation / Quick high-confidence wins)
- **Wave B** (Core diagnosis + direction)
- **Wave C** (Deeper parallel explorations)
- **Wave D** (Close-out, recommendations, handoff)

**Critical rule:** Every major problem cluster in the atlas must be traceable to evidence in the screencast **or** a concrete loctree finding.

---

## 3. Perception Specialists Wave (Usually Wave A or B1)

Dispatch specialized agents whose only job is deep perception:

- One or more agents running heavy loctree work (slice, impact, follow, find on the relevant subtrees).
- One agent doing deep multimodal analysis on the screencast (key moments, emotional intensity, exact UI flows shown, contradictions between what user says and what they do).

These agents produce rich PerceptionArtifacts that later waves will consume.

**They do not design solutions.** They only make the invisible visible.

---

## 4. Diagnostic Synthesis Wave

This is usually the highest-leverage single wave.

One (or very few) high-context agent(s) must connect:
- The lived experience shown in the screencast
- The structural reality revealed by loctree

They produce the **DiagnosisArtifact**:
- Problem clusters with evidence
- "What the user is actually feeling" vs "What the code is structurally doing"
- Early hypotheses about root causes

This wave often requires the strongest model and the most careful brief.

---

## 5. Direction & Planning Waves

Once diagnosis is solid, dispatch waves that produce:

- The **Master Architectural Brief** (SCAFFOLD-style document)
- The detailed **Wave Atlas** with dependency graph
- The set of **Iter-3 worker briefs** using the specialized ScreenScribe template

These briefs are the actual "work orders" that could be handed to an engineering team (or to execution agents in higher tiers of the product).

---

## 6. Verification & Human Review Points

The operator must insert explicit verification gates:

- After major perception/diagnosis waves: internal consistency check + loctree re-verification of key claims.
- Before delivering the final package: optional human senior review (especially valuable in early days of the product).

The operator decides when a wave is "good enough to show the customer" vs "needs another iteration."

---

## 7. Close-out & Stop-Point Handoff

When the job reaches a natural stopping point (or the customer has what they need), the operator produces:

1. The final **Review Package** (curated, high-signal bundle of the best artifacts).
2. A clear **Stop-Point Handoff** for the customer:
   - What we found
   - What we recommend as next steps (with clear waves)
   - What remains genuinely ambiguous or would require more input from them
   - Offer for follow-up waves if they want to go deeper

This handoff is the moment where the "operator button" is explicitly passed back to the human.

---

## 8. Journal Discipline (Specific to This Product)

Every significant step in the journal should capture:

- What we learned from the screencast at this point
- What structural truth loctree revealed that contradicted or confirmed the visual evidence
- Why we made a particular scoping or prioritization decision
- Any moments where the multimodal nature of the input was especially powerful (or especially confusing)

This journal becomes extremely valuable training data for improving the system over time.

---

## 9. Anti-Patterns Specific to ScreenScribe Review Jobs

- Treating the screencast as "just context" and mostly doing normal code review.
- Over-trusting the customer's own diagnosis of the problem.
- Under-using loctree (falling back to "reading the code" instead of structural perception).
- Producing beautiful but unactionable reports instead of operator-grade, wave-planned deliverables.
- Forgetting that the customer showed you their actual suffering — the tone and respect in the output matters.

---

## 10. Success Criteria for a Well-Run Job

You know a ScreenScribe review job was run with real discipline when:

- A reader can clearly see the connection between specific painful moments in the video and specific structural problems in the code.
- The recommended direction feels obviously correct once you see both the video and the loctree evidence.
- The wave plan is realistic and respects real dependencies.
- The customer feels "someone actually watched what I showed them and then deeply understood my codebase."

This is much harder than generic AI code review. That is the point.

---

This runbook is the "how we actually deliver on the promise" document.

It is deliberately written in the voice of someone who has internalized the vc-operator posture and is now applying it to this specific, high-leverage product.

Would you like me to continue with the next major artifact (e.g. the exact structure of the final customer "Review Package", or the integration points with the existing ScreenScribe analysis engine)? Or go deeper on any section above?
