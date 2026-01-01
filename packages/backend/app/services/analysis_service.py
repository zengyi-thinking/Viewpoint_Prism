"""
Analysis Service
Generates AI-powered analysis artifacts: conflicts, timeline, and knowledge graph.
"""

import json
import hashlib
import logging
from typing import List, Dict, Any, Optional
from openai import OpenAI

from app.core import get_settings
from app.services.vector_store import get_vector_store

logger = logging.getLogger(__name__)
settings = get_settings()


class AnalysisService:
    """AI-powered analysis generation service."""

    def __init__(self):
        """Initialize with ModelScope API client."""
        self.client = OpenAI(
            api_key=settings.modelscope_api_key,
            base_url="https://api-inference.modelscope.cn/v1"
        )
        self.model = settings.modelscope_model
        self.vector_store = get_vector_store()

        # Simple in-memory cache
        self._cache: Dict[str, Any] = {}

        if not settings.modelscope_api_key:
            logger.warning("ModelScope API key not configured!")

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

        if not settings.modelscope_api_key:
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

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,
                max_tokens=2000,
            )

            content = response.choices[0].message.content

            # Parse JSON from response
            conflicts = self._parse_json_response(content, [])

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
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Generate smart timeline for a video.

        Args:
            source_id: Video source ID
            use_cache: Whether to use cached results

        Returns:
            Dict with timeline events
        """
        # Check cache
        cache_key = self._get_cache_key("timeline", [source_id])
        if use_cache and cache_key in self._cache:
            logger.info(f"Returning cached timeline for {source_id}")
            return self._cache[cache_key]

        if not settings.modelscope_api_key:
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

            prompt = f"""请为以下视频生成智能时间轴，提取关键事件节点并进行分类。

## 视频标题: {video_title}
## 视频ID: {source_id}

## 视频内容（按时间顺序）：
{content_summary}

## 任务要求：
1. 提取8-15个关键时间节点
2. 为每个事件分类：
   - STORY: 剧情/对话/过场动画/重要信息讲解
   - COMBAT: BOSS战/战斗/打怪/激烈操作
   - EXPLORE: 跑图/收集/闲聊/无关紧要的内容（低优先级）
3. 标记特别重要的节点为关键时刻
4. 时间格式为 MM:SS

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
    "event_type": "STORY或COMBAT或EXPLORE"
  }}
]
```

请只输出JSON数组："""

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,
                max_tokens=1500,
            )

            content = response.choices[0].message.content
            timeline = self._parse_json_response(content, [])

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

        if not settings.modelscope_api_key:
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

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,
                max_tokens=2000,
            )

            content = response.choices[0].message.content
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
