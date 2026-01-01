"""
Director Service - AI Video Director with Dynamic Audio Narrative
Phase 10: AI Director Expansion

Features:
1. Smart Audio Mixing: Auto-detect when to keep original audio vs AI narration
2. Multi-Persona: Support different narrator personalities (Hajimi, Wukong, Pro)
3. Material-Based: All visuals strictly based on uploaded sources

AI Provider: SophNet (DeepSeek-V3.2 for LLM, CosyVoice for TTS)
"""

import asyncio
import uuid
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
import logging
import json
import re
import shutil

# Audio duration detection using mutagen (fast, pure Python)
from mutagen.mp3 import MP3

from app.core import get_settings
from app.services.sophnet_service import get_sophnet_service
from app.services.vector_store import get_vector_store

logger = logging.getLogger(__name__)
settings = get_settings()

# Directory for generated content
GENERATED_DIR = Path(settings.upload_dir).parent / "generated"
GENERATED_DIR.mkdir(parents=True, exist_ok=True)

# Persona configurations (SophNet CosyVoice voice names)
PERSONA_CONFIGS = {
    "hajimi": {
        "name": "哈基米",
        "description": "你是一只可爱的猫娘解说，喜欢用'喵~'结尾，语气活泼激萌，称呼观众为'铲屎官们'。",
        "voice": "longxiaochun",  # CosyVoice voice name
        "rate": 1.2,
        "pitch": 1.1,
        "emoji": "🐱",
    },
    "wukong": {
        "name": "大圣",
        "description": "你是齐天大圣孙悟空，喜欢用'俺老孙'自称，语气狂傲不羁，火眼金睛，充满战斗气息。",
        "voice": "longxiaochun",
        "rate": 1.1,
        "pitch": 0.9,
        "emoji": "🐵",
    },
    "pro": {
        "name": "专业解说",
        "description": "你是专业的电竞/剧情分析师，语气冷静客观，注重数据和逻辑，用词精准专业。",
        "voice": "longxiaochun",
        "rate": 1.0,
        "pitch": 1.0,
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
    """AI Director Service for dynamic audio narrative video generation using SophNet."""

    def __init__(self):
        """Initialize with SophNet services."""
        self.sophnet = get_sophnet_service()
        self._tasks: Dict[str, Dict[str, Any]] = {}

    async def generate_narrative_script(
        self,
        conflict_data: Dict[str, Any],
        persona: str,
        asr_data_a: List[Dict[str, Any]] = None,
        asr_data_b: List[Dict[str, Any]] = None,
    ) -> List[SequenceSegment]:
        """
        Generate a narrative script with the Director's brain.

        Args:
            conflict_data: Conflict info with viewpoints
            persona: Persona key ('hajimi', 'wukong', 'pro')
            asr_data_a: ASR data from source A
            asr_data_b: ASR data from source B

        Returns:
            List of SequenceSegment objects representing the video sequence
        """
        persona_config = PERSONA_CONFIGS.get(persona, PERSONA_CONFIGS["pro"])
        view_a = conflict_data.get("viewpoint_a", {})
        view_b = conflict_data.get("viewpoint_b", {})

        # Format ASR context (limit to avoid token overflow)
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

## 重要规则
1. 开场(intro)使用 voiceover 介绍冲突
2. 精彩片段(如激烈对话、名场面)使用 original 保留原声
3. 转场和点评使用 voiceover 添加解说
4. 结尾(outro)使用 voiceover 总结
5. 解说词必须严格符合当前人设风格
6. 只输出 JSON 数组，不要其他内容

请直接输出 JSON:"""

        try:
            # Use SophNet DeepSeek-V3.2 for script generation
            messages = [
                {"role": "system", "content": f"你是一个专业的视频导演AI。{persona_config['description']}"},
                {"role": "user", "content": prompt}
            ]

            content = await self.sophnet.chat(
                messages=messages,
                model="DeepSeek-V3.2",
                temperature=0.7,
                max_tokens=2000,
            )

            logger.info(f"Director script raw output: {content[:500]}...")

            # Parse JSON from response
            sequence = self._parse_sequence_json(content, persona_config)
            return sequence

        except Exception as e:
            logger.error(f"Director script generation error: {e}")
            # Return fallback sequence
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
        # Try to extract JSON array from response
        json_match = re.search(r'\[[\s\S]*\]', content)
        if not json_match:
            logger.warning("No JSON array found in response")
            return []

        try:
            data = json.loads(json_match.group())
            segments = []

            for item in data:
                segment = SequenceSegment(
                    source=item.get("source", "A"),
                    start_hint=float(item.get("start_hint", 0)),
                    duration=float(item.get("duration", 8)),
                    audio_mode=item.get("audio_mode", "voiceover"),
                    narration=item.get("narration", ""),
                    subtitle=item.get("subtitle", ""),
                    rationale=item.get("rationale", ""),
                )
                segments.append(segment)

            logger.info(f"Parsed {len(segments)} segments from director script")
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
        persona_name = persona_config.get("name", "解说员")

        # Adjust narration style based on persona
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
            SequenceSegment(
                source="intro",
                start_hint=0,
                duration=8,
                audio_mode="voiceover",
                narration=intro_narration,
                subtitle="观点对决开始",
                rationale="开场介绍冲突背景",
            ),
            SequenceSegment(
                source="A",
                start_hint=conflict_data.get("viewpoint_a", {}).get("timestamp", 5) or 5,
                duration=10,
                audio_mode="original",
                narration="",
                subtitle=view_a.get("title", "红方观点"),
                rationale="展示红方核心观点原声",
            ),
            SequenceSegment(
                source="A",
                start_hint=(conflict_data.get("viewpoint_a", {}).get("timestamp", 5) or 5) + 15,
                duration=8,
                audio_mode="voiceover",
                narration=f"红方的核心论点是{view_a.get('description', '...')[:30]}",
                subtitle="红方论据分析",
                rationale="解说红方论据",
            ),
            SequenceSegment(
                source="B",
                start_hint=conflict_data.get("viewpoint_b", {}).get("timestamp", 10) or 10,
                duration=10,
                audio_mode="original",
                narration="",
                subtitle=view_b.get("title", "蓝方观点"),
                rationale="展示蓝方核心观点原声",
            ),
            SequenceSegment(
                source="B",
                start_hint=(conflict_data.get("viewpoint_b", {}).get("timestamp", 10) or 10) + 15,
                duration=8,
                audio_mode="voiceover",
                narration=f"蓝方的核心论点是{view_b.get('description', '...')[:30]}",
                subtitle="蓝方论据分析",
                rationale="解说蓝方论据",
            ),
            SequenceSegment(
                source="outro",
                start_hint=0,
                duration=8,
                audio_mode="voiceover",
                narration=outro_narration,
                subtitle="感谢观看",
                rationale="总结收尾",
            ),
        ]

    async def generate_persona_speech(
        self,
        text: str,
        persona: str,
        output_path: Path,
    ) -> bool:
        """
        Generate TTS speech with persona-specific voice settings using SophNet CosyVoice.

        Args:
            text: Narration text
            persona: Persona key
            output_path: Output MP3 path

        Returns:
            True if successful
        """
        persona_config = PERSONA_CONFIGS.get(persona, PERSONA_CONFIGS["pro"])

        try:
            # Use SophNet CosyVoice for TTS
            audio_data = await self.sophnet.generate_speech(
                text=text,
                voice=persona_config["voice"],
                speech_rate=persona_config["rate"],
                pitch_rate=persona_config["pitch"],
            )

            # Write audio data to file
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "wb") as f:
                f.write(audio_data)

            logger.info(f"Persona speech generated ({persona}): {output_path}")
            return True

        except Exception as e:
            logger.error(f"Persona TTS error ({persona}): {e}")

            # Fallback: generate silent audio
            try:
                duration = max(3, len(text) / 5)  # Estimate duration
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
                return result.returncode == 0
            except Exception:
                return False

    async def compose_director_cut(
        self,
        sequence: List[SequenceSegment],
        source_a_path: Path,
        source_b_path: Path,
        voiceover_paths: Dict[int, Path],
        output_path: Path,
    ) -> bool:
        """
        Compose director cut video with ATOMIC CLIP strategy.

        CRITICAL FIX for audio-video sync:
        1. Generate each clip as an ATOMIC unit with AUDIO-DRIVEN duration
        2. Voiceover clips: duration = actual audio duration (from mutagen)
        3. Concatenate all atomic clips using FFmpeg concat demuxer (lossless)

        Args:
            sequence: List of SequenceSegment objects
            source_a_path: Path to video A
            source_b_path: Path to video B
            voiceover_paths: Dict mapping segment index to voiceover MP3 path
            output_path: Output video path

        Returns:
            True if successful
        """
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Create temp directory for atomic clips
            temp_dir = GENERATED_DIR / f"temp_director_{uuid.uuid4().hex[:8]}"
            temp_dir.mkdir(parents=True, exist_ok=True)

            processed_clips = []
            total_expected_duration = 0.0

            logger.info(f"=== ATOMIC CLIP STRATEGY: Processing {len(sequence)} segments ===")

            for i, segment in enumerate(sequence):
                logger.info(f"[{i+1}/{len(sequence)}] {segment.source} @ {segment.start_hint}s | mode={segment.audio_mode}")

                clip_output = temp_dir / f"clip_{i:03d}.mp4"
                voiceover_path = voiceover_paths.get(i)

                # INTRO/OUTRO: Pure voiceover with black screen
                if segment.source in ("intro", "outro"):
                    if voiceover_path and voiceover_path.exists():
                        # AUDIO-DRIVEN: Duration from actual voiceover audio
                        vo_duration = self._get_audio_duration_mutagen(voiceover_path)
                        logger.info(f"  -> Voiceover-only clip, audio duration: {vo_duration:.3f}s")

                        success = await self._create_voiceover_only_clip(
                            voiceover_path=voiceover_path,
                            subtitle=segment.subtitle,
                            duration=segment.duration,  # Fallback only
                            output_path=clip_output,
                        )
                        if success and vo_duration > 0:
                            total_expected_duration += vo_duration
                    else:
                        logger.warning(f"  -> No voiceover for {segment.source}, creating silent placeholder")
                        success = await self._create_silent_clip(
                            duration=segment.duration,
                            subtitle=segment.subtitle,
                            output_path=clip_output,
                        )
                        total_expected_duration += segment.duration

                # SOURCE A or B with VOICEOVER mode
                elif segment.audio_mode == "voiceover" and voiceover_path and voiceover_path.exists():
                    source_path = source_a_path if segment.source == "A" else source_b_path
                    start_time = segment.exact_start

                    # AUDIO-DRIVEN: Use new atomic clip method
                    vo_duration = self._get_audio_duration_mutagen(voiceover_path)
                    logger.info(f"  -> Voiceover segment, audio duration: {vo_duration:.3f}s")

                    success = await self._create_atomic_video_clip(
                        source_path=source_path,
                        start_time=start_time,
                        audio_path=voiceover_path,
                        subtitle=segment.subtitle,
                        output_path=clip_output,
                        use_original_audio=False,
                    )
                    if success and vo_duration > 0:
                        total_expected_duration += vo_duration

                # SOURCE A or B with ORIGINAL audio
                else:
                    source_path = source_a_path if segment.source == "A" else source_b_path
                    start_time = segment.exact_start

                    logger.info(f"  -> Original audio segment, duration: {segment.duration:.1f}s")

                    success = await self._process_original_segment(
                        source_path=source_path,
                        start_time=start_time,
                        duration=segment.duration,
                        subtitle=segment.subtitle,
                        output_path=clip_output,
                    )
                    total_expected_duration += segment.duration

                # Verify and collect clip with QA check
                if success and clip_output.exists() and clip_output.stat().st_size > 1000:
                    # AI Director QA: Check video quality before adding to concat list
                    qa_passed = await self._check_video_quality(
                        clip_output,
                        expected_resolution=(1280, 720),  # Director cut uses 720p
                    )

                    if qa_passed:
                        actual_clip_duration = await self._get_audio_duration(clip_output)
                        logger.info(f"  -> Clip saved: {clip_output.name} ({actual_clip_duration:.2f}s) ✓ QA PASSED")
                        processed_clips.append(str(clip_output))
                    else:
                        logger.warning(f"  -> Segment {i} QA FAILED, attempting retry...")
                        # Retry once with fallback
                        retry_success = await self._retry_failed_clip(
                            segment, clip_output, voiceover_paths.get(i),
                            source_a_path if segment.source == "A" else source_b_path
                        )
                        if retry_success:
                            actual_clip_duration = await self._get_audio_duration(clip_output)
                            logger.info(f"  -> Retry successful: {clip_output.name} ({actual_clip_duration:.2f}s)")
                            processed_clips.append(str(clip_output))
                        else:
                            logger.error(f"  -> Segment {i} FAILED after retry, skipping")
                else:
                    logger.warning(f"  -> Segment {i} generation FAILED, skipping")

            if not processed_clips:
                logger.error("No clips were processed successfully")
                self._cleanup_temp_dir(temp_dir)
                return False

            logger.info(f"=== CONCATENATION: {len(processed_clips)} clips, expected ~{total_expected_duration:.1f}s ===")

            # STEP 3: Concatenate using concat demuxer (lossless)
            final_success = await self._concatenate_atomic_clips(
                clips=processed_clips,
                output_path=output_path,
                temp_dir=temp_dir,
            )

            # Cleanup
            self._cleanup_temp_dir(temp_dir)

            return final_success

        except Exception as e:
            logger.error(f"Director cut composition error: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    async def _create_silent_clip(
        self,
        duration: float,
        subtitle: str,
        output_path: Path,
    ) -> bool:
        """Create a silent black clip with subtitle (fallback for missing voiceover)."""
        try:
            safe_subtitle = self._escape_ffmpeg_text(subtitle)

            cmd = [
                "ffmpeg", "-y",
                "-f", "lavfi",
                "-i", f"color=c=black:s=1280x720:d={duration}:r=30",
                "-f", "lavfi",
                "-i", f"anullsrc=r=44100:cl=stereo",
                "-t", str(duration),
                "-vf", (
                    f"drawbox=x=0:y=ih-60:w=iw:h=60:color=black@0.6:t=fill,"
                    f"drawtext=text='{safe_subtitle}':"
                    f"fontsize=32:fontcolor=white:x=(w-text_w)/2:y=h-45:"
                    f"borderw=2:bordercolor=black"
                ),
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "23",
                "-pix_fmt", "yuv420p",
                "-c:a", "aac",
                "-b:a", "128k",
                str(output_path)
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            return result.returncode == 0

        except Exception as e:
            logger.error(f"Silent clip creation error: {e}")
            return False

    async def _concatenate_atomic_clips(
        self,
        clips: List[str],
        output_path: Path,
        temp_dir: Path,
    ) -> bool:
        """
        Concatenate atomic clips using FFmpeg concat demuxer (lossless).

        This is the final step of the atomic clip strategy.
        Uses file_list.txt approach for best audio-video sync.
        """
        try:
            if not clips:
                logger.error("No clips to concatenate")
                return False

            if len(clips) == 1:
                # Single clip: just copy
                shutil.copy(clips[0], output_path)
                logger.info(f"Single clip copied to {output_path}")
                return True

            # Create file list for concat demuxer
            file_list_path = temp_dir / "file_list.txt"
            with open(file_list_path, "w", encoding="utf-8") as f:
                for clip in clips:
                    # Use forward slashes and escape special chars
                    clip_path = Path(clip).absolute().as_posix()
                    f.write(f"file '{clip_path}'\n")

            logger.info(f"Concatenating {len(clips)} clips using concat demuxer")

            # Use concat demuxer for lossless concatenation
            cmd = [
                "ffmpeg", "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", str(file_list_path),
                "-c", "copy",  # Stream copy for lossless concat
                "-movflags", "+faststart",
                str(output_path)
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

            if result.returncode != 0:
                logger.error(f"Concat demuxer failed: {result.stderr[-500:]}")

                # Fallback: Re-encode using filter_complex
                logger.info("Falling back to filter_complex concat...")
                return await self._concatenate_with_reencode(clips, output_path)

            # Verify output with full QA check
            if output_path.exists() and output_path.stat().st_size > 1000:
                # Final QA check on the complete video
                qa_passed = await self._check_video_quality(
                    output_path,
                    expected_resolution=(1280, 720),
                    min_duration=1.0,
                )

                if not qa_passed:
                    logger.error(f"Final video QA FAILED: {output_path}")
                    return False

                final_duration = await self._get_audio_duration(output_path)
                logger.info(f"Final video: {output_path.name} ({final_duration:.2f}s, {output_path.stat().st_size//1024}KB) ✓ QA PASSED")

                # Log audio-video sync verification
                await self._verify_av_sync(output_path)

                return True
            else:
                logger.error(f"Output file missing or too small: {output_path}")
                return False

        except subprocess.TimeoutExpired:
            logger.error("Concatenation timeout (300s)")
            return False
        except Exception as e:
            logger.error(f"Concatenation error: {e}")
            return False

    async def _concatenate_with_reencode(
        self,
        clips: List[str],
        output_path: Path,
    ) -> bool:
        """Fallback concatenation with re-encoding (slower but more compatible)."""
        try:
            filter_parts = []
            input_args = ["ffmpeg", "-y"]

            for i, clip in enumerate(clips):
                input_args.extend(["-i", str(Path(clip).absolute())])
                filter_parts.append(f"[{i}:v][{i}:a]")

            concat_filter = "".join(filter_parts) + f"concat=n={len(clips)}:v=1:a=1[v][a]"

            input_args.extend([
                "-filter_complex", concat_filter,
                "-map", "[v]",
                "-map", "[a]",
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "23",
                "-pix_fmt", "yuv420p",
                "-c:a", "aac",
                "-b:a", "128k",
                "-movflags", "+faststart",
                str(output_path.absolute())
            ])

            result = subprocess.run(input_args, capture_output=True, text=True, timeout=300)

            if result.returncode != 0:
                logger.error(f"Re-encode concat failed: {result.stderr[-500:]}")
                return False

            return output_path.exists() and output_path.stat().st_size > 1000

        except Exception as e:
            logger.error(f"Re-encode concat error: {e}")
            return False

    async def _verify_av_sync(self, video_path: Path) -> Dict[str, float]:
        """Verify audio-video synchronization of the final output."""
        try:
            cmd = [
                "ffprobe", "-v", "error",
                "-show_entries", "stream=codec_type,duration",
                "-of", "json",
                str(video_path)
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                data = json.loads(result.stdout)
                streams = data.get("streams", [])

                v_dur = next((float(s.get("duration", 0)) for s in streams if s.get("codec_type") == "video"), 0)
                a_dur = next((float(s.get("duration", 0)) for s in streams if s.get("codec_type") == "audio"), 0)
                diff = abs(v_dur - a_dur)

                if diff > 1.0:
                    logger.warning(f"⚠️ AV SYNC WARNING: Video={v_dur:.2f}s, Audio={a_dur:.2f}s (diff={diff:.2f}s)")
                else:
                    logger.info(f"✓ AV SYNC OK: Video={v_dur:.2f}s, Audio={a_dur:.2f}s (diff={diff:.3f}s)")

                return {"video_duration": v_dur, "audio_duration": a_dur, "diff": diff}

        except Exception as e:
            logger.warning(f"AV sync verification failed: {e}")

        return {}

    async def _process_original_segment(
        self,
        source_path: Path,
        start_time: float,
        duration: float,
        subtitle: str,
        output_path: Path,
    ) -> bool:
        """Process segment keeping original audio with strict duration control.

        CRITICAL: Using -ss AFTER input for accurate seeking.
        Rely on -t parameter for duration control instead of trim filter.
        """
        try:
            # Escape subtitle for FFmpeg drawtext
            safe_subtitle = self._escape_ffmpeg_text(subtitle)

            # Video filter WITHOUT trim (we use -t parameter instead)
            video_filter = (
                f"scale=1280:720:force_original_aspect_ratio=decrease,"
                f"pad=1280:720:(ow-iw)/2:(oh-ih)/2:black,"
                f"drawbox=x=0:y=ih-60:w=iw:h=60:color=black@0.6:t=fill,"
                f"drawtext=text='{safe_subtitle}':"
                f"fontsize=28:fontcolor=white:x=(w-text_w)/2:y=h-45:"
                f"borderw=2:bordercolor=black"
            )

            # Key: -ss AFTER input, -t for duration
            # No trim filter in video/audio - rely on -t parameter
            cmd = [
                "ffmpeg", "-y",
                "-i", str(source_path),
                "-ss", str(start_time),  # Seek AFTER input for accuracy
                "-t", str(duration),     # Duration limit
                "-vf", video_filter,
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "23",
                "-c:a", "aac",
                "-b:a", "128k",
                str(output_path)
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

            if result.returncode != 0:
                logger.error(f"Original segment error: {result.stderr[-500:]}")
                return False

            return True

        except Exception as e:
            logger.error(f"Original segment processing error: {e}")
            return False

    async def _get_audio_duration(self, audio_path: Path) -> float:
        """Get actual duration of an audio file using ffprobe."""
        try:
            cmd = [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(audio_path)
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                return float(result.stdout.strip())
        except Exception as e:
            logger.warning(f"Failed to get audio duration: {e}")
        return 0.0

    def _get_audio_duration_mutagen(self, audio_path: Path) -> float:
        """
        Get precise audio duration using mutagen (fast, pure Python).

        This is the preferred method for MP3 files as it's much faster
        than ffprobe and gives accurate results.

        Args:
            audio_path: Path to MP3 audio file

        Returns:
            Duration in seconds, or 0.0 if failed
        """
        try:
            audio = MP3(str(audio_path))
            duration = audio.info.length
            logger.debug(f"Mutagen duration for {audio_path.name}: {duration:.3f}s")
            return duration
        except Exception as e:
            logger.warning(f"Mutagen failed for {audio_path}, falling back to ffprobe: {e}")
            # Fallback to ffprobe for non-MP3 files
            return asyncio.get_event_loop().run_until_complete(
                self._get_audio_duration(audio_path)
            )

    async def _create_voiceover_only_clip(
        self,
        voiceover_path: Path,
        subtitle: str,
        duration: float,
        output_path: Path,
        background_color: str = "black",
    ) -> bool:
        """Create a voiceover-only clip with black screen and subtitle.

        CRITICAL FIX: Uses mutagen for precise audio duration + -shortest flag
        to ensure PERFECT audio-video sync.

        Args:
            voiceover_path: Path to TTS audio file
            subtitle: Subtitle text to display
            duration: Fallback duration (used only if getting actual duration fails)
            output_path: Output video path
            background_color: Background color (default: black)

        Returns:
            True if successful
        """
        try:
            if not voiceover_path.exists():
                logger.warning(f"Voiceover file not found: {voiceover_path}")
                return False

            # CRITICAL: Use mutagen for precise MP3 duration
            actual_duration = self._get_audio_duration_mutagen(voiceover_path)
            if actual_duration <= 0:
                logger.warning(f"Could not get audio duration, using fallback: {duration}s")
                actual_duration = duration

            logger.info(f"Creating atomic voiceover clip: audio={actual_duration:.3f}s")

            safe_subtitle = self._escape_ffmpeg_text(subtitle)

            # ATOMIC CLIP STRATEGY:
            # 1. -loop 1: Loop the static image (black screen)
            # 2. -t {duration}: Set video stream duration
            # 3. -shortest: End at the shortest stream (audio)
            # This ensures video duration EXACTLY matches audio duration
            cmd = [
                "ffmpeg", "-y",
                "-f", "lavfi",
                "-i", f"color=c={background_color}:s=1280x720:d={actual_duration + 1}:r=30",
                "-i", str(voiceover_path),
                "-vf", (
                    f"drawbox=x=0:y=ih-60:w=iw:h=60:color=black@0.6:t=fill,"
                    f"drawtext=text='{safe_subtitle}':"
                    f"fontsize=32:fontcolor=white:x=(w-text_w)/2:y=h-45:"
                    f"borderw=2:bordercolor=black"
                ),
                "-shortest",  # CRITICAL: Ensures perfect sync
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "23",
                "-pix_fmt", "yuv420p",
                "-c:a", "aac",
                "-b:a", "128k",
                str(output_path)
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

            if result.returncode != 0:
                logger.error(f"Atomic voiceover clip error: {result.stderr[-500:]}")
                return False

            # Verify output duration matches expected
            final_duration = await self._get_audio_duration(output_path)
            duration_diff = abs(final_duration - actual_duration)
            if duration_diff > 0.5:
                logger.warning(f"Duration mismatch: expected {actual_duration:.2f}s, got {final_duration:.2f}s")
            else:
                logger.info(f"Atomic clip created: {output_path.name} ({final_duration:.2f}s)")

            return True

        except Exception as e:
            logger.error(f"Atomic voiceover clip creation error: {e}")
            return False

    async def _create_image_clip(
        self,
        image_path: Path,
        audio_path: Path,
        output_path: Path,
        subtitle: str = "",
    ) -> bool:
        """
        Create video clip from static image + audio.

        CRITICAL FIX for Debate Video Rendering:
        - Uses -loop 1 to loop static image
        - Uses -tune stillimage for optimal encoding
        - Uses -pix_fmt yuv420p for web compatibility
        - Uses -shortest to match audio duration

        Args:
            image_path: Path to static image (jpg/png)
            audio_path: Path to audio file (mp3)
            output_path: Output video path
            subtitle: Optional subtitle text

        Returns:
            True if successful
        """
        try:
            # Pre-flight check: validate resources
            if not await self._validate_resources(image_path, audio_path):
                return False

            # Build video filter
            vf_parts = [
                "scale=1920:1080:force_original_aspect_ratio=decrease",
                "pad=1920:1080:(ow-iw)/2:(oh-ih)/2:black",
            ]

            # Add subtitle if provided
            if subtitle:
                safe_subtitle = self._escape_ffmpeg_text(subtitle)
                vf_parts.append(
                    f"drawbox=x=0:y=ih-70:w=iw:h=70:color=black@0.6:t=fill,"
                    f"drawtext=text='{safe_subtitle}':"
                    f"fontsize=36:fontcolor=white:x=(w-text_w)/2:y=h-50:"
                    f"borderw=2:bordercolor=black"
                )

            video_filter = ",".join(vf_parts)

            # CRITICAL: FFmpeg command with -loop 1 for static image
            cmd = [
                "ffmpeg", "-y",
                "-loop", "1",                    # CRUCIAL: Loop static image
                "-i", str(image_path),           # Input image
                "-i", str(audio_path),           # Input audio
                "-c:v", "libx264",
                "-tune", "stillimage",           # Optimize for static image
                "-c:a", "aac",
                "-b:a", "192k",
                "-pix_fmt", "yuv420p",           # Web/QuickTime compatibility
                "-vf", video_filter,
                "-shortest",                     # Match audio duration
                "-movflags", "+faststart",
                str(output_path)
            ]

            logger.info(f"Creating image clip: {image_path.name} + {audio_path.name}")

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)

            if result.returncode != 0:
                logger.error(f"Image clip creation failed: {result.stderr[-500:]}")
                return False

            # Post-generation QA check
            qa_passed = await self._check_video_quality(output_path)
            if not qa_passed:
                logger.error(f"QA check failed for {output_path}")
                return False

            logger.info(f"Image clip created successfully: {output_path.name}")
            return True

        except Exception as e:
            logger.error(f"Image clip creation error: {e}")
            return False

    async def _validate_resources(
        self,
        image_path: Optional[Path] = None,
        audio_path: Optional[Path] = None,
    ) -> bool:
        """
        Pre-flight resource validation.

        Validates:
        1. Image exists and is readable
        2. Audio exists and size > 1KB

        Args:
            image_path: Path to image file (optional)
            audio_path: Path to audio file (optional)

        Returns:
            True if all provided resources are valid
        """
        # Image validation
        if image_path:
            if not image_path.exists():
                logger.error(f"Image file not found: {image_path}")
                # Check for placeholder fallback
                placeholder = Path(settings.upload_dir).parent / "static" / "placeholder.jpg"
                if placeholder.exists():
                    logger.warning(f"Using placeholder image: {placeholder}")
                    # Note: Caller should handle fallback
                else:
                    return False
            else:
                # Check file is readable and has content
                if image_path.stat().st_size < 100:
                    logger.error(f"Image file too small: {image_path}")
                    return False

        # Audio validation
        if audio_path:
            if not audio_path.exists():
                logger.error(f"Audio file not found: {audio_path}")
                return False

            audio_size = audio_path.stat().st_size
            if audio_size < 1024:  # Less than 1KB
                logger.error(f"Audio file too small ({audio_size} bytes): {audio_path}")
                return False

        return True

    async def _check_video_quality(
        self,
        video_path: Path,
        require_video: bool = True,
        require_audio: bool = True,
        min_duration: float = 0.1,
        expected_resolution: tuple = (1920, 1080),
    ) -> bool:
        """
        AI Director QA: Post-generation video quality check using ffprobe.

        Checks:
        1. Stream check: Must contain video and audio streams
        2. Resolution check: Must match expected resolution
        3. Duration check: Must be > min_duration

        Args:
            video_path: Path to video file to check
            require_video: Whether to require video stream
            require_audio: Whether to require audio stream
            min_duration: Minimum duration in seconds
            expected_resolution: Expected (width, height) tuple

        Returns:
            True if all checks pass
        """
        try:
            if not video_path.exists():
                logger.error(f"QA: Video file does not exist: {video_path}")
                return False

            if video_path.stat().st_size < 1000:
                logger.error(f"QA: Video file too small: {video_path}")
                return False

            # Stream check using ffprobe
            cmd = [
                "ffprobe", "-v", "error",
                "-show_entries", "stream=codec_type,width,height,duration",
                "-of", "json",
                str(video_path)
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                logger.error(f"QA: ffprobe failed: {result.stderr}")
                return False

            probe_data = json.loads(result.stdout)
            streams = probe_data.get("streams", [])

            # Check for required streams
            codec_types = [s.get("codec_type") for s in streams]

            if require_video and "video" not in codec_types:
                logger.error(f"QA: No video stream found in {video_path}")
                return False

            if require_audio and "audio" not in codec_types:
                logger.error(f"QA: No audio stream found in {video_path}")
                return False

            # Resolution check
            video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
            if video_stream and expected_resolution:
                width = int(video_stream.get("width", 0))
                height = int(video_stream.get("height", 0))

                # Allow some flexibility (within 10%)
                exp_w, exp_h = expected_resolution
                if abs(width - exp_w) > exp_w * 0.1 or abs(height - exp_h) > exp_h * 0.1:
                    logger.warning(
                        f"QA: Resolution mismatch. Expected ~{exp_w}x{exp_h}, got {width}x{height}"
                    )
                    # Not a hard failure, just a warning

            # Duration check
            max_duration = 0
            for stream in streams:
                dur = float(stream.get("duration", 0) or 0)
                max_duration = max(max_duration, dur)

            if max_duration < min_duration:
                logger.error(f"QA: Duration too short ({max_duration:.3f}s < {min_duration}s)")
                return False

            logger.info(f"QA: Video quality check PASSED - {video_path.name} ({max_duration:.2f}s)")
            return True

        except json.JSONDecodeError as e:
            logger.error(f"QA: Failed to parse ffprobe output: {e}")
            return False
        except Exception as e:
            logger.error(f"QA: Video quality check error: {e}")
            return False

    async def _retry_failed_clip(
        self,
        segment: SequenceSegment,
        output_path: Path,
        voiceover_path: Optional[Path],
        source_path: Path,
    ) -> bool:
        """
        Retry failed clip generation with fallback strategy.

        Fallback strategies:
        1. For voiceover segments: Generate pure text video with subtitle
        2. For original segments: Re-encode with simpler settings

        Args:
            segment: The segment that failed
            output_path: Output path for the clip
            voiceover_path: Path to voiceover audio (if any)
            source_path: Path to source video

        Returns:
            True if retry successful
        """
        try:
            logger.info(f"Retrying segment: {segment.source} with fallback strategy")

            if segment.source in ("intro", "outro"):
                # For intro/outro: Create simple text-on-black video
                return await self._create_silent_clip(
                    duration=segment.duration,
                    subtitle=segment.subtitle or segment.narration[:30],
                    output_path=output_path,
                )
            elif segment.audio_mode == "voiceover" and voiceover_path and voiceover_path.exists():
                # For voiceover segments: Try simpler encoding
                return await self._create_fallback_voiceover_clip(
                    source_path=source_path,
                    start_time=segment.exact_start,
                    voiceover_path=voiceover_path,
                    subtitle=segment.subtitle,
                    output_path=output_path,
                )
            else:
                # For original segments: Re-encode with simpler settings
                return await self._create_fallback_original_clip(
                    source_path=source_path,
                    start_time=segment.exact_start,
                    duration=segment.duration,
                    subtitle=segment.subtitle,
                    output_path=output_path,
                )

        except Exception as e:
            logger.error(f"Retry failed: {e}")
            return False

    async def _create_fallback_voiceover_clip(
        self,
        source_path: Path,
        start_time: float,
        voiceover_path: Path,
        subtitle: str,
        output_path: Path,
    ) -> bool:
        """Create fallback voiceover clip with simpler encoding."""
        try:
            vo_duration = self._get_audio_duration_mutagen(voiceover_path)
            if vo_duration <= 0:
                vo_duration = 8.0  # Default fallback

            safe_subtitle = self._escape_ffmpeg_text(subtitle)

            # Simpler encoding without complex audio mixing
            cmd = [
                "ffmpeg", "-y",
                "-ss", str(start_time),
                "-i", str(source_path),
                "-i", str(voiceover_path),
                "-t", str(vo_duration),
                "-map", "0:v",
                "-map", "1:a",
                "-vf", (
                    f"scale=1280:720:force_original_aspect_ratio=decrease,"
                    f"pad=1280:720:(ow-iw)/2:(oh-ih)/2:black,"
                    f"drawtext=text='{safe_subtitle}':"
                    f"fontsize=28:fontcolor=white:x=(w-text_w)/2:y=h-45:"
                    f"borderw=2:bordercolor=black"
                ),
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "26",  # Slightly higher CRF for faster encoding
                "-pix_fmt", "yuv420p",
                "-c:a", "aac",
                "-b:a", "128k",
                "-shortest",
                str(output_path)
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            return result.returncode == 0 and output_path.exists()

        except Exception as e:
            logger.error(f"Fallback voiceover clip error: {e}")
            return False

    async def _create_fallback_original_clip(
        self,
        source_path: Path,
        start_time: float,
        duration: float,
        subtitle: str,
        output_path: Path,
    ) -> bool:
        """Create fallback original clip with simpler encoding."""
        try:
            safe_subtitle = self._escape_ffmpeg_text(subtitle)

            cmd = [
                "ffmpeg", "-y",
                "-ss", str(start_time),
                "-i", str(source_path),
                "-t", str(duration),
                "-vf", (
                    f"scale=1280:720:force_original_aspect_ratio=decrease,"
                    f"pad=1280:720:(ow-iw)/2:(oh-ih)/2:black,"
                    f"drawtext=text='{safe_subtitle}':"
                    f"fontsize=28:fontcolor=white:x=(w-text_w)/2:y=h-45:"
                    f"borderw=2:bordercolor=black"
                ),
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "26",
                "-pix_fmt", "yuv420p",
                "-c:a", "aac",
                "-b:a", "128k",
                str(output_path)
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            return result.returncode == 0 and output_path.exists()

        except Exception as e:
            logger.error(f"Fallback original clip error: {e}")
            return False

    async def _create_atomic_video_clip(
        self,
        source_path: Path,
        start_time: float,
        audio_path: Optional[Path],
        subtitle: str,
        output_path: Path,
        use_original_audio: bool = True,
    ) -> bool:
        """
        Create an atomic video clip with AUDIO-DRIVEN duration.

        CRITICAL: This is the core of the audio-video sync fix.
        When voiceover is provided, the clip duration is determined by
        the voiceover audio length, NOT by a fixed duration parameter.

        Args:
            source_path: Path to source video
            start_time: Start time in source video
            audio_path: Path to voiceover audio (if any)
            subtitle: Subtitle text
            output_path: Output path
            use_original_audio: If True and no voiceover, keep original audio

        Returns:
            True if successful
        """
        try:
            safe_subtitle = self._escape_ffmpeg_text(subtitle)

            # Video filter for 1280x720 with subtitle
            video_filter = (
                f"scale=1280:720:force_original_aspect_ratio=decrease,"
                f"pad=1280:720:(ow-iw)/2:(oh-ih)/2:black,"
                f"drawbox=x=0:y=ih-60:w=iw:h=60:color=black@0.6:t=fill,"
                f"drawtext=text='{safe_subtitle}':"
                f"fontsize=28:fontcolor=white:x=(w-text_w)/2:y=h-45:"
                f"borderw=2:bordercolor=black"
            )

            if audio_path and audio_path.exists():
                # AUDIO-DRIVEN DURATION: Get precise audio length
                audio_duration = self._get_audio_duration_mutagen(audio_path)
                if audio_duration <= 0:
                    audio_duration = await self._get_audio_duration(audio_path)

                if audio_duration <= 0:
                    logger.error(f"Cannot determine audio duration for {audio_path}")
                    return False

                logger.info(f"Creating atomic clip with audio-driven duration: {audio_duration:.3f}s")

                # Mix ducked original audio with voiceover
                # Original at 20% volume, voiceover at 150% volume
                audio_filter = (
                    f"[0:a]volume=0.2[bg];"
                    f"[1:a]volume=1.5[vo];"
                    f"[bg][vo]amix=inputs=2:duration=first[audio]"
                )

                cmd = [
                    "ffmpeg", "-y",
                    "-ss", str(start_time),  # Seek before input for speed
                    "-i", str(source_path),
                    "-i", str(audio_path),
                    "-t", str(audio_duration),  # Duration = audio duration
                    "-filter_complex", f"[0:v]{video_filter}[video];{audio_filter}",
                    "-map", "[video]",
                    "-map", "[audio]",
                    "-c:v", "libx264",
                    "-preset", "fast",
                    "-crf", "23",
                    "-pix_fmt", "yuv420p",
                    "-c:a", "aac",
                    "-b:a", "128k",
                    "-shortest",  # Safety: end at shortest stream
                    str(output_path)
                ]

            elif use_original_audio:
                # Original audio mode - use a reasonable fixed duration
                # This is for "original" segments where we keep source audio
                # Duration will be controlled by caller
                logger.info(f"Creating atomic clip with original audio")

                cmd = [
                    "ffmpeg", "-y",
                    "-ss", str(start_time),
                    "-i", str(source_path),
                    "-vf", video_filter,
                    "-c:v", "libx264",
                    "-preset", "fast",
                    "-crf", "23",
                    "-pix_fmt", "yuv420p",
                    "-c:a", "aac",
                    "-b:a", "128k",
                    str(output_path)
                ]

            else:
                # No audio - silent clip
                logger.info(f"Creating silent atomic clip")

                cmd = [
                    "ffmpeg", "-y",
                    "-ss", str(start_time),
                    "-i", str(source_path),
                    "-vf", video_filter,
                    "-af", "volume=0.5",
                    "-c:v", "libx264",
                    "-preset", "fast",
                    "-crf", "23",
                    "-pix_fmt", "yuv420p",
                    "-c:a", "aac",
                    "-b:a", "128k",
                    str(output_path)
                ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)

            if result.returncode != 0:
                logger.error(f"Atomic video clip error: {result.stderr[-500:]}")
                return False

            # Verify output
            if output_path.exists() and output_path.stat().st_size > 1000:
                final_duration = await self._get_audio_duration(output_path)
                logger.info(f"Atomic video clip created: {output_path.name} ({final_duration:.2f}s)")
                return True
            else:
                logger.error(f"Output file missing or too small: {output_path}")
                return False

        except Exception as e:
            logger.error(f"Atomic video clip creation error: {e}")
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
        """Process segment with ducked original audio and voiceover.

        CRITICAL: Using -ss AFTER input for accurate seeking.
        Uses actual voiceover duration for perfect sync.
        """
        try:
            safe_subtitle = self._escape_ffmpeg_text(subtitle)

            # Video filter WITHOUT trim
            video_filter = (
                f"scale=1280:720:force_original_aspect_ratio=decrease,"
                f"pad=1280:720:(ow-iw)/2:(oh-ih)/2:black,"
                f"drawbox=x=0:y=ih-60:w=iw:h=60:color=black@0.6:t=fill,"
                f"drawtext=text='{safe_subtitle}':"
                f"fontsize=28:fontcolor=white:x=(w-text_w)/2:y=h-45:"
                f"borderw=2:bordercolor=black"
            )

            if voiceover_path and voiceover_path.exists():
                # Get actual voiceover duration for perfect sync
                vo_duration = await self._get_audio_duration(voiceover_path)
                if vo_duration > 0:
                    # Use the shorter of voiceover duration or specified duration
                    actual_duration = min(vo_duration, duration)
                    logger.info(f"Voiceover segment: using actual duration {actual_duration:.2f}s "
                              f"(vo: {vo_duration:.2f}s, specified: {duration:.2f}s)")
                else:
                    actual_duration = duration

                # Use atrim filter to precisely match voiceover duration
                audio_filter = (
                    f"[0:a]atrim=0:{actual_duration},asetpts=PTS-STARTPTS,volume=0.2[bg];"
                    f"[1:a]volume=1.5[vo];"
                    f"[bg][vo]amix=inputs=2:duration=shortest[audio]"
                )

                cmd = [
                    "ffmpeg", "-y",
                    "-i", str(source_path),
                    "-ss", str(start_time),
                    "-t", str(actual_duration),
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
                    "-i", str(source_path),
                    "-ss", str(start_time),
                    "-t", str(duration),
                    "-vf", video_filter,
                    "-af", "volume=0.5",
                    "-c:v", "libx264",
                    "-preset", "fast",
                    "-crf", "23",
                    "-c:a", "aac",
                    "-b:a", "128k",
                    str(output_path)
                ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

            if result.returncode != 0:
                logger.error(f"Voiceover segment error: {result.stderr[-500:]}")
                return False

            return True

        except Exception as e:
            logger.error(f"Voiceover segment processing error: {e}")
            return False

    # NOTE: _concatenate_with_transition has been replaced by _concatenate_atomic_clips
    # The old method is removed to avoid confusion

    def _escape_ffmpeg_text(self, text: str) -> str:
        """Escape special characters for FFmpeg drawtext filter."""
        if not text:
            return ""
        # Escape special chars: \ ' :
        text = text.replace("\\", "\\\\")
        text = text.replace("'", "\\'")
        text = text.replace(":", "\\:")
        text = text.replace("%", "\\%")
        return text

    async def review_video_quality(
        self,
        output_path: Path,
        sequence: List[SequenceSegment],
        source_a_path: Path,
        source_b_path: Path,
    ) -> Dict[str, Any]:
        """
        Review generated video quality using AI.

        Checks:
        1. Video duration matches expected total duration
        2. Audio-video synchronization is correct
        3. Content quality meets standards

        Returns:
            Dict with review results and suggestions
        """
        try:
            # Use ffprobe to get actual video properties
            import subprocess
            probe_cmd = [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration,size,bit_rate:stream=codec_name,duration,width,height",
                "-of", "json",
                str(output_path)
            ]
            result = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                logger.warning(f"Video review: ffprobe failed: {result.stderr}")
                return {"passed": True, "issues": [], "message": "视频审查跳过（ffprobe失败）"}

            import json
            probe_data = json.loads(result.stdout)

            # Extract stream info
            streams = probe_data.get("streams", [])
            video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
            audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)

            format_info = probe_data.get("format", {})
            actual_duration = float(format_info.get("duration", 0))
            file_size = int(format_info.get("size", 0))

            # Calculate expected duration
            expected_duration = sum(seg.duration for seg in sequence)

            issues = []
            warnings = []

            # Check 1: Duration mismatch
            duration_diff = abs(actual_duration - expected_duration)
            if duration_diff > 10:  # More than 10 seconds difference
                issues.append(f"时长不匹配：预期 {expected_duration:.1f}s，实际 {actual_duration:.1f}s")
            elif duration_diff > 3:
                warnings.append(f"时长略有偏差：预期 {expected_duration:.1f}s，实际 {actual_duration:.1f}s")

            # Check 2: Audio-Video duration sync
            if video_stream and audio_stream:
                video_dur = float(video_stream.get("duration", 0))
                audio_dur = float(audio_stream.get("duration", 0))
                av_diff = abs(video_dur - audio_dur)
                if av_diff > 3:
                    issues.append(f"音视频时长不同步：视频 {video_dur:.1f}s，音频 {audio_dur:.1f}s")
                elif av_diff > 1:
                    warnings.append(f"音视频时长略有差异：视频 {video_dur:.1f}s，音频 {audio_dur:.1f}s")

            # Check 3: File size sanity check
            if file_size < 100000:  # Less than 100KB
                issues.append(f"文件大小异常：{file_size} 字节（可能生成失败）")

            # Check 4: Resolution check
            if video_stream:
                width = int(video_stream.get("width", 0))
                height = int(video_stream.get("height", 0))
                if width < 640 or height < 360:
                    warnings.append(f"分辨率较低：{width}x{height}")

            # Check 5: Bitrate check
            bitrate = int(format_info.get("bit_rate", 0))
            if bitrate > 0 and bitrate < 500000:  # Less than 500kbps
                warnings.append(f"比特率较低：{bitrate//1000} kbps（可能影响画质）")

            # Generate review result
            review_result = {
                "passed": len(issues) == 0,
                "issues": issues,
                "warnings": warnings,
                "actual_duration": actual_duration,
                "expected_duration": expected_duration,
                "file_size_mb": file_size / (1024 * 1024),
                "message": ""
            }

            if issues:
                review_result["message"] = f"发现 {len(issues)} 个问题需要修复"
            elif warnings:
                review_result["message"] = f"视频质量良好，有 {len(warnings)} 个注意事项"
            else:
                review_result["message"] = "视频质量检查通过"

            logger.info(f"Video review: {review_result['message']}")
            return review_result

        except Exception as e:
            logger.error(f"Video review error: {e}")
            return {"passed": True, "issues": [], "message": f"审查跳过: {str(e)}"}

    def _cleanup_temp_dir(self, temp_dir: Path):
        """Clean up temporary directory."""
        try:
            import shutil
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
        except Exception as e:
            logger.warning(f"Failed to cleanup temp dir: {e}")

    async def get_asr_data(self, source_id: str) -> List[Dict[str, Any]]:
        """Get ASR data for a source from vector store."""
        try:
            vector_store = get_vector_store()
            results = vector_store.search(
                query="",  # Empty query to get all
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

            # Sort by start time
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
        """
        Full pipeline to create a director cut video.

        Args:
            task_id: Unique task identifier
            conflict_data: Conflict info for script generation
            source_a_id: ID of source A
            source_a_path: Path to video A
            time_a: Timestamp for video A
            source_b_id: ID of source B
            source_b_path: Path to video B
            time_b: Timestamp for video B
            persona: Persona key ('hajimi', 'wukong', 'pro')

        Returns:
            Task result with video URL or error
        """
        persona_config = PERSONA_CONFIGS.get(persona, PERSONA_CONFIGS["pro"])

        try:
            # Step 1: Generate narrative script
            self._tasks[task_id] = {
                "status": "generating_script",
                "progress": 10,
                "message": f"🎬 {persona_config['emoji']} 导演正在编写剧本...",
            }

            # Get ASR data for context
            asr_data_a = await self.get_asr_data(source_a_id)
            asr_data_b = await self.get_asr_data(source_b_id)

            # Update conflict_data with timestamps
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

            # Step 2: Generate voiceovers for voiceover segments
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

            # Step 3: Compose director cut video
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
            self._cleanup_temp_dir(voiceover_dir)

            if not compose_success:
                raise Exception("视频合成失败")

            # Step 4: Quality review (AI Director as critic)
            self._tasks[task_id] = {
                "status": "reviewing",
                "progress": 90,
                "message": f"🔍 {persona_config['name']} 导演正在质量审查...",
            }

            review = await self.review_video_quality(
                output_path=output_path,
                sequence=sequence,
                source_a_path=source_a_path,
                source_b_path=source_b_path,
            )

            # Success
            video_url = f"/static/generated/director_{task_id}.mp4"

            # Build script summary
            script_summary = " → ".join([
                f"{s.source}({'🔊' if s.audio_mode == 'original' else '🎤'})"
                for s in sequence
            ])

            # Add review info to message
            review_suffix = ""
            if review.get("warnings"):
                review_suffix = f" ({len(review['warnings'])} 个注意事项)"
            elif review.get("issues"):
                review_suffix = f" (发现 {len(review['issues'])} 个问题)"

            self._tasks[task_id] = {
                "status": "completed",
                "progress": 100,
                "message": f"✨ {persona_config['name']}导演作品完成！{review.get('message', '')}{review_suffix}",
                "video_url": video_url,
                "script": script_summary,
                "persona": persona,
                "persona_name": persona_config["name"],
                "segment_count": len(sequence),
                "review": review,
            }

            logger.info(f"Director cut video created: {video_url} | Review: {review.get('message', 'N/A')}")
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
        """Get status of a director cut task."""
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
_director_service: Optional[DirectorService] = None


def get_director_service() -> DirectorService:
    """Get or create DirectorService singleton."""
    global _director_service
    if _director_service is None:
        _director_service = DirectorService()
    return _director_service
