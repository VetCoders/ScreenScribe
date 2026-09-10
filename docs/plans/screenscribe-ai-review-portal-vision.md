# ScreenScribe AI Review Portal — Full Vision & Artifact System

**Status:** High-Effort Draft v0.2 (xhigh)
**Date:** 2026-05-31
**Context:** Evolution of the family-onko shape merge into a real hosted product
**Core Tagline:** "Daj nam screencast pokazujący problemy z jakimi się borykasz oraz swoje repo — my zrobimy resztę."

---

## 1. The Fundamental Insight

Current software engineering tooling has a massive blind spot:

- **Issue trackers** capture what people *think* the problem is (often poorly).
- **Code analysis tools** (static, AI, etc.) look at the code in isolation.
- **User feedback** is usually textual and low-signal.
- **Screencasts** (the highest-bandwidth way developers actually communicate problems) are almost completely wasted as input for serious engineering work.

**ScreenScribe's unique angle** is to treat the screencast not as "documentation" or "demo", but as **primary, high-fidelity input** — the actual lived experience of friction, confusion, or broken assumptions — and then cross-reference it with deep structural understanding of the codebase.

When you combine:
- Visual + verbal narration of real usage pain (screencast)
- Precise structural perception of the code (loctree + sourcemaps + dependency graphs)
- Disciplined, multi-agent orchestration (vc-operator posture at scale)

...you get something much more powerful than either traditional code review or traditional AI coding assistants.

This is not "AI that writes code from prompts."
This is **"AI that watches how you suffer and then tells you, with structural precision, what to actually build."**

---

## 2. Product Positioning (Level 1)

**ScreenScribe AI Review Portal** is:

> A remote engineering review studio.
> You show us where it hurts (screencast) and give us the body (repo).
> We deliver surgical, high-signal engineering direction.

**Primary customers (initial):**
- Technical founders / small teams who are not senior enough (or don't have time) to do deep architectural diagnosis themselves.
- Teams hitting growth walls where "we know something is wrong but we can't articulate it precisely."
- Companies doing post-mortems or pre-refactor audits.

**Differentiation:**
- Not another static analyzer.
- Not another "chat with your codebase" toy.
- Not generic AI consulting (too slow/expensive).
- **Multimodal + structural + operator-grade discipline** at software speed and cost.

---

## 3. The Core Loop (User Perspective)

1. User records a screencast (5-20 min) while using their own product or debugging.
   - They narrate pain, confusion, "why is this slow?", "this feels wrong", etc.
2. They grant repo access (read-only, specific paths, or full with exclusions).
3. They submit the job via the Portal.
4. System performs deep hybrid analysis.
5. System produces a **high-quality engineering package** (see Artifact System below).
6. Optional: Human senior engineer reviews / augments the package (hybrid model).
7. User receives the package + optional live walkthrough call.

---

## 4. The Artifact System (The Real Product)

This is the heart of the request.

The portal does not deliver "a report" or "some suggestions."

It delivers a **complete, operators-grade engineering work package**, built using the same discipline we developed for vc-operator, but specialized and enhanced for this multimodal input.

### 4.1 Core Package (v1)

Every job produces a structured bundle containing:

**A. Perception Layer (Ground Truth)**
- Loctree full context atlas (structural + runtime map)
- Sourcemap-augmented call graphs and data flow for relevant domains
- Visual findings extracted from the screencast (timestamps + transcribed moments of pain + UI states)
- Cross-references between visual moments and code locations (when possible)

**B. Diagnosis Layer**
- "What the user is actually feeling" (translated from screencast narration into technical terms)
- "What the code is actually doing" (structural truth)
- Gap analysis between the two
- Prioritized problem clusters (not a flat list of issues)

**C. Direction Layer (The Valuable Output)**
- **Master Architectural Brief** (enhanced SCAFFOLD.md style)
- **Wave Atlas** — phased, parallelizable execution plan
- **Iter-3 Worker Briefs** (the 12-section contracts, adapted for this domain)
- **Tracker + Journal** skeleton for the team that will execute the work

**D. Optional Execution Layer (higher tiers)**
- Starter code / refactors for the highest-leverage first wave
- Test harnesses
- Migration scripts

### 4.2 Specialized Adaptations for ScreenScribe + Loctree Input

The standard vc-operator Iter-3 brief is already excellent. For this portal we enhance it with:

- **Visual Evidence sections** — direct links/timestamps into the source screencast.
- **Structural Perception Evidence** — excerpts from loctree atlas + specific slice/impact/find results that justify architectural recommendations.
- **"User Mental Model vs Code Reality"** contrast sections (this is unique value).
- Stronger emphasis on **blast radius** and **dependency ordering** because the input often reveals hidden coupling the user doesn't consciously know about.

---

## 5. Agent Orchestration Model (The Engine)

The portal is powered by fleets of agents running under **enhanced vc-operator posture**.

### Key Roles in the Fleet

- **Perception Specialist(s)**: Heavy loctree + sourcemap + multimodal (screencast transcription + visual analysis) agents. They produce the ground truth layer.
- **Diagnostic Synthesizer**: Connects the visual pain to structural reality. High-context, often higher-tier model.
- **Architecture Scaffolder**: Produces the Master Brief + Wave Atlas (this is where deep product + systems thinking lives).
- **Brief Authors**: Generate the precise Iter-3 worker briefs (can be parallelized).
- **Executor Agents** (optional, higher tier): Actually implement the first wave(s) under strict ownership posture.
- **Verifier / Auditor**: Runs after waves, especially important because the input was ambiguous (screencast).

The **Operator Agent** (vc-operator posture) is the conductor that:
- Builds and maintains the wave atlas
- Dispatches the specialists with proper briefs
- Manages await/recovery
- Maintains the journal and tracker
- Decides when to ask for human (founder or senior reviewer) input
- Produces the final stop-point handoff

This is exactly why we spent so much time defining the vc-operator artifact system — the portal is one of the highest-leverage applications of that posture.

---

## 6. Technical Architecture Sketch (High Level)

**Ingestion Layer**
- Screencast upload + processing (transcription + keyframe extraction + UI state detection)
- Repo ingestion with smart scoping + loctree indexing (incremental where possible)

**Analysis Fabric**
- Loctree as the central structural perception engine
- Multimodal models for screencast understanding
- Agent runtime supporting long-running, stateful operator sessions (the loop mechanism we already have)

**Delivery Layer**
- Structured artifact package (the bundle described above)
- Nice web UI for browsing the findings + waves
- Optional export to Linear/Jira/Notion + GitHub PR drafts

**Trust & Quality Layer**
- Every significant recommendation must be traceable to either:
  - Specific moment in the screencast, or
  - Specific loctree structural finding
- Full provenance and replayability of the agent work (critical for a paid review service)

---

## 7. Phased Build Plan (High Level)

**Phase 0 (Current)**
- Existing local ScreenScribe + the family-onko modular shape work
- Basic job + upload scaffolding we built recently

**Phase 1 — Foundation (MVP of the promise)**
- Solid job model + storage abstraction
- Screencast ingestion + basic multimodal extraction
- Loctree deep integration as first-class citizen
- Operator-orchestrated flow that produces at least the Diagnosis + Direction layers for a narrow domain (e.g. performance or UX friction in a specific flow)
- Basic web portal to submit job and receive package

**Phase 2 — Credible Product**
- Full visual + structural cross-referencing
- High-quality Iter-3 brief generation specialized for this input
- First real paying customers on a manual + semi-automated hybrid model
- Strong provenance and quality bar

**Phase 3 — Leverage**
- More domains (architecture, security smells, onboarding friction, etc.)
- Better automation of the perception and scaffolding layers
- Optional "we can also implement Wave 1 for you" tier

---

## 8. Why This Is Hard (and Therefore Valuable)

Most AI coding tools optimize for the wrong thing: generating code from vague intent.

This product optimizes for something much rarer and higher-leverage:

**Turning ambiguous, high-context, human suffering into precise, structural, actionable engineering truth.**

That is extremely difficult to do well.
Which is exactly why it can be a real business.

---

This document is the starting point for the high-effort design work.

Next steps I can take immediately (tell me the priority):

1. Detailed artifact contract specification (full Iter-3 brief template specialized for ScreenScribe + loctree input).
2. Detailed job/session + orchestration model for the portal.
3. Technical architecture of the ingestion + analysis fabric.
4. Full SCAFFOLD.md for Phase 1 of building the actual portal.
5. Product identity (tone, visual language, etc.) for the portal itself.

Where do you want maximum effort next?
