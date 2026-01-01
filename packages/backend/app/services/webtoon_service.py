"""
Webtoon Service - AI-Powered Cinematic Blog Generation from Video
Phase 14: Cinematic Blog - Transform video into editorial-style visual articles.

Pipeline:
1. Smart Beat Extraction - Select 6-10 key story moments
2. Vision-Language Bridging - Qwen-VL analyzes frames
3. AI Drawing - Qwen-Image generates manga-style illustrations
4. Blog Narrative - DeepSeek writes cohesive article with embedded panels
"""

import asyncio
import logging
import os
import subprocess
import tempfile
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy import select

from app.core import get_settings
from app.core.database import async_session
from app.models.models import Source
from app.services.sophnet_service import get_sophnet_service

logger = logging.getLogger(__name__)
settings = get_settings()

# Directory for generated manga panels
GENERATED_DIR = Path(settings.upload_dir).parent / "generated"
MANGA_DIR = GENERATED_DIR / "manga"
MANGA_DIR.mkdir(parents=True, exist_ok=True)

# Singleton instance
_webtoon_service: Optional["WebtoonService"] = None


def get_webtoon_service() -> "WebtoonService":
    """Get singleton WebtoonService instance."""
    global _webtoon_service
    if _webtoon_service is None:
        _webtoon_service = WebtoonService()
    return _webtoon_service


class WebtoonService:
    """
    Cinematic Blog Generator - Transform video into editorial visual articles.

    Features:
    - Smart story beat extraction
    - VLM-powered frame analysis
    - AI manga illustration generation
    - LLM-generated cohesive blog narrative
    - Streaming panel delivery
    """

    def __init__(self):
        self.tasks: Dict[str, Dict[str, Any]] = {}
        self.sophnet = get_sophnet_service()

    def create_task(self) -> str:
        """Create a new cinematic blog generation task."""
        task_id = uuid.uuid4().hex[:8]
        self.tasks[task_id] = {
            "status": "pending",
            "progress": 0,
            "message": "Task created",
            "panels": [],
            "total_panels": 0,
            "current_panel": 0,
            # Cinematic Blog fields
            "blog_title": "",
            "blog_sections": [],  # List of {type: 'text'|'panel', content/panel_index}
            # Audio Blog fields (Phase 14.5)
            "audio_status": "pending",  # pending | generating | completed | error
            "audio_progress": 0,
            "audio_message": "",
            "audio_url": None,
        }
        return task_id

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task status by ID."""
        return self.tasks.get(task_id)

    def _update_task(self, task_id: str, **kwargs):
        """Update task status."""
        if task_id in self.tasks:
            self.tasks[task_id].update(kwargs)

    async def generate_webtoon(
        self,
        task_id: str,
        source_id: str,
        max_panels: int = 8,
    ):
        """
        Main pipeline: Generate AI webtoon from video source.

        Args:
            task_id: Task identifier
            source_id: Video source ID
            max_panels: Maximum number of manga panels to generate (6-12)
        """
        try:
            # Clamp panel count
            max_panels = max(6, min(12, max_panels))

            self._update_task(
                task_id,
                status="extracting",
                progress=5,
                message="正在分析视频结构...",
                total_panels=max_panels,
            )

            # Step 1: Get video info and extract story beats
            video_path, duration, subtitle_data = await self._get_video_info(source_id)
            if not video_path:
                self._update_task(
                    task_id,
                    status="error",
                    progress=100,
                    message="无法找到视频文件",
                    error="Video file not found",
                )
                return

            # Step 2: Extract key frames at story beats
            self._update_task(
                task_id,
                status="extracting",
                progress=10,
                message="正在提取关键帧...",
            )

            beat_times = self._calculate_story_beats(duration, max_panels)
            frame_paths = await self._extract_frames_at_times(video_path, beat_times)

            if not frame_paths:
                self._update_task(
                    task_id,
                    status="error",
                    progress=100,
                    message="无法提取视频帧",
                    error="Frame extraction failed",
                )
                return

            logger.info(f"Extracted {len(frame_paths)} frames at beats: {beat_times}")

            # Step 3: Process each frame - VLM analyze, LLM script, AI draw
            panels = []
            total_frames = len(frame_paths)

            for i, (frame_path, beat_time) in enumerate(zip(frame_paths, beat_times)):
                panel_num = i + 1
                progress_base = 15 + (i * 80 // total_frames)

                try:
                    # Update progress - Analyzing
                    self._update_task(
                        task_id,
                        status="analyzing",
                        progress=progress_base,
                        message=f"🔍 分析画面 {panel_num}/{total_frames}...",
                        current_panel=panel_num,
                    )

                    # Get nearby subtitle text for context
                    nearby_text = self._get_nearby_subtitle(subtitle_data, beat_time)

                    # VLM: Analyze frame
                    frame_description = await self._analyze_frame(frame_path)
                    logger.info(f"Frame {panel_num} analysis: {frame_description[:100]}...")

                    # Update progress - Scripting
                    self._update_task(
                        task_id,
                        status="scripting",
                        progress=progress_base + 5,
                        message=f"✍️ 编写剧本 {panel_num}/{total_frames}...",
                    )

                    # LLM: Generate caption and drawing prompt
                    caption, draw_prompt, characters = await self._generate_script(
                        frame_description, nearby_text, panel_num, total_frames
                    )
                    logger.info(f"Frame {panel_num} caption: {caption}")

                    # Update progress - Drawing
                    self._update_task(
                        task_id,
                        status="drawing",
                        progress=progress_base + 10,
                        message=f"🎨 绘制漫画 {panel_num}/{total_frames}...",
                    )

                    # AI: Generate manga panel
                    manga_image_url = await self._generate_manga_panel(draw_prompt)
                    logger.info(f"Frame {panel_num} manga generated: {manga_image_url}")

                    # Build panel data
                    panel_data = {
                        "panel_number": panel_num,
                        "time": beat_time,
                        "time_formatted": self._format_time(beat_time),
                        "caption": caption,
                        "characters": characters,
                        "frame_description": frame_description,  # For blog narrative
                        "manga_image_url": manga_image_url,
                        "original_frame_url": f"/static/temp/webtoon_frames/{Path(frame_path).name}",
                        "video_segment": {
                            "source_id": source_id,
                            "start": max(0, beat_time - 5),
                            "end": min(duration, beat_time + 10),
                        },
                    }
                    panels.append(panel_data)

                    # Update task with new panel (streaming)
                    self._update_task(
                        task_id,
                        panels=panels.copy(),
                        progress=progress_base + 15,
                    )

                except Exception as e:
                    logger.error(f"Error processing frame {panel_num}: {e}")
                    # Continue with next frame on error
                    continue

            if not panels:
                self._update_task(
                    task_id,
                    status="error",
                    progress=100,
                    message="无法生成漫画面板",
                    error="No panels generated",
                )
                return

            # Step 4: Generate blog narrative
            self._update_task(
                task_id,
                status="writing",
                progress=92,
                message="📝 撰写博客文章...",
            )

            # Collect all frame descriptions and subtitles for narrative generation
            frame_contexts = []
            for i, (frame_path, beat_time) in enumerate(zip(frame_paths, beat_times)):
                nearby_text = self._get_nearby_subtitle(subtitle_data, beat_time)
                frame_desc = panels[i].get("frame_description", "") if i < len(panels) else ""
                frame_contexts.append({
                    "panel_index": i,
                    "time": beat_time,
                    "description": frame_desc,
                    "subtitle": nearby_text,
                    "caption": panels[i].get("caption", "") if i < len(panels) else "",
                })

            blog_title, blog_sections = await self._generate_blog_narrative(
                frame_contexts, len(panels)
            )

            logger.info(f"Blog narrative generated: {blog_title}, {len(blog_sections)} sections")

            # Complete blog generation (audio will be generated in background)
            self._update_task(
                task_id,
                status="completed",
                progress=100,
                message=f"✨ 电影级博客生成完成！共 {len(panels)} 张插图",
                panels=panels,
                total_panels=len(panels),
                blog_title=blog_title,
                blog_sections=blog_sections,
            )

            logger.info(f"Cinematic blog completed: {len(panels)} panels for source {source_id}")

            # Step 5: Generate audio in background (async fire-and-forget)
            asyncio.create_task(
                self.generate_blog_audio(task_id, blog_sections, blog_title)
            )

        except Exception as e:
            logger.error(f"Webtoon generation failed: {e}")
            self._update_task(
                task_id,
                status="error",
                progress=100,
                message=f"生成失败: {str(e)}",
                error=str(e),
            )

    async def _get_video_info(self, source_id: str) -> tuple:
        """Get video file path, duration, and subtitle data."""
        async with async_session() as db:
            result = await db.execute(
                select(Source).where(Source.id == source_id)
            )
            source = result.scalar_one_or_none()
            if not source:
                return None, 0, []

            # Find video file
            video_path = None
            if source.file_path:
                # Try direct path
                if os.path.exists(source.file_path) and source.file_path.endswith(('.mp4', '.webm', '.mkv')):
                    video_path = source.file_path
                else:
                    # Try video.mp4 in directory
                    video_mp4 = os.path.join(source.file_path, "video.mp4")
                    if os.path.exists(video_mp4):
                        video_path = video_mp4

            if not video_path:
                return None, 0, []

            # Get duration
            duration = source.duration or await self._get_video_duration(video_path)

            # Get subtitle data from Evidence table
            from app.models.models import Evidence
            evidence_result = await db.execute(
                select(Evidence)
                .where(Evidence.source_id == source_id)
                .order_by(Evidence.start_time)
            )
            evidences = evidence_result.scalars().all()

            subtitle_data = []
            for ev in evidences:
                if ev.text_content:
                    subtitle_data.append({
                        "start": ev.start_time,
                        "text": ev.text_content.strip(),
                    })

            return video_path, duration, subtitle_data

    async def _get_video_duration(self, video_path: str) -> float:
        """Get video duration using ffprobe."""
        try:
            cmd = [
                "ffprobe", "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                video_path
            ]
            result = subprocess.run(cmd, capture_output=True, timeout=30)
            if result.returncode == 0:
                import json
                data = json.loads(result.stdout.decode())
                return float(data.get("format", {}).get("duration", 0))
        except Exception as e:
            logger.error(f"Failed to get duration: {e}")
        return 0

    def _calculate_story_beats(self, duration: float, num_beats: int) -> List[float]:
        """
        Calculate optimal story beat timestamps.
        Distributes beats across video with emphasis on beginning and end.
        """
        if duration <= 0:
            return []

        beats = []
        # Golden ratio distribution for natural pacing
        # First beat at ~10%, last at ~90%
        start_ratio = 0.08
        end_ratio = 0.92

        for i in range(num_beats):
            # Use non-linear distribution (slightly emphasize middle)
            t = i / (num_beats - 1) if num_beats > 1 else 0.5
            # Smooth easing
            ratio = start_ratio + (end_ratio - start_ratio) * t
            beat_time = duration * ratio
            beats.append(round(beat_time, 1))

        return beats

    async def _extract_frames_at_times(
        self,
        video_path: str,
        times: List[float],
    ) -> List[str]:
        """Extract frames at specific timestamps using FFmpeg."""
        frame_paths = []
        temp_dir = Path(settings.temp_dir) / "webtoon_frames"
        temp_dir.mkdir(parents=True, exist_ok=True)

        for i, time in enumerate(times):
            output_path = temp_dir / f"beat_{i:02d}_{uuid.uuid4().hex[:6]}.jpg"

            cmd = [
                "ffmpeg", "-y",
                "-ss", str(time),
                "-i", video_path,
                "-vframes", "1",
                "-q:v", "2",
                str(output_path)
            ]

            try:
                result = subprocess.run(cmd, capture_output=True, timeout=30)
                if result.returncode == 0 and output_path.exists():
                    frame_paths.append(str(output_path))
                else:
                    logger.warning(f"Failed to extract frame at {time}s")
            except Exception as e:
                logger.error(f"FFmpeg error at {time}s: {e}")

        return frame_paths

    def _get_nearby_subtitle(
        self,
        subtitle_data: List[Dict],
        time: float,
        window: float = 10.0,
    ) -> str:
        """Get subtitle text near a timestamp."""
        nearby = []
        for sub in subtitle_data:
            if abs(sub["start"] - time) <= window:
                nearby.append(sub["text"])
        return " ".join(nearby) if nearby else ""

    async def _analyze_frame(self, frame_path: str) -> str:
        """Use Qwen-VL to analyze frame content."""
        prompt = """请详细描述这张视频截图中的场景，包括：
1. 人物：外貌特征、服装、表情、动作姿态
2. 环境：场景类型、背景元素、氛围
3. 构图：画面焦点、视角、光线

用简洁的中文描述，控制在150字以内。"""

        try:
            description = await self.sophnet.analyze_video_frame(
                prompt=prompt,
                image_path=Path(frame_path),
            )
            return description
        except Exception as e:
            logger.error(f"Frame analysis failed: {e}")
            return "画面内容无法识别"

    async def _generate_script(
        self,
        frame_description: str,
        nearby_text: str,
        panel_num: int,
        total_panels: int,
    ) -> tuple:
        """
        Use DeepSeek to generate caption and drawing prompt.

        Returns:
            (caption, draw_prompt, characters)
        """
        # Determine panel position for narrative arc
        if panel_num == 1:
            position = "开篇"
        elif panel_num == total_panels:
            position = "结尾"
        elif panel_num <= total_panels // 3:
            position = "铺垫"
        elif panel_num <= 2 * total_panels // 3:
            position = "高潮"
        else:
            position = "收尾"

        prompt = f"""你是一个幽默风趣的漫画编剧。根据以下信息，生成漫画内容：

【画面描述】
{frame_description}

【对话/旁白参考】
{nearby_text if nearby_text else "无对白"}

【叙事位置】
第 {panel_num}/{total_panels} 格，属于"{position}"阶段

请生成：
1. **旁白/吐槽** (Caption): 一句有趣的吐槽、旁白或内心独白。要求：幽默、接地气、有网感，可以用emoji，10-30字。
2. **绘图提示** (Draw Prompt): 用于AI绘画的英文Prompt。要求：描述为日本漫画风格，保留原画构图和人物特征，突出表情和动作。
3. **人物标签** (Characters): 简短描述画面中主要人物的外貌特征（如"蓝衣男子"），用于保持角色一致性。

严格按以下JSON格式输出：
{{"caption": "...", "draw_prompt": "...", "characters": "..."}}"""

        try:
            response = await self.sophnet.chat(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.8,
                max_tokens=500,
            )

            # Parse JSON response
            import json
            import re

            # Try to extract JSON from response
            json_match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                caption = data.get("caption", "...")
                draw_prompt = data.get("draw_prompt", "manga panel, anime style")
                characters = data.get("characters", "")
            else:
                # Fallback
                caption = "这一幕..."
                draw_prompt = f"manga panel depicting {frame_description[:100]}, anime style"
                characters = ""

            return caption, draw_prompt, characters

        except Exception as e:
            logger.error(f"Script generation failed: {e}")
            return "...", f"manga panel, anime style, {frame_description[:50]}", ""

    async def _generate_manga_panel(self, draw_prompt: str) -> str:
        """Generate manga-style image using Qwen-Image."""
        # Enhance prompt with manga style prefix
        enhanced_prompt = (
            "Masterpiece, high quality manga panel, Japanese comic art style, "
            "vivid colors, expressive lines, dynamic composition, "
            "professional manga illustration, detailed artwork. "
            f"Scene: {draw_prompt}"
        )

        try:
            image_path = await self.sophnet.generate_image(
                prompt=enhanced_prompt,
                size="1328*1328",
            )

            # Return static URL for generated image
            if image_path:
                filename = Path(image_path).name
                # Images saved in temp_dir/generated_images/, static mounted at data/
                return f"/static/temp/generated_images/{filename}"

        except Exception as e:
            logger.error(f"Manga generation failed: {e}")

        # Return placeholder on failure
        return "/static/placeholder_manga.png"

    def _format_time(self, seconds: float) -> str:
        """Format seconds to MM:SS."""
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes:02d}:{secs:02d}"

    async def _generate_blog_narrative(
        self,
        frame_contexts: List[Dict],
        total_panels: int,
    ) -> tuple:
        """
        Generate cohesive blog narrative with panel insertion markers.

        Args:
            frame_contexts: List of {panel_index, time, description, subtitle, caption}
            total_panels: Total number of panels

        Returns:
            (blog_title, blog_sections) where blog_sections is a list of
            {type: 'text'|'panel', content/panel_index}
        """
        # Build context for LLM
        segments_info = []
        for ctx in frame_contexts:
            segment = f"""
【片段 {ctx['panel_index'] + 1}】时间码 {self._format_time(ctx['time'])}
- 画面描述: {ctx['description'][:200] if ctx['description'] else '无'}
- 对话/旁白: {ctx['subtitle'][:150] if ctx['subtitle'] else '无'}
- 漫画字幕: {ctx['caption']}"""
            segments_info.append(segment)

        segments_text = "\n".join(segments_info)

        prompt = f"""你是一位犀利的科技评论员和深度内容创作者，擅长将视频内容转化为引人入胜的博客文章。

根据以下视频片段信息，写一篇深度博客文章。文章需要：
1. 有吸引眼球的标题
2. 有观点、有深度、有洞察
3. 文字流畅，像在讲故事
4. 在适当位置插入漫画插图（使用标记 [INSERT_PANEL_X]，X 从 1 到 {total_panels}）

【视频片段信息】
{segments_text}

请按以下格式输出（使用 Markdown）：

# [你的文章标题]

[引言段落，设置悬念或抛出观点]

[INSERT_PANEL_1]

[第一部分正文，讨论第一个画面的内容和意义]

[INSERT_PANEL_2]

[第二部分正文...]

...（每个 PANEL 标记后必须跟随对应的讨论段落）

[INSERT_PANEL_{total_panels}]

[结尾段落，总结或升华]

注意：
- 文章总字数控制在 800-1200 字
- 每个段落 50-150 字
- 语言风格：专业但不乏幽默，犀利但有温度
- 所有 {total_panels} 个 PANEL 标记都必须出现且按顺序排列"""

        try:
            response = await self.sophnet.chat(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=2000,
            )

            # Parse the response into structured sections
            blog_title, blog_sections = self._parse_blog_response(response, total_panels)
            return blog_title, blog_sections

        except Exception as e:
            logger.error(f"Blog narrative generation failed: {e}")
            # Fallback: simple structure
            fallback_sections = [
                {"type": "text", "content": "# 视频精彩回顾\n\n以下是视频中的精彩片段："}
            ]
            for i in range(total_panels):
                fallback_sections.append({"type": "panel", "panel_index": i})
                if i < len(frame_contexts):
                    fallback_sections.append({
                        "type": "text",
                        "content": frame_contexts[i].get("caption", "精彩瞬间")
                    })
            return "视频精彩回顾", fallback_sections

    def _parse_blog_response(
        self,
        response: str,
        total_panels: int,
    ) -> tuple:
        """
        Parse LLM blog response into structured sections.

        Returns:
            (title, sections) where sections is list of {type, content/panel_index}
        """
        import re

        sections = []
        lines = response.strip().split('\n')

        # Extract title (first # heading)
        title = "视频深度解读"
        for line in lines:
            if line.startswith('# '):
                title = line[2:].strip()
                break

        # Parse content, splitting on [INSERT_PANEL_X] markers
        current_text = []
        panel_pattern = re.compile(r'\[INSERT_PANEL_(\d+)\]', re.IGNORECASE)

        for line in lines:
            # Skip the title line
            if line.startswith('# ') and title in line:
                continue

            # Check for panel marker
            match = panel_pattern.search(line)
            if match:
                # Save accumulated text
                if current_text:
                    text_content = '\n'.join(current_text).strip()
                    if text_content:
                        sections.append({"type": "text", "content": text_content})
                    current_text = []

                # Add panel reference
                panel_num = int(match.group(1))
                if 1 <= panel_num <= total_panels:
                    sections.append({"type": "panel", "panel_index": panel_num - 1})

                # Handle any text after the marker on same line
                after_marker = line[match.end():].strip()
                if after_marker:
                    current_text.append(after_marker)
            else:
                current_text.append(line)

        # Don't forget remaining text
        if current_text:
            text_content = '\n'.join(current_text).strip()
            if text_content:
                sections.append({"type": "text", "content": text_content})

        # Validate: ensure all panels are present
        panel_indices = {s["panel_index"] for s in sections if s["type"] == "panel"}
        for i in range(total_panels):
            if i not in panel_indices:
                # Insert missing panel at appropriate position
                insert_pos = len(sections)
                for j, s in enumerate(sections):
                    if s["type"] == "panel" and s["panel_index"] > i:
                        insert_pos = j
                        break
                sections.insert(insert_pos, {"type": "panel", "panel_index": i})

        return title, sections

    # ========================================================================
    # Audio Blog (Podcasting) - Phase 14.5
    # ========================================================================

    async def generate_blog_audio(
        self,
        task_id: str,
        blog_sections: List[Dict],
        blog_title: str = "",
    ) -> Optional[str]:
        """
        Generate podcast audio for the blog content using TTS.

        Args:
            task_id: Task identifier for audio file naming
            blog_sections: List of {type: 'text'|'panel', content/panel_index}
            blog_title: Blog title (included at the beginning of audio)

        Returns:
            URL path to the generated audio file, or None on failure
        """
        try:
            # Update task status
            self._update_task(
                task_id,
                audio_status="generating",
                audio_progress=0,
                audio_message="🎙️ AI is recording the podcast...",
            )

            # Step 1: Extract all text content
            text_parts = []

            # Add title at the beginning
            if blog_title:
                text_parts.append(blog_title)
                text_parts.append("")  # Pause after title

            for section in blog_sections:
                if section.get("type") == "text" and section.get("content"):
                    content = section["content"].strip()
                    # Clean markdown headings for speech
                    content = self._clean_text_for_speech(content)
                    if content:
                        text_parts.append(content)

            if not text_parts:
                logger.warning("No text content found for audio generation")
                return None

            full_text = "\n\n".join(text_parts)
            logger.info(f"Blog audio: {len(full_text)} characters to synthesize")

            # Step 2: Split into segments if too long (>500 chars per segment)
            MAX_SEGMENT_LENGTH = 500
            segments = self._split_text_for_tts(full_text, MAX_SEGMENT_LENGTH)
            logger.info(f"Split into {len(segments)} audio segments")

            # Step 3: Generate audio for each segment
            audio_dir = Path(settings.temp_dir) / "blog_audio"
            audio_dir.mkdir(parents=True, exist_ok=True)

            segment_paths = []
            total_segments = len(segments)

            for i, segment_text in enumerate(segments):
                segment_path = audio_dir / f"{task_id}_seg_{i:02d}.mp3"

                self._update_task(
                    task_id,
                    audio_status="generating",
                    audio_progress=int((i / total_segments) * 80),
                    audio_message=f"🎙️ Recording segment {i + 1}/{total_segments}...",
                )

                try:
                    # Use SophNet CosyVoice with professional narrator voice
                    await self.sophnet.generate_speech_to_file(
                        text=segment_text,
                        output_path=segment_path,
                        voice="longxiaochun",  # Professional narrator voice
                    )

                    if segment_path.exists() and segment_path.stat().st_size > 0:
                        segment_paths.append(segment_path)
                        logger.info(f"Generated audio segment {i + 1}: {segment_path}")
                    else:
                        logger.warning(f"Empty audio segment {i + 1}")

                except Exception as e:
                    logger.error(f"Failed to generate segment {i + 1}: {e}")
                    # Continue with other segments

            if not segment_paths:
                logger.error("No audio segments generated")
                self._update_task(
                    task_id,
                    audio_status="error",
                    audio_message="Audio generation failed",
                )
                return None

            # Step 4: Concatenate segments if multiple
            final_audio_path = audio_dir / f"{task_id}_podcast.mp3"

            self._update_task(
                task_id,
                audio_status="generating",
                audio_progress=85,
                audio_message="🎬 Finalizing podcast audio...",
            )

            if len(segment_paths) == 1:
                # Single segment, just rename
                segment_paths[0].rename(final_audio_path)
            else:
                # Multiple segments, concatenate with FFmpeg
                success = await self._concatenate_audio_segments(
                    segment_paths, final_audio_path
                )
                if not success:
                    logger.error("Failed to concatenate audio segments")
                    self._update_task(
                        task_id,
                        audio_status="error",
                        audio_message="Audio concatenation failed",
                    )
                    return None

                # Cleanup segment files
                for seg_path in segment_paths:
                    try:
                        seg_path.unlink(missing_ok=True)
                    except Exception:
                        pass

            # Step 5: Return audio URL
            audio_url = f"/static/temp/blog_audio/{final_audio_path.name}"

            self._update_task(
                task_id,
                audio_status="completed",
                audio_progress=100,
                audio_message="🎧 Podcast ready!",
                audio_url=audio_url,
            )

            logger.info(f"Blog audio generated: {audio_url}")
            return audio_url

        except Exception as e:
            logger.error(f"Blog audio generation failed: {e}")
            self._update_task(
                task_id,
                audio_status="error",
                audio_message=f"Audio generation failed: {str(e)}",
            )
            return None

    def _clean_text_for_speech(self, text: str) -> str:
        """Clean text content for TTS synthesis."""
        import re

        # Remove markdown headings (## Title -> Title)
        text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)

        # Remove markdown bold/italic markers
        text = re.sub(r'\*{1,2}([^*]+)\*{1,2}', r'\1', text)
        text = re.sub(r'_{1,2}([^_]+)_{1,2}', r'\1', text)

        # Remove markdown links [text](url) -> text
        text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)

        # Remove image references
        text = re.sub(r'!\[([^\]]*)\]\([^)]+\)', '', text)

        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)

        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text).strip()

        return text

    def _split_text_for_tts(
        self,
        text: str,
        max_length: int = 500,
    ) -> List[str]:
        """
        Split text into segments suitable for TTS.
        Respects sentence boundaries where possible.
        """
        if len(text) <= max_length:
            return [text]

        segments = []
        paragraphs = text.split('\n\n')

        current_segment = ""

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            # If paragraph alone exceeds max, split by sentences
            if len(para) > max_length:
                sentences = self._split_into_sentences(para)
                for sentence in sentences:
                    if len(current_segment) + len(sentence) + 1 <= max_length:
                        current_segment += (" " if current_segment else "") + sentence
                    else:
                        if current_segment:
                            segments.append(current_segment.strip())
                        # If single sentence exceeds max, split by chars
                        if len(sentence) > max_length:
                            # Split at max_length boundaries
                            for i in range(0, len(sentence), max_length):
                                segments.append(sentence[i:i + max_length].strip())
                            current_segment = ""
                        else:
                            current_segment = sentence
            else:
                # Try to add paragraph to current segment
                if len(current_segment) + len(para) + 2 <= max_length:
                    current_segment += ("\n\n" if current_segment else "") + para
                else:
                    if current_segment:
                        segments.append(current_segment.strip())
                    current_segment = para

        # Don't forget the last segment
        if current_segment:
            segments.append(current_segment.strip())

        return segments

    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences."""
        import re
        # Split on sentence-ending punctuation followed by space or end
        sentences = re.split(r'(?<=[。！？.!?])\s*', text)
        return [s.strip() for s in sentences if s.strip()]

    async def _concatenate_audio_segments(
        self,
        segment_paths: List[Path],
        output_path: Path,
    ) -> bool:
        """Concatenate multiple audio segments using FFmpeg."""
        try:
            # Create concat list file
            concat_list_path = output_path.parent / f"{output_path.stem}_concat.txt"

            with open(concat_list_path, "w", encoding="utf-8") as f:
                for seg_path in segment_paths:
                    # Use forward slashes and escape single quotes
                    safe_path = str(seg_path).replace("\\", "/").replace("'", "'\\''")
                    f.write(f"file '{safe_path}'\n")

            # FFmpeg concat demuxer
            cmd = [
                "ffmpeg", "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", str(concat_list_path),
                "-c", "copy",
                str(output_path)
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=60,
            )

            # Cleanup concat list
            concat_list_path.unlink(missing_ok=True)

            if result.returncode == 0 and output_path.exists():
                logger.info(f"Audio concatenation successful: {output_path}")
                return True
            else:
                stderr = result.stderr.decode('utf-8', errors='replace')
                logger.error(f"FFmpeg concat failed: {stderr}")
                return False

        except Exception as e:
            logger.error(f"Audio concatenation error: {e}")
            return False
