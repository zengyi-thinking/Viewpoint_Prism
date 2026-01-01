"""Director Service - AI Video Director with Dynamic Audio Narrative."""
import asyncio
import uuid
import subprocess
import logging
import json
import re
from pathlib import Path
from typing import Dict, Any, Optional, List

from app.core import get_settings
from app.services.vector_store import get_vector_store

logger = logging.getLogger(__name__)
settings = get_settings()

GENERATED_DIR = Path(settings.upload_dir).parent / "generated"
GENERATED_DIR.mkdir(parents=True, exist_ok=True)

# Persona configurations
PERSONA_CONFIGS = {
    "hajimi": {
        "name": "哈基米",
        "description": "你是一只可爱的猫娘解说，喜欢用'喵~'结尾，语气活泼激萌，称呼观众为'铲屎官们'。",
        "voice": "zh-CN-XiaoxiaoNeural",
        "rate": "+25%",
        "pitch": "+15Hz",
        "emoji": "🐱",
    },
    "wukong": {
        "name": "大圣",
        "description": "你是齐天大圣孙悟空，喜欢用'俺老孙'自称，语气狂傲不羁，火眼金睛，充满战斗气息。",
        "voice": "zh-CN-YunxiNeural",
        "rate": "+10%",
        "pitch": "-5Hz",
        "emoji": "🐵",
    },
    "pro": {
        "name": "专业解说",
        "description": "你是专业的电竞/剧情分析师，语气冷静客观，注重数据和逻辑，用词精准专业。",
        "voice": "zh-CN-YunyangNeural",
        "rate": "+0%",
        "pitch": "+0Hz",
        "emoji": "🎙️",
    },
}


class SequenceSegment:
    """Represents a segment in the director's sequence."""

    def __init__(
        self,
        source: str,  # 'A', 'B', 'intro', 'outro'
        start_hint: float,
        duration: float,
        audio_mode: str,  # 'original' or 'voiceover'
        narration: str = "",
        subtitle: str = "",
        rationale: str = "",
        exact_start: float = None,
    ):
        self.source = source
        self.start_hint = start_hint
        self.duration = duration
        self.audio_mode = audio_mode
        self.narration = narration
        self.subtitle = subtitle
        self.rationale = rationale
        self.exact_start = exact_start if exact_start is not None else start_hint


class DirectorService:
    """AI Director Service for dynamic audio narrative video generation."""

    def __init__(self):
        self.api_key = settings.modelscope_api_key
        self._tasks: Dict[str, Dict[str, Any]] = {}

    async def generate_narrative_script(
        self,
        conflict_data: Dict[str, Any],
        persona: str,
        asr_data_a: List[Dict[str, Any]] = None,
        asr_data_b: List[Dict[str, Any]] = None,
    ) -> List[SequenceSegment]:
        """Generate a narrative script with the Director's brain."""
        persona_config = PERSONA_CONFIGS.get(persona, PERSONA_CONFIGS["pro"])
        view_a = conflict_data.get("viewpoint_a", {})
        view_b = conflict_data.get("viewpoint_b", {})

        # Format ASR context
        asr_context_a = self._format_asr_context(asr_data_a, "A", max_items=10)
        asr_context_b = self._format_asr_context(asr_data_b, "B", max_items=10)

        prompt = f"""你是一个拥有百万粉丝的视频解说导演。
当前人设是：{persona_config['description']}

基于两个视频的内容和冲突点，编排一个 60-90秒 的短视频脚本。

## 冲突主题
{conflict_data.get('topic', '观点对比')}

## 红方观点 (Source A)
标题: {view_a.get('title', '观点A')}
描述: {view_a.get('description', '')}
{asr_context_a}

## 蓝方观点 (Source B)
标题: {view_b.get('title', '观点B')}
描述: {view_b.get('description', '')}
{asr_context_b}

## 输出要求
请输出一个 JSON 数组，包含 6-10 个片段。每个片段包含：
- source: "A" 或 "B" 或 "intro" (开场) 或 "outro" (结束)
- start_hint: 视频中的大致时间点(秒数，数字)
- duration: 片段时长(5-10秒，数字)
- audio_mode: "original" (保留原声用于精彩时刻) 或 "voiceover" (AI解说用于介绍/转场/总结)
- narration: 如果是 voiceover 模式，写出解说词（必须符合人设风格）；如果是 original 模式，留空字符串
- subtitle: 画面底部显示的字幕内容(精简版，10-20字)
- rationale: 导演备注，为什么选这段(内部参考)

请直接输出 JSON:"

        try:
            from openai import OpenAI

            client = OpenAI(
                api_key=self.api_key,
                base_url="https://api-inference.modelscope.cn/v1",
            )

            response = client.chat.completions.create(
                model="Qwen/Qwen2.5-72B-Instruct",
                messages=[
                    {"role": "system", "content": f"你是一个专业的视频导演AI。{persona_config['description']}"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=2000,
                temperature=0.7,
            )

            content = response.choices[0].message.content.strip()
            sequence = self._parse_sequence_json(content, persona_config)
            return sequence

        except Exception as e:
            logger.error(f"Director script generation error: {e}")
            return self._create_fallback_sequence(conflict_data, persona_config)

    def _format_asr_context(
        self,
        asr_data: List[Dict[str, Any]],
        source_label: str,
        max_items: int = 10
    ) -> str:
        """Format ASR data for context."""
        if not asr_data:
            return f"(Source {source_label} ASR数据暂不可用)"

        lines = []
        for item in asr_data[:max_items]:
            start = item.get("start", 0)
            text = item.get("text", "")
            if text.strip():
                lines.append(f"[{start:.1f}s] {text}")

        if lines:
            return f"### ASR 内容片段\n" + "\n".join(lines)
        return f"(Source {source_label} ASR数据为空)"

    def _parse_sequence_json(
        self,
        content: str,
        persona_config: Dict[str, Any]
    ) -> List[SequenceSegment]:
        """Parse JSON sequence from LLM response."""
        json_match = re.search(r'[[\s\S]*\]', content)
        if not json_match:
            return []

        try:
            data = json.loads(json_match.group())
            segments = []

            for item in data:
                segments.append(SequenceSegment(
                    source=item.get("source", "A"),
                    start_hint=float(item.get("start_hint", 0)),
                    duration=float(item.get("duration", 8)),
                    audio_mode=item.get("audio_mode", "voiceover"),
                    narration=item.get("narration", ""),
                    subtitle=item.get("subtitle", ""),
                    rationale=item.get("rationale", ""),
                ))

            return segments

        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}")
            return []

    def _create_fallback_sequence(
        self,
        conflict_data: Dict[str, Any],
        persona_config: Dict[str, Any]
    ) -> List[SequenceSegment]:
        """Create fallback sequence when LLM fails."""
        view_a = conflict_data.get("viewpoint_a", {})
        view_b = conflict_data.get("viewpoint_b", {})

        intro_narration = ""
        outro_narration = ""

        if persona_config.get("name") == "哈基米":
            intro_narration = f"喵~铲屎官们好呀！今天给大家带来一场精彩的对决，红方说{view_a.get('title', '这样')}，蓝方说{view_b.get('title', '那样')}，到底谁更厉害呢？喵~"
            outro_narration = f"好啦铲屎官们，今天的对决就到这里喵~记得点赞关注哦！喵喵~"
        elif persona_config.get("name") == "大圣":
            intro_narration = f"哼！俺老孙来也！今日这场对决，红方主张{view_a.get('title', '硬刚')}，蓝方坚持{view_b.get('title', '智取')}，看俺老孙给你们评评理！"
            outro_narration = f"呔！这场对决，俺老孙看得分明。诸位好自为之！"
        else:
            intro_narration = f"各位观众好，今天我们来分析一场观点对决。红方认为{view_a.get('title', '观点A')}，蓝方则主张{view_b.get('title', '观点B')}。让我们来看看各自的论据。"
            outro_narration = f"以上就是本期的对比分析。两种观点各有道理，关键在于具体场景的适用性。感谢观看。"

        return [
            SequenceSegment("intro", 0, 8, "voiceover", intro_narration, "观点对决开始", "开场介绍冲突背景"),
            SequenceSegment("A", view_a.get("timestamp", 5) or 5, 10, "original", "", view_a.get("title", "红方观点"), "展示红方核心观点原声"),
            SequenceSegment("B", view_b.get("timestamp", 10) or 10, 10, "original", "", view_b.get("title", "蓝方观点"), "展示蓝方核心观点原声"),
            SequenceSegment("outro", 0, 8, "voiceover", outro_narration, "感谢观看", "总结收尾"),
        ]

    async def generate_persona_speech(
        self,
        text: str,
        persona: str,
        output_path: Path,
    ) -> bool:
        """Generate TTS speech with persona-specific voice settings."""
        persona_config = PERSONA_CONFIGS.get(persona, PERSONA_CONFIGS["pro"])

        try:
            import edge_tts

            communicate = edge_tts.Communicate(
                text,
                persona_config["voice"],
                rate=persona_config["rate"],
                pitch=persona_config["pitch"],
            )
            await communicate.save(str(output_path))

            logger.info(f"Persona speech generated ({persona}): {output_path}")
            return True

        except Exception as e:
            logger.error(f"Persona TTS error ({persona}): {e}")
            return False

    async def compose_director_cut(
        self,
        sequence: List[SequenceSegment],
        source_a_path: Path,
        source_b_path: Path,
        voiceover_paths: Dict[int, Path],
        output_path: Path,
    ) -> bool:
        """Compose director cut video with dynamic audio mixing."""
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)

            temp_dir = GENERATED_DIR / f"temp_director_{uuid.uuid4().hex[:8]}"
            temp_dir.mkdir(parents=True, exist_ok=True)

            processed_clips = []

            for i, segment in enumerate(sequence):
                logger.info(f"Processing segment {i+1}/{len(sequence)}: {segment.source} @ {segment.start_hint}s")

                if segment.source in ("intro", "outro"):
                    source_path = source_a_path
                    start_time = 0 if segment.source == "intro" else max(0, segment.start_hint)
                elif segment.source == "A":
                    source_path = source_a_path
                    start_time = segment.exact_start
                else:
                    source_path = source_b_path
                    start_time = segment.exact_start

                clip_output = temp_dir / f"clip_{i:03d}.mp4"

                if segment.audio_mode == "original":
                    success = await self._process_original_segment(
                        source_path=source_path,
                        start_time=start_time,
                        duration=segment.duration,
                        subtitle=segment.subtitle,
                        output_path=clip_output,
                    )
                else:
                    voiceover_path = voiceover_paths.get(i)
                    success = await self._process_voiceover_segment(
                        source_path=source_path,
                        start_time=start_time,
                        duration=segment.duration,
                        subtitle=segment.subtitle,
                        voiceover_path=voiceover_path,
                        output_path=clip_output,
                    )

                if success and clip_output.exists():
                    processed_clips.append(str(clip_output))

            if not processed_clips:
                logger.error("No clips were processed successfully")
                return False

            final_success = await self._concatenate_clips(
                clips=processed_clips,
                output_path=output_path,
                temp_dir=temp_dir,
            )

            # Cleanup
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

            return final_success

        except Exception as e:
            logger.error(f"Director cut composition error: {e}")
            return False

    async def _process_original_segment(
        self,
        source_path: Path,
        start_time: float,
        duration: float,
        subtitle: str,
        output_path: Path,
    ) -> bool:
        """Process segment keeping original audio."""
        try:
            safe_subtitle = self._escape_ffmpeg_text(subtitle)

            filter_complex = (
                f"scale=1280:720:force_original_aspect_ratio=decrease,"
                f"pad=1280:720:(ow-iw)/2:(oh-ih)/2:black,"
                f"drawbox=x=0:y=ih-60:w=iw:h=60:color=black@0.6:t=fill,"
                f"drawtext=text='{safe_subtitle}':"
                f"fontsize=28:fontcolor=white:x=(w-text_w)/2:y=h-45:"
                f"borderw=2:bordercolor=black"
            )

            cmd = [
                "ffmpeg", "-y",
                "-ss", str(start_time),
                "-i", str(source_path),
                "-t", str(duration),
                "-vf", filter_complex,
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "23",
                "-c:a", "aac",
                "-b:a", "128k",
                str(output_path)
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            return result.returncode == 0

        except Exception as e:
            logger.error(f"Original segment processing error: {e}")
            return False

    async def _process_voiceover_segment(
        self,
        source_path: Path,
        start_time: float,
        duration: float,
        subtitle: str,
        voiceover_path: Optional[Path],
        output_path: Path,
    ) -> bool:
        """Process segment with ducked original audio and voiceover."""
        try:
            safe_subtitle = self._escape_ffmpeg_text(subtitle)

            video_filter = (
                f"scale=1280:720:force_original_aspect_ratio=decrease,"
                f"pad=1280:720:(ow-iw)/2:(oh-ih)/2:black,"
                f"drawbox=x=0:y=ih-60:w=iw:h=60:color=black@0.6:t=fill,"
                f"drawtext=text='{safe_subtitle}':"
                f"fontsize=28:fontcolor=white:x=(w-text_w)/2:y=h-45:"
                f"borderw=2:bordercolor=black"
            )

            if voiceover_path and voiceover_path.exists():
                audio_filter = (
                    f"[0:a]atrim=start={start_time}:duration={duration},asetpts=PTS-STARTPTS,volume=0.1[bg];"
                    f"[1:a]volume=1.5[vo];"
                    f"[bg][vo]amix=inputs=2:duration=longest[audio]"
                )

                cmd = [
                    "ffmpeg", "-y",
                    "-ss", str(start_time),
                    "-i", str(source_path),
                    "-i", str(voiceover_path),
                    "-filter_complex", f"[0:v]{video_filter}[video];{audio_filter}",
                    "-map", "[video]",
                    "-map", "[audio]",
                    "-c:v", "libx264",
                    "-preset", "fast",
                    "-crf", "23",
                    "-c:a", "aac",
                    "-b:a", "128k",
                    str(output_path)
                ]
            else:
                cmd = [
                    "ffmpeg", "-y",
                    "-ss", str(start_time),
                    "-i", str(source_path),
                    "-t", str(duration),
                    "-vf", video_filter,
                    "-af", "volume=0.3",
                    "-c:v", "libx264",
                    "-preset", "fast",
                    "-crf", "23",
                    "-c:a", "aac",
                    "-b:a", "128k",
                    str(output_path)
                ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            return result.returncode == 0

        except Exception as e:
            logger.error(f"Voiceover segment processing error: {e}")
            return False

    async def _concatenate_clips(
        self,
        clips: List[str],
        output_path: Path,
        temp_dir: Path,
    ) -> bool:
        """Concatenate clips."""
        try:
            concat_file = temp_dir / "concat.txt"
            with open(concat_file, "w", encoding="utf-8") as f:
                for clip_path in clips:
                    abs_path = str(Path(clip_path).absolute()).replace(chr(92), '/')
                    f.write(f"file '{abs_path}'\n")

            cmd = [
                "ffmpeg", "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", str(concat_file.absolute()),
                "-c", "copy",
                str(output_path.absolute())
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            return result.returncode == 0

        except Exception as e:
            logger.error(f"Concatenation error: {e}")
            return False

    def _escape_ffmpeg_text(self, text: str) -> str:
        """Escape special characters for FFmpeg drawtext filter."""
        if not text:
            return ""
        text = text.replace("\\", "\\\\")
        text = text.replace("'", "\\'")
        text = text.replace(":", "\\:")
        text = text.replace("%", "\\%")
        return text

    async def get_asr_data(self, source_id: str) -> List[Dict[str, Any]]:
        """Get ASR data for a source from vector store."""
        try:
            vector_store = get_vector_store()
            results = vector_store.search(
                query="",
                n_results=50,
                filter_dict={"source_id": source_id, "chunk_type": "asr"},
            )

            asr_data = []
            for result in results:
                metadata = result.get("metadata", {})
                asr_data.append({
                    "start": metadata.get("start", 0),
                    "end": metadata.get("end", 0),
                    "text": result.get("document", ""),
                })

            asr_data.sort(key=lambda x: x["start"])
            return asr_data

        except Exception as e:
            logger.error(f"Failed to get ASR data: {e}")
            return []

    async def create_director_cut(
        self,
        task_id: str,
        conflict_data: Dict[str, Any],
        source_a_id: str,
        source_a_path: Path,
        time_a: float,
        source_b_id: str,
        source_b_path: Path,
        time_b: float,
        persona: str = "pro",
    ) -> Dict[str, Any]:
        """Full pipeline to create a director cut video."""
        persona_config = PERSONA_CONFIGS.get(persona, PERSONA_CONFIGS["pro"])

        try:
            # Step 1: Generate narrative script
            self._tasks[task_id] = {
                "status": "generating_script",
                "progress": 10,
                "message": f"🎬 {persona_config['emoji']} 导演正在编写剧本...",
            }

            asr_data_a = await self.get_asr_data(source_a_id)
            asr_data_b = await self.get_asr_data(source_b_id)

            conflict_data["viewpoint_a"]["timestamp"] = time_a
            conflict_data["viewpoint_b"]["timestamp"] = time_b

            sequence = await self.generate_narrative_script(
                conflict_data=conflict_data,
                persona=persona,
                asr_data_a=asr_data_a,
                asr_data_b=asr_data_b,
            )

            if not sequence:
                raise Exception("剧本生成失败")

            # Step 2: Generate voiceovers
            self._tasks[task_id] = {
                "status": "generating_voiceover",
                "progress": 30,
                "message": f"🎤 {persona_config['name']}正在录制解说...",
            }

            voiceover_paths = {}
            voiceover_dir = GENERATED_DIR / f"voiceover_{task_id}"
            voiceover_dir.mkdir(parents=True, exist_ok=True)

            for i, segment in enumerate(sequence):
                if segment.audio_mode == "voiceover" and segment.narration:
                    vo_path = voiceover_dir / f"vo_{i:03d}.mp3"
                    success = await self.generate_persona_speech(
                        text=segment.narration,
                        persona=persona,
                        output_path=vo_path,
                    )
                    if success:
                        voiceover_paths[i] = vo_path

            # Step 3: Compose video
            self._tasks[task_id] = {
                "status": "composing_video",
                "progress": 50,
                "message": f"🎬 正在后期合成...",
            }

            output_path = GENERATED_DIR / f"director_{task_id}.mp4"
            compose_success = await self.compose_director_cut(
                sequence=sequence,
                source_a_path=source_a_path,
                source_b_path=source_b_path,
                voiceover_paths=voiceover_paths,
                output_path=output_path,
            )

            # Cleanup voiceover files
            import shutil
            shutil.rmtree(voiceover_dir, ignore_errors=True)

            if not compose_success:
                raise Exception("视频合成失败")

            video_url = f"/static/generated/director_{task_id}.mp4"

            script_summary = " → ".join([
                f"{s.source}({'🔊' if s.audio_mode == 'original' else '🎤'})"
                for s in sequence
            ])

            self._tasks[task_id] = {
                "status": "completed",
                "progress": 100,
                "message": f"✨ {persona_config['name']}导演作品完成！",
                "video_url": video_url,
                "script": script_summary,
                "persona": persona,
                "persona_name": persona_config["name"],
                "segment_count": len(sequence),
            }

            return self._tasks[task_id]

        except Exception as e:
            logger.error(f"Create director cut error: {e}")
            self._tasks[task_id] = {
                "status": "error",
                "progress": 0,
                "message": f"生成失败: {str(e)}",
                "error": str(e),
            }
            return self._tasks[task_id]

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        return self._tasks.get(task_id)

    def create_task(self) -> str:
        task_id = str(uuid.uuid4())[:8]
        self._tasks[task_id] = {
            "status": "pending",
            "progress": 0,
            "message": "等待开始...",
        }
        return task_id


# Singleton
_director_service = None


def get_director_service() -> DirectorService:
    global _director_service
    if _director_service is None:
        _director_service = DirectorService()
    return _director_service
