# Changelog

All notable changes to ScreenScribe will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
