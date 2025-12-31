"""Creative video generation service."""
import logging
import subprocess
import os
import uuid
from pathlib import Path
from typing import Dict, Any, Optional
import edge_tts

from app.services.intelligence import get_intelligence_service
from app.core import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class CreatorService:
    """Generate creative videos (debate, supercut, digest)."""

    def __init__(self):
        self.intel = get_intelligence_service()
        self.generated_dir = Path(settings.generated_dir)
        self.generated_dir.mkdir(parents=True, exist_ok=True)

    async def generate_debate(
        self,
        conflict: Dict[str, Any],
        task_id: str
    ) -> Dict[str, Any]:
        """Generate debate video with split-screen."""
        try:
            # Step 1: Generate script
            script = await self._generate_debate_script(conflict)
            if not script:
                return {"error": "Failed to generate script"}

            # Step 2: TTS for narration
            audio_path = self.generated_dir / f"tts_{task_id}.mp3"
            await self._tts_generate(script, str(audio_path))

            # Step 3: Extract video clips
            vp_a = conflict["viewpoint_a"]
            vp_b = conflict["viewpoint_b"]

            clip_a = self._extract_clip(
                vp_a.get("source_id", ""),
                vp_a.get("timestamp", 0),
                15
            )
            clip_b = self._extract_clip(
                vp_b.get("source_id", ""),
                vp_b.get("timestamp", 0),
                15
            )

            if not clip_a or not clip_b:
                return {"error": "Failed to extract clips"}

            # Step 4: Composite video
            output_path = self.generated_dir / f"debate_{task_id}.mp4"
            success = self._composite_debate(
                str(clip_a), str(clip_b),
                str(audio_path), str(output_path),
                vp_a.get("source_id", ""), vp_b.get("source_id", "")
            )

            if success:
                return {"video_url": f"/static/generated/debate_{task_id}.mp4"}
            else:
                return {"error": "Failed to composite video"}

        except Exception as e:
            logger.error(f"Debate generation error: {e}")
            return {"error": str(e)}

    async def generate_supercut(
        self,
        entity_name: str,
        segments: list,
        task_id: str
    ) -> Dict[str, Any]:
        """Generate entity supercut video."""
        try:
            concat_file = self.generated_dir / f"concat_{task_id}.txt"
            output_path = self.generated_dir / f"supercut_{task_id}.mp4"

            # Build concat list with padding
            lines = []
            for seg in segments[:10]:
                source_id = seg.get("source_id", "")
                timestamp = seg.get("timestamp", 0)
                start = max(0, timestamp - 2)
                duration = 4

                # Find video path
                video_path = self._get_video_path(source_id)
                if video_path:
                    lines.append(f"file '{video_path}'")
                    lines.append(f"duration {duration}")

            concat_file.write_text("\n".join(lines))

            # Run concat demuxer
            cmd = [
                "ffmpeg", "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", str(concat_file),
                "-c", "copy",
                str(output_path)
            ]

            subprocess.run(cmd, capture_output=True, timeout=120)

            if output_path.exists():
                return {"video_url": f"/static/generated/supercut_{task_id}.mp4"}
            else:
                return {"error": "Failed to generate supercut"}

        except Exception as e:
            logger.error(f"Supercut error: {e}")
            return {"error": str(e)}

    async def generate_digest(
        self,
        source_id: str,
        events: list,
        include_types: list,
        task_id: str
    ) -> Dict[str, Any]:
        """Generate digest video from filtered events."""
        try:
            filtered_events = [
                e for e in events
                if e.get("type") in include_types
            ]

            if not filtered_events:
                return {"error": "No events match filter"}

            output_path = self.generated_dir / f"digest_{task_id}.mp4"

            # Build filter complex
            filters = []
            inputs = ["-i", self._get_video_path(source_id)]

            for i, event in enumerate(filtered_events[:20]):
                ts = event.get("timestamp", 0)
                start = max(0, ts - 1)
                duration = 5
                filters.append(f"[0:v]trim=start={start}:duration={duration},setpts=PTS-STARTPTS[v{i}]")
                filters.append(f"[0:a]atrim=start={start}:duration={duration},asetpts=PTS-STARTPTS[a{i}]")

            # Concat with fade
            filters.append(f"{''.join([f'[v{i}][a{i}]' for i in range(len(filtered_events))])}concat=n={len(filtered_events)}:v=1:a=1[vout][aout]")
            filters.append("[vout]fade=t=out:st=4:d=0.5[vfinal]")

            filter_complex = ";".join(filters)

            cmd = [
                "ffmpeg", "-y",
                *inputs,
                "-filter_complex", filter_complex,
                "-map", "[vfinal]",
                "-map", "[aout]",
                str(output_path)
            ]

            subprocess.run(cmd, capture_output=True, timeout=300)

            if output_path.exists():
                return {"video_url": f"/static/generated/digest_{task_id}.mp4"}
            else:
                return {"error": "Failed to generate digest"}

        except Exception as e:
            logger.error(f"Digest error: {e}")
            return {"error": str(e)}

    # ============ Private Helpers ============

    async def _generate_debate_script(self, conflict: Dict) -> str:
        """Generate debate commentary script."""
        vp_a = conflict.get("viewpoint_a", {})
        vp_b = conflict.get("viewpoint_b", {})

        prompt = f"""你是专业的电竞解说。请为以下观点分歧写一段30秒的精彩解说。

观点A: {vp_a.get('view', '')}
观点B: {vp_b.get('view', '')}

要求：
- 激情四射，电竞赛事风格
- 客观分析双方优劣
- 字数: 80-100字
"""

        messages = [{"role": "user", "content": prompt}]
        result = await self.intel.chat_completion(messages)

        if result:
            return result.output["choices"][0]["message"]["content"]
        return ""

    async def _tts_generate(self, text: str, output_path: str):
        """Generate TTS audio."""
        try:
            voice = "zh-CN-YunyangNeural"
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(output_path)
        except Exception as e:
            logger.error(f"TTS error: {e}")

    def _extract_clip(self, source_id: str, timestamp: float, duration: int) -> Optional[str]:
        """Extract clip from source."""
        video_path = self._get_video_path(source_id)
        if not video_path:
            return None

        output_path = self.generated_dir / f"clip_{source_id}_{timestamp}.mp4"

        cmd = [
            "ffmpeg", "-y",
            "-ss", str(timestamp),
            "-i", video_path,
            "-t", str(duration),
            "-c", "copy",
            str(output_path)
        ]

        try:
            subprocess.run(cmd, capture_output=True, check=True, timeout=30)
            return str(output_path)
        except:
            return None

    def _composite_debate(
        self,
        clip_a: str, clip_b: str,
        audio: str, output: str,
        label_a: str, label_b: str
    ) -> bool:
        """Composite split-screen debate video."""
        try:
            cmd = [
                "ffmpeg", "-y",
                "-i", clip_a,
                "-i", clip_b,
                "-i", audio,
                "-filter_complex",
                f"[0:v]scale=640:720[v0];[1:v]scale=640:720[v1];[v0][v1]hstack,drawtext=text='{label_a}':x=10:y=H-30:fontsize=24:fontcolor=white,drawtext=text='{label_b}':x=W-150:y=H-30:fontsize=24:fontcolor=white[vout]",
                "-map", "[vout]",
                "-map", "2:a",
                "-c:v", "libx264",
                "-shortest",
                output
            ]

            subprocess.run(cmd, capture_output=True, check=True, timeout=120)
            return True
        except:
            return False

    def _get_video_path(self, source_id: str) -> Optional[str]:
        """Get video file path from source ID."""
        # In real implementation, query from DB
        upload_dir = Path(settings.upload_dir)
        candidates = list(upload_dir.glob(f"{source_id}.*"))
        return str(candidates[0]) if candidates else None


# Singleton
_creator_service: Optional[CreatorService] = None


def get_creator_service() -> CreatorService:
    global _creator_service
    if _creator_service is None:
        _creator_service = CreatorService()
    return _creator_service
