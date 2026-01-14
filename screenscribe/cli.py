"""CLI interface for ScreenScribe video review automation."""

import os
import shutil
import subprocess
import sys
import webbrowser
from pathlib import Path
from typing import Annotated, Any

import typer
from rich.console import Console
from rich.panel import Panel

from . import __version__
from .audio import FFmpegNotFoundError, check_ffmpeg_installed, extract_audio, get_video_duration
from .checkpoint import (
    PipelineCheckpoint,
    checkpoint_valid_for_video,
    create_checkpoint,
    delete_checkpoint,
    deserialize_detection,
    deserialize_screenshot,
    deserialize_transcription,
    deserialize_unified_finding,
    load_checkpoint,
    save_checkpoint,
    serialize_detection,
    serialize_screenshot,
    serialize_transcription,
    serialize_unified_finding,
)
from .config import ScreenScribeConfig
from .detect import detect_issues, format_timestamp
from .keywords import save_default_keywords
from .report import (
    print_report,
    save_enhanced_json_report,
    save_enhanced_markdown_report,
    save_html_report,
    save_html_report_pro,
)
from .screenshots import extract_screenshots_for_detections

# Legacy imports kept for backwards compatibility (not used in unified pipeline)
# from .semantic import analyze_detections_semantically, generate_executive_summary
from .semantic_filter import (
    SemanticFilterLevel,
    SemanticFilterResult,
    merge_pois_with_detections,
    pois_to_detections,
    semantic_prefilter,
)
from .transcribe import transcribe_audio, validate_audio_quality
from .unified_analysis import (
    UnifiedFinding,
    analyze_all_findings_unified,
    deduplicate_findings,
    generate_unified_summary,
    generate_visual_summary_unified,
)
from .validation import APIKeyError, ModelValidationError, validate_models

# Legacy imports kept for backwards compatibility (not used in unified pipeline)
# from .vision import analyze_screenshots, generate_visual_summary

console = Console()


def _find_next_review_path(base_path: Path) -> tuple[Path, int | None]:
    """Find next available review path, appending _2, _3, etc. if needed.

    Args:
        base_path: The initial desired output path (e.g., video_review)

    Returns:
        Tuple of (available_path, version_number or None if first)
    """

    # Check if base path has a report (not just empty dir or checkpoint)
    def has_report(p: Path) -> bool:
        return (p / "report.html").exists() or (p / "report.json").exists()

    if not base_path.exists() or not has_report(base_path):
        return base_path, None

    # Find next available number
    version = 2
    while True:
        versioned_path = base_path.parent / f"{base_path.name}_{version}"
        if not versioned_path.exists() or not has_report(versioned_path):
            return versioned_path, version
        version += 1
        if version > 99:  # Safety limit
            raise RuntimeError(f"Too many review versions for {base_path.name}")


def version_callback(value: bool) -> None:
    """Show version and exit."""
    if value:
        console.print(f"[bold]ScreenScribe[/] v{__version__}")
        raise typer.Exit()


app = typer.Typer(
    name="screenscribe",
    help="Video review automation with AI-powered analysis. STT→LLM→VLM pipeline.",
    add_completion=False,
)


def _interactive_mode() -> None:
    """Launch interactive mode when no subcommand is given."""
    from rich.prompt import Prompt

    console.print()
    console.print(
        Panel(
            f"[bold]ScreenScribe[/] v{__version__}\n"
            "[dim]Video review automation - extract bugs and changes from screencast[/]",
            border_style="green",
        )
    )
    console.print()

    # Command selection
    commands = {
        "1": ("review", "Analyze video and generate report"),
        "2": ("transcribe", "Transcribe video only"),
        "3": ("config", "Show/edit configuration"),
        "4": ("version", "Show version info"),
    }

    console.print("[bold]Select command:[/]")
    for key, (cmd, desc) in commands.items():
        console.print(f"  [cyan]{key}[/]) [bold]{cmd}[/] - {desc}")
    console.print()

    choice = Prompt.ask("Enter choice", choices=["1", "2", "3", "4"], default="1")
    selected_cmd = commands[choice][0]

    if selected_cmd == "version":
        console.print(f"\n[bold]ScreenScribe[/] v{__version__}")
        raise typer.Exit()

    if selected_cmd == "config":
        console.print("\n[dim]Running:[/] screenscribe config --show")
        subprocess.run([sys.executable, "-m", "screenscribe", "config", "--show"])
        raise typer.Exit()

    # For review/transcribe, ask for video path
    console.print()
    video_path = Prompt.ask(
        "[bold]Video path[/] (paste or drag file here)",
        default="",
    )

    if not video_path.strip():
        console.print("[red]No video path provided. Exiting.[/]")
        raise typer.Exit(1)

    # Clean path (remove quotes if dragged)
    video_path = video_path.strip().strip("'\"")
    video = Path(video_path)

    if not video.exists():
        console.print(f"[red]File not found:[/] [link=file://{video}]{video}[/link]")
        raise typer.Exit(1)

    console.print()
    console.print(f"[dim]Running:[/] screenscribe {selected_cmd} {video}")
    console.print()

    # Use subprocess to call commands (avoids forward reference issues)
    run_cmd = [sys.executable, "-m", "screenscribe", selected_cmd, str(video)]
    subprocess.run(run_cmd)


def _serve_report(output_dir: Path, video_path: Path, port: int = 8765) -> None:
    """Start HTTP server and open report in browser.

    Creates a symlink to the video in output_dir so the server can serve it,
    then starts a simple HTTP server and opens the report in the default browser.

    Args:
        output_dir: Directory containing report.html
        video_path: Path to the source video file
        port: Port for the HTTP server (default: 8765)
    """
    report_file = output_dir / "report.html"
    if not report_file.exists():
        console.print("[yellow]No report.html found, skipping server.[/]")
        return

    # Create symlink to video in output dir if not already there
    video_link = output_dir / video_path.name
    if not video_link.exists() and video_path.exists():
        try:
            video_link.symlink_to(video_path.resolve())
            console.print(
                f"[dim]Created symlink to video: [link=file://{video_link}]{video_link.name}[/link][/]"
            )
        except OSError as e:
            console.print(f"[yellow]Could not create video symlink: {e}[/]")

    # Start HTTP server in background
    console.print()
    console.rule("[bold cyan]Starting Review Server[/]")
    console.print(f"[dim]Serving from:[/] [link=file://{output_dir}]{output_dir}[/link]")
    console.print(f"[bold green]Report URL:[/] http://localhost:{port}/report.html")
    console.print()
    console.print("[dim]Press Ctrl+C to stop the server and exit[/]")
    console.print()

    # Open browser
    url = f"http://localhost:{port}/report.html"
    webbrowser.open(url)

    # Start server (blocking)
    try:
        # Change to output directory and start server
        original_dir = os.getcwd()
        os.chdir(output_dir)

        # Use subprocess for cleaner handling
        server_process = subprocess.Popen(
            [sys.executable, "-m", "http.server", str(port)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        console.print(f"[green]Server running on port {port}[/]")

        # Wait for Ctrl+C
        try:
            server_process.wait()
        except KeyboardInterrupt:
            console.print("\n[yellow]Stopping server...[/]")
            server_process.terminate()
            server_process.wait(timeout=5)

    finally:
        os.chdir(original_dir)
        # Clean up symlink
        if video_link.exists() and video_link.is_symlink():
            try:
                video_link.unlink()
            except OSError:
                pass


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            "-V",
            callback=version_callback,
            is_eager=True,
            help="Show version and exit.",
        ),
    ] = False,
) -> None:
    """ScreenScribe - Video review automation."""
    # If no subcommand given, launch interactive mode
    if ctx.invoked_subcommand is None:
        _interactive_mode()


# Time estimates (seconds per unit)
ESTIMATE_STT_PER_MINUTE = 2.0  # ~2s per minute of video
ESTIMATE_SEMANTIC_PER_DETECTION = 12.0  # ~12s per detection (legacy)
ESTIMATE_VISION_PER_DETECTION = 25.0  # ~25s per screenshot (legacy)
ESTIMATE_UNIFIED_PER_DETECTION = 20.0  # ~20s per finding (unified VLM)
ESTIMATE_SEMANTIC_PREFILTER_PER_MINUTE = 8.0  # ~8s per minute for semantic pre-filter


def _show_estimate(
    duration: float,
    semantic: bool,
    vision: bool,
    detection_count: int | None = None,
    filter_level: str = "keywords",
    use_unified: bool = True,
) -> None:
    """Show estimated processing times.

    Args:
        duration: Video duration in seconds
        semantic: Whether semantic analysis is enabled
        vision: Whether vision analysis is enabled
        detection_count: Known detection count (None for estimate)
        filter_level: Detection filter level (keywords, base, combined)
        use_unified: Whether using unified VLM analysis (default True)
    """
    from rich.table import Table

    table = Table(title="Estimated Processing Time")
    table.add_column("Step", style="cyan")
    table.add_column("Estimate", justify="right")
    table.add_column("Notes", style="dim")

    # Audio extraction (~5s fixed)
    table.add_row("Audio extraction", "~5s", "FFmpeg")

    # STT transcription
    video_minutes = duration / 60
    stt_time = max(30, video_minutes * ESTIMATE_STT_PER_MINUTE)
    table.add_row("Transcription", f"~{int(stt_time)}s", f"{video_minutes:.1f} min video")

    # Detection (depends on filter level)
    prefilter_time = 0.0
    if filter_level in ("base", "combined"):
        prefilter_time = video_minutes * ESTIMATE_SEMANTIC_PREFILTER_PER_MINUTE
        table.add_row(
            "Semantic pre-filter", f"~{int(prefilter_time)}s", "LLM analyzes full transcript"
        )
        if filter_level == "combined":
            table.add_row("Issue detection", "<1s", "Keyword matching + merge")
        else:
            table.add_row("Issue detection", "<1s", "From semantic analysis")
    else:
        table.add_row("Issue detection", "<1s", "Keyword matching")

    # Screenshot extraction
    table.add_row("Screenshots", "~10s", "FFmpeg frame extraction")

    # Estimate detections if not provided
    if detection_count is None:
        if filter_level in ("base", "combined"):
            est_detections = int(video_minutes * 6)  # More findings with semantic
        else:
            est_detections = int(video_minutes * 4)
    else:
        est_detections = detection_count

    # Analysis step (unified or legacy separate)
    if use_unified and (semantic or vision):
        # Unified VLM analysis - single pass
        unified_time = est_detections * ESTIMATE_UNIFIED_PER_DETECTION
        table.add_row(
            "Unified VLM analysis",
            f"~{int(unified_time / 60)}min",
            f"{est_detections} findings x ~{int(ESTIMATE_UNIFIED_PER_DETECTION)}s",
        )
    else:
        # Legacy separate analysis
        if semantic:
            sem_time = est_detections * ESTIMATE_SEMANTIC_PER_DETECTION
            table.add_row(
                "Semantic analysis",
                f"~{int(sem_time / 60)}min",
                f"{est_detections} detections x ~{int(ESTIMATE_SEMANTIC_PER_DETECTION)}s",
            )
        else:
            table.add_row("Semantic analysis", "skipped", "--no-semantic")

        if vision:
            vis_time = est_detections * ESTIMATE_VISION_PER_DETECTION
            table.add_row(
                "Vision analysis",
                f"~{int(vis_time / 60)}min",
                f"{est_detections} screenshots x ~{int(ESTIMATE_VISION_PER_DETECTION)}s",
            )
        else:
            table.add_row("Vision analysis", "skipped", "--no-vision")

    console.print(table)

    # Total estimate
    total_fixed = 5 + stt_time + 1 + 10 + prefilter_time
    if use_unified and (semantic or vision):
        total_analysis = est_detections * ESTIMATE_UNIFIED_PER_DETECTION
    else:
        total_sem = est_detections * ESTIMATE_SEMANTIC_PER_DETECTION if semantic else 0
        total_vis = est_detections * ESTIMATE_VISION_PER_DETECTION if vision else 0
        total_analysis = total_sem + total_vis

    total = total_fixed + total_analysis
    console.print(f"\n[bold]Total estimated time:[/] ~{int(total / 60)} minutes")

    if not semantic and not vision:
        console.print("[dim]Tip: Without AI analysis, processing is very fast![/]")
    elif use_unified:
        console.print("[dim]Using unified VLM pipeline (screenshot + context in single call)[/]")


@app.command()
def review(
    videos: Annotated[
        list[Path],
        typer.Argument(
            help="Path(s) to video file(s) - multiple files processed with shared context",
        ),
    ],
    output: Annotated[
        Path | None,
        typer.Option(
            "--output",
            "-o",
            help="Output directory for screenshots and reports",
        ),
    ] = None,
    language: Annotated[
        str,
        typer.Option(
            "--lang",
            "-l",
            help="Language code for transcription",
        ),
    ] = "pl",
    local: Annotated[
        bool,
        typer.Option(
            "--local",
            help="Use local STT server instead of LibraxisAI cloud",
        ),
    ] = False,
    semantic: Annotated[
        bool,
        typer.Option(
            "--semantic/--no-semantic",
            help="Enable/disable semantic LLM analysis",
        ),
    ] = True,
    vision: Annotated[
        bool,
        typer.Option(
            "--vision/--no-vision",
            help="Enable/disable vision analysis of screenshots",
        ),
    ] = True,
    json_report: Annotated[
        bool,
        typer.Option(
            "--json/--no-json",
            help="Save JSON report",
        ),
    ] = True,
    markdown_report: Annotated[
        bool,
        typer.Option(
            "--markdown/--no-markdown",
            "--md",
            help="Save Markdown report",
        ),
    ] = True,
    html_report: Annotated[
        bool,
        typer.Option(
            "--html/--no-html",
            help="Save interactive HTML report with human review workflow",
        ),
    ] = True,
    pro_report: Annotated[
        bool,
        typer.Option(
            "--pro/--no-pro",
            help="Use Pro HTML template with video player and subtitle sync",
        ),
    ] = True,
    embed_video: Annotated[
        bool,
        typer.Option(
            "--embed-video",
            help="Embed video as base64 in Pro HTML report (only for files <50MB)",
        ),
    ] = False,
    keywords_file: Annotated[
        Path | None,
        typer.Option(
            "--keywords-file",
            "-k",
            help="Path to custom keywords YAML file",
            exists=True,
            dir_okay=False,
        ),
    ] = None,
    resume: Annotated[
        bool,
        typer.Option(
            "--resume",
            help="Resume from previous checkpoint if available",
        ),
    ] = False,
    force: Annotated[
        bool,
        typer.Option(
            "--force",
            help="Force reprocessing, ignore existing checkpoint",
        ),
    ] = False,
    estimate: Annotated[
        bool,
        typer.Option(
            "--estimate",
            help="Show time estimate without processing (uses video duration)",
        ),
    ] = False,
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run",
            help="Run transcription and detection only, show what would be processed",
        ),
    ] = False,
    keywords_only: Annotated[
        bool,
        typer.Option(
            "--keywords-only",
            help="Use fast keyword-based detection instead of semantic pre-filter",
        ),
    ] = False,
    skip_validation: Annotated[
        bool,
        typer.Option(
            "--skip-validation",
            help="Skip model availability check (faster start, may fail mid-pipeline)",
        ),
    ] = False,
    serve: Annotated[
        bool,
        typer.Option(
            "--serve/--no-serve",
            help="Start HTTP server and open report in browser after processing",
        ),
    ] = True,
    port: Annotated[
        int,
        typer.Option(
            "--port",
            "-p",
            help="Port for the HTTP server (default: 8765)",
        ),
    ] = 8765,
    verbose: Annotated[
        bool,
        typer.Option(
            "--verbose",
            "-v",
            help="Show detailed progress and debug information",
        ),
    ] = False,
) -> None:
    """
    Analyze screencast video(s) and generate interactive review reports.

    Pipeline: Audio → STT → Semantic Analysis → Screenshots → VLM → Report

    Features:
    • Response ID chaining: STT→LLM→VLM share context for better analysis
    • Auto-versioning: existing reviews preserved as video_review_2, _3, etc.
    • Interactive HTML report with video player, subtitle sync, and annotations
    • Batch mode: multiple videos with shared context across files

    Detection modes:
    • Default: Semantic pre-filter (LLM analyzes entire transcript)
    • --keywords-only: Fast regex-based detection

    Output options:
    • --serve/--no-serve: Start HTTP server and open report in browser
    • --force: Overwrite existing review instead of versioning
    • --resume: Continue from checkpoint if interrupted

    Examples:
        screenscribe review video.mov
        screenscribe review video1.mov video2.mov video3.mov
        screenscribe review ./recordings/*.mov --no-serve
        screenscribe review video.mov --force --keywords-only
    """
    # Validate video paths exist
    for video in videos:
        if not video.exists():
            console.print(f"[red]Error:[/] Video not found: [link=file://{video}]{video}[/link]")
            raise typer.Exit(1)
        if video.is_dir():
            console.print(
                f"[red]Error:[/] Path is a directory: [link=file://{video}]{video}[/link]"
            )
            raise typer.Exit(1)

    console.print(
        Panel(
            f"[bold cyan]ScreenScribe v{__version__}[/]\n"
            "[dim]Video review automation powered by LibraxisAI[/]",
            border_style="cyan",
        )
    )

    # Check FFmpeg is installed
    try:
        check_ffmpeg_installed()
    except FFmpegNotFoundError as e:
        console.print(f"[red]Error:[/] {e}")
        raise typer.Exit(1) from None

    # Load configuration
    config = ScreenScribeConfig.load()
    config.language = language
    config.use_semantic_analysis = semantic
    config.use_vision_analysis = vision
    config.verbose = verbose

    # Validate endpoint configuration (fail fast on common mistakes)
    config_warnings = config.validate()
    if config_warnings:
        for warning in config_warnings:
            console.print(f"[red]Config Error:[/] {warning}")
        raise typer.Exit(1)

    # Validate model availability (fail fast)
    if not skip_validation and not local:
        try:
            validate_models(config, use_semantic=semantic, use_vision=vision)
        except APIKeyError as e:
            console.print(f"[red]API Key Error:[/] {e}")
            raise typer.Exit(1) from None
        except ModelValidationError as e:
            console.print(f"[red]Model Error:[/] {e}")
            console.print(
                f"[dim]Tip: Check SCREENSCRIBE_{e.model_type.upper()}_MODEL in "
                "~/.config/screenscribe/config.env[/]"
            )
            raise typer.Exit(1) from None

    # Set filter level based on --keywords-only flag
    semantic_filter_level = (
        SemanticFilterLevel.KEYWORDS if keywords_only else SemanticFilterLevel.BASE
    )

    # Batch mode: show overview
    if len(videos) > 1:
        console.print(f"\n[bold cyan]Batch Mode:[/] {len(videos)} videos")
        for i, v in enumerate(videos, 1):
            console.print(f"  {i}. {v.name}")
        console.print("[dim]Videos will share context via response chaining[/]\n")

    # Track context across videos for chaining
    batch_context_response_id: str = ""

    # Process each video
    for video_idx, video in enumerate(videos):
        if len(videos) > 1:
            console.rule(f"[bold magenta]Video {video_idx + 1}/{len(videos)}: {video.name}[/]")

        # Setup output directory (per-video in batch mode)
        video_stem = video.stem  # Video name without extension for file naming
        if output is None:
            base_output = video.parent / f"{video_stem}_review"
        elif len(videos) > 1:
            # Batch mode with -o: use subdirectories
            base_output = output / f"{video_stem}_review"
        else:
            base_output = output

        # Handle existing reviews: append _2, _3, etc. unless --force
        if force:
            video_output = base_output
        else:
            video_output, version = _find_next_review_path(base_output)
            if version:
                console.print(
                    Panel(
                        f"[yellow]Found previous review at:[/] {base_output.name}\n"
                        f"[green]Creating new version:[/] {video_output.name}",
                        title="[bold]Found Previous Review[/]",
                        border_style="yellow",
                    )
                )

        video_output.mkdir(parents=True, exist_ok=True)

        console.print(f"\n[blue]Video:[/] [link=file://{video}]{video}[/link]")
        console.print(f"[blue]Output:[/] [link=file://{video_output}]{video_output}[/link]")
        console.print(
            f"[blue]AI Analysis:[/] Semantic={'✓' if semantic else '✗'} Vision={'✓' if vision else '✗'}"
        )
        console.print(f"[blue]Filter Level:[/] {semantic_filter_level.value}")
        if batch_context_response_id:
            console.print("[blue]Context:[/] Chained from previous video")

        # Get video duration
        duration = 0.0
        try:
            duration = get_video_duration(video)
            console.print(f"[blue]Duration:[/] {format_timestamp(duration)}\n")
        except RuntimeError:
            console.print("[yellow]Could not determine video duration[/]\n")

        # --estimate mode: show time estimates and exit
        if estimate:
            _show_estimate(duration, semantic, vision, filter_level=semantic_filter_level.value)
            continue  # Continue to next video in batch mode

        # Handle --force: delete existing checkpoint
        if force:
            cache_dir = video_output / ".screenscribe_cache"
            if cache_dir.exists():
                shutil.rmtree(cache_dir)
                console.print(
                    "[yellow]Force mode:[/] Deleted existing checkpoint, starting fresh\n"
                )

        # Check for existing checkpoint
        checkpoint: PipelineCheckpoint | None = None
        if resume and not force:
            checkpoint = load_checkpoint(video_output)
            if checkpoint and checkpoint_valid_for_video(checkpoint, video, video_output, language):
                console.print(
                    f"[green]Resuming from checkpoint:[/] "
                    f"{len(checkpoint.completed_stages)} stages complete"
                )
                console.print(f"[dim]Completed: {', '.join(checkpoint.completed_stages)}[/]\n")
            else:
                checkpoint = None
                console.print("[dim]No valid checkpoint found, starting fresh[/]\n")

        # Create new checkpoint if not resuming
        if checkpoint is None:
            checkpoint = create_checkpoint(video, video_output, language)

        # Initialize variables from checkpoint or fresh
        transcription = None
        detections: list[Any] = []
        screenshots: list[Any] = []
        executive_summary = ""
        visual_summary = ""
        pipeline_errors: list[dict[str, str]] = []  # Collect errors for best-effort processing

        # Restore state from checkpoint
        if checkpoint.transcription:
            transcription = deserialize_transcription(checkpoint.transcription)
        if checkpoint.detections:
            detections = [deserialize_detection(d) for d in checkpoint.detections]
        if checkpoint.screenshots:
            screenshots = [deserialize_screenshot(s) for s in checkpoint.screenshots]
        executive_summary = checkpoint.executive_summary
        visual_summary = checkpoint.visual_summary

        # Step 1: Extract audio
        if not checkpoint.is_stage_complete("audio"):
            console.rule("[bold]Step 1: Audio Extraction[/]")
            audio_path = extract_audio(video)
            checkpoint.mark_stage_complete("audio")
            save_checkpoint(checkpoint, video_output)
            console.print()
        else:
            console.print("[dim]Step 1: Audio Extraction - skipped (cached)[/]")
            # Audio is extracted to temp location - need to re-extract if not found
            # This is fine since audio extraction is fast
            audio_path = extract_audio(video)

        # Step 2: Transcribe
        if not checkpoint.is_stage_complete("transcription"):
            console.rule("[bold]Step 2: Transcription[/]")
            transcription = transcribe_audio(
                audio_path,
                language=language,
                use_local=local,
                api_key=config.get_stt_api_key(),
                stt_endpoint=config.stt_endpoint,
                stt_model=config.stt_model,
            )
            checkpoint.transcription = serialize_transcription(transcription)
            checkpoint.mark_stage_complete("transcription")
            save_checkpoint(checkpoint, video_output)

            # Save full transcript
            transcript_path = video_output / f"{video_stem}_transcript.txt"
            with open(transcript_path, "w", encoding="utf-8") as f:
                f.write(transcription.text)
            console.print(
                f"[dim]Saved transcript:[/] [link=file://{transcript_path}]{transcript_path}[/link]\n"
            )
        else:
            console.print("[dim]Step 2: Transcription - skipped (cached)[/]")
            if transcription is None and checkpoint.transcription:
                transcription = deserialize_transcription(checkpoint.transcription)

        if transcription is None:
            console.print("[red]Error: No transcription available[/]")
            continue  # Skip to next video in batch

        # Validate audio quality before proceeding
        is_valid, validation_message, is_warning = validate_audio_quality(transcription)
        if validation_message:
            console.print()
            if is_valid and is_warning:
                console.print(
                    Panel(
                        validation_message,
                        title="[bold yellow]Audio Quality Warning[/]",
                        border_style="yellow",
                    )
                )
                console.print()
            elif not is_valid:
                console.print(
                    Panel(
                        validation_message,
                        title="[bold red]Audio Quality Issue[/]",
                        border_style="red",
                    )
                )
                console.print()
                console.print(
                    "[yellow]Processing stopped.[/] Please fix the audio issue and try again."
                )
                console.print("[dim]If you believe this is a false positive, please report it.[/]")
                delete_checkpoint(video_output)
                continue  # Skip to next video in batch

        # Step 3: Issue Detection (varies by filter level)
        pois = []  # Points of interest from semantic pre-filter

        if not checkpoint.is_stage_complete("detection"):
            console.rule("[bold]Step 3: Issue Detection[/]")

            if semantic_filter_level == SemanticFilterLevel.KEYWORDS:
                # Level 0: Original keyword-based approach
                console.print("[dim]Using keyword-based detection[/]")
                detections = detect_issues(transcription, keywords_file=keywords_file)

            elif semantic_filter_level == SemanticFilterLevel.BASE:
                # Level 1: Semantic pre-filter on entire transcript
                console.print("[cyan]Using semantic pre-filter (analyzing entire transcript)[/]")
                # Chain from STT → semantic filter → VLM
                stt_context = transcription.response_id or batch_context_response_id
                filter_result: SemanticFilterResult = semantic_prefilter(
                    transcription, config, previous_response_id=stt_context
                )
                pois = filter_result.pois
                # Chain semantic filter context to VLM analysis
                if filter_result.response_id:
                    batch_context_response_id = filter_result.response_id
                if pois:
                    # Convert POIs to Detection objects for compatibility
                    detections = pois_to_detections(pois, transcription)
                    console.print(
                        f"[green]Semantic pre-filter identified {len(detections)} findings[/]"
                    )
                else:
                    # Fallback to keywords if semantic fails
                    console.print(
                        "[yellow]Semantic pre-filter returned no results, falling back to keywords[/]"
                    )
                    detections = detect_issues(transcription, keywords_file=keywords_file)

            elif semantic_filter_level == SemanticFilterLevel.COMBINED:
                # Level 2: Keywords + semantic pre-filter
                console.print("[cyan]Using combined detection (keywords + semantic)[/]")

                # First: keyword detection
                keyword_detections = detect_issues(transcription, keywords_file=keywords_file)

                # Second: semantic pre-filter (chain from STT)
                stt_context = transcription.response_id or batch_context_response_id
                filter_result = semantic_prefilter(
                    transcription, config, previous_response_id=stt_context
                )
                pois = filter_result.pois
                # Chain semantic filter context to VLM analysis
                if filter_result.response_id:
                    batch_context_response_id = filter_result.response_id

                if pois:
                    # Merge semantic POIs with keyword detections
                    merged_pois = merge_pois_with_detections(pois, keyword_detections)
                    detections = pois_to_detections(merged_pois, transcription)
                    console.print(
                        f"[green]Combined detection: {len(keyword_detections)} keywords + "
                        f"{len(pois)} semantic → {len(detections)} merged findings[/]"
                    )
                else:
                    # Use keyword detections if semantic fails
                    detections = keyword_detections

            checkpoint.detections = [serialize_detection(d) for d in detections]
            checkpoint.mark_stage_complete("detection")
            save_checkpoint(checkpoint, video_output)
            console.print()
        else:
            console.print("[dim]Step 3: Issue Detection - skipped (cached)[/]")

        if not detections:
            console.print("[yellow]No issues detected in the video.[/]")
            delete_checkpoint(video_output)
            continue

        # --dry-run mode: show detection results and estimates, then exit
        if dry_run:
            console.rule("[bold]Dry Run Results[/]")
            console.print(f"\n[green]Found {len(detections)} issues:[/]")
            console.print(f"  • {sum(1 for d in detections if d.category == 'bug')} bugs")
            console.print(f"  • {sum(1 for d in detections if d.category == 'change')} changes")
            console.print(f"  • {sum(1 for d in detections if d.category == 'ui')} UI issues")

            console.print("\n[bold]Sample detections:[/]")
            for i, d in enumerate(detections[:5], 1):
                console.print(
                    f"  {i}. [{d.category}] @ {format_timestamp(d.segment.start)}: "
                    f"{d.segment.text[:60]}..."
                )
            if len(detections) > 5:
                console.print(f"  ... and {len(detections) - 5} more")

            console.print("\n[bold]Estimated time for full processing:[/]")
            _show_estimate(
                duration,
                semantic,
                vision,
                detection_count=len(detections),
                filter_level=semantic_filter_level.value,
            )

            console.print("\n[dim]Run without --dry-run to process fully.[/]")
            delete_checkpoint(video_output)
            continue

        # Step 4: Extract screenshots
        if not checkpoint.is_stage_complete("screenshots"):
            console.rule("[bold]Step 4: Screenshot Extraction[/]")
            screenshots_dir = video_output / "screenshots"
            screenshots = extract_screenshots_for_detections(video, detections, screenshots_dir)
            checkpoint.screenshots = [serialize_screenshot(d, p) for d, p in screenshots]
            checkpoint.mark_stage_complete("screenshots")
            save_checkpoint(checkpoint, video_output)
            console.print()
        else:
            console.print("[dim]Step 4: Screenshot Extraction - skipped (cached)[/]")

        # Save basic JSON report immediately (before AI analysis)
        # This ensures we have results even if AI steps fail
        if json_report:
            save_enhanced_json_report(
                detections,
                screenshots,
                video,
                video_output / f"{video_stem}_report.json",
                unified_findings=[],
                executive_summary="",
                errors=[],
            )
            console.print("[dim]Basic JSON report saved (AI analysis pending)[/]")

        # Step 5: Unified VLM Analysis - replaces separate semantic + vision
        # VLM analyzes both screenshot AND full transcript context together
        unified_findings: list[UnifiedFinding] = []

        if (semantic or vision) and config.get_vision_api_key():
            if not checkpoint.is_stage_complete("unified_analysis"):
                console.rule("[bold]Step 5: Unified VLM Analysis[/]")
                console.print("[cyan]Analyzing screenshots + transcript context together...[/]")
                try:
                    unified_findings = analyze_all_findings_unified(
                        screenshots, config, previous_response_id=batch_context_response_id
                    )
                    # Deduplicate similar findings before saving
                    if unified_findings:
                        original_count = len(unified_findings)
                        unified_findings = deduplicate_findings(unified_findings)
                        if len(unified_findings) < original_count:
                            console.print(
                                f"[green]Deduplicated:[/] {original_count} → "
                                f"{len(unified_findings)} findings"
                            )
                            # Filter detections/screenshots to match deduplicated findings
                            keep_ids = {f.detection_id for f in unified_findings}
                            if keep_ids and len(keep_ids) < len(screenshots):
                                screenshots = [
                                    (d, p) for (d, p) in screenshots if d.segment.id in keep_ids
                                ]
                                detections = [d for (d, _) in screenshots]
                    checkpoint.unified_findings = [
                        serialize_unified_finding(f) for f in unified_findings
                    ]
                    if unified_findings:
                        try:
                            executive_summary = generate_unified_summary(unified_findings, config)
                            checkpoint.executive_summary = executive_summary
                            visual_summary = generate_visual_summary_unified(unified_findings)
                            checkpoint.visual_summary = visual_summary
                        except Exception as e:
                            console.print(f"[yellow]Summary generation failed: {e}[/]")
                            pipeline_errors.append(
                                {
                                    "stage": "summary_generation",
                                    "message": str(e),
                                }
                            )
                except Exception as e:
                    console.print(f"[yellow]Unified analysis failed: {e}[/]")
                    console.print("[dim]Continuing without AI analysis...[/]")
                    pipeline_errors.append(
                        {
                            "stage": "unified_analysis",
                            "message": str(e),
                        }
                    )
                checkpoint.mark_stage_complete("unified_analysis")
                # Also mark legacy stages complete for checkpoint compatibility
                checkpoint.mark_stage_complete("semantic")
                checkpoint.mark_stage_complete("vision")
                save_checkpoint(checkpoint, video_output)
                console.print()
            else:
                console.print("[dim]Step 5: Unified VLM Analysis - skipped (cached)[/]")
                # Restore from checkpoint if available
                if checkpoint.unified_findings:
                    unified_findings = [
                        deserialize_unified_finding(f) for f in checkpoint.unified_findings
                    ]
        else:
            checkpoint.mark_stage_complete("unified_analysis")
            checkpoint.mark_stage_complete("semantic")
            checkpoint.mark_stage_complete("vision")

        # Step 6: Generate reports
        console.rule("[bold]Step 6: Report Generation[/]")

        if json_report:
            save_enhanced_json_report(
                detections,
                screenshots,
                video,
                video_output / f"{video_stem}_report.json",
                unified_findings=unified_findings,
                executive_summary=executive_summary,
                errors=pipeline_errors,
            )

        if markdown_report:
            save_enhanced_markdown_report(
                detections,
                screenshots,
                video,
                video_output / f"{video_stem}_report.md",
                unified_findings=unified_findings,
                executive_summary=executive_summary,
                visual_summary=visual_summary,
                errors=pipeline_errors,
            )

        if html_report:
            if pro_report:
                save_html_report_pro(
                    detections,
                    screenshots,
                    video,
                    video_output / f"{video_stem}_report.html",
                    segments=transcription.segments if transcription else None,
                    unified_findings=unified_findings,
                    executive_summary=executive_summary,
                    errors=pipeline_errors,
                    embed_video=embed_video,
                )
            else:
                save_html_report(
                    detections,
                    screenshots,
                    video,
                    video_output / f"{video_stem}_report.html",
                    unified_findings=unified_findings,
                    executive_summary=executive_summary,
                    errors=pipeline_errors,
                )

        # Show errors summary if any
        if pipeline_errors:
            console.print(
                f"[yellow]⚠️ {len(pipeline_errors)} error(s) occurred during processing.[/]"
            )
            console.print("[dim]Check report for details. Results are partial.[/]")

        console.print()

        # Print executive summary if available
        if executive_summary:
            console.print(
                Panel(executive_summary, title="[bold]Executive Summary[/]", border_style="green")
            )
            console.print()

        # Print summary to console
        print_report(detections, screenshots, video)

        # Clean up checkpoint on success
        delete_checkpoint(video_output)

        # Final success output
        console.rule("[bold green]Finished successfully![/]")
        console.print()
        json_path = video_output / "report.json"
        md_path = video_output / "report.md"
        html_path = video_output / "report.html"
        console.print(
            f"[green]Enhanced report saved:[/]\n[link=file://{json_path}]{json_path}[/link]"
        )
        console.print(
            f"[green]Enhanced Markdown report saved:[/]\n[link=file://{md_path}]{md_path}[/link]"
        )
        console.print(
            f"[green]HTML Pro report saved:[/]\n[link=file://{html_path}]{html_path}[/link]"
        )
        console.print()
        console.rule(f"[dim]ScreenScribe v{__version__} by VetCoders[/]")

        # Update context for next video in batch
        if unified_findings:
            last_finding = unified_findings[-1]
            if hasattr(last_finding, "response_id") and last_finding.response_id:
                batch_context_response_id = last_finding.response_id

        # Store last video info for serve
        last_video = video
        last_output = video_output

    # After all videos processed, optionally serve the last report
    if serve and "last_output" in locals():
        _serve_report(last_output, last_video, port)


@app.command()
def transcribe(
    video: Annotated[
        Path,
        typer.Argument(
            help="Path to video file",
            exists=True,
            dir_okay=False,
        ),
    ],
    output: Annotated[
        Path | None,
        typer.Option(
            "--output",
            "-o",
            help="Output file for transcript",
        ),
    ] = None,
    language: Annotated[
        str,
        typer.Option(
            "--lang",
            "-l",
            help="Language code for transcription",
        ),
    ] = "pl",
    local: Annotated[
        bool,
        typer.Option(
            "--local",
            help="Use local STT server",
        ),
    ] = False,
) -> None:
    """
    Transcribe video audio to text (no analysis).

    Quick transcription using LibraxisAI STT or local Whisper.
    Outputs plain text transcript to stdout or file.

    Examples:
        screenscribe transcribe video.mov
        screenscribe transcribe video.mov -o transcript.txt
        screenscribe transcribe video.mov --local --lang en
    """
    config = ScreenScribeConfig.load()

    # Extract audio
    audio_path = extract_audio(video)

    # Transcribe
    result = transcribe_audio(
        audio_path,
        language=language,
        use_local=local,
        api_key=config.get_stt_api_key(),
        stt_endpoint=config.stt_endpoint,
        stt_model=config.stt_model,
    )

    # Output
    if output:
        with open(output, "w", encoding="utf-8") as f:
            f.write(result.text)
        console.print(f"[green]Transcript saved:[/] [link=file://{output}]{output}[/link]")
    else:
        console.print()
        console.print(result.text)


@app.command()
def config(
    show: Annotated[
        bool,
        typer.Option(
            "--show",
            help="Show current configuration",
        ),
    ] = False,
    init: Annotated[
        bool,
        typer.Option(
            "--init",
            help="Create default config file",
        ),
    ] = False,
    init_keywords: Annotated[
        bool,
        typer.Option(
            "--init-keywords",
            help="Create keywords.yaml in current directory for customization",
        ),
    ] = False,
    set_key: Annotated[
        str | None,
        typer.Option(
            "--set-key",
            help="Set API key in config",
        ),
    ] = None,
) -> None:
    """
    Manage ScreenScribe configuration.

    Config file: ~/.config/screenscribe/config.env

    Options:
        --show         Display current config values
        --init         Create default config file
        --init-keywords Create keywords.yaml for custom detection
        --set-key KEY  Save API key to config

    Examples:
        screenscribe config --show
        screenscribe config --init
        screenscribe config --set-key sk-xxx
    """
    cfg = ScreenScribeConfig.load()

    if set_key:
        cfg.api_key = set_key
        path = cfg.save_default_config()
        console.print(f"[green]API key saved to:[/] [link=file://{path}]{path}[/link]")
        return

    if init:
        config_path = Path.home() / ".config" / "screenscribe" / "config.env"
        if config_path.exists():
            console.print(
                f"[yellow]Config already exists:[/] [link=file://{config_path}]{config_path}[/link]"
            )
            console.print("[dim]Use --show to view current config[/]")
            if not typer.confirm("Overwrite existing config?", default=False):
                console.print("[dim]Aborted. Existing config preserved.[/]")
                return
        path = cfg.save_default_config()
        console.print(f"[green]Config created:[/] [link=file://{path}]{path}[/link]")
        console.print("[dim]Edit this file to customize settings[/]")
        return

    if init_keywords:
        keywords_path = Path.cwd() / "keywords.yaml"
        if keywords_path.exists():
            console.print(
                f"[yellow]Keywords file already exists:[/] [link=file://{keywords_path}]{keywords_path}[/link]"
            )
            console.print("[dim]Delete it first if you want to reset to defaults[/]")
            return
        save_default_keywords(keywords_path)
        console.print("[dim]Edit this file to customize detection keywords[/]")
        return

    if show:
        console.print("[bold]Current Configuration:[/]\n")

        # API Keys
        console.print("[cyan]API Keys:[/]")
        console.print(
            f"  Main: {'*' * 16 + cfg.api_key[-8:] if cfg.api_key else '[red]NOT SET[/]'}"
        )
        if cfg.stt_api_key and cfg.stt_api_key != cfg.api_key:
            console.print(f"  STT:  {'*' * 16 + cfg.stt_api_key[-8:]}")
        if cfg.llm_api_key and cfg.llm_api_key != cfg.api_key:
            console.print(f"  LLM:  {'*' * 16 + cfg.llm_api_key[-8:]}")
        if cfg.vision_api_key and cfg.vision_api_key != cfg.api_key:
            console.print(f"  Vision: {'*' * 16 + cfg.vision_api_key[-8:]}")

        # Endpoints
        console.print("\n[cyan]Endpoints:[/]")
        console.print(f"  STT:    {cfg.stt_endpoint}")
        console.print(f"  LLM:    {cfg.llm_endpoint}")
        console.print(f"  Vision: {cfg.vision_endpoint}")
        console.print(f"  [dim](Base fallback: {cfg.api_base})[/]")

        # Models
        console.print("\n[cyan]Models:[/]")
        console.print(f"  STT:    {cfg.stt_model}")
        console.print(f"  LLM:    {cfg.llm_model}")
        console.print(f"  Vision: {cfg.vision_model}")

        # Processing
        console.print("\n[cyan]Processing:[/]")
        console.print(f"  Language: {cfg.language}")
        console.print(f"  Semantic: {cfg.use_semantic_analysis}")
        console.print(f"  Vision:   {cfg.use_vision_analysis}")
        return

    # Default: show help
    console.print(
        "Use --show to view config, --init to create, --init-keywords for custom keywords, "
        "or --set-key to set API key"
    )


@app.command()
def version() -> None:
    """Show version information."""
    console.print(f"[bold]ScreenScribe v{__version__}[/]")
    console.print("[dim]Video review automation powered by LibraxisAI[/]")
    console.print(
        "[dim]⌜ScreenScribe⌟ © 2025 — Maciej & Monika + Klaudiusz (AI) & Mikserka (AI)[/]"
    )


if __name__ == "__main__":
    app()
