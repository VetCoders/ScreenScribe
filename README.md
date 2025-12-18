# Cinescribe

**Video review automation for screencast commentary analysis.**

Cinescribe extracts actionable insights from screencast recordings by transcribing audio commentary, detecting mentions of bugs, changes, and UI issues, capturing relevant screenshots, and generating comprehensive reports with AI-powered semantic analysis.

## Features

- **Audio Extraction**: Automatically extracts audio from video files (MOV, MP4, etc.) using FFmpeg
- **Speech-to-Text**: Transcribes audio with word-level timestamps via LibraxisAI STT API
- **Issue Detection**: Identifies bugs, change requests, and UI issues from Polish and English keywords
- **Screenshot Capture**: Extracts frames at timestamps where issues are mentioned
- **Semantic Analysis**: Uses LLM to analyze each finding, assign severity, and suggest fixes
- **Vision Analysis**: Optional screenshot analysis using vision-capable models
- **Report Generation**: Creates JSON and Markdown reports with executive summaries

## Installation

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager
- FFmpeg (for audio/video processing)
- LibraxisAI API key

### Install FFmpeg

```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt install ffmpeg

# Windows (via chocolatey)
choco install ffmpeg
```

### Install Cinescribe

```bash
# Clone the repository
git clone https://github.com/LibraxisAI/cinescribe.git
cd cinescribe

# Install globally using uv
uv tool install .

# Verify installation
cinescribe version
```

### Configure API Key

```bash
# Initialize config and set API key
cinescribe config --init
cinescribe config --set-key YOUR_LIBRAXIS_API_KEY

# Or manually edit ~/.config/cinescribe/config.env
```

## Quick Start

```bash
# Full analysis of a screencast video
cinescribe review path/to/video.mov

# Output to specific directory
cinescribe review video.mov -o ./my-review

# Skip vision analysis (faster)
cinescribe review video.mov --no-vision

# Transcription only
cinescribe transcribe video.mov -o transcript.txt
```

## How It Works

```
Video File (MOV/MP4)
        │
        ▼
┌───────────────────┐
│  Audio Extraction │  FFmpeg extracts audio track
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│   Transcription   │  LibraxisAI STT with timestamps
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│  Issue Detection  │  Keyword matching (PL/EN)
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│    Screenshots    │  FFmpeg frame extraction
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│ Semantic Analysis │  LLM severity + action items
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│  Report Generation│  JSON + Markdown output
└───────────────────┘
```

## Output Structure

```
video_review/
├── transcript.txt      # Full transcription
├── report.json         # Machine-readable report
├── report.md           # Human-readable Markdown
└── screenshots/
    ├── 01_bug_01-23.jpg
    ├── 02_change_02-45.jpg
    └── ...
```

## Report Contents

Each report includes:

- **Executive Summary**: AI-generated overview of key issues and priorities
- **Statistics**: Breakdown by category (bugs, changes, UI) and severity
- **Detailed Findings**: For each detected issue:
  - Timestamp and category
  - Original transcript text
  - Context (surrounding dialogue)
  - AI Analysis:
    - Severity rating (critical/high/medium/low)
    - Summary
    - Affected components
    - Action items
    - Suggested fix
  - Screenshot

## Configuration

Config file location: `~/.config/cinescribe/config.env`

```env
# API Configuration
LIBRAXIS_API_KEY=your-api-key-here
LIBRAXIS_API_BASE=https://api.libraxis.cloud

# Models
CINESCRIBE_STT_MODEL=whisper-1
CINESCRIBE_LLM_MODEL=ai-suggestions
CINESCRIBE_VISION_MODEL=ai-suggestions

# Processing Options
CINESCRIBE_LANGUAGE=pl
CINESCRIBE_SEMANTIC=true
CINESCRIBE_VISION=true
```

## CLI Reference

### `cinescribe review`

Full video analysis pipeline.

```bash
cinescribe review VIDEO [OPTIONS]

Options:
  -o, --output PATH       Output directory (default: VIDEO_review/)
  -l, --lang TEXT         Language code for transcription (default: pl)
  --local                 Use local STT server instead of cloud
  --semantic/--no-semantic  Enable/disable LLM analysis (default: enabled)
  --vision/--no-vision    Enable/disable vision analysis (default: enabled)
  --json/--no-json        Save JSON report (default: enabled)
  --markdown/--no-markdown  Save Markdown report (default: enabled)
```

### `cinescribe transcribe`

Transcription only, without analysis.

```bash
cinescribe transcribe VIDEO [OPTIONS]

Options:
  -o, --output PATH       Output file for transcript
  -l, --lang TEXT         Language code (default: pl)
  --local                 Use local STT server
```

### `cinescribe config`

Manage configuration.

```bash
cinescribe config [OPTIONS]

Options:
  --show                  Show current configuration
  --init                  Create default config file
  --set-key TEXT          Set API key in config
```

### `cinescribe version`

Show version information.

## Detected Keywords

Cinescribe detects issues based on keywords in both Polish and English:

**Bugs**: bug, błąd, nie działa, crash, error, broken, failed, exception...

**Changes**: zmiana, zmienić, poprawić, update, modify, refactor, rename...

**UI Issues**: UI, interfejs, wygląd, layout, design, button, margin, padding...

## Performance

Typical processing times for a 15-minute video:

| Step | Duration |
|------|----------|
| Audio extraction | ~5s |
| Transcription | ~30s |
| Issue detection | <1s |
| Screenshot extraction | ~10s |
| Semantic analysis (44 issues) | ~8-10 min |
| Vision analysis (optional) | ~20+ min |

## Development

```bash
# Clone and setup
git clone https://github.com/LibraxisAI/cinescribe.git
cd cinescribe
uv sync

# Run from source
uv run cinescribe review video.mov

# Run linters
uv run ruff check cinescribe/
uv run mypy cinescribe/

# Run tests
uv run pytest
```

## Architecture

```
cinescribe/
├── __init__.py       # Version info
├── cli.py            # Typer CLI interface
├── config.py         # Configuration management
├── audio.py          # FFmpeg audio extraction
├── transcribe.py     # LibraxisAI STT integration
├── detect.py         # Keyword-based issue detection
├── screenshots.py    # Frame extraction
├── semantic.py       # LLM semantic analysis
├── vision.py         # Vision model analysis
└── report.py         # Report generation (JSON/Markdown)
```

## API Integration

Cinescribe uses LibraxisAI's unified API:

- **STT**: `POST /v1/audio/transcriptions` (OpenAI-compatible)
- **LLM**: `POST /v1/responses` (Responses API format)
- **Vision**: `POST /v1/responses` with `input_image` (auto-routed to VLM)

## License

MIT License

---

**Created by M&K (c)2025 The LibraxisAI Team**
