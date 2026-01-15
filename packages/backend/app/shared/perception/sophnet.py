"""
SophNet AI Service - Unified API wrapper for all SophNet capabilities.

This service provides a unified interface to:
- LLM: DeepSeek-V3.2 (via OpenAI SDK)
- VLM: Qwen2.5-VL-72B-Instruct (via OpenAI SDK)
- TTS: CosyVoice (via HTTP)
- Image: Qwen-Image (via HTTP)
- Embedding: BGE-M3 (via HTTP)
"""

import asyncio
import base64
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

import httpx
from openai import AsyncOpenAI

from app.core import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

SOPHNET_BASE_URL = "https://www.sophnet.com/api/open-apis/v1"
SOPHNET_API_BASE = "https://www.sophnet.com/api/open-apis"


class SophNetService:
    """
    Unified service for all SophNet AI capabilities.

    Uses AsyncOpenAI for LLM/VLM and httpx for TTS/Image/Embedding.
    """

    def __init__(self):
        """Initialize SophNet service with API credentials."""
        self.api_key = settings.sophnet_api_key
        self.project_id = settings.sophnet_project_id

        if not self.api_key:
            logger.warning("SophNet API key not configured!")
            return

        self.openai_client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=SOPHNET_BASE_URL,
        )

        self.tts_easyllm_id = settings.sophnet_tts_easyllm_id
        self.embedding_easyllm_id = settings.sophnet_embedding_easyllm_id

        logger.info(f"SophNetService initialized: project={self.project_id}")

    async def chat(
        self,
        messages: List[Dict[str, Any]],
        model: str = "DeepSeek-V3.2",
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> str:
        """Send chat completion request to DeepSeek-V3.2."""
        if not self.api_key:
            return "API key not configured"

        try:
            response = await self.openai_client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Chat failed: {e}")
            return f"Error: {str(e)}"

    async def analyze_video_frame(
        self,
        prompt: str,
        image_path: Optional[Path] = None,
        base64_image: Optional[str] = None,
        image_url: Optional[str] = None,
        model: str = "Qwen2.5-VL-72B-Instruct",
    ) -> str:
        """Analyze a video frame using Qwen2.5-VL."""
        if not self.api_key:
            return "API key not configured"

        final_image_url = None

        if image_url:
            final_image_url = image_url
        elif base64_image:
            final_image_url = f"data:image/jpeg;base64,{base64_image}"
        elif image_path:
            with open(image_path, "rb") as f:
                base64_data = base64.b64encode(f.read()).decode("utf-8")
            final_image_url = f"data:image/jpeg;base64,{base64_data}"
        else:
            return "Error: No image provided"

        try:
            response = await self.openai_client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {"url": final_image_url},
                            },
                        ],
                    }
                ],
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"VLM analysis failed: {e}")
            return f"Error: {str(e)}"

    async def analyze_frames(
        self,
        frame_paths: List[Path],
        frame_interval: int = 5,
        prompt: str = "请简要描述画面中的关键信息，包括：场景类型、主要物体或人物、任何可见的文字或数字、正在发生的动作。请用中文回答，控制在100字以内。",
    ) -> List[Dict[str, Any]]:
        """Analyze multiple frames using Qwen2.5-VL."""
        if not frame_paths:
            return []

        results = []
        for i, frame_path in enumerate(frame_paths):
            timestamp = i * frame_interval
            description = await self.analyze_video_frame(
                prompt=prompt, image_path=frame_path
            )
            results.append(
                {"timestamp": timestamp, "description": description, "frame_path": str(frame_path)}
            )

            if i < len(frame_paths) - 1:
                await asyncio.sleep(0.5)

            if (i + 1) % 5 == 0:
                logger.info(f"Analyzed {i + 1}/{len(frame_paths)} frames")

        return results

    async def generate_speech(
        self,
        text: str,
        voice: str = "longxiaochun",
        model: str = "cosyvoice-v1",
        format: str = "MP3_16000HZ_MONO_128KBPS",
        volume: int = 80,
        speech_rate: float = 1.0,
        pitch_rate: float = 1.0,
    ) -> bytes:
        """Generate speech audio using CosyVoice."""
        if not self.api_key:
            raise ValueError("API key not configured")

        url = f"{SOPHNET_API_BASE}/projects/{self.project_id}/easyllms/voice/synthesize-audio-stream"

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        payload = {
            "easyllm_id": self.tts_easyllm_id,
            "text": [text],
            "synthesis_param": {
                "model": model,
                "voice": voice,
                "format": format,
                "volume": volume,
                "speechRate": speech_rate,
                "pitchRate": pitch_rate,
            },
        }

        audio_data = bytearray()

        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream("POST", url, headers=headers, json=payload) as response:
                if response.status_code != 200:
                    error_content = await response.aread()
                    error_text = error_content.decode('utf-8', errors='replace')
                    raise Exception(f"TTS request failed ({response.status_code}): {error_text}")

                async for line in response.aiter_lines():
                    if line and line.startswith("data:"):
                        try:
                            data = json.loads(line[5:])
                            frame = data.get("audioFrame")
                            if frame:
                                audio_data.extend(base64.b64decode(frame))
                        except json.JSONDecodeError:
                            continue

        return bytes(audio_data)

    async def generate_speech_to_file(
        self,
        text: str,
        output_path: Path,
        voice: str = "longxiaochun",
    ) -> Path:
        """Generate speech and save to file."""
        audio_data = await self.generate_speech(text, voice=voice)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(audio_data)
        return output_path

    async def generate_image(
        self,
        prompt: str,
        size: str = "1328*1328",
        seed: Optional[int] = None,
        model: str = "qwen-image",
        max_polls: int = 30,
        poll_interval: float = 2.0,
    ) -> str:
        """Generate image using Qwen-Image with async polling."""
        if not self.api_key:
            raise ValueError("API key not configured")

        import requests
        import uuid as uuid_lib

        def _generate_image_sync():
            create_url = f"{SOPHNET_API_BASE}/projects/easyllms/imagegenerator/task"

            headers = {
                "Authorization": f"Bearer {self.api_key}",
            }

            payload = {
                "model": model,
                "input": {"prompt": prompt},
                "parameters": {"size": size},
            }
            if seed is not None:
                payload["parameters"]["seed"] = seed

            logger.info(f"Creating image generation task with prompt: {prompt[:50]}...")

            create_resp = requests.post(create_url, headers=headers, json=payload, timeout=60.0)

            if create_resp.status_code != 200:
                error_text = create_resp.text
                logger.error(f"Image task creation failed ({create_resp.status_code}): {error_text}")
                raise Exception(f"Image task creation failed ({create_resp.status_code}): {error_text}")

            create_result = create_resp.json()
            task_id = create_result.get("output", {}).get("taskId")
            if not task_id:
                raise ValueError(f"No taskId returned in response: {create_result}")

            logger.info(f"Image task created: {task_id}")

            status_url = f"{create_url}/{task_id}"
            image_url = None

            import time
            for poll_num in range(max_polls):
                time.sleep(poll_interval)

                status_resp = requests.get(
                    status_url,
                    headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                    timeout=60.0
                )

                if status_resp.status_code != 200:
                    logger.warning(f"Poll {poll_num + 1}: status code {status_resp.status_code}")
                    continue

                status_result = status_resp.json()
                output = status_result.get("output", {})
                task_status = output.get("taskStatus")

                logger.debug(f"Poll {poll_num + 1}: status={task_status}")

                if task_status == "SUCCEEDED":
                    results = output.get("results") or []
                    if results and isinstance(results, list):
                        image_url = results[0].get("url")
                        if image_url:
                            logger.info(f"Image generation succeeded: {image_url}")
                            break
                elif task_status in {"FAILED", "CANCELED"}:
                    error_msg = output.get("errorMessage", "Unknown error")
                    raise Exception(f"Image generation {task_status}: {error_msg}")
            else:
                raise TimeoutError(f"Image generation timed out after {max_polls * poll_interval} seconds")

            if not image_url:
                raise ValueError(f"No image URL in successful response: {output}")

            download_resp = requests.get(image_url, timeout=60.0)
            if download_resp.status_code != 200:
                raise Exception(f"Failed to download image: {image_url}")

            temp_dir = Path(settings.temp_dir) / "generated_images"
            temp_dir.mkdir(parents=True, exist_ok=True)

            safe_prompt = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in prompt[:50])
            filename = f"{safe_prompt}_{uuid_lib.uuid4().hex[:8]}.png"
            output_path = temp_dir / filename

            with open(output_path, "wb") as f:
                f.write(download_resp.content)

            logger.info(f"Generated image saved to: {output_path}")
            return str(output_path)

        return await asyncio.to_thread(_generate_image_sync)

    async def get_embedding(self, text: str, dimensions: int = 1024) -> List[float]:
        """Get text embedding using BGE-M3."""
        if not self.api_key:
            raise ValueError("API key not configured")

        url = f"{SOPHNET_API_BASE}/projects/{self.project_id}/easyllms/embeddings"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "easyllm_id": self.embedding_easyllm_id,
            "input_texts": [text],
            "dimensions": dimensions,
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, headers=headers, json=payload)

            if response.status_code != 200:
                error_text = response.text
                logger.error(f"Embedding request failed ({response.status_code}): {error_text}")
                raise Exception(f"Embedding request failed: {error_text}")

            result = response.json()
            embedding = None

            if "data" in result:
                data = result["data"]
                if isinstance(data, dict) and "embedding" in data:
                    embedding = data["embedding"]
                elif isinstance(data, list) and len(data) > 0:
                    first_item = data[0]
                    if isinstance(first_item, dict) and "embedding" in first_item:
                        embedding = first_item["embedding"]
                    elif isinstance(first_item, list):
                        embedding = first_item
                    else:
                        embedding = data[0]
                elif isinstance(data, list):
                    embedding = data[0]

            if embedding is None and "embeddings" in result:
                embeddings = result["embeddings"]
                if isinstance(embeddings, list) and len(embeddings) > 0:
                    embedding = embeddings[0]

            if embedding is None and "embedding" in result:
                embedding = result["embedding"]

            if embedding is None and "output" in result:
                output = result["output"]
                if isinstance(output, list) and len(output) > 0:
                    embedding = output[0]
                elif isinstance(output, dict) and "embedding" in output:
                    embedding = output["embedding"]

            if embedding is None and "result" in result:
                result_data = result["result"]
                if isinstance(result_data, list) and len(result_data) > 0:
                    embedding = result_data[0]
                elif isinstance(result_data, dict) and "embedding" in result_data:
                    embedding = result_data["embedding"]

            if embedding is None:
                raise ValueError(f"Unexpected response format, cannot find embedding: {result}")

            if not isinstance(embedding, list):
                raise ValueError(f"Embedding is not a list: {type(embedding)}, value: {embedding}")

            logger.info(f"Generated embedding with {len(embedding)} dimensions")
            return embedding

    async def get_embeddings_batch(
        self, texts: List[str], dimensions: int = 1024
    ) -> List[List[float]]:
        """Get embeddings for multiple texts."""
        if not self.api_key:
            raise ValueError("API key not configured")

        url = f"{SOPHNET_API_BASE}/projects/{self.project_id}/easyllms/embeddings"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "easyllm_id": self.embedding_easyllm_id,
            "input_texts": texts,
            "dimensions": dimensions,
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, headers=headers, json=payload)

            if response.status_code != 200:
                error_text = response.text
                logger.error(f"Embedding batch request failed ({response.status_code}): {error_text}")
                raise Exception(f"Embedding batch request failed: {error_text}")

            result = response.json()
            embeddings = None

            if "data" in result:
                data = result["data"]
                if isinstance(data, list):
                    if len(data) > 0 and isinstance(data[0], dict) and "embedding" in data[0]:
                        embeddings = [item["embedding"] for item in data]
                    else:
                        embeddings = data
                elif isinstance(data, dict) and "embedding" in data:
                    embeddings = [data["embedding"]]
                elif isinstance(data, dict) and "embeddings" in data:
                    embeddings = data["embeddings"]
            elif "embeddings" in result:
                embeddings = result["embeddings"]
            elif "output" in result:
                embeddings = result["output"]
            elif "result" in result:
                embeddings = result["result"]

            if embeddings is None:
                raise ValueError(f"Unexpected response format: {result}")

            if not isinstance(embeddings, list):
                raise ValueError(f"Embeddings is not a list: {type(embeddings)}")

            logger.info(f"Generated {len(embeddings)} embeddings")
            return embeddings


_sophnet_service: Optional[SophNetService] = None


def get_sophnet_service() -> SophNetService:
    """Get or create SophNetService singleton."""
    global _sophnet_service
    if _sophnet_service is None:
        _sophnet_service = SophNetService()
    return _sophnet_service
