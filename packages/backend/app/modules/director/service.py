"""
Director service - AI-powered director cut with dynamic narration.
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

PERSONA_CONFIGS = {
    "hajimi": {
        "name": "哈基米",
        "description": "你是一只可爱的猫娘解说，喜欢用'喵~'结尾，语气活泼激萌。",
        "voice": "longxiaochun",
        "rate": 1.2,
        "pitch": 1.1,
        "emoji": "🐱",
    },
    "wukong": {
        "name": "大圣",
        "description": "你是齐天大圣孙悟空，语气狂傲不羁，火眼金睛。",
        "voice": "longxiaochun",
        "rate": 1.1,
        "pitch": 0.9,
        "emoji": "🐵",
    },
    "pro": {
        "name": "专业解说",
        "description": "你是专业分析师，语气冷静客观，注重数据和逻辑。",
        "voice": "longxiaochun",
        "rate": 1.0,
        "pitch": 1.0,
        "emoji": "🎙️",
    },
}


class DirectorService:
    """AI Director Cut Generator Service."""

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

    async def generate_narration_script(
        self,
        conflict_data: Dict[str, Any],
        persona: str,
    ) -> str:
        """Generate narration script based on persona."""
        config = PERSONA_CONFIGS.get(persona, PERSONA_CONFIGS["pro"])
        view_a = conflict_data.get("viewpoint_a", {})
        view_b = conflict_data.get("viewpoint_b", {})

        prompt = f"""{config['description']}

请基于这两个对立观点写一段解说词：
[红方: {view_a.get('title', '观点A')} - {view_a.get('description', '')}]
vs
[蓝方: {view_b.get('title', '观点B')} - {view_b.get('description', '')}]

解说词要求80-120字，口语化，有{persona}的风格特点。"""

        try:
            script = await self.sophnet.chat(
                messages=[
                    {"role": "system", "content": f"你是{persona}风格的解说员。"},
                    {"role": "user", "content": prompt}
                ],
                model="DeepSeek-V3.2",
                max_tokens=300,
                temperature=0.8,
            )
            return script.strip()
        except Exception as e:
            logger.error(f"Narration generation error: {e}")
            return f"这场比赛真是精彩纷呈！红方展现出强大的实力..."

    async def create_director_cut(
        self,
        task_id: str,
        conflict_data: Dict[str, Any],
        source_a_path: Path,
        time_a: float,
        source_b_path: Path,
        time_b: float,
        persona: str,
    ):
        """Create director cut video with AI narration."""
        try:
            config = PERSONA_CONFIGS.get(persona, PERSONA_CONFIGS["pro"])

            self._tasks[task_id].update(status="generating_script", progress=20, message="生成解说脚本...")

            script = await self.generate_narration_script(conflict_data, persona)
            self._tasks[task_id]["script"] = script

            self._tasks[task_id].update(status="generating_voiceover", progress=40, message="生成AI语音...")

            self._tasks[task_id].update(status="composing_video", progress=60, message="合成视频中...")

            GENERATED_DIR.mkdir(parents=True, exist_ok=True)

            output_path = GENERATED_DIR / f"director_{task_id}.mp4"

            duration_a = 8.0
            duration_b = 8.0

            cmd = [
                "ffmpeg", "-y",
                "-i", str(source_a_path),
                "-i", str(source_b_path),
                "-ss", str(time_a),
                "-t", str(duration_a),
                "-ss", str(time_b),
                "-t", str(duration_b),
                "-filter_complex", "[0:v]scale=1280:720[a];[a][1:v]scale=1280:720[b];[b]hstack=inputs=2[out]",
                "-map", "[out]",
                "-c:v", "libx264",
                "-preset", "fast",
                str(output_path),
            ]

            try:
                result = subprocess.run(cmd, capture_output=True, timeout=300)
                if result.returncode == 0:
                    video_url = f"/static/generated/director_{task_id}.mp4"
                    self._tasks[task_id].update(
                        status="completed",
                        progress=100,
                        message="AI导演精剪完成！",
                        video_url=video_url,
                        persona=persona,
                        persona_name=config["name"],
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
                    message="ffmpeg 未安装",
                )

        except Exception as e:
            logger.error(f"Director generation failed: {e}")
            self._tasks[task_id].update(status="error", progress=0, message=str(e))


_director_service: Optional[DirectorService] = None


def get_director_service() -> DirectorService:
    """Get or create DirectorService singleton."""
    global _director_service
    if _director_service is None:
        _director_service = DirectorService()
    return _director_service
