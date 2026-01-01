"""
Analysis Service
Generates AI-powered analysis artifacts: conflicts, timeline, and knowledge graph.

Uses SophNet DeepSeek-V3.2 for all AI analysis tasks.
"""

import json
import hashlib
import logging
from typing import List, Dict, Any, Optional

from app.core import get_settings
from app.services.vector_store import get_vector_store
from app.services.sophnet_service import get_sophnet_service

logger = logging.getLogger(__name__)
settings = get_settings()


class AnalysisService:
    """AI-powered analysis generation service using SophNet."""

    def __init__(self):
        """Initialize with SophNet service."""
        self.sophnet = get_sophnet_service()
        self.vector_store = get_vector_store()

        # Simple in-memory cache
        self._cache: Dict[str, Any] = {}

        if not settings.sophnet_api_key:
            logger.warning("SophNet API key not configured!")

    def _get_cache_key(self, operation: str, source_ids: List[str]) -> str:
        """Generate cache key from operation and source IDs."""
        content = f"{operation}:{':'.join(sorted(source_ids))}"
        return hashlib.md5(content.encode()).hexdigest()

    def _format_timestamp(self, seconds: float) -> str:
        """Convert seconds to MM:SS format."""
        if seconds is None or seconds < 0:
            return "00:00"
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins:02d}:{secs:02d}"

    def _get_source_documents(
        self,
        source_ids: List[str],
        limit_per_source: int = 50
    ) -> Dict[str, List[Dict]]:
        """
        Get documents for multiple sources.

        Returns:
            Dict mapping source_id to list of documents
        """
        result = {}
        for source_id in source_ids:
            docs = self.vector_store.get_source_documents(source_id)
            # Sort by timestamp
            docs.sort(key=lambda x: x.get("metadata", {}).get("start", 0))
            result[source_id] = docs[:limit_per_source]
        return result

    def _build_source_summary(self, source_docs: Dict[str, List[Dict]]) -> str:
        """Build a summary of all sources for LLM context."""
        parts = []
        for source_id, docs in source_docs.items():
            if not docs:
                continue

            video_title = docs[0].get("metadata", {}).get("video_title", source_id)
            parts.append(f"\n### 视频: {video_title} (ID: {source_id})")

            for doc in docs[:30]:  # Limit docs per source
                metadata = doc.get("metadata", {})
                timestamp = self._format_timestamp(metadata.get("start", 0))
                doc_type = metadata.get("type", "unknown")
                text = doc.get("text", "")[:200]

                if doc_type == "visual":
                    parts.append(f"[{timestamp}] 画面: {text}")
                else:
                    parts.append(f"[{timestamp}] 语音: {text}")

        return "\n".join(parts)

    async def generate_conflicts(
        self,
        source_ids: List[str],
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Generate conflict analysis between multiple video sources.

        Args:
            source_ids: List of video source IDs to analyze
            use_cache: Whether to use cached results

        Returns:
            Dict with conflicts list
        """
        if len(source_ids) < 1:
            return {"conflicts": [], "message": "需要至少1个视频源进行分析"}

        # Check cache
        cache_key = self._get_cache_key("conflicts", source_ids)
        if use_cache and cache_key in self._cache:
            logger.info(f"Returning cached conflicts for {source_ids}")
            return self._cache[cache_key]

        if not settings.sophnet_api_key:
            return {"conflicts": [], "message": "AI服务未配置"}

        try:
            # Get source documents
            source_docs = self._get_source_documents(source_ids)
            if not any(source_docs.values()):
                return {"conflicts": [], "message": "没有找到视频内容数据"}

            summary = self._build_source_summary(source_docs)

            # Build prompt
            prompt = f"""请分析以下视频内容，找出不同视频之间的观点分歧或信息差异。

## 视频内容摘要：
{summary}

## 任务要求：
1. 识别视频间的观点分歧、策略差异或信息矛盾
2. 如果只有一个视频，分析其中的关键决策点或可能存在争议的内容
3. 给出AI分析结论

## 输出格式（必须是有效JSON数组）：
```json
[
  {{
    "id": "conflict-1",
    "topic": "分歧主题",
    "severity": "critical|warning|info",
    "viewpoint_a": {{
      "source_id": "视频ID",
      "source_name": "视频标题",
      "title": "观点A标题",
      "description": "详细描述（50字内）",
      "timestamp": 时间戳秒数,
      "color": "red"
    }},
    "viewpoint_b": {{
      "source_id": "视频ID",
      "source_name": "视频标题",
      "title": "观点B标题",
      "description": "详细描述（50字内）",
      "timestamp": 时间戳秒数,
      "color": "blue"
    }},
    "verdict": "AI分析结论"
  }}
]
```

请只输出JSON数组，不要包含其他文字："""

            content = await self.sophnet.chat(
                messages=[
                    {"role": "system", "content": "你是一个专业的视频分析AI，擅长识别观点分歧和信息差异。"},
                    {"role": "user", "content": prompt}
                ],
                model="DeepSeek-V3.2",
                temperature=0.5,
                max_tokens=2000,
            )

            # Parse JSON from response
            conflicts = self._parse_json_response(content, [])

            # Post-process: Ensure source_id and source_name are correct
            # LLM may return placeholder IDs, so we map them to actual source IDs
            conflicts = self._fix_conflict_sources(conflicts, source_docs)

            result = {"conflicts": conflicts}

            # Cache result
            self._cache[cache_key] = result
            logger.info(f"Generated {len(conflicts)} conflicts for {source_ids}")

            return result

        except Exception as e:
            logger.error(f"Error generating conflicts: {e}")
            return {"conflicts": [], "message": f"分析出错: {str(e)}"}

    async def generate_timeline(
        self,
        source_id: str,
        use_cache: bool = True,
        quality_check: bool = True
    ) -> Dict[str, Any]:
        """
        Generate smart timeline for a video with optional quality review.

        Args:
            source_id: Video source ID
            use_cache: Whether to use cached results
            quality_check: Whether AI should review and filter low-quality events

        Returns:
            Dict with timeline events
        """
        # Check cache
        cache_key = self._get_cache_key("timeline", [source_id])
        if use_cache and cache_key in self._cache:
            logger.info(f"Returning cached timeline for {source_id}")
            return self._cache[cache_key]

        if not settings.sophnet_api_key:
            return {"timeline": [], "message": "AI服务未配置"}

        try:
            # Get source documents
            docs = self.vector_store.get_source_documents(source_id)
            if not docs:
                return {"timeline": [], "message": "没有找到视频内容数据"}

            video_title = docs[0].get("metadata", {}).get("video_title", source_id)

            # Build content summary
            content_parts = []
            docs.sort(key=lambda x: x.get("metadata", {}).get("start", 0))
            for doc in docs[:60]:
                metadata = doc.get("metadata", {})
                timestamp = self._format_timestamp(metadata.get("start", 0))
                start_seconds = metadata.get("start", 0)
                doc_type = metadata.get("type", "unknown")
                text = doc.get("text", "")[:150]
                type_label = "画面" if doc_type == "visual" else "语音"
                content_parts.append(f"[{timestamp}/{start_seconds}s] {type_label}: {text}")

            content_summary = "\n".join(content_parts)

            # Enhanced prompt for quality-conscious timeline generation
            quality_instruction = ""
            if quality_check:
                quality_instruction = """
## 质量审查标准
作为专业内容审查员，请确保每个时间节点：
1. **内容明确**: 必须有清晰的情节或事件发生，不是模糊或无效内容
2. **视觉价值**: 画面包含有意义的动作、对话或关键信息
3. **避免重复**: 不要选择内容相似或重复的时间段
4. **节奏把控**: STORY 和 COMBAT 交替出现，保持观看节奏
排除标准：
- 纯黑屏/加载画面
- 重复的操作或对话
- 无意义的等待时间
- 模糊不清的情节
"""

            prompt = f"""请为以下视频生成智能时间轴，提取关键事件节点并进行分类。

## 视频标题: {video_title}
## 视频ID: {source_id}

## 视频内容（按时间顺序）：
{content_summary}
{quality_instruction}
## 任务要求：
1. 提取10-18个关键时间节点（质量优先于数量）
2. 为每个事件分类：
   - STORY: 剧情/对话/过场动画/重要信息讲解
   - COMBAT: BOSS战/战斗/打怪/激烈操作
   - EXPLORE: 跑图/收集/闲聊/无关紧要的内容（低优先级）
3. 标记特别重要的节点为关键时刻（is_key_moment: true）
4. 时间格式为 MM:SS，同时提供精确的秒数（timestamp）
5. 每个片段建议时长 8-15 秒，确保内容完整

## 输出格式（必须是有效JSON数组）：
```json
[
  {{
    "id": "event-1",
    "time": "MM:SS",
    "timestamp": 时间戳秒数,
    "title": "事件标题",
    "description": "事件描述（30字内）",
    "source_id": "{source_id}",
    "is_key_moment": true或false,
    "event_type": "STORY或COMBAT或EXPLORE",
    "quality_score": 1-10的质量评分（10为最高质量）
  }}
]
```

请只输出JSON数组："""

            content = await self.sophnet.chat(
                messages=[
                    {"role": "system", "content": "你是一个专业的视频内容审查AI，擅长提取高质量关键节点并进行分类。你严格把关内容质量，确保每个时间节点都有明确的观看价值。"},
                    {"role": "user", "content": prompt}
                ],
                model="DeepSeek-V3.2",
                temperature=0.5,
                max_tokens=2000,
            )
            timeline = self._parse_json_response(content, [])

            # Post-process: filter out low-quality events if quality_check is enabled
            if quality_check and timeline:
                original_count = len(timeline)
                timeline = [
                    event for event in timeline
                    if event.get("quality_score", 5) >= 5  # Keep events with quality 5+
                ]
                logger.info(f"Quality check filtered {original_count - len(timeline)} low-quality events")

            # Ensure all required fields exist
            for event in timeline:
                if "source_id" not in event:
                    event["source_id"] = source_id
                if "is_key_moment" not in event:
                    event["is_key_moment"] = False
                if "quality_score" not in event:
                    event["quality_score"] = 7

            result = {"timeline": timeline, "source_id": source_id}

            # Cache result
            self._cache[cache_key] = result
            logger.info(f"Generated {len(timeline)} timeline events for {source_id}")

            return result

        except Exception as e:
            logger.error(f"Error generating timeline: {e}")
            return {"timeline": [], "message": f"生成时间轴出错: {str(e)}"}

    async def generate_graph(
        self,
        source_ids: List[str],
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Generate knowledge graph from video content.

        Args:
            source_ids: List of video source IDs
            use_cache: Whether to use cached results

        Returns:
            Dict with nodes and links
        """
        # Check cache
        cache_key = self._get_cache_key("graph", source_ids)
        if use_cache and cache_key in self._cache:
            logger.info(f"Returning cached graph for {source_ids}")
            return self._cache[cache_key]

        if not settings.sophnet_api_key:
            return {"nodes": [], "links": [], "message": "AI服务未配置"}

        try:
            # Get source documents
            source_docs = self._get_source_documents(source_ids)
            if not any(source_docs.values()):
                return {"nodes": [], "links": [], "message": "没有找到视频内容数据"}

            summary = self._build_source_summary(source_docs)

            prompt = f"""请从以下视频内容中提取实体和关系，构建知识图谱。

## 视频内容：
{summary}

## 任务要求：
1. 提取关键实体：人物、物品、地点、概念等
2. 识别实体间的关系
3. 尽可能标注实体出现的时间戳

## 实体类别：
- character: 人物/角色
- item: 物品/道具
- location: 地点/场景
- boss: BOSS/敌人
- concept: 概念/术语

## 关系类型：
- weak_to: 弱点/克制
- effective_against: 有效对抗
- found_in: 出现在
- obtained_from: 获取自
- related_to: 相关于
- belongs_to: 属于

## 输出格式（必须是有效JSON对象）：
```json
{{
  "nodes": [
    {{"id": "node-1", "name": "实体名称", "category": "类别", "timestamp": 时间戳或null}}
  ],
  "links": [
    {{"source": "node-1", "target": "node-2", "relation": "关系类型"}}
  ]
}}
```

请只输出JSON对象："""

            content = await self.sophnet.chat(
                messages=[
                    {"role": "system", "content": "你是一个专业的知识图谱构建AI，擅长从文本中提取实体和关系。"},
                    {"role": "user", "content": prompt}
                ],
                model="DeepSeek-V3.2",
                temperature=0.5,
                max_tokens=2000,
            )
            graph = self._parse_json_response(content, {"nodes": [], "links": []})

            # Handle case where LLM returns a list instead of object
            if isinstance(graph, list):
                # Assume it's a list of nodes without links
                logger.warning("Graph returned as list, converting to object format")
                graph = {"nodes": graph, "links": []}

            result = {"nodes": graph.get("nodes", []), "links": graph.get("links", [])}

            # Cache result
            self._cache[cache_key] = result
            logger.info(f"Generated graph with {len(result['nodes'])} nodes for {source_ids}")

            return result

        except Exception as e:
            logger.error(f"Error generating graph: {e}")
            return {"nodes": [], "links": [], "message": f"生成图谱出错: {str(e)}"}

    def _parse_json_response(self, content: str, default: Any) -> Any:
        """Parse JSON from LLM response, handling various formats."""
        import re

        if not content:
            return default

        # Clean up content: remove potential BOM and normalize whitespace
        content = content.strip()
        if content.startswith('\ufeff'):
            content = content[1:]

        # Try direct parse first
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            logger.debug(f"Direct JSON parse failed: {e}")

        # Try to extract JSON from markdown code blocks
        # Pattern 1: ```json ... ``` (more robust regex)
        json_block_patterns = [
            r'```json\s*([\s\S]*?)```',  # Standard markdown json block
            r'```\s*json\s*([\s\S]*?)```',  # With space
            r'```JSON\s*([\s\S]*?)```',  # Uppercase
        ]

        for pattern in json_block_patterns:
            match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
            if match:
                json_str = match.group(1).strip()
                # Remove any leading/trailing newlines
                json_str = json_str.strip('\n\r')
                try:
                    result = json.loads(json_str)
                    logger.debug(f"Parsed JSON from json code block, length: {len(json_str)}")
                    return result
                except json.JSONDecodeError as e:
                    logger.debug(f"JSON block parse failed: {e}")
                    # Try to fix common issues
                    json_str_fixed = self._fix_json_string(json_str)
                    try:
                        result = json.loads(json_str_fixed)
                        logger.debug(f"Parsed JSON after fixing")
                        return result
                    except json.JSONDecodeError:
                        pass

        # Pattern 2: ``` ... ``` (generic code block)
        code_block_match = re.search(r'```\s*([\s\S]*?)```', content, re.DOTALL)
        if code_block_match:
            json_str = code_block_match.group(1).strip()
            # Skip if it starts with a language identifier
            if not json_str.startswith(('python', 'javascript', 'java', 'c++', 'html', 'css')):
                try:
                    result = json.loads(json_str)
                    logger.debug(f"Parsed JSON from ``` block")
                    return result
                except json.JSONDecodeError as e:
                    logger.debug(f"Code block parse failed: {e}")

        # Pattern 3: Find array [...] or object {...}
        # For arrays - find the outermost balanced brackets
        array_match = re.search(r'(\[[\s\S]*\])', content, re.DOTALL)
        if array_match:
            json_str = array_match.group(1).strip()
            try:
                result = json.loads(json_str)
                logger.debug(f"Parsed JSON array directly")
                return result
            except json.JSONDecodeError as e:
                logger.debug(f"Array parse failed: {e}")
                # Try fixing
                json_str_fixed = self._fix_json_string(json_str)
                try:
                    result = json.loads(json_str_fixed)
                    logger.debug(f"Parsed JSON array after fixing")
                    return result
                except json.JSONDecodeError:
                    pass

        # For objects
        object_match = re.search(r'(\{[\s\S]*\})', content, re.DOTALL)
        if object_match:
            json_str = object_match.group(1).strip()
            try:
                result = json.loads(json_str)
                logger.debug(f"Parsed JSON object directly")
                return result
            except json.JSONDecodeError as e:
                logger.debug(f"Object parse failed: {e}")
                # Try fixing
                json_str_fixed = self._fix_json_string(json_str)
                try:
                    result = json.loads(json_str_fixed)
                    logger.debug(f"Parsed JSON object after fixing")
                    return result
                except json.JSONDecodeError:
                    pass

        # Log failure with safe encoding
        try:
            preview = content[:300].encode('utf-8', errors='replace').decode('utf-8')
            logger.warning(f"Failed to parse JSON from response: {preview}...")
        except Exception:
            logger.warning("Failed to parse JSON from response (encoding error in preview)")

        return default

    def _fix_json_string(self, json_str: str) -> str:
        """Attempt to fix common JSON formatting issues."""
        import re

        # Remove trailing commas before ] or }
        json_str = re.sub(r',\s*([}\]])', r'\1', json_str)

        # Fix unescaped quotes in strings (simple heuristic)
        # This is a best-effort fix

        # Remove any control characters except newline and tab
        json_str = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', json_str)

        return json_str

    def _fix_conflict_sources(
        self,
        conflicts: List[Dict[str, Any]],
        source_docs: Dict[str, List[Dict]]
    ) -> List[Dict[str, Any]]:
        """
        Fix conflict data to ensure source_id and source_name are correct.

        LLM may return placeholder IDs like 'source-a' or 'source-b' instead of actual IDs.
        This method maps them to the correct source IDs from source_docs.
        """
        if not conflicts:
            return conflicts

        # Build a mapping from source index (0, 1) to actual source_id
        source_ids_list = list(source_docs.keys())
        source_names = {}

        for source_id, docs in source_docs.items():
            if docs:
                metadata = docs[0].get("metadata", {})
                source_names[source_id] = metadata.get("video_title", source_id)

        # Pattern to detect placeholder source IDs
        placeholder_patterns = ["source-a", "source-b", "source_a", "source_b", ":source-a", ":source-b"]

        for conflict in conflicts:
            viewpoint_a = conflict.get("viewpoint_a", {})
            viewpoint_b = conflict.get("viewpoint_b", {})

            # Fix viewpoint_a
            a_source_id = viewpoint_a.get("source_id", "")
            if any(p in a_source_id.lower() for p in placeholder_patterns):
                # Map to first source
                if len(source_ids_list) > 0:
                    conflict["viewpoint_a"]["source_id"] = source_ids_list[0]
                    conflict["viewpoint_a"]["source_name"] = source_names.get(source_ids_list[0], "视频A")

            # Fix viewpoint_b
            b_source_id = viewpoint_b.get("source_id", "")
            if any(p in b_source_id.lower() for p in placeholder_patterns):
                # Map to second source (or first if only one source)
                target_idx = 1 if len(source_ids_list) > 1 else 0
                conflict["viewpoint_b"]["source_id"] = source_ids_list[target_idx]
                conflict["viewpoint_b"]["source_name"] = source_names.get(source_ids_list[target_idx], "视频B")

            # Also fix missing source_name
            if not viewpoint_a.get("source_name") and viewpoint_a.get("source_id") in source_names:
                conflict["viewpoint_a"]["source_name"] = source_names[viewpoint_a["source_id"]]
            if not viewpoint_b.get("source_name") and viewpoint_b.get("source_id") in source_names:
                conflict["viewpoint_b"]["source_name"] = source_names[viewpoint_b["source_id"]]

        return conflicts

    def clear_cache(self, source_ids: Optional[List[str]] = None):
        """Clear cached analysis results."""
        if source_ids is None:
            self._cache.clear()
            logger.info("Cleared all analysis cache")
        else:
            # Clear cache entries containing any of the source IDs
            keys_to_remove = []
            for key in self._cache:
                for sid in source_ids:
                    if sid in str(self._cache.get(key, {})):
                        keys_to_remove.append(key)
                        break
            for key in keys_to_remove:
                del self._cache[key]
            logger.info(f"Cleared cache for sources: {source_ids}")


# Singleton instance
_analysis_service: Optional[AnalysisService] = None


def get_analysis_service() -> AnalysisService:
    """Get or create AnalysisService singleton."""
    global _analysis_service
    if _analysis_service is None:
        _analysis_service = AnalysisService()
    return _analysis_service
