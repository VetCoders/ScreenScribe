# Cinescribe Usage Guide

This guide covers practical examples and workflows for using Cinescribe to analyze screencast videos.

## Table of Contents

1. [Basic Usage](#basic-usage)
2. [Common Workflows](#common-workflows)
3. [Understanding Output](#understanding-output)
4. [Advanced Options](#advanced-options)
5. [Troubleshooting](#troubleshooting)

## Basic Usage

### Analyzing a Video

The most common use case is analyzing a screencast recording where someone reviews an application:

```bash
cinescribe review ~/Videos/app-review.mov
```

This will:
1. Extract audio from the video
2. Transcribe the audio with timestamps
3. Detect mentions of bugs, changes, and UI issues
4. Capture screenshots at relevant moments
5. Run AI semantic analysis on each finding
6. Generate JSON and Markdown reports

### Output Location

By default, output goes to a folder named `{video}_review/` next to the video file:

```bash
# Creates: ~/Videos/app-review_review/
cinescribe review ~/Videos/app-review.mov

# Specify custom output directory
cinescribe review ~/Videos/app-review.mov -o ~/Desktop/review-results
```

## Common Workflows

### Quick Review (No AI Analysis)

For a fast review without waiting for AI analysis:

```bash
cinescribe review video.mov --no-semantic --no-vision
```

This gives you:
- Full transcript
- Screenshots at issue timestamps
- Basic report with detected keywords

Processing time: ~1-2 minutes for a 15-minute video.

### Semantic Analysis Only (Recommended)

Skip vision analysis for faster results while keeping the valuable LLM insights:

```bash
cinescribe review video.mov --no-vision
```

This includes:
- Full transcript
- Screenshots
- AI-powered severity ratings
- Action items and suggested fixes
- Executive summary

Processing time: ~10 minutes for a 15-minute video with 40+ issues.

### Full Analysis

Enable all features including vision-based screenshot analysis:

```bash
cinescribe review video.mov
```

This adds:
- UI element identification in screenshots
- Visual issue detection
- Accessibility observations
- Design feedback

Processing time: ~30+ minutes for a 15-minute video.

### Transcription Only

Just get the transcript without any analysis:

```bash
cinescribe transcribe video.mov -o transcript.txt
```

Useful for:
- Quick transcription needs
- Pre-processing before manual review
- Archiving meeting recordings

## Understanding Output

### Directory Structure

```
video_review/
├── transcript.txt      # Plain text transcript
├── report.json         # Full structured data
├── report.md           # Human-readable report
└── screenshots/
    ├── 01_bug_01-23.jpg      # Category_timestamp.jpg
    ├── 02_change_02-45.jpg
    ├── 03_ui_03-12.jpg
    └── ...
```

### Report.md Structure

The Markdown report contains:

```markdown
# Video Review Report

## Executive Summary
[AI-generated 3-5 sentence overview]

## Summary
| Category | Count |
|----------|-------|
| Bugs | 18 |
| Change Requests | 14 |
| UI Issues | 12 |

### By Severity
| Severity | Count |
|----------|-------|
| 🔴 Critical | 2 |
| 🟠 High | 25 |
| 🟡 Medium | 15 |
| 🟢 Low | 2 |

## Findings

### 🐛 #1 BUG 🔴 [CRITICAL] @ 01:23
> Original transcript text...

**AI Analysis:**
- **Summary:** Brief description of the issue
- **Affected:** Component A, Component B
- **Fix:** Suggested resolution

**Action Items:**
- [ ] Task 1
- [ ] Task 2

![Screenshot](01_bug_01-23.jpg)
```

### Report.json Structure

```json
{
  "video": "/path/to/video.mov",
  "generated_at": "2025-12-17T23:39:00",
  "executive_summary": "...",
  "summary": {
    "total": 44,
    "bugs": 18,
    "changes": 14,
    "ui": 12
  },
  "severity_breakdown": {
    "critical": 2,
    "high": 25,
    "medium": 15,
    "low": 2
  },
  "findings": [
    {
      "id": 1,
      "category": "bug",
      "timestamp_start": 83.2,
      "timestamp_formatted": "01:23",
      "text": "Original transcript...",
      "context": "Surrounding text...",
      "keywords": ["nie działa", "bug"],
      "screenshot": "screenshots/01_bug_01-23.jpg",
      "semantic_analysis": {
        "severity": "critical",
        "summary": "...",
        "action_items": ["..."],
        "affected_components": ["..."],
        "suggested_fix": "..."
      }
    }
  ]
}
```

## Advanced Options

### Language Selection

Default is Polish (`pl`), but you can specify other languages:

```bash
# English
cinescribe review video.mov --lang en

# German
cinescribe review video.mov --lang de
```

Note: Keyword detection is optimized for Polish and English.

### Local STT Server

Use a local Whisper server instead of LibraxisAI cloud:

```bash
cinescribe review video.mov --local
```

Requires a local STT server running at `localhost:8237`.

### Report Format Selection

Control which reports are generated:

```bash
# JSON only
cinescribe review video.mov --no-markdown

# Markdown only
cinescribe review video.mov --no-json

# Both (default)
cinescribe review video.mov
```

### Configuration

View current settings:

```bash
cinescribe config --show
```

Output:
```
Current Configuration:

API Base: https://api.libraxis.cloud
API Key: ********************abc123
STT Model: whisper-1
LLM Model: ai-suggestions
Vision Model: ai-suggestions
Language: pl
Semantic Analysis: True
Vision Analysis: True
```

## Troubleshooting

### "No API key" Error

Set your API key:

```bash
cinescribe config --set-key YOUR_API_KEY
```

Or edit `~/.config/cinescribe/config.env` directly.

### FFmpeg Not Found

Install FFmpeg:

```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt install ffmpeg
```

### Slow Processing

Semantic analysis takes ~10-15 seconds per finding. For faster results:

```bash
# Skip AI analysis entirely
cinescribe review video.mov --no-semantic --no-vision

# Skip only vision (recommended)
cinescribe review video.mov --no-vision
```

### No Issues Detected

If no issues are found, check:

1. **Language**: Ensure `--lang` matches the video's language
2. **Keywords**: The detector looks for specific keywords. Try reviewing the transcript:
   ```bash
   cinescribe transcribe video.mov -o transcript.txt
   cat transcript.txt | grep -i "bug\|error\|problem\|zmiana"
   ```

### API Timeout

For large videos with many issues, the API might timeout. Solutions:

1. Process in smaller batches (split video)
2. Skip vision analysis: `--no-vision`
3. Increase timeout in code (edit `semantic.py`, `vision.py`)

### Permission Denied

If you get permission errors:

```bash
# Make sure ~/.local/bin is in PATH
export PATH="$HOME/.local/bin:$PATH"

# Add to your shell profile
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
```

## Tips & Best Practices

### Recording Tips

For best results when recording screencasts:

1. **Speak clearly** and mention specific issues
2. **Use keywords** like "bug", "błąd", "zmiana", "problem"
3. **Pause briefly** when discussing an issue
4. **Reference UI elements** by name

### Workflow Integration

1. **Review meetings**: Record screen reviews, run Cinescribe, get instant task list
2. **QA testing**: Record test sessions, generate bug reports automatically
3. **Design feedback**: Record design reviews, extract UI issues
4. **Code reviews**: Screen-share walkthroughs, capture refactoring needs

### Processing Large Videos

For videos longer than 30 minutes:

```bash
# Split video first (using ffmpeg)
ffmpeg -i long-video.mov -t 900 -c copy part1.mov
ffmpeg -i long-video.mov -ss 900 -t 900 -c copy part2.mov

# Process each part
cinescribe review part1.mov -o review-part1
cinescribe review part2.mov -o review-part2
```

---

**Created by M&K (c)2025 The LibraxisAI Team**
