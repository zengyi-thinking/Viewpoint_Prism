"""
Analysis service - AI-powered video analysis.
"""

import json
import hashlib
import logging
import traceback
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime

from app.core import get_settings
from app.shared.perception import get_sophnet_service
from app.shared.storage import get_vector_store

logger = logging.getLogger(__name__)
settings = get_settings()


class AnalysisService:
    """AI-powered analysis generation service."""

    def __init__(self):
        """Initialize with services."""
        self.sophnet = get_sophnet_service()
        self._vector_store = None  # 延迟初始化
        self._cache: Dict[str, Any] = {}

    @property
    def vector_store(self):
        """Lazy load vector store."""
        if self._vector_store is None:
            self._vector_store = get_vector_store()
        return self._vector_store

    def _get_cache_key(self, operation: str, source_ids: List[str]) -> str:
        """Generate cache key."""
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
        """Get documents for multiple sources."""
        result = {}
        for source_id in source_ids:
            docs = self.vector_store.get_source_documents(source_id)
            docs.sort(key=lambda x: x.get("metadata", {}).get("start", 0))
            result[source_id] = docs[:limit_per_source]
        return result

    def _build_source_summary(self, source_docs: Dict[str, List[Dict]]) -> str:
        """Build summary of all sources."""
        parts = []
        for source_id, docs in source_docs.items():
            if docs:
                texts = [d.get("text", "") for d in docs[:10]]
                combined = " ".join(texts)
                parts.append(f"[Source {source_id}]: {combined[:500]}")
        return "\n\n".join(parts) if parts else "No content available"

    def _clean_llm_json(self, response: str) -> str:
        """Strip markdown code fences from LLM responses."""
        cleaned = response.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            cleaned = "\n".join(lines).strip()
        return cleaned

    def _to_static_url(self, path_value: Optional[str]) -> Optional[str]:
        """Convert filesystem path to /static URL if possible."""
        if not path_value:
            return None
        if path_value.startswith("/static/"):
            return path_value
        path = Path(path_value)
        static_root = settings.resolve_path(settings.upload_dir).parent
        try:
            if path.is_absolute():
                rel = path.relative_to(static_root).as_posix()
            else:
                rel = Path(path_value).as_posix().lstrip("/")
        except Exception:
            return None
        return f"/static/{rel}"

    def _static_url_if_exists(self, path_value: Optional[str]) -> Optional[str]:
        """Return /static URL only if the underlying file exists."""
        if not path_value:
            return None
        if path_value.startswith("http://") or path_value.startswith("https://"):
            return path_value
        static_url = self._to_static_url(path_value)
        if not static_url:
            return None
        static_root = settings.resolve_path(settings.upload_dir).parent
        rel_path = static_url.replace("/static/", "", 1)
        target = static_root / rel_path
        return static_url if target.exists() else None

    def _fallback_one_pager(self, source_ids: List[str], source_docs: Dict[str, List[Dict]]) -> Dict[str, Any]:
        """Build a simple one-pager when LLM output is unavailable."""
        insights = []
        evidence_items = []
        evidence_images = []
        video_titles = []

        for sid, docs in source_docs.items():
            if docs:
                title = docs[0].get("metadata", {}).get("video_title") or sid
            else:
                title = sid
            video_titles.append(title)

            for doc in docs[:3]:
                text = doc.get("text", "").strip()
                if text:
                    insights.append(text[:120])
                frame_path = doc.get("metadata", {}).get("frame_path")
                url = self._to_static_url(frame_path)
                if url:
                    evidence_items.append({
                        "url": url,
                        "caption": "",
                        "related_insight_index": None,
                    })
                    evidence_images.append(url)

        if not insights:
            insights = ["暂无可用的分析内容，请先完成视频分析。"]

        return {
            "headline": "视频洞察简报",
            "tldr": "当前视频内容尚未生成完整洞察。",
            "insights": insights[:5],
            "conceptual_image": None,
            "evidence_items": evidence_items[:6],
            "evidence_images": evidence_images[:6],
            "generated_at": datetime.utcnow().isoformat(),
            "source_ids": source_ids,
            "video_titles": video_titles,
        }

    def _normalize_conflicts(self, conflicts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Normalize conflict records to match response schema."""
        normalized = []
        for idx, item in enumerate(conflicts):
            if not isinstance(item, dict):
                continue
            viewpoint_a = item.get("viewpoint_a") or {}
            viewpoint_b = item.get("viewpoint_b") or {}
            normalized.append({
                "id": item.get("id") or f"conflict_{idx + 1}",
                "topic": item.get("topic") or "unknown",
                "severity": item.get("severity") or "info",
                "viewpoint_a": {
                    "source_id": viewpoint_a.get("source_id", ""),
                    "source_name": viewpoint_a.get("source_name", ""),
                    "title": viewpoint_a.get("title", ""),
                    "description": viewpoint_a.get("description", ""),
                    "timestamp": viewpoint_a.get("timestamp"),
                    "color": viewpoint_a.get("color", ""),
                },
                "viewpoint_b": {
                    "source_id": viewpoint_b.get("source_id", ""),
                    "source_name": viewpoint_b.get("source_name", ""),
                    "title": viewpoint_b.get("title", ""),
                    "description": viewpoint_b.get("description", ""),
                    "timestamp": viewpoint_b.get("timestamp"),
                    "color": viewpoint_b.get("color", ""),
                },
                "verdict": item.get("verdict") or "",
            })
        return normalized

    def _normalize_graph(self, graph: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize graph structure to match response schema."""
        if not isinstance(graph, dict):
            return {"nodes": [], "links": []}

        nodes = []
        raw_nodes = graph.get("nodes", []) or []
        for idx, node in enumerate(raw_nodes):
            if not isinstance(node, dict):
                continue
            node_id = node.get("id") or f"node_{idx + 1}"
            nodes.append({
                "id": node_id,
                "name": node.get("name") or node_id,
                "category": node.get("category") or "other",
                "timestamp": node.get("timestamp"),
                "source_id": node.get("source_id"),
            })

        links = []
        raw_links = graph.get("links", []) or []
        for link in raw_links:
            if not isinstance(link, dict):
                continue
            source = link.get("source")
            target = link.get("target")
            if not source or not target:
                continue
            links.append({
                "source": source,
                "target": target,
                "relation": link.get("relation"),
            })

        return {"nodes": nodes, "links": links}

    def _normalize_timeline(self, timeline: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Normalize timeline events to match response schema."""
        normalized = []
        for idx, event in enumerate(timeline):
            if not isinstance(event, dict):
                continue
            timestamp = event.get("timestamp")
            if timestamp is None:
                timestamp = 0
            time_str = event.get("time") or self._format_timestamp(timestamp)
            normalized.append({
                "id": event.get("id") or f"event_{idx + 1}",
                "time": time_str,
                "timestamp": timestamp,
                "title": event.get("title") or "",
                "description": event.get("description") or "",
                "source_id": event.get("source_id") or "",
                "is_key_moment": bool(event.get("is_key_moment", False)),
                "event_type": event.get("event_type") or "STORY",
            })
        return normalized

    async def generate_conflicts(self, source_ids: List[str]) -> List[Dict[str, Any]]:
        """Generate conflict analysis."""
        cache_key = self._get_cache_key("conflicts", source_ids)
        if cache_key in self._cache:
            return self._cache[cache_key]

        source_docs = self._get_source_documents(source_ids)
        combined_text = self._build_source_summary(source_docs)

        prompt = f"""分析以下视频内容，找出主要观点冲突或分歧：

{combined_text}

请以JSON格式返回冲突列表，每个冲突包含：
- topic: 冲突主题
- severity: 严重程度 (critical/warning/info)
- viewpoint_a: 甲方观点 (包含 source_id, title, description)
- viewpoint_b: 乙方观点 (包含 source_id, title, description)
- verdict: 你的判断

请返回JSON数组格式。"""

        response = await self.sophnet.chat(
            messages=[{"role": "user", "content": prompt}],
            model="DeepSeek-V3.2",
        )

        try:
            # Clean up markdown code blocks if present
            cleaned = response.strip()
            if cleaned.startswith("```"):
                # Remove markdown code block markers
                lines = cleaned.split("\n")
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].startswith("```"):
                    lines = lines[:-1]
                cleaned = "\n".join(lines).strip()
            
            conflicts = json.loads(cleaned)
            if not isinstance(conflicts, list):
                conflicts = [conflicts]
            conflicts = self._normalize_conflicts(conflicts)
            self._cache[cache_key] = conflicts
        except json.JSONDecodeError:
            conflicts = []
            logger.warning(f"Failed to parse conflict analysis. Response: {response[:200]}")

        return conflicts

    async def generate_graph(self, source_ids: List[str]) -> Dict[str, Any]:
        """Generate knowledge graph."""
        cache_key = self._get_cache_key("graph", source_ids)
        if cache_key in self._cache:
            return self._cache[cache_key]

        source_docs = self._get_source_documents(source_ids)
        combined_text = self._build_source_summary(source_docs)

        prompt = f"""从以下内容中提取实体和关系，构建知识图谱：

{combined_text}

请提取所有实体（人物、地点、物品、事件等）和它们之间的关系。
以JSON格式返回：
- nodes: 实体列表 (id, name, category)
- links: 关系列表 (source, target, relation)

请返回JSON对象。"""

        response = await self.sophnet.chat(
            messages=[{"role": "user", "content": prompt}],
            model="DeepSeek-V3.2",
        )

        try:
            # Clean up markdown code blocks if present
            cleaned = response.strip()
            if cleaned.startswith("```"):
                lines = cleaned.split("\n")
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].startswith("```"):
                    lines = lines[:-1]
                cleaned = "\n".join(lines).strip()
            
            graph = json.loads(cleaned)
            graph = self._normalize_graph(graph)
            self._cache[cache_key] = graph
        except json.JSONDecodeError:
            graph = {"nodes": [], "links": []}
            logger.warning(f"Failed to parse graph analysis. Response: {response[:200]}")

        return graph

    async def generate_timeline(self, source_ids: List[str]) -> Dict[str, Any]:
        """Generate timeline events."""
        cache_key = self._get_cache_key("timeline", source_ids)
        if cache_key in self._cache:
            return self._cache[cache_key]

        source_docs = self._get_source_documents(source_ids)
        combined_text = self._build_source_summary(source_docs)

        prompt = f"""从以下内容中提取时间线事件：

{combined_text}

请提取关键事件，按时间顺序排列。
以JSON格式返回事件列表，每个事件包含：
- id: 事件ID
- time: 格式化时间 (MM:SS)
- timestamp: 时间戳(秒)
- title: 事件标题
- description: 事件描述
- is_key_moment: 是否为关键时刻
- event_type: 事件类型 (STORY/COMBAT/EXPLORE)

请返回JSON数组。"""

        response = await self.sophnet.chat(
            messages=[{"role": "user", "content": prompt}],
            model="DeepSeek-V3.2",
        )

        try:
            # Clean up markdown code blocks if present
            cleaned = response.strip()
            if cleaned.startswith("```"):
                lines = cleaned.split("\n")
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].startswith("```"):
                    lines = lines[:-1]
                cleaned = "\n".join(lines).strip()
            
            timeline = json.loads(cleaned)
            if not isinstance(timeline, list):
                timeline = []
            timeline = self._normalize_timeline(timeline)
            self._cache[cache_key] = timeline
        except json.JSONDecodeError:
            timeline = []
            logger.warning(f"Failed to parse timeline. Response: {response[:200]}")

        return {"timeline": timeline}

    async def extract_entities_from_source(
        self,
        source_id: str
    ) -> List:
        """从视频源抽取实体并持久化

        Args:
            source_id: 视频源ID

        Returns:
            抽取到的实体列表
        """
        from app.core.database import async_session
        from app.modules.analysis.dao import EntityDAO, EntityMentionDAO
        from app.models.models import Entity, Evidence
        from sqlalchemy import select

        async with async_session() as session:
            entity_dao = EntityDAO(session)
            mention_dao = EntityMentionDAO(session)

            # 首先尝试从数据库的Evidence表获取转写文本
            result = await session.execute(
                select(Evidence)
                .where(Evidence.source_id == source_id)
                .where(Evidence.text_content != None)
                .where(Evidence.text_content != "")
                .order_by(Evidence.start_time)
            )
            evidences = result.scalars().all()

            # 构建文档列表
            documents = []
            for ev in evidences:
                if ev.text_content and ev.text_content.strip():
                    documents.append({
                        "text": ev.text_content.strip(),
                        "metadata": {
                            "source_id": source_id,
                            "start": ev.start_time,
                            "end": ev.end_time,
                        }
                    })

            # 如果数据库没有，尝试从向量存储获取
            if not documents:
                try:
                    source_docs = self._get_source_documents([source_id])
                    documents = source_docs.get(source_id, [])
                except Exception as e:
                    logger.warning(f"[AnalysisService] Vector store unavailable: {e}")

            if not documents:
                logger.warning(f"[AnalysisService] No documents found for source {source_id}")
                return []

            # 构建文本
            texts = [d.get("text", "") for d in documents[:20] if d.get("text")]
            if not texts:
                logger.warning(f"[AnalysisService] No text content found for source {source_id}")
                return []

            combined_text = "\n\n".join(texts)

            # 使用LLM抽取实体
            prompt = f"""从以下内容中提取所有实体（人物、地点、组织、事件等）。

{combined_text[:2000]}

请以JSON格式返回：
{{
  "entities": [
    {{"name": "实体名", "type": "PERSON|LOCATION|ORGANIZATION|EVENT|OTHER", "description": "简短描述"}}
  ]
}}
只返回JSON，不要其他内容。"""

            try:
                response = await self.sophnet.chat(
                    messages=[{"role": "user", "content": prompt}],
                    model="DeepSeek-V3.2"
                )

                cleaned = self._clean_llm_json(response)
                data = json.loads(cleaned)
                entities_data = data.get("entities", [])

                entities = []
                for entity_data in entities_data:
                    name = entity_data.get("name", "").strip()
                    if not name:
                        continue

                    # 检查是否已存在
                    existing = await entity_dao.find_by_name(name)
                    if existing:
                        # 更新提及次数和时间
                        existing[0].mention_count += 1
                        existing[0].last_seen_at = datetime.utcnow()
                        entities.append(existing[0])

                        # 创建新的提及记录
                        await mention_dao.create(
                            entity_id=existing[0].id,
                            source_id=source_id,
                            timestamp=documents[0].get("metadata", {}).get("start", 0),
                            context=documents[0].get("text", "")[:200]
                        )
                        continue

                    # 创建新实体
                    entity = await entity_dao.create(
                        name=name,
                        type=entity_data.get("type", "OTHER"),
                        description=entity_data.get("description", ""),
                        canonical_name=name.lower()
                    )
                    entities.append(entity)

                    # 创建提及记录
                    await mention_dao.create(
                        entity_id=entity.id,
                        source_id=source_id,
                        timestamp=documents[0].get("metadata", {}).get("start", 0),
                        context=documents[0].get("text", "")[:200]
                    )

                await session.commit()
                logger.info(f"[AnalysisService] Extracted {len(entities)} entities from source {source_id}")
                return entities

            except Exception as e:
                logger.error(f"[AnalysisService] Failed to extract entities: {e}")
                logger.error(traceback.format_exc())
                return []

    async def generate_analysis(
        self,
        source_ids: List[str],
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """Generate complete analysis."""
        if not use_cache:
            self._cache.clear()

        conflicts = await self.generate_conflicts(source_ids)
        graph = await self.generate_graph(source_ids)
        timeline_result = await self.generate_timeline(source_ids)

        return {
            "conflicts": conflicts,
            "graph": graph,
            "timeline": timeline_result.get("timeline", []),
        }

    async def generate_one_pager(
        self,
        source_ids: List[str],
        use_cache: bool = True,
    ) -> Dict[str, Any]:
        """Generate a one-pager report."""
        cache_key = self._get_cache_key("one_pager", source_ids)
        if use_cache and cache_key in self._cache:
            return self._cache[cache_key]

        source_docs = self._get_source_documents(source_ids, limit_per_source=30)
        combined_text = self._build_source_summary(source_docs)

        if combined_text == "No content available":
            result = self._fallback_one_pager(source_ids, source_docs)
            self._cache[cache_key] = result
            return result

        prompt = f"""请基于以下内容生成一页纸简报，返回严格的 JSON 对象，字段包括：
headline (string), tldr (string), insights (string数组，3-5条),
conceptual_image (string或null), evidence_items (数组，每项含 url, caption, related_insight_index),
evidence_images (string数组), generated_at (ISO时间字符串), source_ids (string数组), video_titles (string数组)。

仅返回 JSON，不要添加任何额外说明。

内容如下：
{combined_text}
"""

        response = await self.sophnet.chat(
            messages=[{"role": "user", "content": prompt}],
            model="DeepSeek-V3.2",
        )

        if response.strip() == "API key not configured":
            result = self._fallback_one_pager(source_ids, source_docs)
            self._cache[cache_key] = result
            return result

        try:
            cleaned = self._clean_llm_json(response)
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            result = self._fallback_one_pager(source_ids, source_docs)
            self._cache[cache_key] = result
            return result

        evidence_items = []
        for item in data.get("evidence_items", []) or []:
            if not isinstance(item, dict):
                continue
            url = self._static_url_if_exists(item.get("url"))
            if not url:
                continue
            evidence_items.append({
                "url": url,
                "caption": item.get("caption", ""),
                "related_insight_index": item.get("related_insight_index"),
            })

        evidence_images = []
        for url in data.get("evidence_images", []) or []:
            static_url = self._static_url_if_exists(url)
            if static_url:
                evidence_images.append(static_url)

        conceptual_image = self._static_url_if_exists(data.get("conceptual_image"))

        if not evidence_items and not evidence_images:
            fallback = self._fallback_one_pager(source_ids, source_docs)
            evidence_items = fallback.get("evidence_items", [])
            evidence_images = fallback.get("evidence_images", [])

        result = {
            "headline": data.get("headline", "视频洞察简报"),
            "tldr": data.get("tldr", ""),
            "insights": data.get("insights", []) or [],
            "conceptual_image": conceptual_image,
            "evidence_items": evidence_items,
            "evidence_images": evidence_images,
            "generated_at": data.get("generated_at") or datetime.utcnow().isoformat(),
            "source_ids": data.get("source_ids") or source_ids,
            "video_titles": data.get("video_titles", []) or [],
        }

        self._cache[cache_key] = result
        return result


_analysis_service: Optional[AnalysisService] = None


def get_analysis_service() -> AnalysisService:
    """Get or create AnalysisService singleton."""
    global _analysis_service
    if _analysis_service is None:
        _analysis_service = AnalysisService()
    return _analysis_service
