"""Audio extraction from video files using FFmpeg."""

import subprocess
import tempfile
from pathlib import Path

from rich.console import Console

console = Console()


def extract_audio(video_path: Path, output_path: Path | None = None) -> Path:
    """
    Extract audio from video file using FFmpeg.

    Args:
        video_path: Path to input video file
        output_path: Optional output path. If None, creates temp file.

    Returns:
        Path to extracted audio file (MP3 format for API compatibility)
    """
    if not video_path.exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")

    if output_path is None:
        # Create temp file with .mp3 extension
        temp_dir = Path(tempfile.gettempdir())
        output_path = temp_dir / f"cinescribe_{video_path.stem}.mp3"

    console.print(f"[blue]Extracting audio from:[/] {video_path.name}")

    cmd = [
        "ffmpeg",
        "-i", str(video_path),
        "-vn",  # No video
        "-acodec", "libmp3lame",
        "-q:a", "2",  # High quality
        "-ar", "16000",  # 16kHz for speech recognition
        "-ac", "1",  # Mono
        "-y",  # Overwrite
        str(output_path)
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg failed: {result.stderr}")

    console.print(f"[green]Audio extracted:[/] {output_path}")
    return output_path


def get_video_duration(video_path: Path) -> float:
    """Get video duration in seconds using FFprobe."""
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(video_path)
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        raise RuntimeError(f"FFprobe failed: {result.stderr}")

    return float(result.stdout.strip())
