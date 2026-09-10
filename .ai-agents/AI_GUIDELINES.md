# AI Guidelines for ScreenScribe

## Build and configuration
- Python requires >=3.11 (see `pyproject.toml`).
- Dependency manager: `uv`. Dev install: `uv sync --dev`. CLI install: `uv tool install .`.
- System dependency: `ffmpeg` and `ffprobe` must be on PATH (audio extraction and screenshots).
- Full pipeline (STT -> detection -> unified VLM -> reports):
  - `uv run screenscribe review /path/video.mov`
- Reduced pipeline (fast, no LLM/VLM):
  - `uv run screenscribe review /path/video.mov --keywords-only --no-semantic --no-vision --no-serve`
- Local STT mode:
  - `uv run screenscribe review /path/video.mov --local`
  - Local endpoint is `http://localhost:7237/transcribe` in `screenscribe/transcribe.py`.
- Output defaults:
  - Output dir: `<video_stem>_review/`
  - Reports: `<video_stem>_report.json`, `<video_stem>_report.md`, `<video_stem>_report.html`
  - Screenshots: `screenshots/`
  - Checkpoint: `.screenscribe_cache/checkpoint.json`
- Resume/force:
  - `--resume` uses the checkpoint if the video hash and language still match.
  - `--force` deletes the cache and reprocesses.

### Secrets and environment
- Config file search order (see `screenscribe/config.py`):
  - `~/.config/screenscribe/config.env`
  - `~/.screenscribe.env`
  - `/etc/screenscribe/config.env`
  - Local `.env` is NOT auto-loaded.
- Environment override keys (see `ScreenScribeConfig._load_from_env`):
  - `SCREENSCRIBE_API_KEY`
  - `LIBRAXIS_API_KEY`
  - `OPENAI_API_KEY`
  - `SCREENSCRIBE_STT_API_KEY`
  - `SCREENSCRIBE_LLM_API_KEY`
  - `SCREENSCRIBE_VISION_API_KEY`
  - `SCREENSCRIBE_API_BASE`
  - `LIBRAXIS_API_BASE`
  - `SCREENSCRIBE_STT_ENDPOINT`
  - `SCREENSCRIBE_LLM_ENDPOINT`
  - `SCREENSCRIBE_VISION_ENDPOINT`
  - `SCREENSCRIBE_STT_MODEL`
  - `SCREENSCRIBE_LLM_MODEL`
  - `SCREENSCRIBE_VISION_MODEL`
  - `SCREENSCRIBE_LANGUAGE`
  - `SCREENSCRIBE_SEMANTIC`
  - `SCREENSCRIBE_VISION`
- Safe secrets handling:
  - Use `screenscribe config --init` and `screenscribe config --set-key` to write keys to the home config file.
  - Or set env vars in your shell session. Do not commit secrets.
- Endpoint rules:
  - `SCREENSCRIBE_API_BASE` normalizes and derives `/v1/...` endpoints only if endpoints are still defaults.
  - Explicit endpoints always win. `ScreenScribeConfig.validate()` rejects Libraxis endpoints using `/v1/chat/completions`.

## Testing
- Pytest config is in `pyproject.toml`; markers include `integration` and `slow`.
- Unit tests (verified):
  - `uv run pytest tests/ -v -m "not integration" --tb=short`
- Integration tests (verified to skip without a key):
  - `uv run pytest tests/test_integration.py -v -m integration`
  - Set `LIBRAXIS_API_KEY` to run against the live API.
- Added test example (verified):
  - `tests/test_config_env.py` checks API base normalization and endpoint derivation.
  - `uv run pytest tests/test_config_env.py -v`
- Lint (verified):
  - `uv run ruff check screenscribe tests`
- Type check (currently failing):
  - `uv run mypy screenscribe`
  - Current error: `screenscribe/cli.py:1206` expects `Path` but gets `Path | None`.

## Development practices for AI agents
- Style and tooling:
  - `ruff` format with 100-char lines and double quotes.
  - `mypy` is strict for `screenscribe/` (tests are exempt). Add type hints to new functions.
- CLI output:
  - Use `rich.console.Console` (`console.print`) instead of raw `print`.
- API requests:
  - Reuse `api_utils.retry_request` and `build_llm_request_body` to keep Responses API and Chat Completions compatibility.
- Pipeline structure:
  - Prefer the unified VLM pipeline in `screenscribe/unified_analysis.py`.
  - `screenscribe/semantic.py` and `screenscribe/vision.py` are legacy and only kept for backward compatibility.
- Detection keywords:
  - Use `KeywordsConfig` in `screenscribe/keywords.py`.
  - Keyword files are searched in `keywords.yaml`, `screenscribe_keywords.yaml`, `.screenscribe/keywords.yaml`, or provided via `--keywords-file`.
- Checkpointing:
  - `PipelineCheckpoint` in `screenscribe/checkpoint.py` tracks stages under `.screenscribe_cache`.
  - Keep stage names aligned if adding new pipeline stages.

### Project-specific gotchas
- `--no-semantic` does not skip the semantic prefilter unless `--keywords-only` is also set.
- Batch mode chains `response_id` across videos; only batch related videos if you want shared context.
- Local STT endpoints use the `audio` form field; cloud endpoints use `file`.
- `--serve` starts `python -m http.server` and creates a symlink to the video in the output dir; use `--no-serve` in headless environments.

### Reuse before adding new code
- Search first with `rg` in `screenscribe/` for existing helpers (API utils, report builders, checkpointing, prompts).
- Prefer extending `report.py` and `html_pro` renderers instead of creating parallel report outputs.
- When changing behavior or adding new agent guidance, update `.ai-agents/AI_GUIDELINES.md`.
