"""
Montage Service for Highlight Nebula feature.
Handles concept extraction, nebula structure building, and highlight reel generation.
"""

import asyncio
import logging
import os
import subprocess
import tempfile
import uuid
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select

from app.core import get_settings
from app.core.database import async_session
from app.models.models import Source
from app.services.vector_store import get_vector_store
from app.services.sophnet_service import get_sophnet_service

logger = logging.getLogger(__name__)
settings = get_settings()
GENERATED_DIR = Path(settings.upload_dir).parent / "generated"
GENERATED_DIR.mkdir(parents=True, exist_ok=True)

# Singleton instance
_montage_service: Optional["MontageService"] = None


def get_montage_service() -> "MontageService":
    """Get singleton MontageService instance."""
    global _montage_service
    if _montage_service is None:
        _montage_service = MontageService()
    return _montage_service


class MontageService:
    """Service for building knowledge nebula and generating highlight reels."""

    def __init__(self):
        self.tasks: Dict[str, Dict[str, Any]] = {}
        self.generated_dir = str(GENERATED_DIR)

    def create_task(self) -> str:
        """Create a new task and return its ID."""
        task_id = uuid.uuid4().hex[:8]
        self.tasks[task_id] = {
            "status": "pending",
            "progress": 0,
            "message": "Task created",
        }
        return task_id

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task status by ID."""
        return self.tasks.get(task_id)

    def _update_task(self, task_id: str, **kwargs):
        """Update task status."""
        if task_id in self.tasks:
            self.tasks[task_id].update(kwargs)

    async def get_global_concepts(
        self,
        top_k: int = 50,
        min_length: int = 2,
        max_length: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Extract high-frequency concepts from all video content.
        Returns list of {text, value} dicts.
        """
        vector_store = get_vector_store()

        # Get all documents
        docs = vector_store.get_all_documents()
        if not docs:
            return []

        # Count word frequencies
        word_counts: Counter = Counter()
        for doc in docs:
            text = doc.get("text", "")
            # Simple word extraction (Chinese-aware)
            words = self._extract_words(text, min_length, max_length)
            word_counts.update(words)

        # Get top concepts
        top_concepts = word_counts.most_common(top_k)
        return [{"text": word, "value": count} for word, count in top_concepts]

    async def get_nebula_structure(
        self,
        top_k: int = 80,
        min_length: int = 2,
        max_length: int = 10,
    ) -> Dict[str, Any]:
        """
        Build 3D nebula graph structure with nodes and co-occurrence links.
        Returns: {"nodes": [{id, val, group}], "links": [{source, target, value}]}
        """
        vector_store = get_vector_store()

        # Get all documents
        docs = vector_store.get_all_documents()
        if not docs:
            return {"nodes": [], "links": []}

        # Count word frequencies and co-occurrences
        word_counts: Counter = Counter()
        co_occurrences: Counter = Counter()

        for doc in docs:
            text = doc.get("text", "")
            words = self._extract_words(text, min_length, max_length)

            # Count individual words
            word_counts.update(words)

            # Count co-occurrences (pairs in same document)
            unique_words = list(set(words))
            for i, w1 in enumerate(unique_words):
                for w2 in unique_words[i + 1:]:
                    pair = tuple(sorted([w1, w2]))
                    co_occurrences[pair] += 1

        # Get top nodes
        top_words = [word for word, _ in word_counts.most_common(top_k)]
        top_set = set(top_words)

        # Build nodes with classification
        nodes = []
        for word in top_words:
            nodes.append({
                "id": word,
                "val": word_counts[word],
                "group": self._classify_entity_type(word),
            })

        # Build links (only between top nodes)
        links = []
        for (w1, w2), count in co_occurrences.most_common():
            if w1 in top_set and w2 in top_set and count >= 2:
                links.append({
                    "source": w1,
                    "target": w2,
                    "value": count,
                })

        logger.info(f"Nebula structure: {len(nodes)} nodes, {len(links)} links")
        return {"nodes": nodes, "links": links}

    def _extract_words(
        self,
        text: str,
        min_length: int = 2,
        max_length: int = 10,
    ) -> List[str]:
        """Extract meaningful words from text."""
        import re

        # Remove punctuation and split
        # Keep Chinese characters and alphanumeric
        words = re.findall(r'[\u4e00-\u9fff]+|[a-zA-Z0-9]+', text)

        # Filter by length
        return [
            w for w in words
            if min_length <= len(w) <= max_length
            and not w.isdigit()  # Skip pure numbers
        ]

    def _classify_entity_type(self, word: str) -> str:
        """Classify entity type based on word characteristics."""
        # Simple heuristics for classification
        location_indicators = ['市', '省', '县', '区', '镇', '村', '山', '河', '湖', '海', '岛']
        person_indicators = ['先生', '女士', '总', '长', '师', '员']
        tech_indicators = ['AI', 'API', '系统', '平台', '技术', '算法', '模型', '数据']

        for indicator in location_indicators:
            if indicator in word:
                return 'location'

        for indicator in person_indicators:
            if indicator in word:
                return 'person'

        for indicator in tech_indicators:
            if indicator in word or word.isupper():
                return 'tech'

        return 'concept'

    async def search_concept_segments(
        self,
        concept: str,
        top_k: int = 10,
    ) -> List[Dict[str, Any]]:
        """Search for video segments related to a concept."""
        vector_store = get_vector_store()

        # Search in vector store (use n_results parameter)
        results = vector_store.search(concept, n_results=top_k)

        segments = []
        for result in results:
            metadata = result.get("metadata", {})
            # distance is from vector store, convert to positive score (lower distance = higher score)
            distance = result.get("distance", 0)
            score = float(1.0 - min(distance, 1.0))  # Convert distance to 0-1 score
            segments.append({
                "source_id": metadata.get("source_id", ""),
                "video_title": metadata.get("title", "Unknown"),
                "start": metadata.get("start", 0),
                "end": metadata.get("end", 0),
                "text": result.get("text", ""),
                "score": score,
            })

        return segments

    async def create_concept_supercut(
        self,
        task_id: str,
        concept: str,
        top_k: int = 10,
        max_duration: float = 90.0,
    ):
        """
        Create a highlight reel video for a concept.

        Pipeline:
        1. RAG search for relevant segments
        2. LLM sorts segments into narrative order
        3. FFmpeg composes video with xfade transitions
        """
        try:
            self._update_task(
                task_id,
                status="searching",
                progress=10,
                message="正在搜索相关片段...",
            )

            # Step 1: Search for segments
            segments = await self.search_concept_segments(concept, top_k=top_k)
            if not segments:
                self._update_task(
                    task_id,
                    status="error",
                    progress=100,
                    message=f"未找到与 '{concept}' 相关的内容",
                    error="No segments found",
                )
                return

            logger.info(f"Found {len(segments)} segments for concept: {concept}")

            self._update_task(
                task_id,
                status="sorting",
                progress=30,
                message="AI 正在编排叙事顺序...",
            )

            # Step 2: Sort segments using LLM
            sorted_segments = await self._sort_segments_with_llm(concept, segments)

            logger.info(f"Sorted {len(sorted_segments)} segments for concept: {concept}")

            self._update_task(
                task_id,
                status="composing",
                progress=50,
                message="正在合成高光视频...",
            )

            # Step 3: Compose video
            video_path = await self._compose_video(
                task_id,
                concept,
                sorted_segments,
                max_duration,
            )

            if video_path:
                # Build segment info for response
                segment_infos = [
                    {
                        "source_id": seg["source_id"],
                        "video_title": seg["video_title"],
                        "timestamp": self._format_time(seg["start"]),
                        "score": seg["score"],
                    }
                    for seg in sorted_segments
                ]

                self._update_task(
                    task_id,
                    status="completed",
                    progress=100,
                    message=f"'{concept}' 专题速览生成完成！",
                    video_url=f"/static/generated/{os.path.basename(video_path)}",
                    concept=concept,
                    segment_count=len(sorted_segments),
                    segments=segment_infos,
                )

                logger.info(f"Concept supercut created for '{concept}': /static/generated/{os.path.basename(video_path)}")
            else:
                self._update_task(
                    task_id,
                    status="error",
                    progress=100,
                    message="视频合成失败",
                    error="Video composition failed",
                )

        except Exception as e:
            logger.error(f"Error creating concept supercut: {e}")
            self._update_task(
                task_id,
                status="error",
                progress=100,
                message=f"生成失败: {str(e)}",
                error=str(e),
            )

    async def _sort_segments_with_llm(
        self,
        concept: str,
        segments: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Use LLM to sort segments into a logical narrative order."""
        if len(segments) <= 1:
            return segments

        # Prepare segment descriptions
        segment_descs = []
        for i, seg in enumerate(segments):
            text = seg.get("text", "")[:200]
            segment_descs.append(f"seg_{i}: {text}")

        prompt = f"""你是一个视频编辑专家。我有以下关于"{concept}"的视频片段，请按照最佳叙事顺序排列它们。

片段列表:
{chr(10).join(segment_descs)}

请按照以下叙事结构排序:
1. 定义/介绍 - 首先介绍概念
2. 核心内容 - 主要讨论和分析
3. 注意事项/风险 - 警告或限制
4. 总结/展望 - 结论或未来方向

请只返回排序后的片段ID，用逗号分隔，例如: seg_2, seg_0, seg_1, seg_3
"""

        try:
            sophnet = get_sophnet_service()
            response = await sophnet.chat(prompt)

            # Parse response
            import re
            matches = re.findall(r'seg_(\d+)', response)

            if matches:
                logger.info(f"LLM sort response: {', '.join(['seg_' + m for m in matches])}")
                sorted_indices = [int(m) for m in matches if int(m) < len(segments)]
                # Add any missing segments at the end
                all_indices = set(range(len(segments)))
                missing = all_indices - set(sorted_indices)
                sorted_indices.extend(missing)

                return [segments[i] for i in sorted_indices if i < len(segments)]
        except Exception as e:
            logger.warning(f"LLM sorting failed, using original order: {e}")

        return segments

    async def _compose_video(
        self,
        task_id: str,
        concept: str,
        segments: List[Dict[str, Any]],
        max_duration: float,
    ) -> Optional[str]:
        """Compose video clips with xfade transitions."""
        if not segments:
            return None

        # Get video paths and prepare clips
        clips = []
        total_duration = 0

        async with async_session() as db:
            for i, seg in enumerate(segments):
                if total_duration >= max_duration:
                    break

                source_id = seg.get("source_id")
                if not source_id:
                    continue

                result = await db.execute(select(Source).where(Source.id == source_id))
                source = result.scalars().first()
                if not source or not source.file_path:
                    continue

                # Find the video file
                video_path = os.path.join(source.file_path, "video.mp4")
                if not os.path.exists(video_path):
                    # Try the file_path directly
                    if os.path.exists(source.file_path):
                        video_path = source.file_path
                    else:
                        continue

                start = float(seg.get("start", 0))
                end = float(seg.get("end", start + 10))
                duration = min(end - start, max_duration - total_duration, 15)  # Max 15s per clip

                if duration > 0:
                    clips.append({
                        "path": video_path,
                        "start": start,
                        "duration": duration,
                    })
                    total_duration += duration

                    logger.info(f"Processing segment {i + 1}/{len(segments)}: {video_path}")

        if not clips:
            return None

        # Generate output path
        output_path = os.path.join(
            self.generated_dir,
            f"supercut_{concept}_{task_id}.mp4"
        )

        # Compose with FFmpeg
        try:
            await self._ffmpeg_xfade_concat(clips, output_path)
            logger.info(f"Supercut video created: {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"FFmpeg composition failed: {e}")
            return None

    async def _ffmpeg_xfade_concat(
        self,
        clips: List[Dict[str, Any]],
        output_path: str,
        transition_duration: float = 0.5,
    ):
        """Concatenate clips with xfade transitions using FFmpeg."""
        if len(clips) == 0:
            raise ValueError("No clips to process")

        if len(clips) == 1:
            # Single clip - just trim and copy
            clip = clips[0]
            cmd = [
                "ffmpeg", "-y",
                "-ss", str(clip["start"]),
                "-i", clip["path"],
                "-t", str(clip["duration"]),
                "-c:v", "libx264", "-preset", "fast",
                "-c:a", "aac",
                output_path
            ]
            subprocess.run(cmd, check=True, capture_output=True)
            return

        # Multiple clips - use xfade
        logger.info(f"Running xfade concat with {len(clips)} clips...")

        # Create temporary trimmed clips
        temp_clips = []
        temp_dir = tempfile.mkdtemp()

        try:
            for i, clip in enumerate(clips):
                temp_path = os.path.join(temp_dir, f"clip_{i}.mp4")
                cmd = [
                    "ffmpeg", "-y",
                    "-ss", str(clip["start"]),
                    "-i", clip["path"],
                    "-t", str(clip["duration"]),
                    "-c:v", "libx264", "-preset", "fast",
                    "-c:a", "aac",
                    "-ar", "44100",
                    "-ac", "2",
                    temp_path
                ]
                subprocess.run(cmd, check=True, capture_output=True)
                temp_clips.append(temp_path)

            # Build xfade filter chain
            if len(temp_clips) == 2:
                # Simple case: two clips
                filter_complex = f"[0:v][1:v]xfade=transition=fade:duration={transition_duration}:offset={clips[0]['duration'] - transition_duration}[v];[0:a][1:a]acrossfade=d={transition_duration}[a]"
                cmd = [
                    "ffmpeg", "-y",
                    "-i", temp_clips[0],
                    "-i", temp_clips[1],
                    "-filter_complex", filter_complex,
                    "-map", "[v]", "-map", "[a]",
                    "-c:v", "libx264", "-preset", "fast",
                    "-c:a", "aac",
                    output_path
                ]
            else:
                # Multiple clips - chain xfades
                inputs = []
                for path in temp_clips:
                    inputs.extend(["-i", path])

                # Build progressive xfade chain
                filter_parts = []
                current_offset = clips[0]["duration"] - transition_duration

                # Video xfades
                filter_parts.append(f"[0:v][1:v]xfade=transition=fade:duration={transition_duration}:offset={current_offset}[v1]")
                for i in range(2, len(temp_clips)):
                    current_offset += clips[i-1]["duration"] - transition_duration
                    prev = f"v{i-1}"
                    curr = f"v{i}" if i < len(temp_clips) - 1 else "v"
                    filter_parts.append(f"[{prev}][{i}:v]xfade=transition=fade:duration={transition_duration}:offset={current_offset}[{curr}]")

                # Audio crossfades
                filter_parts.append(f"[0:a][1:a]acrossfade=d={transition_duration}[a1]")
                for i in range(2, len(temp_clips)):
                    prev = f"a{i-1}"
                    curr = f"a{i}" if i < len(temp_clips) - 1 else "a"
                    filter_parts.append(f"[{prev}][{i}:a]acrossfade=d={transition_duration}[{curr}]")

                filter_complex = ";".join(filter_parts)

                cmd = ["ffmpeg", "-y"] + inputs + [
                    "-filter_complex", filter_complex,
                    "-map", "[v]", "-map", "[a]",
                    "-c:v", "libx264", "-preset", "fast",
                    "-c:a", "aac",
                    output_path
                ]

            subprocess.run(cmd, check=True, capture_output=True)
            logger.info("xfade concat successful")

        finally:
            # Cleanup temp files
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

    def _format_time(self, seconds: float) -> str:
        """Format seconds to MM:SS string."""
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes:02d}:{secs:02d}"
