"""
Illustrator Service - AI Image Generation for Video Covers and Storyboards
Phase 11: Visual Content Generation

Uses SophNet Qwen-Image to generate:
- Video thumbnails/covers
- Storyboard frames for director cuts
- Illustrations for enhanced visual storytelling
"""

import logging
import uuid
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

from app.core import get_settings
from app.services.sophnet_service import get_sophnet_service

logger = logging.getLogger(__name__)
settings = get_settings()

# Directory for generated content
GENERATED_DIR = Path(settings.upload_dir).parent / "generated"
IMAGES_DIR = GENERATED_DIR / "images"
IMAGES_DIR.mkdir(parents=True, exist_ok=True)


class IllustratorService:
    """AI Image Generation service using SophNet Qwen-Image."""

    def __init__(self):
        """Initialize with SophNet service."""
        self.sophnet = get_sophnet_service()
        self._tasks: Dict[str, Dict[str, Any]] = {}

    async def generate_cover(
        self,
        video_title: str,
        video_description: str = "",
        style: str = "realistic",
        task_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate a cover image for a video.

        Args:
            video_title: Title of the video
            video_description: Optional description for context
            style: Image style (realistic, cartoon, anime, etc.)
            task_id: Optional existing task ID

        Returns:
            Task result with image URL or error
        """
        if task_id is None:
            task_id = str(uuid.uuid4())[:8]

        try:
            self._tasks[task_id] = {
                "status": "generating",
                "progress": 50,
                "message": "🎨 正在生成视频封面...",
            }

            # Build prompt based on style
            prompt = self._build_cover_prompt(video_title, video_description, style)

            logger.info(f"Generating cover for: {video_title}, style: {style}")

            # Generate image using SophNet
            image_path = await self.sophnet.generate_image(
                prompt=prompt,
                size="1328*1328",
            )

            # Generate accessible URL
            filename = Path(image_path).name
            image_url = f"/static/generated/images/{filename}"

            self._tasks[task_id] = {
                "status": "completed",
                "progress": 100,
                "message": "✨ 封面生成完成！",
                "image_url": image_url,
                "image_path": image_path,
                "prompt_used": prompt,
                "style": style,
            }

            logger.info(f"Cover generated: {image_url}")
            return self._tasks[task_id]

        except Exception as e:
            logger.error(f"Cover generation error: {e}")
            self._tasks[task_id] = {
                "status": "error",
                "progress": 0,
                "message": f"生成失败: {str(e)}",
                "error": str(e),
            }
            return self._tasks[task_id]

    async def generate_storyboard(
        self,
        script_segments: List[Dict[str, Any]],
        style: str = "cinematic",
        task_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate storyboard images for a director's script.

        Args:
            script_segments: List of script segments with narration/description
            style: Image style for storyboard frames
            task_id: Optional existing task ID

        Returns:
            Task result with storyboard frame URLs
        """
        if task_id is None:
            task_id = str(uuid.uuid4())[:8]

        try:
            self._tasks[task_id] = {
                "status": "generating",
                "progress": 10,
                "message": f"🎬 正在生成分镜脚本 ({len(script_segments)} 帧)...",
            }

            storyboard_frames = []
            total_frames = min(len(script_segments), 6)  # Limit to 6 frames

            for i, segment in enumerate(script_segments[:total_frames]):
                self._tasks[task_id]["progress"] = 10 + (i * 15)
                self._tasks[task_id]["message"] = f"🎬 正在生成第 {i+1}/{total_frames} 帧..."

                # Build prompt for this frame
                narration = segment.get("narration", "")
                subtitle = segment.get("subtitle", "")
                description = segment.get("rationale", "")

                prompt = self._build_storyboard_prompt(
                    narration=narration,
                    subtitle=subtitle,
                    description=description,
                    style=style,
                    frame_number=i + 1,
                    total_frames=total_frames,
                )

                # Generate image
                image_path = await self.sophnet.generate_image(
                    prompt=prompt,
                    size="1024*576",  # 16:9 aspect ratio
                    seed=42 + i,
                )

                # Generate URL
                filename = Path(image_path).name
                image_url = f"/static/generated/images/{filename}"

                storyboard_frames.append({
                    "frame_number": i + 1,
                    "image_url": image_url,
                    "image_path": image_path,
                    "narration": narration[:100] if narration else subtitle,
                    "prompt_used": prompt,
                })

                logger.info(f"Storyboard frame {i+1} generated: {image_url}")

            self._tasks[task_id] = {
                "status": "completed",
                "progress": 100,
                "message": f"✨ 分镜脚本生成完成！({len(storyboard_frames)} 帧)",
                "frames": storyboard_frames,
                "style": style,
            }

            return self._tasks[task_id]

        except Exception as e:
            logger.error(f"Storyboard generation error: {e}")
            self._tasks[task_id] = {
                "status": "error",
                "progress": 0,
                "message": f"生成失败: {str(e)}",
                "error": str(e),
            }
            return self._tasks[task_id]

    async def generate_manga_panel(
        self,
        scene_description: str,
        characters: str = "",
        mood: str = "dramatic",
        task_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate a manga-style panel image.

        Args:
            scene_description: Description of the scene
            characters: Character descriptions (optional)
            mood: Mood of the scene (dramatic, funny, action, etc.)
            task_id: Optional existing task ID

        Returns:
            Task result with manga panel URL
        """
        if task_id is None:
            task_id = str(uuid.uuid4())[:8]

        try:
            self._tasks[task_id] = {
                "status": "generating",
                "progress": 50,
                "message": "🎨 正在生成漫画分镜...",
            }

            # Build manga-style prompt
            prompt = self._build_manga_prompt(
                scene=scene_description,
                characters=characters,
                mood=mood,
            )

            # Generate image (portrait orientation for manga)
            image_path = await self.sophnet.generate_image(
                prompt=prompt,
                size="768*1024",  # Portrait orientation
            )

            filename = Path(image_path).name
            image_url = f"/static/generated/images/{filename}"

            self._tasks[task_id] = {
                "status": "completed",
                "progress": 100,
                "message": "✨ 漫画分镜生成完成！",
                "image_url": image_url,
                "image_path": image_path,
                "prompt_used": prompt,
                "mood": mood,
            }

            logger.info(f"Manga panel generated: {image_url}")
            return self._tasks[task_id]

        except Exception as e:
            logger.error(f"Manga panel generation error: {e}")
            self._tasks[task_id] = {
                "status": "error",
                "progress": 0,
                "message": f"生成失败: {str(e)}",
                "error": str(e),
            }
            return self._tasks[task_id]

    def _build_cover_prompt(
        self,
        title: str,
        description: str,
        style: str,
    ) -> str:
        """Build prompt for cover image generation."""
        style_prompts = {
            "realistic": "photorealistic, high quality, detailed, cinematic lighting",
            "cartoon": "colorful cartoon style, vibrant, fun, expressive",
            "anime": "anime style, vibrant colors, dynamic composition",
            "minimalist": "minimalist design, clean, simple, elegant",
            "dramatic": "dramatic lighting, cinematic, intense atmosphere",
        }

        style_desc = style_prompts.get(style, style_prompts["realistic"])

        if description:
            prompt = f"Professional cover image for: {title}. {description}. Style: {style_desc}, high quality, 4K"
        else:
            prompt = f"Professional cover image for: {title}. Style: {style_desc}, high quality, 4K"

        return prompt

    def _build_storyboard_prompt(
        self,
        narration: str,
        subtitle: str,
        description: str,
        style: str,
        frame_number: int,
        total_frames: int,
    ) -> str:
        """Build prompt for storyboard frame generation."""
        style_prompts = {
            "cinematic": "cinematic shot, film still, professional lighting, shallow depth of field",
            "anime": "anime key visual, vibrant colors, dynamic angle",
            "cartoon": "storyboard sketch, clean lines, colorful",
            "minimalist": "clean composition, simple shapes, minimalist",
        }

        style_desc = style_prompts.get(style, style_prompts["cinematic"])

        # Combine narration and description
        content = narration or subtitle or description
        prompt = f"Storyboard frame {frame_number} of {total_frames}: {content}. Style: {style_desc}, wide shot, detailed"

        return prompt

    def _build_manga_prompt(
        self,
        scene: str,
        characters: str,
        mood: str,
    ) -> str:
        """Build prompt for manga panel generation."""
        mood_styles = {
            "dramatic": "dramatic lighting, intense atmosphere, high contrast",
            "funny": "chibi style, cute, humorous, expressive",
            "action": "dynamic action pose, motion lines, energy, impact",
            "romantic": "soft lighting, romantic atmosphere, gentle, warm",
            "mysterious": "shadows, mysterious atmosphere, intriguing",
        }

        mood_desc = mood_styles.get(mood, mood_styles["dramatic"])

        if characters:
            prompt = f"Manga panel: {scene}. Characters: {characters}. Style: {mood_desc}, black and white ink style, professional manga art"
        else:
            prompt = f"Manga panel: {scene}. Style: {mood_desc}, black and white ink style, professional manga art"

        return prompt

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get status of an illustration task."""
        return self._tasks.get(task_id)

    def create_task(self) -> str:
        """Create a new task and return its ID."""
        task_id = str(uuid.uuid4())[:8]
        self._tasks[task_id] = {
            "status": "pending",
            "progress": 0,
            "message": "等待开始...",
        }
        return task_id


# Singleton instance
_illustrator_service: Optional[IllustratorService] = None


def get_illustrator_service() -> IllustratorService:
    """Get or create IllustratorService singleton."""
    global _illustrator_service
    if _illustrator_service is None:
        _illustrator_service = IllustratorService()
    return _illustrator_service
