"""Media processing service using FFmpeg."""
import subprocess
import os
import logging
from pathlib import Path
from typing import List

logger = logging.getLogger(__name__)


class MediaProcessor:
    """FFmpeg media processing wrapper."""

    def get_video_duration(self, video_path: str) -> float:
        """Get video duration in seconds."""
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            video_path
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                timeout=30
            )
            return float(result.stdout.strip())
        except Exception as e:
            logger.error(f"Duration error: {e}")
            return 0.0

    def extract_audio(self, video_path: str, output_path: str) -> bool:
        """Extract audio from video."""
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-vn", "-acodec", "pcm_s16le",
            "-ar", "16000",
            "-ac", "1",
            output_path
        ]

        try:
            subprocess.run(
                cmd,
                capture_output=True,
                check=True,
                timeout=120
            )
            return True
        except Exception as e:
            logger.error(f"Audio extraction error: {e}")
            return False

    def extract_frames(
        self,
        video_path: str,
        output_dir: str,
        fps: float = 0.5
    ) -> List[str]:
        """Extract frames from video."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        pattern = str(output_path / "frame_%04d.jpg")

        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-vf", f"fps=1/{int(1/fps)}",
            "-q:v", "2",
            pattern
        ]

        try:
            subprocess.run(
                cmd,
                capture_output=True,
                check=True,
                timeout=300
            )

            # Return list of extracted frames
            frames = sorted(output_path.glob("frame_*.jpg"))
            return [str(f) for f in frames]

        except Exception as e:
            logger.error(f"Frame extraction error: {e}")
            return []
