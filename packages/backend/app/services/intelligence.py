"""AI intelligence service using DashScope."""
import asyncio
import logging
from typing import List, Dict, Any, Optional
from dashscope import Audio, Vision, Generation
from dashscope.api_entities.dashscope_response import Message

from app.core import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class IntelligenceService:
    """DashScope AI service wrapper."""

    def __init__(self):
        self.api_key = settings.dashscope_api_key

    async def transcribe_audio(
        self,
        audio_path: str,
        model: str = "paraformer-v2"
    ) -> List[Dict[str, Any]]:
        """
        Transcribe audio using Paraformer ASR.

        Returns:
            List of {start, end, text} segments
        """
        try:
            result = Audio.transcription(
                model=model,
                file_urls=[f"file://{audio_path}"],
                format="wav"
            )

            if result.status_code != 200:
                logger.error(f"ASR error: {result.message}")
                return []

            # Parse output
            transcription = result.output["results"][0]["transcription"]
            segments = []

            for sentence in transcription.get("sentences", []):
                segments.append({
                    "start": sentence["begin_time"],
                    "end": sentence["end_time"],
                    "text": sentence["text"]
                })

            return segments

        except Exception as e:
            logger.error(f"Transcription error: {e}")
            return []

    async def analyze_frame(
        self,
        image_path: str,
        model: str = "qwen-vl-max"
    ) -> str:
        """
        Analyze single frame using Qwen-VL.

        Returns:
            Image description text
        """
        try:
            result = Vision.call(
                model=model,
                prompt="Describe this image in detail, focusing on characters, actions, and environment.",
                image=f"file://{image_path}"
            )

            if result.status_code != 200:
                logger.error(f"VL error: {result.message}")
                return "Image analysis failed"

            return result.output["choices"][0]["message"]["content"][0]["text"]

        except Exception as e:
            logger.error(f"Frame analysis error: {e}")
            return ""

    async def analyze_frames(
        self,
        frames: List[str],
        max_concurrent: int = 10
    ) -> List[str]:
        """Analyze multiple frames concurrently."""
        semaphore = asyncio.Semaphore(max_concurrent)

        async def analyze_with_limit(frame_path: str) -> str:
            async with semaphore:
                return await self.analyze_frame(frame_path)

        tasks = [analyze_with_limit(frame) for frame in frames]
        return await asyncio.gather(*tasks)

    async def generate_embeddings(
        self,
        texts: List[str],
        model: str = "text-embedding-v2"
    ) -> List[List[float]]:
        """Generate text embeddings."""
        try:
            result = Generation.call(
                model=model,
                input=texts
            )

            if result.status_code != 200:
                logger.error(f"Embedding error: {result.message}")
                return [[0.0] * 1536 for _ in texts]

            return result.output["embeddings"]

        except Exception as e:
            logger.error(f"Embedding error: {e}")
            return [[0.0] * 1536 for _ in texts]

    async def chat_completion(
        self,
        messages: List[Dict],
        model: str = "qwen2.5-72b-instruct",
        stream: bool = False
    ):
        """LLM chat completion."""
        try:
            result = Generation.call(
                model=model,
                messages=messages,
                stream=stream,
                result_format="message"
            )

            if result.status_code != 200:
                logger.error(f"LLM error: {result.message}")
                return None

            return result

        except Exception as e:
            logger.error(f"LLM error: {e}")
            return None


# Singleton
_intelligence_service: Optional[IntelligenceService] = None


def get_intelligence_service() -> IntelligenceService:
    global _intelligence_service
    if _intelligence_service is None:
        _intelligence_service = IntelligenceService()
    return _intelligence_service
