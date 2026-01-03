"""CLI interface for ScreenScribe video review automation."""

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
    merge_pois_with_detections,
    pois_to_detections,
    semantic_prefilter,
)
from .transcribe import transcribe_audio, validate_audio_quality
from .unified_analysis import (
    UnifiedFinding,
    analyze_all_findings_unified,
    generate_unified_summary,
    generate_visual_summary_unified,
)
from .validation import APIKeyError, ModelValidationError, validate_models

# Legacy imports kept for backwards compatibility (not used in unified pipeline)
# from .vision import analyze_screenshots, generate_visual_summary

console = Console()


def version_callback(value: bool) -> None:
    """Show version and exit."""
    if value:
        console.print(f"[bold]ScreenScribe[/] v{__version__}")
        raise typer.Exit()


app = typer.Typer(
    name="screenscribe",
    help="Video review automation - extract bugs and changes from screencast commentary.",
    add_completion=False,
)


@app.callback()
def main(
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
    pass


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
) -> None:
    """
    Analyze screencast video(s) for bugs and change requests.

    Extracts audio, transcribes it, detects issues mentioned in commentary,
    captures screenshots, and optionally analyzes with AI models.

    Supports batch mode: pass multiple videos and they will be processed
    sequentially with shared context (each video "remembers" previous ones).

    By default, uses semantic pre-filtering (LLM analyzes entire transcript)
    for comprehensive issue detection. Use --keywords-only for faster,
    keyword-based detection.

    Use --resume to continue from a previous interrupted run.
    Use --estimate to see time estimates without processing.
    Use --dry-run to run only transcription and detection (no AI, no screenshots).

    Examples:
        screenscribe review video.mov
        screenscribe review video1.mov video2.mov video3.mov
        screenscribe review ./recordings/*.mov
    """
    # Validate video paths exist
    for video in videos:
        if not video.exists():
            console.print(f"[red]Error:[/] Video not found: {video}")
            raise typer.Exit(1)
        if video.is_dir():
            console.print(f"[red]Error:[/] Path is a directory: {video}")
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
        if output is None:
            video_output = video.parent / f"{video.stem}_review"
        elif len(videos) > 1:
            # Batch mode with -o: use subdirectories
            video_output = output / f"{video.stem}_review"
        else:
            video_output = output
        video_output.mkdir(parents=True, exist_ok=True)

        console.print(f"\n[blue]Video:[/] {video}")
        console.print(f"[blue]Output:[/] {video_output}")
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

        # Check for existing checkpoint
        checkpoint: PipelineCheckpoint | None = None
        if resume:
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
            transcript_path = video_output / "transcript.txt"
            with open(transcript_path, "w", encoding="utf-8") as f:
                f.write(transcription.text)
            console.print(f"[dim]Saved transcript: {transcript_path}[/]\n")
        else:
            console.print("[dim]Step 2: Transcription - skipped (cached)[/]")
            if transcription is None and checkpoint.transcription:
                transcription = deserialize_transcription(checkpoint.transcription)

        if transcription is None:
            console.print("[red]Error: No transcription available[/]")
            continue  # Skip to next video in batch

        # Validate audio quality before proceeding
        is_valid, validation_error = validate_audio_quality(transcription)
        if not is_valid and validation_error:
            console.print()
            console.print(
                Panel(
                    validation_error, title="[bold red]Audio Quality Issue[/]", border_style="red"
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
                pois = semantic_prefilter(transcription, config)
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

                # Second: semantic pre-filter
                pois = semantic_prefilter(transcription, config)

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

        # Save basic report immediately (before AI analysis)
        # This ensures we have results even if AI steps fail
        if json_report:
            save_enhanced_json_report(
                detections,
                screenshots,
                video,
                video_output / "report.json",
                unified_findings=[],
                executive_summary="",
                errors=[],
            )
        if markdown_report:
            save_enhanced_markdown_report(
                detections,
                screenshots,
                video,
                video_output / "report.md",
                unified_findings=[],
                executive_summary="",
                visual_summary="",
                errors=[],
            )
        if html_report:
            if pro_report:
                save_html_report_pro(
                    detections,
                    screenshots,
                    video,
                    video_output / "report.html",
                    segments=transcription.segments if transcription else None,
                    unified_findings=[],
                    executive_summary="",
                    errors=[],
                    embed_video=embed_video,
                )
            else:
                save_html_report(
                    detections,
                    screenshots,
                    video,
                    video_output / "report.html",
                    unified_findings=[],
                    executive_summary="",
                    errors=[],
                )
        console.print("[dim]Basic report saved (AI analysis pending)[/]")

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
                video_output / "report.json",
                unified_findings=unified_findings,
                executive_summary=executive_summary,
                errors=pipeline_errors,
            )

        if markdown_report:
            save_enhanced_markdown_report(
                detections,
                screenshots,
                video,
                video_output / "report.md",
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
                    video_output / "report.html",
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
                    video_output / "report.html",
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

        console.print(f"\n[bold green]Done![/] Results saved to: {video_output}\n")

        # Update context for next video in batch
        if unified_findings:
            last_finding = unified_findings[-1]
            if hasattr(last_finding, "response_id") and last_finding.response_id:
                batch_context_response_id = last_finding.response_id


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
    Transcribe a video file without full analysis.

    Useful for getting just the transcript text.
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
        console.print(f"[green]Transcript saved:[/] {output}")
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

    Config is stored in ~/.config/screenscribe/config.env
    """
    cfg = ScreenScribeConfig.load()

    if set_key:
        cfg.api_key = set_key
        path = cfg.save_default_config()
        console.print(f"[green]API key saved to:[/] {path}")
        return

    if init:
        config_path = Path.home() / ".config" / "screenscribe" / "config.env"
        if config_path.exists():
            console.print(f"[yellow]Config already exists:[/] {config_path}")
            console.print("[dim]Use --show to view current config[/]")
            if not typer.confirm("Overwrite existing config?", default=False):
                console.print("[dim]Aborted. Existing config preserved.[/]")
                return
        path = cfg.save_default_config()
        console.print(f"[green]Config created:[/] {path}")
        console.print("[dim]Edit this file to customize settings[/]")
        return

    if init_keywords:
        keywords_path = Path.cwd() / "keywords.yaml"
        if keywords_path.exists():
            console.print(f"[yellow]Keywords file already exists:[/] {keywords_path}")
            console.print("[dim]Delete it first if you want to reset to defaults[/]")
            return
        save_default_keywords(keywords_path)
        console.print("[dim]Edit this file to customize detection keywords[/]")
        return

    if show:
        console.print("[bold]Current Configuration:[/]\n")
        console.print(f"API Base: {cfg.api_base}")
        console.print(
            f"API Key: {'*' * 20 + cfg.api_key[-8:] if cfg.api_key else '[red]NOT SET[/]'}"
        )
        console.print(f"STT Model: {cfg.stt_model}")
        console.print(f"LLM Model: {cfg.llm_model}")
        console.print(f"Vision Model: {cfg.vision_model}")
        console.print(f"Language: {cfg.language}")
        console.print(f"Semantic Analysis: {cfg.use_semantic_analysis}")
        console.print(f"Vision Analysis: {cfg.use_vision_analysis}")
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
