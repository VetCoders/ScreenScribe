# Family-onko Portal Deploy Preparation — Operator Grade Closure Plan

**Status:** Draft v0.1
**Branch:** `experimental/deployment-preparation`
**Date:** 2026-05-31
**Author:** Klaudiusz (as operator-grade plan for Maciej)
**Context:** Post family-onko shape merge cleanup + multiple loop dispatches
**Explicit Constraint:** Stop at last step before any deployment / release / public exposure.

---

## 1. Context & Diagnosis (Loctree-informed)

### Structural Reality (from `loct context --full --markdown --no-aicx`)

- The project remains structurally dominated by two legacy, high-LOC servers (`analyze_server.py` 1114 LOC, `review_server.py`) and a very large `cli.py` (1941 LOC).
- Core analysis logic lives in `unified_analysis.py` (1766 LOC) — one of the highest-leverage and highest-risk modules.
- The new `screenscribe/server/` package exists but is still small and partially orphaned. `server/app.py` was an aspirational unified factory that, until recent interventions, could not even be instantiated.
- Hotspots with high fan-in: `config.py`, `transcribe.py`, `detect.py`, `unified_analysis.py`.
- There is no coherent job/session abstraction at the system level that could serve as the foundation for a multi-user hosted portal.
- Deployment surface is minimal (basic Dockerfile created late in the process, no storage abstraction, no worker separation, weak env contracts for hosted mode).

### The Real Gap (not just "more cleanup")

We successfully performed **architectural shape surgery** (moving toward the family-onko-portal modular FastAPI style). However, we have not yet built the **product surface** required for a hosted portal:

- Video upload as a first-class, job-oriented operation.
- A durable job/session model that decouples upload from analysis from result consumption.
- A single, credible entrypoint (`server/app.py` or successor) that can serve as the production portal.
- Credible deployment preparation (storage strategy, worker model, environment contracts, containerization that actually supports the new shape).

The current state creates a dangerous illusion: the code looks more "modern" while the hosted product capability remains almost non-existent.

---

## 2. Definition of Done

The gap is considered closed when the following is true:

1. There exists a stable, non-crashing `create_app()` in the `server/` package that serves as the primary entrypoint for hosted usage.
2. A first-class `PortalJob` model exists and is used by upload, analysis triggering, and result retrieval.
3. `POST /upload` creates a job. `POST /jobs/{id}/analyze` can trigger (at minimum) a headless analysis path that produces usable results stored against the job.
4. Basic but credible deployment artifacts exist:
   - Production-grade Dockerfile
   - docker-compose with web + worker separation (even if the worker is initially simple)
   - Storage abstraction (local filesystem + clear extension points)
   - Environment variable contracts documented and validated
5. The CLI has a non-destructive way to run the new portal shape (`screenscribe serve --portal` or equivalent).
6. Existing local interactive flows (`screenscribe review` / `analyze`) remain fully functional and untouched for local users.
7. The entire surface passes `make check` + basic portal flow smoke tests.
8. Clear documentation exists explaining the current state, limitations, and migration path.

**Non-goal (explicit):** This plan does **not** include public deployment, production secrets management, auth layer, scaling, or billing.

---

## 3. Constraints & Guardrails

- **Living Tree**: All work happens on the shared `experimental/deployment-preparation` branch. Dirty worktree is the normal state.
- **Loop Discipline**: The 10-minute recurring dispatch (019e7c91fe56) continues to fire. Every phase must produce shippable increments that survive the next loop firing.
- **No breakage of local DX**: `screenscribe review` and `screenscribe analyze` must continue to work exactly as before for local users.
- **Maximal reuse**: The heavy lifting in `unified_analysis.py`, `transcribe.py`, etc. must be reused rather than duplicated or heavily refactored early.
- **Stop before deployment**: No Docker images pushed, no staging environments created, no public URLs, no `vc-release` steps without explicit new authorization.
- **Loctree priority**: High-fan-in modules (`config.py`, `transcribe.py`, `unified_analysis.py`, `cli.py`) are touched only when strictly necessary and with narrow blast radius.

---

## 4. Phased Step-by-Step Plan

### Phase 0 — Current Baseline (Already Partially Delivered)

**Goal**: Reach a state where the unified app no longer lies and basic job scaffolding exists.

**Already achieved (as of last dispatches):**
- Removal of crashing eager calls in `server/app.py`.
- Introduction of `PortalJob` model + `jobs.py`.
- Upload now creates real jobs.
- `/jobs` and `/jobs/{id}` endpoints.
- Basic `/jobs/{id}/analyze` stub.
- Improved Dockerfile + docker-compose.

**Verification**: The unified app starts. Upload → job creation works. Basic job status works.

**Status**: Mostly complete.

---

### Phase 1 — Make the Portal Flow Actually Do Analysis (Highest Priority)

**Goal**: After uploading a video, an operator can trigger analysis via the new portal surface and receive usable results.

#### 1.1 Headless Analysis Trigger for Jobs
- Implement real (or progressively real) analysis inside `POST /jobs/{job_id}/analyze`.
- Reuse existing functions from `unified_analysis.py`, `transcribe.py`, `detect.py` etc. as much as possible.
- Store results in `job.results` in a structured way.
- Handle errors gracefully and update job status.

**Files expected to change**:
- `screenscribe/server/jobs.py` (possibly extend model)
- `screenscribe/server/routers/jobs.py`
- New or extended service in `screenscribe/server/` (e.g. `analysis_service.py` or thin orchestrator)

**Verification**:
- Upload a video via the unified app.
- Call analyze on the job.
- Job eventually reaches `completed` with some results (even if partial at first).

#### 1.2 Result Retrieval Endpoints
- `GET /jobs/{job_id}/results` (structured JSON)
- Optional lightweight Markdown summary endpoint.

#### 1.3 Storage Configuration
- Make upload directory fully driven by `ScreenScribeConfig` + environment variable.
- Document the contract.

**Decision Point**: How much of the real analysis pipeline do we wire in 1.1 vs. leaving as progressive enhancement?

---

### Phase 2 — Credible Deployment Surface

**Goal**: Someone who receives the code can actually stand up a reasonable hosted environment.

#### 2.1 Production Dockerfile
- Proper multi-stage build.
- Non-root user.
- Healthcheck.
- Minimal attack surface.

#### 2.2 docker-compose Hardening
- Clear separation of concerns (web vs. future worker).
- Named volumes with correct ownership.
- Environment variable documentation.

#### 2.3 Storage Abstraction (First Cut)
- Define a small `StorageBackend` protocol.
- Local filesystem implementation (current behavior).
- Clear extension point + documentation for S3-compatible backend.

#### 2.4 Environment & Configuration for Hosted Mode
- New section in config for portal-specific settings.
- `.env.example` tailored for hosted/portal usage.
- Validation at startup when running in portal mode.

**Files**:
- `Dockerfile` (replace/improve current one)
- `docker-compose.yml`
- `screenscribe/config.py`
- New file: `screenscribe/server/storage.py` (or similar)

---

### Phase 3 — CLI Integration & Controlled Migration Path

**Goal**: Make the new portal shape usable without forcing everyone to use uvicorn directly.

#### 3.1 New CLI Surface
- `screenscribe serve --portal` (or `screenscribe portal serve`).
- This should run the unified `create_app()` with appropriate defaults.

#### 3.2 Optional Legacy UI Exposure
- Decide whether (and how) to expose the old interactive analyze/review UIs under the unified app (e.g. `/legacy/analyze`, `/legacy/review`).

**High risk area** — `cli.py` is a major hotspot. Changes here must be extremely narrow.

---

### Phase 4 — Hardening & Operational Readiness (Pre-Staging)

**Goal**: The surface is no longer obviously dangerous to run in a semi-production environment.

- Basic rate limiting and upload protections.
- Job retention / cleanup policy.
- Structured logging improvements for portal mode.
- Better error surfaces and observability hooks.
- Documentation (`docs/PORTAL.md` or equivalent) that is honest about current limitations.

---

### Phase 5 — Optional / Future (Out of Scope for Initial Closure)

- Real background worker separation.
- Persistent job store (database).
- Authentication / authorization layer.
- Object storage integration (S3 etc.).
- Frontend for upload + job monitoring.
- Scaling / multi-replica considerations.

These are deliberately marked as future so we do not suffer scope explosion.

---

## 5. Risk Register (Operator View)

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|----------|
| Touching high-fan-in modules too early (esp. `unified_analysis.py`, `cli.py`) | High | Very High | Keep changes in `server/` as long as possible. Use narrow adapters. |
| Over-engineering the job model before we know real usage patterns | Medium | High | Start minimal. Add complexity only when driven by actual requirements. |
| Breaking local developer experience | Medium | High | Never change behavior of existing `review` / `analyze` commands in Phase 1–2. |
| Underestimating storage & cleanup requirements | High | Medium | Treat storage abstraction as a first-class citizen from Phase 2. |
| Analysis taking too long and blocking the web worker | High | Medium-High | Design from the beginning with async/background in mind (even if implementation is simple at first). |
| Parallel dispatches from the 10m loop creating conflicting changes | Medium | Medium | Small, frequent, well-described commits. Clear phase boundaries. |

---

## 6. Decision Points (Require Operator Input)

1. Depth of Phase 1.1 analysis integration (full pipeline vs. progressive stub).
2. Storage abstraction scope in Phase 2 (local only vs. local + S3 interface from day one).
3. Whether legacy interactive UIs should be mountable under the unified app early (Phase 3) or later.
4. Exact CLI surface for running the portal (`--portal` flag vs. new subcommand).
5. Tolerance for temporary code duplication between legacy servers and new job-based flow during transition.

---

## 7. Verification & Feedback Loops

- Every sub-phase must pass `make check` (or at minimum `ruff check` + relevant tests).
- Manual smoke test of the portal flow after every meaningful increment.
- The 10-minute loop will naturally provide external review pressure.
- Explicit "gate" at the end of each major phase before moving to the next.

---

## 8. Success Criteria (Measurable)

- An engineer can clone the repo, run the new portal app, upload a video via API, trigger analysis, and retrieve results.
- The same engineer can build and run the application using the provided Docker artifacts.
- Existing local users are completely unaffected.
- The plan itself survives at least two full cycles of the 10-minute dispatch loop without major contradictions.

---

**Next Action**

This document lives at:

**`/Users/maciejgad/vc-workspace/VetCoders/Screenscribe/docs/plans/family-onko-portal-deploy-preparation.md`**

Once you confirm this structure and level of rigor is acceptable, I will expand the highest-priority phases (especially Phase 1) into detailed, file-by-file implementation plans with proposed commit sequencing.

Say the word and we go deeper on the first phase.
