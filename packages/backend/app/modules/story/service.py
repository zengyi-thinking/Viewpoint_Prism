"""
Story service - Webtoon/Cinematic Blog generation.
"""

import uuid
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional, List
import logging

from app.core import get_settings
from app.shared.perception import get_sophnet_service
from app.shared.storage import get_vector_store

logger = logging.getLogger(__name__)
settings = get_settings()

GENERATED_DIR = settings.resolve_path(settings.upload_dir).parent / "generated"
MANGA_DIR = GENERATED_DIR / "manga"
MANGA_DIR.mkdir(parents=True, exist_ok=True)


class StoryService:
    """Cinematic Blog / Webtoon Generation Service."""

    def __init__(self):
        """Initialize with services."""
        self.sophnet = get_sophnet_service()
        self.tasks: Dict[str, Dict[str, Any]] = {}

    def create_task(self) -> str:
        """Create a new task."""
        task_id = uuid.uuid4().hex[:8]
        self.tasks[task_id] = {
            "status": "pending",
            "progress": 0,
            "message": "Task created",
            "panels": [],
            "total_panels": 0,
            "current_panel": 0,
        }
        return task_id

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task status."""
        return self.tasks.get(task_id)

    def _format_time(self, seconds: float) -> str:
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins}:{secs:02d}"

    def _to_static_url(self, path_value: Optional[str]) -> Optional[str]:
        if not path_value:
            return None
        if path_value.startswith("/static/"):
            return path_value
        path = Path(path_value)
        static_root = settings.resolve_path(settings.upload_dir).parent
        try:
            rel = path.relative_to(static_root).as_posix() if path.is_absolute() else path.as_posix().lstrip("/")
        except Exception:
            return None
        return f"/static/{rel}"

    def _build_panels_from_docs(self, source_id: str, max_panels: int) -> List[Dict[str, Any]]:
        vector_store = get_vector_store()
        docs = vector_store.get_source_documents(source_id)
        visuals = [d for d in docs if d.get("metadata", {}).get("type") == "visual"]
        visuals.sort(key=lambda d: d.get("metadata", {}).get("start", 0))

        panels = []
        for i, doc in enumerate(visuals[:max_panels]):
            meta = doc.get("metadata", {})
            start = float(meta.get("start", 0))
            end = float(meta.get("end", start + 5))
            frame_path = meta.get("frame_path")
            frame_url = self._to_static_url(frame_path)
            if not frame_url:
                continue
            panels.append({
                "panel_number": len(panels) + 1,
                "time": start,
                "time_formatted": self._format_time(start),
                "caption": doc.get("text", "")[:120],
                "characters": "",
                "frame_description": doc.get("text", ""),
                "manga_image_url": frame_url,
                "original_frame_url": frame_url,
                "video_segment": {
                    "source_id": source_id,
                    "start": start,
                    "end": end,
                },
            })
        return panels

    def _fallback_panels_from_frames(self, source_id: str, max_panels: int) -> List[Dict[str, Any]]:
        temp_dir = settings.resolve_path(settings.temp_dir) / source_id / "frames"
        frame_paths = sorted(temp_dir.glob("frame_*.jpg"))[:max_panels]
        panels = []
        for i, frame_path in enumerate(frame_paths):
            start = float(i * 5)
            frame_url = self._to_static_url(str(frame_path))
            if not frame_url:
                continue
            panels.append({
                "panel_number": len(panels) + 1,
                "time": start,
                "time_formatted": self._format_time(start),
                "caption": f"场景 {i + 1}",
                "characters": "",
                "frame_description": "",
                "manga_image_url": frame_url,
                "original_frame_url": frame_url,
                "video_segment": {
                    "source_id": source_id,
                    "start": start,
                    "end": start + 5,
                },
            })
        return panels

    async def _build_blog_sections(self, source_id: str, panels: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        vector_store = get_vector_store()
        docs = vector_store.get_source_documents(source_id)
        transcripts = [d for d in docs if d.get("metadata", {}).get("type") == "transcript"]
        transcripts.sort(key=lambda d: d.get("metadata", {}).get("start", 0))
        combined = " ".join([t.get("text", "") for t in transcripts[:20]])

        if not combined.strip():
            return [{"type": "text", "content": "暂无转写内容，以下为关键画面摘要。"}]

        prompt = f"""请基于以下转写内容生成简短的电影博客段落（3-5段），每段不超过80字。只输出JSON数组，每项包含: type, content。\n\n内容:\n{combined}\n"""
        response = await self.sophnet.chat(
            messages=[{"role": "user", "content": prompt}],
            model="DeepSeek-V3.2",
        )
        if response.strip() == "API key not configured":
            return [{"type": "text", "content": combined[:200]}]

        try:
            import json
            cleaned = response.strip()
            if cleaned.startswith("```"):
                lines = cleaned.split("\n")
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].startswith("```"):
                    lines = lines[:-1]
                cleaned = "\n".join(lines).strip()
            sections = json.loads(cleaned)
            if isinstance(sections, list):
                return sections
        except Exception:
            pass

        return [{"type": "text", "content": combined[:200]}]

    async def generate_webtoon(
        self,
        task_id: str,
        source_id: str,
        max_panels: int = 8,
    ):
        """Generate webtoon panels from video."""
        try:
            self.tasks[task_id].update(
                status="extracting",
                progress=10,
                message="正在提取关键帧...",
                total_panels=max_panels,
            )

            panels = self._build_panels_from_docs(source_id, max_panels)
            if not panels:
                panels = self._fallback_panels_from_frames(source_id, max_panels)

            for i, panel in enumerate(panels, 1):
                self.tasks[task_id].update(
                    status="drawing",
                    progress=10 + int(80 * i / max_panels),
                    message=f"正在绘制第 {i}/{max_panels} 格...",
                    current_panel=i,
                    panels=panels[:i],
                )
                await asyncio.sleep(0.1)

            self.tasks[task_id].update(
                status="writing",
                progress=95,
                message="正在生成博客文案...",
                panels=panels,
                blog_title=f"故事流 - {source_id[:8]}",
                blog_sections=await self._build_blog_sections(source_id, panels),
            )

            self.tasks[task_id].update(
                status="completed",
                progress=100,
                message="故事流生成完成！",
                panels=panels,
                current_panel=max_panels,
            )

        except Exception as e:
            logger.error(f"Webtoon generation failed: {e}")
            self.tasks[task_id].update(
                status="error",
                progress=0,
                message=str(e),
                error=str(e),
            )


_story_service: Optional[StoryService] = None


def get_story_service() -> StoryService:
    """Get or create StoryService singleton."""
    global _story_service
    if _story_service is None:
        _story_service = StoryService()
    return _story_service
