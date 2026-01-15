"""
Media processing service - FFmpeg-based video processing.
"""

import asyncio
import subprocess
import json
import sys
from pathlib import Path
from typing import List, Optional
import logging

from app.core import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def _run_ffmpeg_sync(cmd: List[str], timeout: int = 300) -> tuple:
    """Run FFmpeg command synchronously."""
    try:
        use_shell = sys.platform == "win32"

        if use_shell:
            cmd_str = " ".join(f'"{c}"' if " " in c else c for c in cmd)
            result = subprocess.run(
                cmd_str,
                shell=True,
                capture_output=True,
                timeout=timeout,
            )
        else:
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=timeout,
            )

        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, b"", b"Timeout expired"
    except Exception as e:
        return -1, b"", str(e).encode()


class MediaProcessor:
    """FFmpeg-based media processing service."""

    def __init__(self, base_dir: Optional[Path] = None):
        """Initialize media processor."""
        if base_dir:
            self.base_dir = base_dir
        else:
            self.base_dir = settings.resolve_path(settings.temp_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    async def get_video_duration(self, video_path: Path) -> Optional[float]:
        """Get video duration using ffprobe."""
        try:
            cmd = [
                "ffprobe",
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                str(video_path)
            ]

            returncode, stdout, stderr = await asyncio.to_thread(
                _run_ffmpeg_sync, cmd, 60
            )

            if returncode == 0:
                data = json.loads(stdout.decode())
                duration = float(data.get("format", {}).get("duration", 0))
                logger.info(f"Video duration: {duration:.2f}s")
                return duration
            else:
                logger.error(f"ffprobe failed: {stderr.decode()}")
                return None

        except Exception as e:
            logger.error(f"Failed to get video duration: {e}")
            return None

    async def extract_audio(
        self,
        video_path: Path,
        source_id: str,
        sample_rate: int = 16000
    ) -> Optional[Path]:
        """Extract audio from video file."""
        output_dir = self.base_dir / source_id
        output_dir.mkdir(parents=True, exist_ok=True)
        audio_path = output_dir / "audio.wav"

        try:
            cmd = [
                "ffmpeg",
                "-y",
                "-i", str(video_path),
                "-vn",
                "-acodec", "pcm_s16le",
                "-ar", str(sample_rate),
                "-ac", "1",
                str(audio_path)
            ]

            logger.info(f"Extracting audio from {video_path}")

            returncode, stdout, stderr = await asyncio.to_thread(
                _run_ffmpeg_sync, cmd, 300
            )

            if returncode == 0 and audio_path.exists():
                logger.info(f"Audio extracted to: {audio_path}")
                return audio_path
            else:
                logger.error(f"FFmpeg audio extraction failed: {stderr.decode()}")
                return None

        except Exception as e:
            logger.error(f"Failed to extract audio: {e}")
            return None

    async def extract_frames(
        self,
        video_path: Path,
        source_id: str,
        interval: int = 5
    ) -> List[Path]:
        """Extract frames from video at specified interval."""
        output_dir = self.base_dir / source_id / "frames"
        output_dir.mkdir(parents=True, exist_ok=True)

        try:
            output_pattern = output_dir / "frame_%05d.jpg"

            cmd = [
                "ffmpeg",
                "-y",
                "-i", str(video_path),
                "-vf", f"fps=1/{interval}",
                "-q:v", "2",
                str(output_pattern)
            ]

            logger.info(f"Extracting frames every {interval}s from {video_path}")

            returncode, stdout, stderr = await asyncio.to_thread(
                _run_ffmpeg_sync, cmd, 300
            )

            if returncode == 0:
                frames = sorted(output_dir.glob("frame_*.jpg"))
                logger.info(f"Extracted {len(frames)} frames")
                return frames
            else:
                logger.error(f"FFmpeg frame extraction failed: {stderr.decode()}")
                return []

        except Exception as e:
            logger.error(f"Failed to extract frames: {e}")
            return []

    async def process_video(
        self,
        video_path: Path,
        source_id: str,
        frame_interval: int = 5
    ) -> dict:
        """Full video processing: extract audio and frames."""
        logger.info(f"Processing video: {video_path}")

        duration_task = self.get_video_duration(video_path)
        audio_task = self.extract_audio(video_path, source_id)
        frames_task = self.extract_frames(video_path, source_id, frame_interval)

        duration, audio_path, frame_paths = await asyncio.gather(
            duration_task, audio_task, frames_task
        )

        result = {
            "duration": duration,
            "audio_path": audio_path,
            "frame_paths": frame_paths,
            "frame_interval": frame_interval,
        }

        logger.info(f"Video processing complete: {len(frame_paths)} frames")
        return result


_media_processor: Optional[MediaProcessor] = None


def get_media_processor() -> MediaProcessor:
    """Get or create MediaProcessor singleton."""
    global _media_processor
    if _media_processor is None:
        _media_processor = MediaProcessor()
    return _media_processor
