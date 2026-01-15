"""
ASR Service - Speech-to-Text using local Whisper model.
Handles audio transcription for video content.
"""

import asyncio
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

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
            logger.info("Loading Whisper 'base' model...")
            _whisper_model = whisper.load_model("base")
            logger.info("Whisper model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
    return _whisper_model


DEFAULT_VLM_PROMPT = (
    "请简要描述画面中的关键信息，包括：场景类型、主要物体或人物、"
    "任何可见的文字或数字、正在发生的动作。请用中文回答，控制在100字以内。"
)


class ASRService:
    """ASR (Automatic Speech Recognition) service using Whisper."""

    def __init__(self):
        """Initialize ASR service."""
        pass

    async def transcribe_audio(self, audio_path) -> List[Dict[str, Any]]:
        """
        Transcribe audio using local Whisper model.

        Args:
            audio_path: Path to audio file (str or Path)

        Returns:
            List of transcript segments with timestamp and text
        """
        if not _WHISPER_AVAILABLE:
            logger.warning("Whisper ASR not available, skipping transcription")
            return []

        # Convert to Path if string
        audio_path = Path(audio_path) if isinstance(audio_path, str) else audio_path

        if not audio_path.exists():
            logger.error(f"Audio file not found: {audio_path}")
            return []

        logger.info(f"Starting ASR transcription for: {audio_path}")

        try:
            model = _get_whisper_model()
            if model is None:
                logger.error("Failed to load Whisper model")
                return []

            def transcribe():
                result = model.transcribe(
                    str(audio_path),
                    language="zh",
                    task="transcribe",
                    word_timestamps=True,
                )
                return result

            result = await asyncio.to_thread(transcribe)

            transcripts = []
            segments = result.get("segments", [])

            for seg in segments:
                start = seg.get("start", 0)
                end = seg.get("end", 0)
                transcripts.append({
                    "start": start,
                    "end": end,
                    "timestamp": start,
                    "text": seg.get("text", "").strip(),
                    "duration": end - start,
                })

            logger.info(f"ASR transcription complete: {len(transcripts)} segments")
            return transcripts

        except Exception as e:
            logger.error(f"ASR transcription failed: {e}")
            return []


_asr_service: Optional[ASRService] = None


def get_asr_service() -> ASRService:
    """Get or create ASRService singleton."""
    global _asr_service
    if _asr_service is None:
        _asr_service = ASRService()
    return _asr_service
