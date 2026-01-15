"""
Debate service - AI-powered debate video generation.
"""

import uuid
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional
import logging
import asyncio

from app.core import get_settings
from app.shared.perception import get_sophnet_service

logger = logging.getLogger(__name__)
settings = get_settings()

GENERATED_DIR = settings.resolve_path(settings.upload_dir).parent / "generated"


class DebateService:
    """AI Debate Video Generator Service."""

    def __init__(self):
        """Initialize with services."""
        self.sophnet = get_sophnet_service()
        self._tasks: Dict[str, Dict[str, Any]] = {}

    def create_task(self) -> str:
        """Create a new task."""
        task_id = uuid.uuid4().hex[:8]
        self._tasks[task_id] = {
            "status": "pending",
            "progress": 0,
            "message": "Task created",
        }
        return task_id

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task status."""
        return self._tasks.get(task_id)

    async def generate_script(self, conflict_data: Dict[str, Any]) -> str:
        """Generate debate script using LLM."""
        view_a = conflict_data.get("viewpoint_a", {})
        view_b = conflict_data.get("viewpoint_b", {})

        prompt = f"""作为热血电竞解说员，基于这两个对立观点：
[红方: {view_a.get('title', '观点A')} - {view_a.get('description', '')}]
vs
[蓝方: {view_b.get('title', '观点B')} - {view_b.get('description', '')}]

请写一段30-50字的激昂开场白，介绍这场风格对决。要求口语化、有悬念。"""

        try:
            script = await self.sophnet.chat(
                messages=[
                    {"role": "system", "content": "你是一个专业的电竞解说员，风格热血激昂。"},
                    {"role": "user", "content": prompt}
                ],
                model="DeepSeek-V3.2",
                max_tokens=200,
                temperature=0.8,
            )
            return script.strip()
        except Exception as e:
            logger.error(f"Script generation error: {e}")
            return f"欢迎来到今天的对决！红方主张{view_a.get('title', '硬刚')}，蓝方坚持{view_b.get('title', '智取')}，谁能笑到最后？"

    async def create_debate_video(
        self,
        task_id: str,
        conflict_data: Dict[str, Any],
        source_a_path: Path,
        time_a: float,
        source_b_path: Path,
        time_b: float,
    ):
        """Create debate video with split-screen composition."""
        try:
            self._tasks[task_id].update(status="generating_script", progress=20, message="生成解说脚本...")

            script = await self.generate_script(conflict_data)
            self._tasks[task_id]["script"] = script

            self._tasks[task_id].update(status="generating_voiceover", progress=40, message="生成语音...")

            self._tasks[task_id].update(status="composing_video", progress=60, message="合成视频中...")

            GENERATED_DIR.mkdir(parents=True, exist_ok=True)
            output_path = GENERATED_DIR / f"debate_{task_id}.mp4"

            duration_a = 10.0
            duration_b = 10.0

            cmd = [
                "ffmpeg", "-y",
                "-i", str(source_a_path),
                "-i", str(source_b_path),
                "-ss", str(time_a),
                "-t", str(duration_a),
                "-ss", str(time_b),
                "-t", str(duration_b),
                "-filter_complex", "[0:v]pad=w=2*iw:h=ih[a];[a][1:v]overlay=w=2*iw[b];[b]concat=v=0:a=0",
                "-c:v", "libx264",
                "-preset", "fast",
                str(output_path),
            ]

            try:
                result = subprocess.run(cmd, capture_output=True, timeout=300)
                if result.returncode == 0:
                    video_url = f"/static/generated/debate_{task_id}.mp4"
                    self._tasks[task_id].update(
                        status="completed",
                        progress=100,
                        message="辩论视频生成完成！",
                        video_url=video_url,
                    )
                else:
                    self._tasks[task_id].update(
                        status="error",
                        progress=0,
                        message=f"视频合成失败: {result.stderr.decode()[:200]}",
                    )
            except FileNotFoundError:
                self._tasks[task_id].update(
                    status="error",
                    progress=0,
                    message="ffmpeg 未安装，无法合成视频",
                )

        except Exception as e:
            logger.error(f"Debate generation failed: {e}")
            self._tasks[task_id].update(status="error", progress=0, message=str(e))


_debate_service: Optional[DebateService] = None


def get_debate_service() -> DebateService:
    """Get or create DebateService singleton."""
    global _debate_service
    if _debate_service is None:
        _debate_service = DebateService()
    return _debate_service
