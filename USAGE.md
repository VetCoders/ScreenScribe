# ScreenScribe Usage Guide

This guide covers practical examples and workflows for using ScreenScribe to analyze screencast videos.

## Table of Contents

1. [Basic Usage](#basic-usage)
2. [Batch Mode](#batch-mode)
3. [Common Workflows](#common-workflows)
4. [Understanding Output](#understanding-output)
5. [Sentiment Detection](#sentiment-detection)
6. [Detection Modes](#detection-modes)
7. [Multi-Provider Setup](#multi-provider-setup)
8. [Advanced Options](#advanced-options)
9. [Time Estimates and Dry Run](#time-estimates-and-dry-run)
10. [Custom Keywords](#custom-keywords)
11. [Resuming Interrupted Processing](#resuming-interrupted-processing)
12. [Troubleshooting](#troubleshooting)

## Basic Usage

### Analyzing a Video

The most common use case is analyzing a screencast recording where someone reviews an application:

```bash
screenscribe review ~/Videos/app-review.mov
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
screenscribe review ~/Videos/app-review.mov

# Specify custom output directory
screenscribe review ~/Videos/app-review.mov -o ~/Desktop/review-results
```

## Batch Mode

Process multiple videos in one command with **shared context** — the AI remembers findings from previous videos via Responses API chaining.

### Analyzing Multiple Videos

```bash
# Process all videos sequentially with context chaining
screenscribe review video1.mov video2.mov video3.mov

# With glob patterns
screenscribe review ~/Videos/sprint-review/*.mov

# With custom output directory
screenscribe review *.mov -o ./all-reviews
```

### How Context Chaining Works

When processing multiple videos, ScreenScribe uses the Responses API `previous_response_id` to maintain context:

```
Video 1, Finding 5 → response_id: "abc123"
Video 2, Finding 1 → previous_response_id: "abc123"  ← VLM knows Video 1 findings!
Video 2, Finding 3 → response_id: "def456"
Video 3, Finding 1 → previous_response_id: "def456"  ← VLM knows Video 1+2!
```

This means:
- Later videos benefit from earlier context
- VLM can identify patterns across videos
- Duplicate findings are better understood

### Output Structure in Batch Mode

Each video gets its own subdirectory:

```
all-reviews/
├── video1_review/
│   ├── transcript.txt
│   ├── report.json
│   ├── report.md
│   └── screenshots/
├── video2_review/
│   └── ...
└── video3_review/
    └── ...
```

### Example: Sprint Review Analysis

```bash
# Analyze all recordings from a sprint review session
screenscribe review \
  ~/Videos/sprint-review/day1.mov \
  ~/Videos/sprint-review/day2.mov \
  ~/Videos/sprint-review/day3.mov \
  -o ~/Reports/sprint-42-review

# VLM will remember issues from day1 when analyzing day2,
# and can say "this is similar to the button issue from earlier"
```

## Common Workflows

### Quick Review (No AI Analysis)

For a fast review without waiting for AI analysis:

```bash
screenscribe review video.mov --no-semantic --no-vision
```

This gives you:
- Full transcript
- Screenshots at issue timestamps
- Basic report with detected keywords

Processing time: ~1-2 minutes for a 15-minute video.

### Semantic Analysis Only (Recommended)

Skip vision analysis for faster results while keeping the valuable LLM insights:

```bash
screenscribe review video.mov --no-vision
```

This includes:
- Full transcript
- Screenshots
- AI-powered severity ratings
- Action items and suggested fixes
- Executive summary

Processing time: ~10 minutes for a 15-minute video with 40+ issues.

### Full Analysis (Unified VLM Pipeline)

Enable all features with the unified VLM pipeline — a single VLM call analyzes both screenshot AND transcript together:

```bash
screenscribe review video.mov
```

This includes:
- Full transcript with timestamps
- Screenshots at issue moments
- **Unified VLM analysis** (semantic + visual in one call):
  - Severity ratings and action items
  - UI element identification
  - Visual issue detection
  - Accessibility observations
  - Design feedback
- Executive summary

Processing time: ~15-20 minutes for a 15-minute video with 40 issues (~20s per finding).

### Transcription Only

Just get the transcript without any analysis:

```bash
screenscribe transcribe video.mov -o transcript.txt
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
        "is_issue": true,
        "sentiment": "problem",
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

See [Sentiment Detection](#sentiment-detection) for details on `is_issue` and `sentiment` fields.

## Sentiment Detection

ScreenScribe understands context and **negations**. Not every detected transcript fragment is a problem - sometimes users confirm that something works correctly.

### Understanding `is_issue` and `sentiment`

Each finding in the report includes:

| Field | Values | Description |
|-------|--------|-------------|
| `is_issue` | `true` / `false` | Whether user reports a problem or confirms OK |
| `sentiment` | `problem` / `positive` / `neutral` | Tone of the user's statement |

### Examples

| User says... | is_issue | sentiment | Interpretation |
|--------------|----------|-----------|----------------|
| "This button doesn't work" | `true` | `problem` | Reports a bug |
| "The white backgrounds don't bother me" | `false` | `positive` | Confirms it's OK |
| "Should be transparent" | `true` | `problem` | Requests a change |
| "Works nicely now" | `false` | `positive` | Confirms fix worked |
| "It's ugly" | `true` | `problem` | Reports UI issue |
| "Let me check this section" | `false` | `neutral` | Neutral observation |

### Negation Handling

ScreenScribe pays special attention to negations:

- "nie działa" (doesn't work) → **problem**
- "nie przeszkadza" (doesn't bother) → **OK**
- "no problem here" → **OK**
- "not an issue" → **OK**

### In Reports

**Markdown report** uses plain-text severity labels (no emojis):

```markdown
### [OK] #3 UI @ 00:32

> The white backgrounds don't bother me in dropdowns.

*User confirms this is working correctly - not an issue.*
```

**JSON report** includes full sentiment data for filtering:

```json
{
  "semantic_analysis": {
    "is_issue": false,
    "sentiment": "positive",
    "severity": "none",
    "summary": "User confirms white backgrounds are acceptable in dropdowns"
  }
}
```

### Filtering in Post-Processing

Use `is_issue` to filter real problems from confirmations:

```bash
# Extract only actual issues
jq '.findings | map(select(.semantic_analysis.is_issue == true))' report.json

# Count real issues vs confirmations
jq '{
  issues: [.findings[] | select(.semantic_analysis.is_issue == true)] | length,
  confirmations: [.findings[] | select(.semantic_analysis.is_issue == false)] | length
}' report.json
```

## Detection Modes

ScreenScribe offers two detection modes with different speed/accuracy tradeoffs.

### Semantic Pre-Filter (Default)

```bash
screenscribe review video.mov
```

**How it works:**
1. LLM analyzes the **entire transcript** before frame extraction
2. Identifies "points of interest" based on context and meaning
3. Extracts screenshots only at flagged moments

**Pros:**
- Finds issues that keyword matching would miss
- Understands implicit problems: "navigation feels slow"
- Contextual awareness: "this works here but not there"

**Cons:**
- Slower (~8s per minute of video for pre-filter)
- Requires API calls

### Keywords Only (Fast Mode)

```bash
screenscribe review video.mov --keywords-only
```

**How it works:**
1. Scans transcript for predefined keywords (bug, błąd, nie działa, etc.)
2. Extracts screenshots at keyword matches
3. No LLM pre-analysis

**Pros:**
- Very fast (<1s for detection)
- No API costs for detection phase
- Predictable results

**Cons:**
- Misses issues without explicit keywords
- No contextual understanding
- ~70-80% recall compared to semantic mode

### When to Use Which

| Scenario | Recommended Mode |
|----------|------------------|
| Full review with budget | Default (semantic) |
| Quick triage | `--keywords-only` |
| API rate limited | `--keywords-only` |
| Non-technical reviewer | Default (semantic) |
| Clear bug mentions | `--keywords-only` |

### Performance Comparison

For a 15-minute video with ~40 issues:

| Mode | Detection Time | API Calls | Issues Found |
|------|----------------|-----------|--------------|
| Semantic | ~2 min | 1 (pre-filter) | ~40 |
| Keywords | <1s | 0 | ~30-35 |

## Multi-Provider Setup

ScreenScribe supports using different API providers for different tasks. This is useful for cost optimization — e.g., cheaper STT with LibraxisAI, powerful VLM with OpenAI.

### Per-Endpoint API Keys

```env
# ~/.config/screenscribe/config.env

# LibraxisAI for STT (cheaper transcription)
LIBRAXIS_API_KEY=vista-xxx

# OpenAI for VLM (unified analysis)
OPENAI_API_KEY=sk-proj-xxx

# Explicit endpoints (full URLs)
SCREENSCRIBE_STT_ENDPOINT=https://api.libraxis.cloud/v1/audio/transcriptions
SCREENSCRIBE_LLM_ENDPOINT=https://api.openai.com/v1/responses
SCREENSCRIBE_VISION_ENDPOINT=https://api.openai.com/v1/responses

# Models
SCREENSCRIBE_STT_MODEL=whisper-1
SCREENSCRIBE_LLM_MODEL=gpt-4o
SCREENSCRIBE_VISION_MODEL=gpt-4o
```

### How Keys Are Resolved

| Key Variable | Used For |
|--------------|----------|
| `LIBRAXIS_API_KEY` | STT endpoint |
| `OPENAI_API_KEY` | LLM + Vision endpoints |
| `SCREENSCRIBE_API_KEY` | Fallback for all endpoints |

### Example Configurations

**All OpenAI:**
```env
OPENAI_API_KEY=sk-proj-xxx
SCREENSCRIBE_STT_ENDPOINT=https://api.openai.com/v1/audio/transcriptions
SCREENSCRIBE_LLM_ENDPOINT=https://api.openai.com/v1/responses
SCREENSCRIBE_VISION_ENDPOINT=https://api.openai.com/v1/responses
```

**All LibraxisAI:**
```env
LIBRAXIS_API_KEY=vista-xxx
# Endpoints default to LibraxisAI, no need to specify
```

**Hybrid (recommended for cost):**
```env
LIBRAXIS_API_KEY=vista-xxx              # STT
OPENAI_API_KEY=sk-proj-xxx              # VLM
SCREENSCRIBE_STT_ENDPOINT=https://api.libraxis.cloud/v1/audio/transcriptions
SCREENSCRIBE_LLM_ENDPOINT=https://api.openai.com/v1/responses
SCREENSCRIBE_VISION_ENDPOINT=https://api.openai.com/v1/responses
```

## Advanced Options

### Language Selection

Default is Polish (`pl`), but you can specify other languages:

```bash
# English
screenscribe review video.mov --lang en

# German
screenscribe review video.mov --lang de
```

Note: Keyword detection is optimized for Polish and English.

### Local STT Server

Use a local Whisper server instead of LibraxisAI cloud:

```bash
screenscribe review video.mov --local
```

Requires a local STT server running at `localhost:8237`.

### Report Format Selection

Control which reports are generated:

```bash
# JSON only
screenscribe review video.mov --no-markdown

# Markdown only
screenscribe review video.mov --no-json

# Both (default)
screenscribe review video.mov
```

### Configuration

View current settings:

```bash
screenscribe config --show
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

## Time Estimates and Dry Run

Before committing to a full analysis (which can take 30+ minutes for long videos), you can preview what will happen.

### Quick Time Estimate

See how long processing will take without doing any work:

```bash
screenscribe review video.mov --estimate
```

Output:
```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃              Estimated Processing Time                         ┃
┣━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫
┃ Step                ┃ Estimate  ┃ Notes                        ┃
┡━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Audio extraction    │ ~5s       │ FFmpeg                       │
│ Transcription       │ ~30s      │ 15.0 min video               │
│ Issue detection     │ <1s       │ Keyword matching             │
│ Screenshots         │ ~10s      │ FFmpeg frame extraction      │
│ Semantic analysis   │ ~8min     │ ~40 detections (estimated)   │
│ Vision analysis     │ ~16min    │ ~40 screenshots (estimated)  │
└─────────────────────┴───────────┴──────────────────────────────┘

Total estimated time: ~25 minutes
Tip: Use --no-vision for faster processing (saves ~60% time)
```

### Dry Run Mode

Run transcription and detection to see exactly what issues will be found, then stop:

```bash
screenscribe review video.mov --dry-run
```

This actually processes the video (transcription takes ~30s), but stops before:
- Taking screenshots
- Running AI analysis
- Generating full reports

Output:
```
─────────────────── Dry Run Results ───────────────────

Found 44 issues:
  • 18 bugs
  • 14 changes
  • 12 UI issues

Sample detections:
  1. [bug] @ 01:23: Ten przycisk nie działa, trzeba to naprawić...
  2. [change] @ 02:45: Powinniśmy zmienić ten layout na bardziej...
  3. [ui] @ 03:12: Modal jest za mały, nie widać całego tekstu...
  ... and 41 more

Estimated time for full processing:
  Semantic analysis: ~8min (44 detections x ~12s)
  Vision analysis: ~18min (44 screenshots x ~25s)

Run without --dry-run to process fully.
```

### When to Use Which

| Mode | Use When |
|------|----------|
| `--estimate` | Quick check before starting, no API calls |
| `--dry-run` | Want to see actual detections before full processing |
| (no flag) | Ready to run full analysis |

## Custom Keywords

ScreenScribe allows you to define custom keywords for issue detection, tailored to your project's vocabulary.

### Creating a Keywords File

```bash
# Generate default keywords.yaml in current directory
screenscribe config --init-keywords
```

This creates a `keywords.yaml` file you can customize:

```yaml
# keywords.yaml
bug:
  # Polish
  - "nie działa"
  - "błąd"
  - "zepsute"
  # English
  - "broken"
  - "crash"
  - "error"
  # Project-specific
  - "regression"
  - "flaky test"

change:
  - "trzeba zmienić"
  - "should refactor"
  - "TODO"
  - "FIXME"

ui:
  - "button"
  - "modal"
  - "dropdown"
  - "navbar"
```

### Using Custom Keywords

```bash
# Explicit file path
screenscribe review video.mov --keywords-file ~/my-project/keywords.yaml

# Auto-detect (looks for keywords.yaml in current directory)
cd ~/my-project
screenscribe review ~/Videos/review.mov
```

### Keywords Search Order

1. Explicit `--keywords-file` path
2. `keywords.yaml` in current directory
3. `screenscribe_keywords.yaml` in current directory
4. `.screenscribe/keywords.yaml` in current directory
5. Built-in defaults (Polish + English)

## Resuming Interrupted Processing

Long videos with many issues can take 30+ minutes to process. If processing is interrupted (Ctrl+C, network error, system restart), you can resume from where it left off.

### How It Works

ScreenScribe automatically saves checkpoints after each pipeline stage:

1. Audio extraction
2. Transcription
3. Issue detection
4. Screenshot extraction
5. Semantic analysis
6. Vision analysis

Checkpoints are stored in `.screenscribe_cache/` inside the output directory.

### Resuming Processing

```bash
# Resume from last checkpoint
screenscribe review video.mov --resume

# With specific output directory
screenscribe review video.mov -o ./my-review --resume
```

When resuming, you'll see:

```
Resuming from checkpoint: 4 stages complete
Completed: audio, transcription, detection, screenshots

Step 1: Audio Extraction - skipped (cached)
Step 2: Transcription - skipped (cached)
Step 3: Issue Detection - skipped (cached)
Step 4: Screenshot Extraction - skipped (cached)
Step 5: Semantic Analysis (LLM)
  [1/44] Analyzing bug @ 12.3s...
```

### Checkpoint Validation

Checkpoints are validated before resuming:

- Video file hash must match (detects if video changed)
- Output directory must match
- Language setting must match

If validation fails, processing starts fresh.

### Clearing Checkpoints

Checkpoints are automatically deleted after successful completion. To force a fresh start:

```bash
# Remove checkpoint manually
rm -rf ./video_review/.screenscribe_cache/

# Or just don't use --resume
screenscribe review video.mov
```

## Error Handling

ScreenScribe uses a "best effort" approach - if something fails, it continues and gives you partial results.

### What Happens When Things Fail

| If this fails... | ScreenScribe will... |
|------------------|----------------------|
| Semantic analysis | Continue without AI insights, report basic detections |
| Vision analysis | Continue without screenshot analysis |
| Executive summary | Continue with individual analyses |
| Single API request | Retry 3 times with backoff, then skip that item |

### Errors in Reports

When errors occur, they appear in your report:

**In Markdown:**
```markdown
## ⚠️ Processing Errors

Some analysis steps encountered errors but processing continued:

- **semantic_analysis:** Connection timeout after 3 retries
- **vision_analysis:** API rate limit exceeded
```

**In JSON:**
```json
{
  "errors": [
    {"stage": "semantic_analysis", "message": "Connection timeout"},
    {"stage": "vision_analysis", "message": "Rate limit exceeded"}
  ]
}
```

### Partial Results Are Still Useful

Even with errors, you get:
- Full transcript
- All detected issues
- Screenshots
- Whatever AI analysis succeeded

This means you never lose work due to a temporary API issue.

## Troubleshooting

### Audio Contains No Speech

If you see this warning:
```
⚠️ Audio appears to contain little or no speech!
The recording may have been made without microphone input.
```

**Common causes:**

1. **Microphone not enabled during recording**
   - macOS: Press `Cmd+Shift+5` → Click "Options" → Select your microphone
   - Windows: Settings → Sound → Input device

2. **Wrong audio input selected**
   - Check System Preferences/Settings for correct microphone
   - Some apps default to "No Audio" or system sounds only

3. **Microphone volume too low**
   - Check input level in System Preferences → Sound → Input
   - Ensure microphone isn't muted

4. **Screen recording without audio permission**
   - macOS: System Preferences → Privacy & Security → Microphone
   - Grant permission to your recording app

**To verify your recording has audio:**
```bash
ffprobe -v quiet -show_streams video.mov | grep -E "codec_type|sample_rate"
```

### "No API key" Error

Set your API key:

```bash
screenscribe config --set-key YOUR_API_KEY
```

Or edit `~/.config/screenscribe/config.env` directly.

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
screenscribe review video.mov --no-semantic --no-vision

# Skip only vision (recommended)
screenscribe review video.mov --no-vision
```

### No Issues Detected

If no issues are found, check:

1. **Language**: Ensure `--lang` matches the video's language
2. **Keywords**: The detector looks for specific keywords. Try reviewing the transcript:
   ```bash
   screenscribe transcribe video.mov -o transcript.txt
   cat transcript.txt | grep -i "bug\|error\|problem\|zmiana"
   ```

### API Timeout or Network Errors

ScreenScribe includes automatic retry logic with exponential backoff. Most transient errors are handled automatically.

If you still experience issues:

1. Use `--resume` to continue from where it stopped
2. Skip vision analysis: `--no-vision`
3. Process in smaller batches (split video)

```bash
# Resume after network error
screenscribe review video.mov --resume
```

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

1. **Review meetings**: Record screen reviews, run ScreenScribe, get instant task list
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
screenscribe review part1.mov -o review-part1
screenscribe review part2.mov -o review-part2
```

---

**Made with (งಠ_ಠ)ง by ⌜ ScreenScribe ⌟ © 2025**

*Maciej & Monika + Klaudiusz (AI) + Mikserka (AI)*
