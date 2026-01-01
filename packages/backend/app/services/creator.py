"""
Creator Service - AI Video Generator
Phase 6: The Alchemist + Phase 7: Entity Supercut

Features:
1. AI Debate Videos (Phase 6): Script + TTS + Split-screen composition
2. Entity Supercut (Phase 7): Knowledge graph entity → Video compilation with watermarks
"""

import asyncio
import uuid
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, List
import logging
import json

from app.core import get_settings
from app.services.vector_store import get_vector_store

logger = logging.getLogger(__name__)
settings = get_settings()

# Directory for generated content
GENERATED_DIR = Path(settings.upload_dir).parent / "generated"
GENERATED_DIR.mkdir(parents=True, exist_ok=True)


class CreatorService:
    """AI Debate Video Generator Service."""

    def __init__(self):
        """Initialize with API settings."""
        self.api_key = settings.modelscope_api_key
        # Task tracking
        self._tasks: Dict[str, Dict[str, Any]] = {}

    async def generate_script(self, conflict_data: Dict[str, Any]) -> str:
        """
        Generate debate introduction script using LLM.

        Args:
            conflict_data: Conflict info with viewpoint_a and viewpoint_b

        Returns:
            Generated script text (30-50 characters, oral style)
        """
        view_a = conflict_data.get("viewpoint_a", {})
        view_b = conflict_data.get("viewpoint_b", {})

        prompt = f"""你是一个热血的电竞解说员。基于这两个对立观点：
[红方: {view_a.get('title', '观点A')} - {view_a.get('description', '')}]
vs
[蓝方: {view_b.get('title', '观点B')} - {view_b.get('description', '')}]

请写一段30-50字的激昂开场白，介绍这场风格对决。要求口语化、有悬念。不要带任何markdown格式。"""

        try:
            from openai import OpenAI

            client = OpenAI(
                api_key=self.api_key,
                base_url="https://api-inference.modelscope.cn/v1",
            )

            response = client.chat.completions.create(
                model="Qwen/Qwen2.5-72B-Instruct",
                messages=[
                    {"role": "system", "content": "你是一个专业的电竞解说员，风格热血激昂。"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=200,
                temperature=0.8,
            )

            script = response.choices[0].message.content.strip()
            logger.info(f"Generated script: {script[:50]}...")
            return script

        except Exception as e:
            logger.error(f"Script generation error: {e}")
            # Fallback script
            return f"欢迎来到今天的对决！红方主张{view_a.get('title', '硬刚')}，蓝方坚持{view_b.get('title', '智取')}，谁能笑到最后？让我们拭目以待！"

    async def generate_voiceover(self, text: str, output_path: Path, duration: float = 15.0) -> bool:
        """
        Generate TTS voiceover using Edge-TTS.
        Falls back to silent audio if TTS fails.

        Args:
            text: Script text to convert
            output_path: Path for output MP3 file
            duration: Duration in seconds for fallback silent audio

        Returns:
            True if successful
        """
        try:
            import edge_tts

            # Use Chinese narrator voice suitable for commentary
            voice = "zh-CN-YunxiNeural"  # Male, energetic voice

            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(str(output_path))

            logger.info(f"Voiceover generated: {output_path}")
            return True

        except Exception as e:
            logger.error(f"TTS generation error: {e}")

            # Fallback: Generate silent audio using FFmpeg
            try:
                logger.info("Falling back to silent audio generation")
                cmd = [
                    "ffmpeg", "-y",
                    "-f", "lavfi",
                    "-i", f"anullsrc=r=44100:cl=stereo",
                    "-t", str(duration),
                    "-c:a", "libmp3lame",
                    "-q:a", "4",
                    str(output_path)
                ]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                if result.returncode == 0:
                    logger.info(f"Silent audio generated: {output_path}")
                    return True
                else:
                    logger.error(f"FFmpeg silent audio error: {result.stderr}")
                    return False
            except Exception as fallback_error:
                logger.error(f"Fallback audio generation error: {fallback_error}")
                return False

    async def compose_debate_video(
        self,
        video_a_path: Path,
        time_a: float,
        video_b_path: Path,
        time_b: float,
        voiceover_path: Path,
        output_path: Path,
        clip_duration: float = 15.0,
    ) -> bool:
        """
        Compose split-screen debate video using FFmpeg.

        Pipeline:
        1. Trim: Extract 15s clips from each video
        2. Scale: Resize to same height (720p)
        3. Layout: Horizontal stack with separator line
        4. Audio Mix: Background (20%) + Voiceover (100%)
        5. Output: MP4 file

        Args:
            video_a_path: Path to video A
            time_a: Start timestamp for video A
            video_b_path: Path to video B
            time_b: Start timestamp for video B
            voiceover_path: Path to TTS audio
            output_path: Output video path
            clip_duration: Duration of each clip (default 15s)

        Returns:
            True if successful
        """
        try:
            # Ensure output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # FFmpeg complex filter for split-screen with audio mixing
            # Filter:
            # 1. Trim and scale both videos to 640x720
            # 2. Horizontal stack with 4px black separator
            # 3. Add source labels
            # 4. Mix audio: original at 20% + voiceover at 100%

            filter_complex = """
[0:v]trim=start={time_a}:duration={duration},setpts=PTS-STARTPTS,scale=640:720:force_original_aspect_ratio=decrease,pad=640:720:(ow-iw)/2:(oh-ih)/2,drawtext=text='SOURCE A':x=10:y=10:fontsize=24:fontcolor=white:borderw=2:bordercolor=black[v0];
[1:v]trim=start={time_b}:duration={duration},setpts=PTS-STARTPTS,scale=640:720:force_original_aspect_ratio=decrease,pad=640:720:(ow-iw)/2:(oh-ih)/2,drawtext=text='SOURCE B':x=10:y=10:fontsize=24:fontcolor=white:borderw=2:bordercolor=black[v1];
[v0][v1]hstack=inputs=2[video];
[0:a]atrim=start={time_a}:duration={duration},asetpts=PTS-STARTPTS,volume=0.2[a0];
[1:a]atrim=start={time_b}:duration={duration},asetpts=PTS-STARTPTS,volume=0.2[a1];
[a0][a1]amix=inputs=2:duration=longest[bg];
[2:a]volume=1.0[vo];
[bg][vo]amix=inputs=2:duration=longest[audio]
""".format(time_a=time_a, time_b=time_b, duration=clip_duration).strip().replace('\n', '')

            cmd = [
                "ffmpeg", "-y",
                "-i", str(video_a_path),
                "-i", str(video_b_path),
                "-i", str(voiceover_path),
                "-filter_complex", filter_complex,
                "-map", "[video]",
                "-map", "[audio]",
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "23",
                "-c:a", "aac",
                "-b:a", "128k",
                "-t", str(clip_duration),
                str(output_path)
            ]

            logger.info(f"Running FFmpeg command...")
            logger.info(f"Video A: {video_a_path}")
            logger.info(f"Video B: {video_b_path}")
            logger.info(f"Voiceover: {voiceover_path}")
            logger.info(f"Output: {output_path}")

            # Run FFmpeg synchronously (async subprocess has issues on Windows)
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
                cwd=str(Path(__file__).parent.parent.parent)  # Run from backend dir
            )

            logger.info(f"FFmpeg return code: {result.returncode}")

            if result.returncode == 0:
                logger.info(f"Video composed successfully: {output_path}")
                return True
            else:
                stderr_msg = result.stderr[-1000:] if len(result.stderr) > 1000 else result.stderr
                logger.error(f"FFmpeg stderr: {stderr_msg}")
                return False

        except Exception as e:
            logger.error(f"Video composition error: {e}")
            return False

    async def create_debate_video(
        self,
        task_id: str,
        conflict_data: Dict[str, Any],
        source_a_id: str,
        source_a_path: Path,
        time_a: float,
        source_b_id: str,
        source_b_path: Path,
        time_b: float,
    ) -> Dict[str, Any]:
        """
        Full pipeline to create a debate video.

        Args:
            task_id: Unique task identifier
            conflict_data: Conflict info for script generation
            source_a_id: ID of source A
            source_a_path: Path to video A
            time_a: Timestamp for video A
            source_b_id: ID of source B
            source_b_path: Path to video B
            time_b: Timestamp for video B

        Returns:
            Task result with video URL or error
        """
        try:
            # Update task status
            self._tasks[task_id] = {
                "status": "generating_script",
                "progress": 10,
                "message": "AI 正在撰写解说词...",
            }

            # Step 1: Generate script
            script = await self.generate_script(conflict_data)

            self._tasks[task_id] = {
                "status": "generating_voiceover",
                "progress": 30,
                "message": "正在生成配音...",
            }

            # Step 2: Generate voiceover
            voiceover_path = GENERATED_DIR / f"{task_id}_voiceover.mp3"
            tts_success = await self.generate_voiceover(script, voiceover_path)

            if not tts_success:
                raise Exception("TTS generation failed")

            self._tasks[task_id] = {
                "status": "composing_video",
                "progress": 50,
                "message": "正在合成视频...",
            }

            # Step 3: Compose video
            output_path = GENERATED_DIR / f"debate_{task_id}.mp4"
            compose_success = await self.compose_debate_video(
                video_a_path=source_a_path,
                time_a=time_a,
                video_b_path=source_b_path,
                time_b=time_b,
                voiceover_path=voiceover_path,
                output_path=output_path,
            )

            if not compose_success:
                raise Exception("Video composition failed")

            # Success
            video_url = f"/static/generated/debate_{task_id}.mp4"

            self._tasks[task_id] = {
                "status": "completed",
                "progress": 100,
                "message": "视频生成完成！",
                "video_url": video_url,
                "script": script,
            }

            logger.info(f"Debate video created: {video_url}")
            return self._tasks[task_id]

        except Exception as e:
            logger.error(f"Create debate video error: {e}")
            self._tasks[task_id] = {
                "status": "error",
                "progress": 0,
                "message": f"生成失败: {str(e)}",
                "error": str(e),
            }
            return self._tasks[task_id]

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a creation task."""
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

    # ========================================
    # Phase 7: Entity Supercut Methods
    # ========================================

    async def search_entity_clips(
        self,
        entity_name: str,
        top_k: int = 5,
        padding: float = 2.0
    ) -> List[Dict[str, Any]]:
        """
        Search for video clips mentioning an entity in ChromaDB.

        Args:
            entity_name: Name of the entity to search (e.g., "定风珠", "虎先锋")
            top_k: Maximum number of clips to return
            padding: Seconds to add before/after each clip

        Returns:
            List of clip info: [{source_id, video_path, start, end, label, score}]
        """
        try:
            vector_store = get_vector_store()

            # Search for entity mentions
            results = vector_store.search(
                query=entity_name,
                n_results=top_k * 2,  # Get more results for filtering
            )

            if not results:
                logger.warning(f"No results found for entity: {entity_name}")
                return []

            # Process results and build clip list
            clips = []
            seen_segments = set()  # Avoid duplicate time segments

            for result in results:
                metadata = result.get("metadata", {})
                source_id = metadata.get("source_id", "")
                start_time = metadata.get("start", 0)
                end_time = metadata.get("end", start_time + 5)
                video_title = metadata.get("video_title", "Unknown")
                distance = result.get("distance", 1.0)

                # Skip if no source_id
                if not source_id:
                    continue

                # Create segment key to avoid duplicates
                segment_key = f"{source_id}_{int(start_time)}"
                if segment_key in seen_segments:
                    continue
                seen_segments.add(segment_key)

                # Get video path from database
                video_path = await self._get_video_path(source_id)
                if not video_path:
                    continue

                # Apply padding
                padded_start = max(0, start_time - padding)
                padded_end = end_time + padding

                clips.append({
                    "source_id": source_id,
                    "video_path": video_path,
                    "video_title": video_title,
                    "start": padded_start,
                    "end": padded_end,
                    "original_start": start_time,
                    "label": f"{video_title} | {self._format_timestamp(start_time)}",
                    "score": 1.0 - distance,  # Convert distance to similarity score
                })

                if len(clips) >= top_k:
                    break

            # Sort by source_id and start_time for coherent playback
            clips.sort(key=lambda x: (x["source_id"], x["start"]))

            logger.info(f"Found {len(clips)} clips for entity: {entity_name}")
            return clips

        except Exception as e:
            logger.error(f"Entity search error: {e}")
            return []

    async def _get_video_path(self, source_id: str) -> Optional[str]:
        """Get video file path from database by source_id."""
        try:
            from sqlalchemy import select
            from app.core import async_session
            from app.models import Source

            async with async_session() as session:
                result = await session.execute(
                    select(Source).where(Source.id == source_id)
                )
                source = result.scalar_one_or_none()
                if source:
                    return source.file_path
            return None
        except Exception as e:
            logger.error(f"Failed to get video path for {source_id}: {e}")
            return None

    def _format_timestamp(self, seconds: float) -> str:
        """Format seconds to MM:SS string."""
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes:02d}:{secs:02d}"

    async def compose_supercut_video(
        self,
        clips: List[Dict[str, Any]],
        entity_name: str,
        output_path: Path,
    ) -> bool:
        """
        Compose entity supercut video with watermarks using FFmpeg.

        Pipeline:
        1. Trim each clip from source videos
        2. Add watermark text (Source + Timestamp) on each clip
        3. Concatenate all clips
        4. Output as single MP4

        Args:
            clips: List of clip info from search_entity_clips
            entity_name: Entity name for output filename
            output_path: Output video path

        Returns:
            True if successful
        """
        if not clips:
            logger.error("No clips provided for supercut")
            return False

        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Create temporary directory for intermediate files
            temp_dir = GENERATED_DIR / f"temp_{uuid.uuid4().hex[:8]}"
            temp_dir.mkdir(parents=True, exist_ok=True)

            # Step 1: Process each clip (trim + watermark)
            processed_clips = []
            for i, clip in enumerate(clips):
                video_path = clip["video_path"]
                start = clip["start"]
                duration = clip["end"] - clip["start"]
                label = clip["label"]

                # Output path for this clip
                clip_output = temp_dir / f"clip_{i:03d}.mp4"

                # FFmpeg filter for watermark
                # Avoid colons in text (conflicts with FFmpeg filter syntax)
                # Use MM.SS format instead of MM:SS
                timestamp = self._format_timestamp(clip['original_start']).replace(':', '.')
                safe_label = f"Source_{i+1}_{timestamp}"

                filter_complex = (
                    f"drawtext=text={safe_label}:"
                    f"x=10:y=h-40:fontsize=24:fontcolor=white:"
                    f"borderw=2:bordercolor=black"
                )

                cmd = [
                    "ffmpeg", "-y",
                    "-ss", str(start),
                    "-i", str(video_path),
                    "-t", str(duration),
                    "-vf", filter_complex,
                    "-c:v", "libx264",
                    "-preset", "fast",
                    "-crf", "23",
                    "-c:a", "aac",
                    "-b:a", "128k",
                    str(clip_output)
                ]

                logger.info(f"Processing clip {i+1}/{len(clips)}: {video_path}")

                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=120,
                )

                if result.returncode != 0:
                    # Log more of the error message for debugging
                    stderr_end = result.stderr[-1000:] if len(result.stderr) > 1000 else result.stderr
                    logger.error(f"Clip processing failed for {video_path}")
                    logger.error(f"FFmpeg stderr: {stderr_end}")
                    continue

                processed_clips.append(str(clip_output))

            if not processed_clips:
                logger.error("No clips were processed successfully")
                self._cleanup_temp_dir(temp_dir)
                return False

            # Step 2: Create concat file with absolute paths
            concat_file = temp_dir / "concat.txt"
            with open(concat_file, "w", encoding="utf-8") as f:
                for clip_path in processed_clips:
                    # Use absolute path with forward slashes for FFmpeg compatibility
                    abs_path = str(Path(clip_path).absolute()).replace(chr(92), '/')
                    f.write(f"file '{abs_path}'\n")

            # Log concat file contents for debugging
            logger.info(f"Concat file contents: {concat_file.read_text()[:500]}")

            # Step 3: Concatenate all clips
            concat_cmd = [
                "ffmpeg", "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", str(concat_file.absolute()),
                "-c", "copy",
                str(output_path.absolute())
            ]

            logger.info(f"Concatenating {len(processed_clips)} clips...")

            result = subprocess.run(
                concat_cmd,
                capture_output=True,
                text=True,
                timeout=300,
            )

            # Cleanup temp files
            self._cleanup_temp_dir(temp_dir)

            if result.returncode == 0:
                logger.info(f"Supercut video created: {output_path}")
                return True
            else:
                # Log more of the error
                stderr_end = result.stderr[-1500:] if len(result.stderr) > 1500 else result.stderr
                logger.error(f"Concatenation failed: {stderr_end}")
                return False

        except Exception as e:
            logger.error(f"Supercut composition error: {e}")
            return False

    def _cleanup_temp_dir(self, temp_dir: Path):
        """Clean up temporary directory."""
        try:
            import shutil
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
        except Exception as e:
            logger.warning(f"Failed to cleanup temp dir: {e}")

    async def create_entity_supercut(
        self,
        task_id: str,
        entity_name: str,
        top_k: int = 5,
    ) -> Dict[str, Any]:
        """
        Full pipeline to create an entity supercut video.

        Args:
            task_id: Unique task identifier
            entity_name: Name of the entity
            top_k: Maximum number of clips

        Returns:
            Task result with video URL or error
        """
        try:
            # Update task status
            self._tasks[task_id] = {
                "status": "searching",
                "progress": 10,
                "message": f"正在搜索 '{entity_name}' 相关片段...",
            }

            # Step 1: Search for clips
            clips = await self.search_entity_clips(entity_name, top_k=top_k)

            if not clips:
                raise Exception(f"未找到与 '{entity_name}' 相关的视频片段")

            self._tasks[task_id] = {
                "status": "composing",
                "progress": 40,
                "message": f"正在合成 {len(clips)} 个片段...",
            }

            # Step 2: Compose supercut video
            safe_entity_name = "".join(c for c in entity_name if c.isalnum() or c in "._-")[:20]
            output_path = GENERATED_DIR / f"supercut_{safe_entity_name}_{task_id}.mp4"

            compose_success = await self.compose_supercut_video(
                clips=clips,
                entity_name=entity_name,
                output_path=output_path,
            )

            if not compose_success:
                raise Exception("视频合成失败")

            # Success
            video_url = f"/static/generated/supercut_{safe_entity_name}_{task_id}.mp4"

            # Build clip info for response
            clip_info = [
                {
                    "source_id": c["source_id"],
                    "video_title": c["video_title"],
                    "timestamp": self._format_timestamp(c["original_start"]),
                    "score": round(c["score"], 2),
                }
                for c in clips
            ]

            self._tasks[task_id] = {
                "status": "completed",
                "progress": 100,
                "message": "混剪视频生成完成！",
                "video_url": video_url,
                "entity_name": entity_name,
                "clip_count": len(clips),
                "clips": clip_info,
            }

            logger.info(f"Supercut video created for '{entity_name}': {video_url}")
            return self._tasks[task_id]

        except Exception as e:
            logger.error(f"Create supercut error: {e}")
            self._tasks[task_id] = {
                "status": "error",
                "progress": 0,
                "message": f"生成失败: {str(e)}",
                "error": str(e),
            }
            return self._tasks[task_id]

    async def get_entity_stats(self, entity_name: str) -> Dict[str, Any]:
        """
        Get statistics for an entity (for Entity Card display).
        Uses exact text matching in documents for accurate counts.

        Args:
            entity_name: Name of the entity

        Returns:
            Statistics including video count and occurrence count
        """
        try:
            vector_store = get_vector_store()

            # Use ChromaDB's where_document filter for exact text matching
            # This is more accurate than semantic search for entity statistics
            try:
                results = vector_store.collection.get(
                    where_document={"$contains": entity_name},
                    include=["metadatas", "documents"]
                )
            except Exception as e:
                logger.warning(f"ChromaDB where_document query failed: {e}, falling back to search")
                # Fallback to semantic search if where_document fails
                search_results = vector_store.search(
                    query=entity_name,
                    n_results=100,
                )
                # Filter results to only those containing the entity name
                results = {
                    "ids": [],
                    "metadatas": [],
                    "documents": []
                }
                for r in search_results:
                    if entity_name.lower() in r.get("text", "").lower():
                        results["metadatas"].append(r.get("metadata", {}))
                        results["documents"].append(r.get("text", ""))

            if not results.get("metadatas"):
                return {
                    "entity_name": entity_name,
                    "video_count": 0,
                    "occurrence_count": 0,
                }

            # Count unique videos and occurrences
            video_ids = set()
            occurrence_count = 0

            metadatas = results.get("metadatas", [])
            for metadata in metadatas:
                source_id = metadata.get("source_id", "") if isinstance(metadata, dict) else ""
                if source_id:
                    video_ids.add(source_id)
                    occurrence_count += 1

            logger.info(f"Entity stats for '{entity_name}': {len(video_ids)} videos, {occurrence_count} occurrences")

            return {
                "entity_name": entity_name,
                "video_count": len(video_ids),
                "occurrence_count": occurrence_count,
            }

        except Exception as e:
            logger.error(f"Get entity stats error: {e}")
            return {
                "entity_name": entity_name,
                "video_count": 0,
                "occurrence_count": 0,
            }

    # ========================================
    # Phase 8: Smart Timeline & Digest Methods
    # ========================================

    async def compose_digest_video(
        self,
        source_path: Path,
        segments: List[Dict[str, Any]],
        output_path: Path,
        add_fade: bool = True,
    ) -> bool:
        """
        Compose digest video by concatenating selected segments with transitions.

        Pipeline:
        1. Trim each segment from source video
        2. Add fade transitions between segments (optional)
        3. Concatenate all segments
        4. Output as single MP4

        Args:
            source_path: Path to source video
            segments: List of segments [{start, end, title, event_type}]
            output_path: Output video path
            add_fade: Whether to add fade transitions

        Returns:
            True if successful
        """
        if not segments:
            logger.error("No segments provided for digest")
            return False

        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Create temporary directory for intermediate files
            temp_dir = GENERATED_DIR / f"temp_digest_{uuid.uuid4().hex[:8]}"
            temp_dir.mkdir(parents=True, exist_ok=True)

            processed_clips = []
            fade_duration = 0.5 if add_fade else 0

            for i, segment in enumerate(segments):
                start = max(0, segment["start"] - 1.0)  # 1s padding before
                end = segment["end"] + 1.0  # 1s padding after
                duration = end - start

                clip_output = temp_dir / f"segment_{i:03d}.mp4"

                # Build filter for fade effects
                if add_fade and len(segments) > 1:
                    # Add fade in at start (except first clip) and fade out at end (except last clip)
                    filters = []
                    if i > 0:
                        filters.append(f"fade=t=in:st=0:d={fade_duration}")
                    if i < len(segments) - 1:
                        filters.append(f"fade=t=out:st={duration - fade_duration}:d={fade_duration}")

                    # Audio fade
                    audio_filters = []
                    if i > 0:
                        audio_filters.append(f"afade=t=in:st=0:d={fade_duration}")
                    if i < len(segments) - 1:
                        audio_filters.append(f"afade=t=out:st={duration - fade_duration}:d={fade_duration}")

                    vf = ",".join(filters) if filters else None
                    af = ",".join(audio_filters) if audio_filters else None

                    cmd = [
                        "ffmpeg", "-y",
                        "-ss", str(start),
                        "-i", str(source_path),
                        "-t", str(duration),
                    ]

                    if vf:
                        cmd.extend(["-vf", vf])
                    if af:
                        cmd.extend(["-af", af])

                    cmd.extend([
                        "-c:v", "libx264",
                        "-preset", "fast",
                        "-crf", "23",
                        "-c:a", "aac",
                        "-b:a", "128k",
                        str(clip_output)
                    ])
                else:
                    # Simple trim without fade
                    cmd = [
                        "ffmpeg", "-y",
                        "-ss", str(start),
                        "-i", str(source_path),
                        "-t", str(duration),
                        "-c:v", "libx264",
                        "-preset", "fast",
                        "-crf", "23",
                        "-c:a", "aac",
                        "-b:a", "128k",
                        str(clip_output)
                    ]

                logger.info(f"Processing segment {i+1}/{len(segments)}: {segment.get('title', 'Unknown')}")

                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=120,
                )

                if result.returncode != 0:
                    stderr_end = result.stderr[-500:] if len(result.stderr) > 500 else result.stderr
                    logger.error(f"Segment processing failed: {stderr_end}")
                    continue

                processed_clips.append(str(clip_output))

            if not processed_clips:
                logger.error("No segments were processed successfully")
                self._cleanup_temp_dir(temp_dir)
                return False

            # Create concat file with absolute paths
            concat_file = temp_dir / "concat.txt"
            with open(concat_file, "w", encoding="utf-8") as f:
                for clip_path in processed_clips:
                    abs_path = str(Path(clip_path).absolute()).replace(chr(92), '/')
                    f.write(f"file '{abs_path}'\n")

            logger.info(f"Concatenating {len(processed_clips)} segments...")

            # Concatenate all clips
            concat_cmd = [
                "ffmpeg", "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", str(concat_file.absolute()),
                "-c", "copy",
                str(output_path.absolute())
            ]

            result = subprocess.run(
                concat_cmd,
                capture_output=True,
                text=True,
                timeout=300,
            )

            # Cleanup temp files
            self._cleanup_temp_dir(temp_dir)

            if result.returncode == 0:
                logger.info(f"Digest video created: {output_path}")
                return True
            else:
                stderr_end = result.stderr[-1000:] if len(result.stderr) > 1000 else result.stderr
                logger.error(f"Concatenation failed: {stderr_end}")
                return False

        except Exception as e:
            logger.error(f"Digest composition error: {e}")
            return False

    async def create_video_digest(
        self,
        task_id: str,
        source_id: str,
        source_path: Path,
        timeline_events: List[Dict[str, Any]],
        include_types: List[str] = ["STORY", "COMBAT"],
    ) -> Dict[str, Any]:
        """
        Full pipeline to create a video digest.

        Args:
            task_id: Unique task identifier
            source_id: Video source ID
            source_path: Path to source video
            timeline_events: List of timeline events with event_type
            include_types: Event types to include (default: STORY, COMBAT)

        Returns:
            Task result with video URL or error
        """
        try:
            # Update task status
            self._tasks[task_id] = {
                "status": "filtering",
                "progress": 10,
                "message": "正在筛选精华片段...",
            }

            # Filter events by type
            filtered_events = [
                e for e in timeline_events
                if e.get("event_type", "STORY") in include_types
            ]

            if not filtered_events:
                raise Exception(f"没有找到类型为 {include_types} 的事件")

            # Sort by timestamp
            filtered_events.sort(key=lambda x: x.get("timestamp", 0))

            # Build segments with proper time ranges
            segments = []
            for i, event in enumerate(filtered_events):
                start = event.get("timestamp", 0)

                # Calculate end time: next event's start or +30 seconds
                if i + 1 < len(filtered_events):
                    next_start = filtered_events[i + 1].get("timestamp", start + 30)
                    end = min(next_start, start + 60)  # Max 60s per segment
                else:
                    end = start + 30  # Last segment: 30 seconds

                segments.append({
                    "start": start,
                    "end": end,
                    "title": event.get("title", ""),
                    "event_type": event.get("event_type", "STORY"),
                })

            self._tasks[task_id] = {
                "status": "composing",
                "progress": 30,
                "message": f"正在合成 {len(segments)} 个精华片段...",
            }

            # Compose digest video
            output_path = GENERATED_DIR / f"digest_{task_id}.mp4"
            compose_success = await self.compose_digest_video(
                source_path=source_path,
                segments=segments,
                output_path=output_path,
                add_fade=True,
            )

            if not compose_success:
                raise Exception("视频合成失败")

            # Calculate total duration
            total_duration = sum(s["end"] - s["start"] for s in segments)

            # Success
            video_url = f"/static/generated/digest_{task_id}.mp4"

            self._tasks[task_id] = {
                "status": "completed",
                "progress": 100,
                "message": "浓缩视频生成完成！",
                "video_url": video_url,
                "source_id": source_id,
                "segment_count": len(segments),
                "include_types": include_types,
                "total_duration": round(total_duration, 1),
            }

            logger.info(f"Digest video created: {video_url}")
            return self._tasks[task_id]

        except Exception as e:
            logger.error(f"Create digest error: {e}")
            self._tasks[task_id] = {
                "status": "error",
                "progress": 0,
                "message": f"生成失败: {str(e)}",
                "error": str(e),
            }
            return self._tasks[task_id]


# Singleton instance
_creator_service: Optional[CreatorService] = None


def get_creator_service() -> CreatorService:
    """Get or create CreatorService singleton."""
    global _creator_service
    if _creator_service is None:
        _creator_service = CreatorService()
    return _creator_service
