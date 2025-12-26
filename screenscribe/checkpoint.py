"""Checkpoint system for resumable pipeline processing."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from rich.console import Console

from .detect import Detection
from .semantic import SemanticAnalysis
from .transcribe import Segment, TranscriptionResult

console = Console()

CHECKPOINT_DIR_NAME = ".screenscribe_cache"
CHECKPOINT_FILE_NAME = "checkpoint.json"


@dataclass
class PipelineCheckpoint:
    """Checkpoint state for the video processing pipeline."""

    video_path: str
    video_hash: str
    output_dir: str
    language: str

    # Completed stages
    completed_stages: list[str] = field(default_factory=list)

    # Stage data
    transcription: dict[str, Any] | None = None
    detections: list[dict[str, Any]] = field(default_factory=list)
    screenshots: list[dict[str, Any]] = field(default_factory=list)
    semantic_analyses: list[dict[str, Any]] = field(default_factory=list)
    vision_analyses: list[dict[str, Any]] = field(default_factory=list)
    executive_summary: str = ""
    visual_summary: str = ""

    def is_stage_complete(self, stage: str) -> bool:
        """Check if a stage has been completed."""
        return stage in self.completed_stages

    def mark_stage_complete(self, stage: str) -> None:
        """Mark a stage as completed."""
        if stage not in self.completed_stages:
            self.completed_stages.append(stage)

    def get_next_stage(self) -> str | None:
        """Get the next stage to process."""
        all_stages = [
            "audio",
            "transcription",
            "detection",
            "screenshots",
            "semantic",
            "vision",
            "report",
        ]
        for stage in all_stages:
            if stage not in self.completed_stages:
                return stage
        return None


def get_checkpoint_dir(output_dir: Path) -> Path:
    """Get the checkpoint directory path."""
    return output_dir / CHECKPOINT_DIR_NAME


def get_checkpoint_path(output_dir: Path) -> Path:
    """Get the checkpoint file path."""
    return get_checkpoint_dir(output_dir) / CHECKPOINT_FILE_NAME


def compute_file_hash(file_path: Path, chunk_size: int = 65536) -> str:
    """Compute SHA256 hash of a file."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(chunk_size):
            sha256.update(chunk)
    return sha256.hexdigest()[:16]  # First 16 chars is enough for our purposes


def save_checkpoint(checkpoint: PipelineCheckpoint, output_dir: Path) -> None:
    """Save checkpoint to disk."""
    checkpoint_dir = get_checkpoint_dir(output_dir)
    checkpoint_dir.mkdir(parents=True, exist_ok=True)

    checkpoint_path = get_checkpoint_path(output_dir)
    with open(checkpoint_path, "w", encoding="utf-8") as f:
        json.dump(asdict(checkpoint), f, indent=2, ensure_ascii=False)

    console.print(f"[dim]Checkpoint saved: {checkpoint_path}[/]")


def load_checkpoint(output_dir: Path) -> PipelineCheckpoint | None:
    """Load checkpoint from disk if it exists."""
    checkpoint_path = get_checkpoint_path(output_dir)

    if not checkpoint_path.exists():
        return None

    try:
        with open(checkpoint_path, encoding="utf-8") as f:
            data = json.load(f)
        return PipelineCheckpoint(**data)
    except (json.JSONDecodeError, TypeError, KeyError) as e:
        console.print(f"[yellow]Could not load checkpoint: {e}[/]")
        return None


def delete_checkpoint(output_dir: Path) -> None:
    """Delete checkpoint after successful completion."""
    checkpoint_path = get_checkpoint_path(output_dir)
    if checkpoint_path.exists():
        checkpoint_path.unlink()
        console.print("[dim]Checkpoint cleaned up[/]")

    # Also try to remove the cache directory if empty
    checkpoint_dir = get_checkpoint_dir(output_dir)
    if checkpoint_dir.exists() and not any(checkpoint_dir.iterdir()):
        checkpoint_dir.rmdir()


def checkpoint_valid_for_video(
    checkpoint: PipelineCheckpoint, video_path: Path, output_dir: Path, language: str
) -> bool:
    """Check if a checkpoint is valid for the given video."""
    # Check paths match
    if checkpoint.video_path != str(video_path.absolute()):
        console.print("[yellow]Checkpoint is for a different video file[/]")
        return False

    if checkpoint.output_dir != str(output_dir.absolute()):
        console.print("[yellow]Checkpoint is for a different output directory[/]")
        return False

    if checkpoint.language != language:
        console.print("[yellow]Checkpoint is for a different language setting[/]")
        return False

    # Check video hasn't changed
    current_hash = compute_file_hash(video_path)
    if checkpoint.video_hash != current_hash:
        console.print("[yellow]Video file has changed since checkpoint[/]")
        return False

    return True


def create_checkpoint(video_path: Path, output_dir: Path, language: str) -> PipelineCheckpoint:
    """Create a new checkpoint for a video."""
    return PipelineCheckpoint(
        video_path=str(video_path.absolute()),
        video_hash=compute_file_hash(video_path),
        output_dir=str(output_dir.absolute()),
        language=language,
    )


# --- Serialization helpers ---


def serialize_transcription(transcription: TranscriptionResult) -> dict[str, Any]:
    """Serialize TranscriptionResult to dict."""
    return {
        "text": transcription.text,
        "language": transcription.language,
        "segments": [
            {
                "id": s.id,
                "start": s.start,
                "end": s.end,
                "text": s.text,
                "no_speech_prob": s.no_speech_prob,
            }
            for s in transcription.segments
        ],
    }


def deserialize_transcription(data: dict[str, Any]) -> TranscriptionResult:
    """Deserialize dict to TranscriptionResult."""
    segments = [
        Segment(
            id=s["id"],
            start=s["start"],
            end=s["end"],
            text=s["text"],
            no_speech_prob=s.get("no_speech_prob", 0.0),  # Default for old checkpoints
        )
        for s in data["segments"]
    ]
    return TranscriptionResult(text=data["text"], language=data["language"], segments=segments)


def serialize_detection(detection: Detection) -> dict[str, Any]:
    """Serialize Detection to dict."""
    return {
        "segment": {
            "id": detection.segment.id,
            "start": detection.segment.start,
            "end": detection.segment.end,
            "text": detection.segment.text,
            "no_speech_prob": detection.segment.no_speech_prob,
        },
        "category": detection.category,
        "keywords_found": detection.keywords_found,
        "context": detection.context,
    }


def deserialize_detection(data: dict[str, Any]) -> Detection:
    """Deserialize dict to Detection."""
    seg_data = data["segment"]
    segment = Segment(
        id=seg_data["id"],
        start=seg_data["start"],
        end=seg_data["end"],
        text=seg_data["text"],
        no_speech_prob=seg_data.get("no_speech_prob", 0.0),
    )
    return Detection(
        segment=segment,
        category=data["category"],
        keywords_found=data["keywords_found"],
        context=data["context"],
    )


def serialize_semantic_analysis(analysis: SemanticAnalysis) -> dict[str, Any]:
    """Serialize SemanticAnalysis to dict."""
    return asdict(analysis)


def deserialize_semantic_analysis(data: dict[str, Any]) -> SemanticAnalysis:
    """Deserialize dict to SemanticAnalysis."""
    # Add defaults for new fields (backwards compatibility with old checkpoints)
    data.setdefault("is_issue", True)
    data.setdefault("sentiment", "problem")
    return SemanticAnalysis(**data)


def serialize_screenshot(detection: Detection, path: Path) -> dict[str, Any]:
    """Serialize screenshot info to dict."""
    return {
        "detection": serialize_detection(detection),
        "path": str(path),
    }


def deserialize_screenshot(data: dict[str, Any]) -> tuple[Detection, Path]:
    """Deserialize dict to screenshot tuple."""
    detection = deserialize_detection(data["detection"])
    path = Path(data["path"])
    return (detection, path)
