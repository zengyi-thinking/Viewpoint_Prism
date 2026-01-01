"""
SophNet AI Service - Unified API wrapper for all SophNet capabilities.

This service provides a unified interface to:
- LLM: DeepSeek-V3.2 (via OpenAI SDK)
- VLM: Qwen2.5-VL-72B-Instruct (via OpenAI SDK)
- TTS: CosyVoice (via HTTP)
- Image: Qwen-Image (via HTTP)
- Embedding: BGE-M3 (via HTTP)
"""

import base64
import json
import logging
import tempfile
from pathlib import Path
from typing import List, Dict, Any, Optional

import httpx
from openai import AsyncOpenAI

from app.core import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# SophNet API configuration
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

        # Initialize AsyncOpenAI client for LLM and VLM
        self.openai_client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=SOPHNET_BASE_URL,
        )

        # EasyLLM IDs for specific services
        self.tts_easyllm_id = settings.sophnet_tts_easyllm_id
        self.embedding_easyllm_id = settings.sophnet_embedding_easyllm_id

        logger.info(f"SophNetService initialized: project={self.project_id}")

    # ========================================================================
    # LLM / Chat (DeepSeek-V3.2)
    # ========================================================================

    async def chat(
        self,
        messages: List[Dict[str, Any]],
        model: str = "DeepSeek-V3.2",
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> str:
        """
        Send chat completion request to DeepSeek-V3.2.

        Args:
            messages: List of message dicts with "role" and "content"
            model: Model name (default: DeepSeek-V3.2)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Returns:
            Generated text response
        """
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

    # ========================================================================
    # VLM / Video Frame Analysis (Qwen2.5-VL)
    # ========================================================================

    async def analyze_video_frame(
        self,
        prompt: str,
        image_path: Optional[Path] = None,
        base64_image: Optional[str] = None,
        image_url: Optional[str] = None,
        model: str = "Qwen2.5-VL-72B-Instruct",
    ) -> str:
        """
        Analyze a video frame using Qwen2.5-VL.

        Args:
            prompt: Text prompt for the image
            image_path: Path to image file (optional if base64_image or image_url provided)
            base64_image: Base64 encoded image (optional if image_path or image_url provided)
            image_url: Public URL to image (optional, takes priority)
            model: Model name (default: Qwen2.5-VL-72B-Instruct)

        Returns:
            Image description/analysis text
        """
        if not self.api_key:
            return "API key not configured"

        # Determine the image URL to use
        final_image_url = None

        if image_url:
            # Use provided URL directly
            final_image_url = image_url
        elif base64_image:
            # Convert base64 to data URL
            final_image_url = f"data:image/jpeg;base64,{base64_image}"
        elif image_path:
            # Read file and convert to base64
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
        """
        Analyze multiple frames using Qwen2.5-VL.

        Args:
            frame_paths: List of frame image paths
            frame_interval: Seconds between frames (for timestamp calculation)
            prompt: Prompt to use for each frame

        Returns:
            List of analysis results with timestamps
        """
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

            # Rate limiting
            if i < len(frame_paths) - 1:
                await asyncio.sleep(0.5)

            if (i + 1) % 5 == 0:
                logger.info(f"Analyzed {i + 1}/{len(frame_paths)} frames")

        return results

    # ========================================================================
    # TTS / Speech Synthesis (CosyVoice)
    # ========================================================================

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
        """
        Generate speech audio using CosyVoice.

        Args:
            text: Text to synthesize
            voice: Voice role name (default: longxiaochun)
            model: Model name (default: cosyvoice-v1)
            format: Audio format
            volume: Volume (0-100)
            speech_rate: Speech rate multiplier
            pitch_rate: Pitch rate multiplier

        Returns:
            Audio data as bytes
        """
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
                    # Read error response
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
        """
        Generate speech and save to file.

        Args:
            text: Text to synthesize
            output_path: Output file path
            voice: Voice role name

        Returns:
            Path to generated audio file
        """
        audio_data = await self.generate_speech(text, voice=voice)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(audio_data)
        return output_path

    # ========================================================================
    # Image Generation (Qwen-Image)
    # ========================================================================

    async def generate_image(
        self,
        prompt: str,
        size: str = "1328*1328",
        seed: Optional[int] = None,
        model: str = "qwen-image",
        max_polls: int = 30,
        poll_interval: float = 2.0,
    ) -> str:
        """
        Generate image using Qwen-Image with async polling.

        Args:
            prompt: Text prompt for image generation
            size: Image size (e.g., "1328*1328")
            seed: Random seed for reproducibility
            model: Model name
            max_polls: Maximum number of polling attempts
            poll_interval: Seconds between polls

        Returns:
            Local path to downloaded image
        """
        if not self.api_key:
            raise ValueError("API key not configured")

        # Step 1: Create the image generation task
        create_url = f"{SOPHNET_API_BASE}/projects/easyllms/imagegenerator/task"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": model,
            "input": {"prompt": prompt},
            "parameters": {"size": size},
        }
        if seed is not None:
            payload["parameters"]["seed"] = seed

        logger.info(f"Creating image generation task with prompt: {prompt[:50]}...")

        async with httpx.AsyncClient(timeout=60.0) as client:
            # Create task
            create_resp = await client.post(create_url, headers=headers, json=payload)

            if create_resp.status_code != 200:
                error_text = create_resp.text
                logger.error(f"Image task creation failed ({create_resp.status_code}): {error_text}")
                raise Exception(f"Image task creation failed ({create_resp.status_code}): {error_text}")

            create_result = create_resp.json()
            logger.debug(f"Image task creation response: {create_result}")

            # Extract task ID from response
            task_id = create_result.get("output", {}).get("taskId")
            if not task_id:
                raise ValueError(f"No taskId returned in response: {create_result}")

            logger.info(f"Image task created: {task_id}")

            # Step 2: Poll for task completion
            status_url = f"{create_url}/{task_id}"

            for poll_num in range(max_polls):
                await asyncio.sleep(poll_interval)

                status_resp = await client.get(
                    status_url,
                    headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
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

            # Step 3: Download the generated image
            if not image_url:
                raise ValueError(f"No image URL in successful response: {output}")

            download_resp = await client.get(image_url)
            if download_resp.status_code != 200:
                raise Exception(f"Failed to download image: {image_url}")

            # Step 4: Save to local file
            temp_dir = Path(settings.temp_dir) / "generated_images"
            temp_dir.mkdir(parents=True, exist_ok=True)

            # Generate filename from prompt
            safe_prompt = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in prompt[:50])
            import uuid
            filename = f"{safe_prompt}_{uuid.uuid4().hex[:8]}.png"
            output_path = temp_dir / filename

            with open(output_path, "wb") as f:
                f.write(download_resp.content)

            logger.info(f"Generated image saved to: {output_path}")
            return str(output_path)

    # ========================================================================
    # Embedding (BGE-M3)
    # ========================================================================

    async def get_embedding(self, text: str, dimensions: int = 1024) -> List[float]:
        """
        Get text embedding using BGE-M3.

        Args:
            text: Input text
            dimensions: Embedding dimensions (default: 1024 for BGE-M3)

        Returns:
            Embedding vector as list of floats
        """
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
            logger.debug(f"Embedding response keys: {result.keys()}, full response: {result}")

            # Extract embedding from response - try multiple possible formats
            embedding = None

            # Format 1: {"data": {"embedding": [vector], ...}} - Actual API format
            if "data" in result:
                data = result["data"]
                if isinstance(data, dict) and "embedding" in data:
                    embedding = data["embedding"]
                elif isinstance(data, list) and len(data) > 0:
                    # If list, check if first item has embedding
                    first_item = data[0]
                    if isinstance(first_item, dict) and "embedding" in first_item:
                        embedding = first_item["embedding"]
                    elif isinstance(first_item, list):
                        embedding = first_item
                    else:
                        embedding = data[0]
                elif isinstance(data, list):
                    embedding = data[0]

            # Format 2: {"embeddings": [[embedding_vector], ...]}
            if embedding is None and "embeddings" in result:
                embeddings = result["embeddings"]
                if isinstance(embeddings, list) and len(embeddings) > 0:
                    embedding = embeddings[0]

            # Format 3: {"embedding": [vector]}
            if embedding is None and "embedding" in result:
                embedding = result["embedding"]

            # Format 4: {"output": [[vector], ...]} or {"output": [[vector]]}
            if embedding is None and "output" in result:
                output = result["output"]
                if isinstance(output, list) and len(output) > 0:
                    embedding = output[0]
                elif isinstance(output, dict) and "embedding" in output:
                    embedding = output["embedding"]

            # Format 5: {"result": [[vector], ...]}
            if embedding is None and "result" in result:
                result_data = result["result"]
                if isinstance(result_data, list) and len(result_data) > 0:
                    embedding = result_data[0]
                elif isinstance(result_data, dict) and "embedding" in result_data:
                    embedding = result_data["embedding"]

            if embedding is None:
                raise ValueError(f"Unexpected response format, cannot find embedding: {result}")

            # Ensure embedding is a list of floats
            if not isinstance(embedding, list):
                raise ValueError(f"Embedding is not a list: {type(embedding)}, value: {embedding}")

            logger.info(f"Generated embedding with {len(embedding)} dimensions")
            return embedding

    async def get_embeddings_batch(
        self, texts: List[str], dimensions: int = 1024
    ) -> List[List[float]]:
        """
        Get embeddings for multiple texts.

        Args:
            texts: List of input texts
            dimensions: Embedding dimensions

        Returns:
            List of embedding vectors
        """
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
            logger.debug(f"Batch embedding response keys: {result.keys()}")

            # Try multiple possible formats
            embeddings = None

            if "data" in result:
                data = result["data"]
                if isinstance(data, list):
                    # Check if list of dict with embedding key
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


# Import asyncio for analyze_frames
import asyncio


# Singleton instance
_sophnet_service: Optional[SophNetService] = None


def get_sophnet_service() -> SophNetService:
    """Get or create SophNetService singleton."""
    global _sophnet_service
    if _sophnet_service is None:
        _sophnet_service = SophNetService()
    return _sophnet_service
