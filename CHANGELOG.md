# Changelog

All notable changes to ScreenScribe will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.4] - 2026-01-13

### Added

- **HTML Pro Report** (`--pro`): Interactive HTML report with video player and annotations:
  - Embedded video player with subtitle sync (click finding to seek)
  - Screenshot annotation tools: pen, rectangle, arrow with color picker
  - Lightbox view for full-resolution annotation
  - Annotations persist in localStorage between sessions
  - Green dot indicator on thumbnails with annotations

- **ZIP Export**: Bundle for sharing with AI agents and external tools:
  - `review.json` with human review data (severity, status, notes)
  - `annotated/` folder with PNG screenshots (annotations burned in)
  - Client-side generation via JSZip

- **VTT Subtitle Generator**: Auto-generated subtitles for video player sync

- **Dual API Format Support**: Works with both LibraxisAI Responses API and OpenAI Chat Completions format (auto-detected from endpoint URL)

- **Makefile**: Development workflow with `make dev`, `make test`, `make lint`, git hooks setup

### Changed

- JSON parsing resilience in unified analysis - pipeline continues on malformed API responses

### Fixed

- Annotation position stability - annotations no longer jump on window resize
- Export consistency - annotated screenshots match live preview exactly
- Pen tool element creation
- Arrow head sizing unified between live preview and export

## [0.1.3] - 2025-12-30

### Added

- **Unified VLM Pipeline**: CRITICAL REFACTOR — Single VLM call replaces separate LLM + VLM analysis. VLM now analyzes screenshot AND full transcript context together in one API call. ~45% faster (~20s vs ~37s per finding).

- **Multi-Provider API Support**: Per-endpoint API keys for hybrid setups:
  - `LIBRAXIS_API_KEY` → STT (cheaper transcription)
  - `OPENAI_API_KEY` → LLM + Vision
  - Getter methods: `get_stt_api_key()`, `get_llm_api_key()`, `get_vision_api_key()`

- **Batch Mode**: Process multiple videos with shared context. Response chaining via `previous_response_id` persists across videos — VLM remembers findings from video 1 when analyzing video 2.

- **Explicit Endpoint Configuration**: Full URL configuration instead of path guessing:
  - `SCREENSCRIBE_STT_ENDPOINT=https://api.libraxis.cloud/v1/audio/transcriptions`
  - `SCREENSCRIBE_LLM_ENDPOINT=https://api.openai.com/v1/responses`
  - `SCREENSCRIBE_VISION_ENDPOINT=https://api.openai.com/v1/responses`

- **UnifiedFinding Dataclass**: Combines all semantic + vision fields in single result:
  - Semantic: `is_issue`, `sentiment`, `severity`, `summary`, `action_items`, `suggested_fix`
  - Vision: `ui_elements`, `issues_detected`, `accessibility_notes`, `design_feedback`

### Changed

- VLM receives full transcript context (not just 200 chars)
- Unified auth header: `Authorization: Bearer` (removed `x-api-key`)
- Report structure: `unified_analysis` block replaces separate `semantic_analysis` + `vision_analysis`
- Shared `image_utils.py` module for image encoding (deduplicated)

### Deprecated

- `semantic.py` and `vision.py` kept as legacy reference but no longer used in main pipeline

## [0.1.2] - 2025-12-29

### Added

- **Sentiment Detection**: New `is_issue` and `sentiment` fields in semantic analysis to distinguish real problems from confirmations and positive statements. Supports negation understanding ("doesn't work" vs "doesn't bother me").

- **Audio Quality Validation**: Detects silent recordings and warns about missing microphone input before processing, saving API costs on empty transcriptions.

- **Model Validation (Fail-Fast)**: Validates availability of STT, LLM, and Vision models at pipeline start. Prevents wasted processing when API endpoints are unavailable.

- **Response API Chaining**: Vision analysis now receives context from semantic analysis via Responses API `previous_response_id`. Zero token duplication — the model "remembers" the previous analysis.

- **AI-Optimized Report Format**: JSON output restructured for efficient AI agent consumption with flattened structure and clear action items.

- **Skip Non-Issues Optimization**: Vision analysis automatically skips findings where `is_issue=False`, reducing API calls and processing time.

### Changed

- Report JSON now includes `response_id` field for conversation chaining traceability
- Semantic analysis captures and exposes API response IDs
- Vision prompts shortened when chaining is active (model has context)

### Fixed

- Improved mypy strict type checking compliance
- Consistent error handling across API calls

## [0.1.1] - 2025-12-28

### Added

- **Semantic Pre-Filtering**: LLM analyzes the entire transcript before frame extraction, finding issues that keyword matching might miss
- Custom keywords configuration via YAML files
- Checkpoint system for resumable pipeline processing
- Retry logic with exponential backoff for API resilience
- i18n support for prompts (Polish and English)
- Dry run mode for previewing detection results
- Time estimation before processing

### Changed

- Detection modes: semantic (default) vs keywords-only (fast)
- Improved progress display with Rich panels

## [0.1.0] - 2025-12-27

### Added

- Initial release
- Audio extraction from video files (MOV, MP4) via FFmpeg
- Speech-to-text transcription via LibraxisAI STT API
- Keyword-based issue detection (bugs, changes, UI issues)
- Screenshot extraction at issue timestamps
- Semantic analysis with LLM (severity, action items, suggested fixes)
- Vision analysis with VLM (optional)
- Report generation (JSON and Markdown)
- CLI with `review`, `transcribe`, `config`, and `version` commands
- Configuration management via environment files
- Pre-commit hooks for code quality

---

**Made with (งಠ_ಠ)ง by the ⌜ ScreenScribe ⌟ 𝖙𝖊𝖆𝖒 (c) 2025**
