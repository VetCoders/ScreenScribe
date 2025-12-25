"""Screenshot extraction from video at specific timestamps."""

import subprocess
from pathlib import Path

from rich.console import Console

from .detect import Detection, format_timestamp

console = Console()


def extract_screenshot(video_path: Path, timestamp: float, output_path: Path) -> Path:
    """
    Extract a single screenshot from video at timestamp.

    Args:
        video_path: Path to video file
        timestamp: Time in seconds
        output_path: Where to save the screenshot

    Returns:
        Path to saved screenshot
    """
    cmd = [
        "ffmpeg",
        "-ss",
        str(timestamp),
        "-i",
        str(video_path),
        "-vframes",
        "1",
        "-q:v",
        "2",  # High quality JPEG
        "-y",
        str(output_path),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg screenshot failed: {result.stderr}")

    return output_path


def extract_screenshots_for_detections(
    video_path: Path, detections: list[Detection], output_dir: Path, offset: float = 0.5
) -> list[tuple[Detection, Path]]:
    """
    Extract screenshots for all detections.

    Args:
        video_path: Path to video file
        detections: List of detections
        output_dir: Directory to save screenshots
        offset: Seconds after start to capture (default: 0.5s into segment)

    Returns:
        List of (Detection, screenshot_path) tuples
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    results = []
    console.print(f"[blue]Extracting {len(detections)} screenshots...[/]")

    for i, detection in enumerate(detections, 1):
        # Calculate timestamp (start + offset, but not past end)
        timestamp = min(detection.segment.start + offset, detection.segment.end)

        # Generate filename
        ts_str = format_timestamp(timestamp).replace(":", "-")
        filename = f"{i:02d}_{detection.category}_{ts_str}.jpg"
        output_path = output_dir / filename

        try:
            extract_screenshot(video_path, timestamp, output_path)
            results.append((detection, output_path))
            console.print(f"  [green]✓[/] {filename} [dim]({format_timestamp(timestamp)})[/]")
        except RuntimeError as e:
            console.print(f"  [red]✗[/] Failed: {e}")

    console.print(f"[green]Extracted {len(results)} screenshots[/]")
    return results


def extract_keyframes_around_detection(
    video_path: Path,
    detection: Detection,
    output_dir: Path,
    num_frames: int = 3,
    interval: float = 2.0,
) -> list[Path]:
    """
    Extract multiple keyframes around a detection for context.

    Args:
        video_path: Path to video file
        detection: The detection
        output_dir: Directory to save screenshots
        num_frames: Number of frames to extract
        interval: Seconds between frames

    Returns:
        List of screenshot paths
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Calculate timestamps centered on detection
    center = (detection.segment.start + detection.segment.end) / 2
    start_offset = -((num_frames - 1) / 2) * interval

    paths = []
    for i in range(num_frames):
        timestamp = max(0, center + start_offset + (i * interval))
        ts_str = format_timestamp(timestamp).replace(":", "-")
        filename = f"keyframe_{ts_str}.jpg"
        output_path = output_dir / filename

        try:
            extract_screenshot(video_path, timestamp, output_path)
            paths.append(output_path)
        except RuntimeError:
            pass  # Skip failed frames

    return paths
