"""AI Director service with multi-persona support."""
import logging
from typing import Dict, Any, Optional
from pathlib import Path
import subprocess

from app.services.intelligence import get_intelligence_service
from app.core import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


# Persona configurations
PERSONAS = {
    "hajimi": {
        "voice": "zh-CN-XiaoxiaoNeural",
        "rate": "+25%",
        "pitch": "+15Hz",
        "prompt": "你是一只可爱的猫娘解说，喜欢用'喵'结尾，称呼观众为'铲屎官'。"
    },
    "wukong": {
        "voice": "zh-CN-YunxiNeural",
        "rate": "+10%",
        "pitch": "-5Hz",
        "prompt": "你是齐天大圣孙悟空，喜欢用'俺老孙'自称，语气狂傲不羁。"
    },
    "pro": {
        "voice": "zh-CN-YunyangNeural",
        "rate": "+0%",
        "pitch": "+0Hz",
        "prompt": "你是专业的电竞/剧情分析师，语气冷静客观，注重数据和逻辑。"
    }
}


class DirectorService:
    """AI Director Cut service with persona support."""

    def __init__(self):
        self.intel = get_intelligence_service()
        self.generated_dir = Path(settings.generated_dir)
        self.generated_dir.mkdir(parents=True, exist_ok=True)

    async def generate_director_cut(
        self,
        conflict: Dict[str, Any],
        persona: str = "pro",
        task_id: str = ""
    ) -> Dict[str, Any]:
        """Generate AI director cut with persona narration."""

        try:
            # Validate persona
            if persona not in PERSONAS:
                persona = "pro"

            persona_config = PERSONAS[persona]

            # Step 1: Generate sequence
            sequence = await self._generate_sequence(conflict, persona)
            if not sequence:
                return {"error": "Failed to generate sequence"}

            # Step 2: Generate narration script
            script = await self._generate_narration(sequence, persona)
            if not script:
                return {"error": "Failed to generate narration"}

            # Step 3: TTS with persona voice
            audio_path = self.generated_dir / f"director_tts_{task_id}.mp3"
            await self._tts_with_persona(
                script,
                str(audio_path),
                persona_config
            )

            # Step 4: Composite director cut
            output_path = self.generated_dir / f"director_{task_id}.mp4"
            success = self._composite_director_cut(
                sequence,
                str(audio_path),
                str(output_path)
            )

            if success:
                return {
                    "video_url": f"/static/generated/director_{task_id}.mp4",
                    "script": script,
                    "persona": persona,
                    "persona_name": self._get_persona_name(persona)
                }
            else:
                return {"error": "Failed to composite video"}

        except Exception as e:
            logger.error(f"Director cut error: {e}")
            return {"error": str(e)}

    # ============ Private Helpers ============

    async def _generate_sequence(
        self,
        conflict: Dict[str, Any],
        persona: str
    ) -> list:
        """Generate editing sequence."""
        vp_a = conflict.get("viewpoint_a", {})
        vp_b = conflict.get("viewpoint_b", {})

        prompt = f"""你是AI导演。请为以下两个观点片段生成剪辑序列。

片段A: {vp_a.get('source_id', '')} @ {vp_a.get('timestamp', 0)}s
片段B: {vp_b.get('source_id', '')} @ {vp_b.get('timestamp', 0)}s

返回 JSON:
```json
{{
  "sequence": [
    {{"type": "intro", "duration": 3, "audio_mode": "voiceover"}},
    {{"type": "clip", "source_id": "{vp_a.get('source_id')}", "timestamp": {vp_a.get('timestamp', 0)}, "duration": 10, "audio_mode": "original"}},
    {{"type": "clip", "source_id": "{vp_b.get('source_id')}", "timestamp": {vp_b.get('timestamp', 0)}, "duration": 10, "audio_mode": "voiceover"}},
    {{"type": "outro", "duration": 2, "audio_mode": "voiceover"}}
  ]
}}
```
"""

        messages = [{"role": "user", "content": prompt}]
        result = await self.intel.chat_completion(messages)

        if result:
            import json
            content = result.output["choices"][0]["message"]["content"]
            try:
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                data = json.loads(content)
                return data.get("sequence", [])
            except:
                pass

        # Fallback sequence
        return [
            {"type": "intro", "duration": 3, "audio_mode": "voiceover"},
            {"type": "clip", "source_id": vp_a.get("source_id", ""), "timestamp": vp_a.get("timestamp", 0), "duration": 10, "audio_mode": "original"},
            {"type": "clip", "source_id": vp_b.get("source_id", ""), "timestamp": vp_b.get("timestamp", 0), "duration": 10, "audio_mode": "voiceover"},
            {"type": "outro", "duration": 2, "audio_mode": "voiceover"}
        ]

    async def _generate_narration(
        self,
        sequence: list,
        persona: str
    ) -> str:
        """Generate narration script."""
        persona_prompt = PERSONAS[persona]["prompt"]

        prompt = f"""{persona_prompt}

请为以下剪辑序列撰写解说词（总时长30秒）：
{sequence}
"""

        messages = [{"role": "user", "content": prompt}]
        result = await self.intel.chat_completion(messages)

        if result:
            return result.output["choices"][0]["message"]["content"]
        return ""

    async def _tts_with_persona(
        self,
        text: str,
        output_path: str,
        persona_config: Dict
    ):
        """Generate TTS with persona voice settings."""
        try:
            import edge_tts

            voice = persona_config["voice"]
            rate = persona_config.get("rate", "+0%")
            pitch = persona_config.get("pitch", "+0Hz")

            communicate = edge_tts.Communicate(
                text,
                voice,
                rate=rate,
                pitch=pitch
            )
            await communicate.save(output_path)

        except Exception as e:
            logger.error(f"Director TTS error: {e}")

    def _composite_director_cut(
        self,
        sequence: list,
        audio_path: str,
        output_path: str
    ) -> bool:
        """Composite director cut video with dynamic audio mixing."""
        try:
            # For MVP, simple concat
            # Full implementation would handle sequence dynamically
            cmd = [
                "ffmpeg", "-y",
                "-i", audio_path,
                "-f", "lavfi",
                "-i", "color=c=black:s=1280x720:d=25",
                "-c:v", "libx264",
                "-t", "30",
                "-pix_fmt", "yuv420p",
                output_path
            ]

            subprocess.run(cmd, capture_output=True, timeout=120)
            return True

        except Exception as e:
            logger.error(f"Director composite error: {e}")
            return False

    def _get_persona_name(self, persona: str) -> str:
        """Get persona display name."""
        names = {
            "hajimi": "哈基米",
            "wukong": "大圣",
            "pro": "专业解说"
        }
        return names.get(persona, "未知")


# Singleton
_director_service: Optional[DirectorService] = None


def get_director_service() -> DirectorService:
    global _director_service
    if _director_service is None:
        _director_service = DirectorService()
    return _director_service
