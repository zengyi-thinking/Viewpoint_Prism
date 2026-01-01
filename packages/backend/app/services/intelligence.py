"""
Intelligence Service
Handles AI analysis using SophNet APIs (Qwen2.5-VL for visual analysis)
and local Whisper for speech-to-text.
"""

import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging

from app.services.sophnet_service import get_sophnet_service

logger = logging.getLogger(__name__)

# Force reload timestamp - 2026-01-01 12:35:00

# Try to import whisper for local ASR
_WHISPER_AVAILABLE = False
_whisper_model = None

try:
    import whisper
    _WHISPER_AVAILABLE = True
    logger.info("Whisper ASR is available")
except ImportError:
    logger.warning("Whisper not installed. ASR transcription will be disabled. Install with: pip install openai-whisper")


def _get_whisper_model():
    """Get or load Whisper model (lazy loading)."""
    global _whisper_model
    if not _WHISPER_AVAILABLE:
        return None
    if _whisper_model is None:
        try:
            # Use base model for balance of speed and accuracy
            logger.info("Loading Whisper 'base' model...")
            _whisper_model = whisper.load_model("base")
            logger.info("Whisper model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
    return _whisper_model

# Default VLM prompt for frame analysis
DEFAULT_VLM_PROMPT = (
    "请简要描述画面中的关键信息，包括：场景类型、主要物体或人物、"
    "任何可见的文字或数字、正在发生的动作。请用中文回答，控制在100字以内。"
)


class IntelligenceService:
    """SophNet-based AI intelligence service."""

    def __init__(self):
        """Initialize with SophNet service."""
        self.sophnet = get_sophnet_service()

    async def transcribe_audio(self, audio_path: Path) -> List[Dict[str, Any]]:
        """
        Transcribe audio using local Whisper model.

        Args:
            audio_path: Path to audio file (WAV format, 16kHz recommended)

        Returns:
            List of transcript segments with timestamp and text
        """
        if not _WHISPER_AVAILABLE:
            logger.warning("Whisper ASR not available, skipping transcription")
            return []

        if not audio_path.exists():
            logger.error(f"Audio file not found: {audio_path}")
            return []

        logger.info(f"Starting ASR transcription for: {audio_path}")

        try:
            # Run Whisper transcription in thread pool to avoid blocking
            model = _get_whisper_model()
            if model is None:
                logger.error("Failed to load Whisper model")
                return []

            def transcribe():
                result = model.transcribe(
                    str(audio_path),
                    language="zh",  # Chinese by default, can detect None
                    task="transcribe",
                    word_timestamps=True,
                )
                return result

            # Run in thread pool for non-blocking execution
            result = await asyncio.to_thread(transcribe)

            # Process results into transcript segments
            transcripts = []
            segments = result.get("segments", [])

            for seg in segments:
                transcripts.append({
                    "timestamp": seg.get("start", 0),
                    "text": seg.get("text", "").strip(),
                    "duration": seg.get("end", 0) - seg.get("start", 0),
                })

            logger.info(f"ASR transcription complete: {len(transcripts)} segments")
            return transcripts

        except Exception as e:
            logger.error(f"ASR transcription failed: {e}")
            return []

    async def analyze_frame(
        self,
        frame_path: Path,
        timestamp: float,
        prompt: str = DEFAULT_VLM_PROMPT,
    ) -> Dict[str, Any]:
        """
        Analyze a single frame using Qwen2.5-VL.

        Args:
            frame_path: Path to frame image
            timestamp: Frame timestamp in seconds
            prompt: Analysis prompt

        Returns:
            Analysis result with timestamp and description
        """
        description = await self.sophnet.analyze_video_frame(
            prompt=prompt,
            image_path=frame_path,
        )

        return {
            "timestamp": timestamp,
            "description": description,
            "frame_path": str(frame_path),
        }

    async def analyze_frames(
        self,
        frame_paths: List[Path],
        frame_interval: int = 5,
        prompt: str = DEFAULT_VLM_PROMPT,
    ) -> List[Dict[str, Any]]:
        """
        Analyze multiple frames using Qwen2.5-VL.

        Args:
            frame_paths: List of frame image paths
            frame_interval: Seconds between frames (for timestamp calculation)
            prompt: Analysis prompt

        Returns:
            List of frame analysis results
        """
        if not frame_paths:
            return []

        logger.info(f"Analyzing {len(frame_paths)} frames using SophNet VLM")
        results = []

        # Process frames with rate limiting
        for i, frame_path in enumerate(frame_paths):
            timestamp = i * frame_interval
            result = await self.analyze_frame(frame_path, timestamp, prompt)
            results.append(result)

            # Rate limiting: avoid hitting API limits
            if i < len(frame_paths) - 1:
                await asyncio.sleep(0.5)

            # Log progress
            if (i + 1) % 5 == 0:
                logger.info(f"Analyzed {i + 1}/{len(frame_paths)} frames")

        logger.info(f"Frame analysis complete: {len(results)} results")
        return results


# Singleton instance
_intelligence_service: Optional[IntelligenceService] = None


def get_intelligence_service() -> IntelligenceService:
    """Get or create IntelligenceService singleton."""
    global _intelligence_service
    if _intelligence_service is None:
        _intelligence_service = IntelligenceService()
    return _intelligence_service
