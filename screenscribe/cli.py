"""CLI interface for ScreenScribe video review automation."""

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel

from . import __version__
from .audio import extract_audio, get_video_duration
from .config import ScreenScribeConfig
from .detect import detect_issues, format_timestamp
from .report import (
    print_report,
    save_enhanced_json_report,
    save_enhanced_markdown_report,
)
from .screenshots import extract_screenshots_for_detections
from .semantic import analyze_detections_semantically, generate_executive_summary
from .transcribe import transcribe_audio
from .vision import analyze_screenshots, generate_visual_summary

console = Console()
app = typer.Typer(
    name="screenscribe",
    help="Video review automation - extract bugs and changes from screencast commentary.",
    add_completion=False,
)


@app.command()
def review(
    video: Annotated[
        Path,
        typer.Argument(
            help="Path to video file (MOV, MP4, etc.)",
            exists=True,
            dir_okay=False,
        ),
    ],
    output: Annotated[
        Path,
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
) -> None:
    """
    Analyze a screencast video for bugs and change requests.

    Extracts audio, transcribes it, detects issues mentioned in commentary,
    captures screenshots, and optionally analyzes with AI models.
    """
    console.print(
        Panel(
            f"[bold cyan]ScreenScribe v{__version__}[/]\n"
            "[dim]Video review automation powered by LibraxisAI[/]",
            border_style="cyan",
        )
    )

    # Load configuration
    config = ScreenScribeConfig.load()
    config.language = language
    config.use_semantic_analysis = semantic
    config.use_vision_analysis = vision

    # Setup output directory
    if output is None:
        output = video.parent / f"{video.stem}_review"
    output.mkdir(parents=True, exist_ok=True)

    console.print(f"\n[blue]Video:[/] {video}")
    console.print(f"[blue]Output:[/] {output}")
    console.print(
        f"[blue]AI Analysis:[/] Semantic={'✓' if semantic else '✗'} Vision={'✓' if vision else '✗'}"
    )

    # Get video duration
    try:
        duration = get_video_duration(video)
        console.print(f"[blue]Duration:[/] {format_timestamp(duration)}\n")
    except RuntimeError:
        console.print("[yellow]Could not determine video duration[/]\n")

    # Step 1: Extract audio
    console.rule("[bold]Step 1: Audio Extraction[/]")
    audio_path = extract_audio(video)
    console.print()

    # Step 2: Transcribe
    console.rule("[bold]Step 2: Transcription[/]")
    transcription = transcribe_audio(
        audio_path, language=language, use_local=local, api_key=config.api_key
    )

    # Save full transcript
    transcript_path = output / "transcript.txt"
    with open(transcript_path, "w", encoding="utf-8") as f:
        f.write(transcription.text)
    console.print(f"[dim]Saved transcript: {transcript_path}[/]\n")

    # Step 3: Detect issues
    console.rule("[bold]Step 3: Issue Detection[/]")
    detections = detect_issues(transcription)
    console.print()

    if not detections:
        console.print("[yellow]No issues detected in the video.[/]")
        return

    # Step 4: Extract screenshots
    console.rule("[bold]Step 4: Screenshot Extraction[/]")
    screenshots_dir = output / "screenshots"
    screenshots = extract_screenshots_for_detections(video, detections, screenshots_dir)
    console.print()

    # Step 5: Semantic Analysis (LLM)
    semantic_analyses = []
    executive_summary = ""
    if semantic and config.api_key:
        console.rule("[bold]Step 5: Semantic Analysis (LLM)[/]")
        semantic_analyses = analyze_detections_semantically(detections, config)
        if semantic_analyses:
            executive_summary = generate_executive_summary(semantic_analyses, config)
        console.print()

    # Step 6: Vision Analysis
    vision_analyses = []
    visual_summary = ""
    if vision and config.api_key:
        console.rule("[bold]Step 6: Vision Analysis[/]")
        vision_analyses = analyze_screenshots(screenshots, config)
        if vision_analyses:
            visual_summary = generate_visual_summary(vision_analyses, config)
        console.print()

    # Step 7: Generate reports
    console.rule("[bold]Step 7: Report Generation[/]")

    if json_report:
        save_enhanced_json_report(
            detections,
            screenshots,
            video,
            output / "report.json",
            semantic_analyses=semantic_analyses,
            vision_analyses=vision_analyses,
            executive_summary=executive_summary,
        )

    if markdown_report:
        save_enhanced_markdown_report(
            detections,
            screenshots,
            video,
            output / "report.md",
            semantic_analyses=semantic_analyses,
            vision_analyses=vision_analyses,
            executive_summary=executive_summary,
            visual_summary=visual_summary,
        )

    console.print()

    # Print executive summary if available
    if executive_summary:
        console.print(
            Panel(executive_summary, title="[bold]Executive Summary[/]", border_style="green")
        )
        console.print()

    # Print summary to console
    print_report(detections, screenshots, video)

    console.print(f"\n[bold green]Done![/] Results saved to: {output}\n")


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
        Path,
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
        audio_path, language=language, use_local=local, api_key=config.api_key
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
    set_key: Annotated[
        str,
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
        path = cfg.save_default_config()
        console.print(f"[green]Config created:[/] {path}")
        console.print("[dim]Edit this file to customize settings[/]")
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
    console.print("Use --show to view config, --init to create, or --set-key to set API key")


@app.command()
def version() -> None:
    """Show version information."""
    console.print(f"[bold]ScreenScribe v{__version__}[/]")
    console.print("[dim]Video review automation powered by LibraxisAI[/]")
    console.print("[dim]Created by M&K (c)2025 The LibraxisAI Team[/]")


if __name__ == "__main__":
    app()
