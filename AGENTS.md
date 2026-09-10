<!-- loctree-doctrine: v1 -->
## **LOCTREE + AICX + VIBECRAFTED — ZŁOTE RUNO**

> **Loctree first, brak doubt. Grep = potwierdzony hak.**

Strukturalna percepcja PRZED każdym sięgnięciem po `grep`/`awk`/`sed`/
`find`/`Read+offset`. Plus aicx jako historia intencji, vibecrafted jako
dyscyplina dowodu. Trio jest kanonem.

**Reguła operacyjna:**

- Pierwszy ruch przy każdym strukturalnym pytaniu (kto importuje X,
  gdzie żyje symbol Y, co pęknie po edycji Z, blast radius, struktura
  katalogu A) → `loctree-mcp` tool (`context` / `slice` / `impact` /
  `find` / `focus` / `follow`).
- Każde sięgnięcie po `grep`/`awk`/`sed`/`find` na rzeczy która
  **powinna być** loctree-side = **hak**. Zapisz wpis do backlogu
  (`cuts/loctree-haki.md` per-repo albo operator-managed global).
- "Doubt" w wyborze tool = anti-pattern. Albo loctree to znajdzie,
  albo nie umie i wtedy hak + fallback.
- Sfabrykowane doctriny ("CodeScribe grep-first", "szybciej grepem",
  "loctree pewnie nie ma") = halucynacja klasy `cutoffflu`. Zakaz.
- `loctree-mcp` niedostępne? Użyj `loct` cli, ale napisz 'haka'
   sygnalizującego ten problem.

**Lokalizacja backloga "Loctree fail":**

- Pisz **na końcu** pliku ~/.vibecrafted/loctree/loctree-fail.md
- Nie twórz na nowo, nie nadpisuj - to plik przeznaczony do appendowania.
- Nie musisz czytać istniejących wpisów. Jeśli Twój hak jest zgłoszony
  kolejny raz to sygnał o jego trafności, a nie powielanie.

**Dlaczego:** Vista (duet weterynarzy × AI agents) to istniejący proof.
Loctree perfection skaluje ten model do każdego foundera nieprogramisty
bez milionów. Continuous backlog closure = warunek wiarygodności tej tezy.

<!-- /loctree-doctrine -->

# AGENTS.md

This file provides guidance to Codex (Codex.ai/code) when working with code in this repository.

## Project Overview

ScreenScribe is a Python CLI tool for video review automation. It extracts actionable insights from screencast recordings by transcribing audio commentary, detecting bugs/changes/UI issues, capturing screenshots at relevant timestamps, and generating AI-powered reports.

## Essential Commands

```bash
# Development setup
uv sync                              # Install dependencies
uv run screenscribe --help          # Run CLI

# Testing
make test                           # Unit tests (fast, no API needed)
make test-integration              # Integration tests (requires LIBRAXIS_API_KEY)
uv run pytest tests/test_detect.py::TestDetectIssues::test_empty_transcription -v  # Single test

# Code quality
make check                         # All checks (lint + typecheck + security)
make lint                          # ruff check screenscribe tests
make format                        # ruff format + fix
make typecheck                     # mypy screenscribe

# Install globally
make install                       # uv tool install .
```

## Architecture

The pipeline processes videos in 7 stages (each checkpointed for resumability):

```
Video → Audio Extraction → STT Transcription → Issue Detection → Screenshots → Semantic Analysis → Vision Analysis → Report
        (FFmpeg)           (LibraxisAI API)    (keywords/LLM)    (FFmpeg)       (LLM)              (VLM)           (JSON/MD)
```

### Core Modules

| Module | Purpose |
|--------|---------|
| `cli.py` | Typer CLI with `review`, `transcribe`, `config`, `version` commands |
| `semantic_filter.py` | LLM pre-filtering on entire transcript (SemanticFilterLevel enum) |
| `detect.py` | Keyword-based issue detection, Detection dataclass |
| `transcribe.py` | LibraxisAI STT integration, Segment/TranscriptionResult dataclasses |
| `api_utils.py` | retry_request() with exponential backoff, make_api_request() |
| `checkpoint.py` | Pipeline state serialization for resumable processing |
| `semantic.py` | Per-finding LLM analysis |
| `vision.py` | VLM screenshot analysis |
| `report.py` | JSON + Markdown report generation |

### Key Data Structures

```python
@dataclass
class Segment:
    id: int
    start: float  # seconds
    end: float
    text: str
    no_speech_prob: float = 0.0

@dataclass
class Detection:
    segment: Segment
    category: str  # "bug", "change", "ui"
    keywords_found: list[str]
    context: str

@dataclass
class PointOfInterest:  # From semantic pre-filter
    timestamp_start: float
    timestamp_end: float
    category: Literal["bug", "change", "ui", "performance", "accessibility", "other"]
    confidence: float
    reasoning: str
    transcript_excerpt: str
```

### Detection Modes

- `--keywords-only` → Fast regex-based detection (SemanticFilterLevel.KEYWORDS)
- Default → LLM analyzes entire transcript before frame extraction (SemanticFilterLevel.BASE)
- Combined → Keywords + semantic merged (SemanticFilterLevel.COMBINED)

## Development Patterns

### HTTP Requests
Always use `httpx` with retry logic:
```python
from .api_utils import retry_request, make_api_request

result = retry_request(my_function, max_retries=3, operation_name="My operation")
response = make_api_request(client, "POST", url, json=payload)
```

### Best-Effort Processing
Pipeline continues even if AI steps fail:
```python
try:
    semantic_analyses = analyze_detections_semantically(detections, config)
except Exception as e:
    console.print(f"[yellow]Semantic analysis failed: {e}[/]")
    pipeline_errors.append({"stage": "semantic_analysis", "message": str(e)})
```

### Terminal Output
Use Rich for all terminal output:
```python
from rich.console import Console
console = Console()
console.print("[blue]Status:[/] Processing...")
console.print(Panel("Summary", border_style="green"))
```

## Configuration

Config loaded from (in order): `.env` → `~/.config/screenscribe/config.env` → `~/.screenscribe.env`

Key environment variables:
- `LIBRAXIS_API_KEY` - Required for cloud STT/LLM
- `LIBRAXIS_API_BASE` - API base URL (default: `https://api.libraxis.cloud`)
- `SCREENSCRIBE_LLM_MODEL` - LLM model (default: `ai-suggestions`)

## Code Style

- **Line length**: 100 characters
- **Type hints**: Strict mypy (all code fully typed)
- **Imports**: Standard → Third-party → Local (relative with `.`)
- **Quotes**: Double quotes
- **Formatter**: ruff

## Testing Notes

- Tests use pytest with `@pytest.mark.integration` for API tests
- Unit tests in `tests/test_detect.py`, `tests/test_semantic_filter.py`
- Integration tests require `LIBRAXIS_API_KEY` env var
- Fixtures use Polish text (bilingual support: PL/EN)

## API Integration

All API calls go through LibraxisAI unified API:
- STT: `POST /v1/audio/transcriptions` (OpenAI-compatible)
- LLM: `POST /v1/responses` (Responses API format)
- Vision: `POST /v1/responses` with `input_image`

HTTP client uses 600s timeout for large file transcription.
