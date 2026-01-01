"""
Intelligence Service
Handles AI analysis using DashScope APIs (Paraformer ASR & Qwen-VL).
"""

import asyncio
import base64
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging
import httpx

from app.core import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# DashScope API endpoints
DASHSCOPE_ASR_URL = "https://dashscope.aliyuncs.com/api/v1/services/audio/asr/transcription"
DASHSCOPE_VL_URL = "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"
DASHSCOPE_FILE_URL = "https://dashscope.aliyuncs.com/api/v1/uploads"


class IntelligenceService:
    """DashScope-based AI intelligence service."""

    def __init__(self):
        """Initialize with DashScope API key."""
        self.api_key = settings.dashscope_api_key
        if not self.api_key:
            logger.warning("DashScope API key not configured!")

    def _get_headers(self) -> dict:
        """Get common API headers."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def _upload_file_for_asr(self, file_path: Path) -> Optional[str]:
        """
        Upload audio file to DashScope for ASR processing.

        Args:
            file_path: Path to audio file

        Returns:
            File URL for ASR, or None if failed
        """
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                # First, get upload URL
                response = await client.post(
                    DASHSCOPE_FILE_URL,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                    },
                    json={
                        "model": "paraformer-v2",
                        "file_name": file_path.name,
                    }
                )

                if response.status_code != 200:
                    logger.error(f"Failed to get upload URL: {response.text}")
                    return None

                upload_data = response.json()
                upload_url = upload_data.get("data", {}).get("upload_url")
                file_url = upload_data.get("data", {}).get("file_url")

                if not upload_url:
                    logger.error("No upload URL in response")
                    return None

                # Upload the file
                with open(file_path, "rb") as f:
                    file_content = f.read()

                upload_response = await client.put(
                    upload_url,
                    content=file_content,
                    headers={"Content-Type": "audio/wav"}
                )

                if upload_response.status_code in [200, 201]:
                    logger.info(f"File uploaded successfully: {file_url}")
                    return file_url
                else:
                    logger.error(f"File upload failed: {upload_response.text}")
                    return None

        except Exception as e:
            logger.error(f"Error uploading file: {e}")
            return None

    async def transcribe_audio(self, audio_path: Path) -> List[Dict[str, Any]]:
        """
        Transcribe audio using DashScope Paraformer ASR.

        Args:
            audio_path: Path to audio file (WAV format, 16kHz)

        Returns:
            List of transcript segments with timestamps:
            [{"start": 0.0, "end": 2.5, "text": "..."}]
        """
        if not self.api_key:
            logger.error("No DashScope API key configured")
            return []

        logger.info(f"Starting ASR transcription for: {audio_path}")

        try:
            # Use dashscope SDK with synchronous Recognizer for local files
            import dashscope
            from dashscope.audio.asr import Recognition

            dashscope.api_key = self.api_key

            # Use synchronous recognition which supports local files directly
            recognition = Recognition(
                model="paraformer-realtime-v2",
                format="wav",
                sample_rate=16000,
                language_hints=["zh", "en"],
                callback=None,  # Synchronous mode
            )

            # Run recognition in thread pool to avoid blocking
            def run_recognition():
                results = []
                try:
                    result = recognition.call(str(audio_path))
                    if result.status_code == 200:
                        # Parse recognition result
                        sentences = result.get_sentence()
                        if sentences:
                            for sentence in sentences:
                                results.append({
                                    "start": sentence.get("begin_time", 0) / 1000.0,
                                    "end": sentence.get("end_time", 0) / 1000.0,
                                    "text": sentence.get("text", "")
                                })
                        logger.info(f"ASR transcription completed: {len(results)} segments")
                    else:
                        logger.error(f"ASR failed: {result.message}")
                except Exception as e:
                    logger.error(f"ASR recognition error: {e}")
                return results

            segments = await asyncio.to_thread(run_recognition)
            return segments

        except ImportError:
            logger.warning("dashscope SDK not available, using HTTP API")
            return await self._transcribe_audio_http(audio_path)

        except Exception as e:
            logger.error(f"ASR transcription error: {e}")
            return []

    async def _transcribe_audio_http(self, audio_path: Path) -> List[Dict[str, Any]]:
        """Fallback HTTP-based ASR implementation."""
        # Upload file first
        file_url = await self._upload_file_for_asr(audio_path)
        if not file_url:
            return []

        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                # Submit transcription task
                response = await client.post(
                    DASHSCOPE_ASR_URL,
                    headers=self._get_headers(),
                    json={
                        "model": "paraformer-v2",
                        "input": {
                            "file_urls": [file_url]
                        },
                        "parameters": {
                            "language_hints": ["zh", "en"]
                        }
                    }
                )

                if response.status_code != 200:
                    logger.error(f"ASR request failed: {response.text}")
                    return []

                result = response.json()
                task_id = result.get("output", {}).get("task_id")

                # Poll for results
                for _ in range(100):  # Max 5 minutes
                    await asyncio.sleep(3)

                    status_response = await client.get(
                        f"{DASHSCOPE_ASR_URL}/{task_id}",
                        headers=self._get_headers()
                    )

                    if status_response.status_code == 200:
                        status_data = status_response.json()
                        task_status = status_data.get("output", {}).get("task_status")

                        if task_status == "SUCCEEDED":
                            return self._parse_asr_result(status_data.get("output", {}))
                        elif task_status == "FAILED":
                            logger.error("ASR task failed")
                            return []

                return []

        except Exception as e:
            logger.error(f"HTTP ASR error: {e}")
            return []

    def _parse_asr_result(self, output: dict) -> List[Dict[str, Any]]:
        """Parse ASR result into structured segments."""
        segments = []

        try:
            results = output.get("results", [])
            for result in results:
                transcripts = result.get("transcription_url") or result.get("transcript", {})

                # Handle different result formats
                if isinstance(transcripts, str):
                    # Direct transcript text
                    segments.append({
                        "start": 0.0,
                        "end": 0.0,
                        "text": transcripts
                    })
                elif isinstance(transcripts, dict):
                    sentences = transcripts.get("sentences", [])
                    for sentence in sentences:
                        segments.append({
                            "start": sentence.get("begin_time", 0) / 1000.0,
                            "end": sentence.get("end_time", 0) / 1000.0,
                            "text": sentence.get("text", "")
                        })

        except Exception as e:
            logger.error(f"Error parsing ASR result: {e}")

        logger.info(f"Parsed {len(segments)} transcript segments")
        return segments

    async def analyze_frame(self, frame_path: Path, timestamp: float) -> Dict[str, Any]:
        """
        Analyze a single frame using Qwen-VL.

        Args:
            frame_path: Path to frame image
            timestamp: Frame timestamp in seconds

        Returns:
            Analysis result with timestamp and description
        """
        if not self.api_key:
            return {"timestamp": timestamp, "description": "API key not configured"}

        try:
            # Read and encode image
            with open(frame_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode("utf-8")

            # Use dashscope SDK
            import dashscope
            from dashscope import MultiModalConversation

            dashscope.api_key = self.api_key

            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "image": f"data:image/jpeg;base64,{image_data}"
                        },
                        {
                            "text": "请简要描述画面中的关键信息，包括：场景类型、主要物体或人物、任何可见的文字或数字、正在发生的动作。请用中文回答，控制在100字以内。"
                        }
                    ]
                }
            ]

            response = MultiModalConversation.call(
                model="qwen-vl-plus",
                messages=messages,
            )

            if response.status_code == 200:
                content = response.output.get("choices", [{}])[0].get("message", {}).get("content", [])
                description = ""
                for item in content:
                    if isinstance(item, dict) and "text" in item:
                        description = item["text"]
                        break
                    elif isinstance(item, str):
                        description = item
                        break

                return {
                    "timestamp": timestamp,
                    "description": description,
                    "frame_path": str(frame_path)
                }
            else:
                logger.error(f"VL analysis failed: {response.message}")
                return {
                    "timestamp": timestamp,
                    "description": f"Analysis failed: {response.message}",
                    "frame_path": str(frame_path)
                }

        except Exception as e:
            logger.error(f"Frame analysis error: {e}")
            return {
                "timestamp": timestamp,
                "description": f"Error: {str(e)}",
                "frame_path": str(frame_path)
            }

    async def analyze_frames(
        self,
        frame_paths: List[Path],
        frame_interval: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Analyze multiple frames using Qwen-VL.

        Args:
            frame_paths: List of frame image paths
            frame_interval: Seconds between frames (for timestamp calculation)

        Returns:
            List of frame analysis results
        """
        if not frame_paths:
            return []

        logger.info(f"Analyzing {len(frame_paths)} frames")
        results = []

        # Process frames with rate limiting
        for i, frame_path in enumerate(frame_paths):
            timestamp = i * frame_interval
            result = await self.analyze_frame(frame_path, timestamp)
            results.append(result)

            # Rate limiting: avoid hitting API limits
            if i < len(frame_paths) - 1:
                await asyncio.sleep(1)

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
