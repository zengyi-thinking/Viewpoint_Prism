"""
RAG (Retrieval-Augmented Generation) Service
Handles chat with video content using vector search and SophNet LLM.
"""

import json
import logging
from typing import List, Dict, Any, Optional, Generator

from app.services.sophnet_service import get_sophnet_service
from app.services.vector_store import get_vector_store

logger = logging.getLogger(__name__)


class RAGService:
    """RAG-based chat service for video intelligence using SophNet."""

    def __init__(self):
        """Initialize with SophNet service."""
        self.sophnet = get_sophnet_service()
        self.vector_store = get_vector_store()
        self.model = "DeepSeek-V3.2"

    def _format_timestamp(self, seconds: float) -> str:
        """Convert seconds to MM:SS format."""
        if seconds is None or seconds < 0:
            return "00:00"
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins:02d}:{secs:02d}"

    def _build_context(
        self,
        results: List[Dict[str, Any]],
        source_titles: Dict[str, str]
    ) -> str:
        """
        Build context string from search results.

        Args:
            results: Search results from vector store
            source_titles: Mapping of source_id to video title

        Returns:
            Formatted context string
        """
        if not results:
            return "没有找到相关的视频片段。"

        context_parts = []
        for i, r in enumerate(results, 1):
            metadata = r.get("metadata", {})
            source_id = metadata.get("source_id", "unknown")
            doc_type = metadata.get("type", "unknown")
            start_time = metadata.get("start", 0)
            video_title = source_titles.get(source_id, metadata.get("video_title", "Unknown"))
            text = r.get("text", "")

            timestamp_str = self._format_timestamp(start_time)

            # Format based on document type
            if doc_type == "visual":
                context_parts.append(
                    f"[{i}] 视觉描述 [{video_title} {timestamp_str}]: {text}"
                )
            else:
                context_parts.append(
                    f"[{i}] 语音内容 [{video_title} {timestamp_str}]: {text}"
                )

        return "\n".join(context_parts)

    def _build_system_prompt(self) -> str:
        """Build the system prompt for RAG chat."""
        return """你是一个专业的视频情报助手，名为"视界棱镜"。你的任务是基于检索到的视频片段回答用户的问题。

## 核心要求：
1. **必须引用证据来源**：在回答中，使用格式 `[视频标题 MM:SS]` 标注信息来源
2. **综合多源信息**：如果多个视频提供了相关信息，请综合分析
3. **区分类型**：视觉描述描述的是画面内容，语音内容是说话者说的话
4. **客观准确**：只基于提供的片段回答，不要编造信息
5. **简洁专业**：回答应该清晰、有条理

## 引用格式示例：
- 根据视频分析，[教程视频A 03:20]提到了这个技巧...
- 画面显示[演示视频 05:45]中的操作步骤...

请基于提供的视频片段回答用户问题。"""

    async def chat_with_video(
        self,
        query: str,
        source_ids: Optional[List[str]] = None,
        n_results: int = 15
    ) -> Dict[str, Any]:
        """
        Chat with video content using RAG.

        Args:
            query: User's question
            source_ids: Optional list of source IDs to search
            n_results: Number of search results to retrieve

        Returns:
            Dict with response content and references
        """
        try:
            # Step 1: Check if vector store has any data
            total_docs = self.vector_store.collection.count()
            logger.info(f"RAG Query: {query}, sources: {source_ids}, total_docs_in_db: {total_docs}")

            if total_docs == 0:
                return {
                    "content": "抱歉，知识库中没有任何视频数据。请确保视频已完成处理（状态为\"就绪\"），或尝试重新处理视频。\n\n提示：可以在视频源列表中点击\"重新处理\"按钮来重新索引视频内容。",
                    "references": [],
                    "context_used": []
                }

            # Step 2: Retrieve relevant documents
            results = self.vector_store.search(
                query=query,
                source_ids=source_ids,
                n_results=n_results
            )

            # DEBUG: Log retrieved results with scores
            if results:
                logger.info(f"RAG: Retrieved {len(results)} results for query='{query[:50]}...'")
                for i, r in enumerate(results[:3]):  # Log top 3
                    metadata = r.get("metadata", {})
                    distance = r.get("distance", 0)
                    logger.info(f"  [{i+1}] distance={distance:.3f}, source_id={metadata.get('source_id', 'unknown')[:8]}..., type={metadata.get('type', 'unknown')}, text_preview={r.get('text', '')[:50]}...")
            else:
                logger.warning(f"RAG: No results found for query='{query[:50]}...', source_ids={source_ids}")

            if not results:
                # Check if the specific sources have data
                if source_ids:
                    available_sources = set()
                    all_results = self.vector_store.collection.get(include=['metadatas'])
                    for m in (all_results.get('metadatas') or []):
                        if m and 'source_id' in m:
                            available_sources.add(m['source_id'])

                    missing_sources = set(source_ids) - available_sources
                    if missing_sources:
                        return {
                            "content": f"抱歉，选中的视频尚未完成内容索引。\n\n未索引的视频ID: {', '.join(list(missing_sources)[:3])}...\n\n请尝试：\n1. 等待视频处理完成\n2. 重新处理视频（调用 /api/sources/{{source_id}}/reprocess）\n3. 选择其他已处理完成的视频",
                            "references": [],
                            "context_used": []
                        }

                return {
                    "content": "抱歉，没有找到与您问题相关的视频内容。请尝试其他问题，或确保已上传并处理了视频。",
                    "references": [],
                    "context_used": []
                }

            # Build source title mapping
            source_titles = {}
            for r in results:
                sid = r.get("metadata", {}).get("source_id", "")
                title = r.get("metadata", {}).get("video_title", "")
                if sid and title:
                    source_titles[sid] = title

            # Step 3: Build context
            context = self._build_context(results, source_titles)

            # Step 4: Generate response using SophNet DeepSeek
            messages = [
                {"role": "system", "content": self._build_system_prompt()},
                {"role": "user", "content": f"## 检索到的视频片段：\n{context}\n\n## 用户问题：\n{query}"}
            ]

            content = await self.sophnet.chat(
                messages=messages,
                model=self.model,
                temperature=0.7,
                max_tokens=1500,
            )

            # Step 5: Extract references from context
            references = []
            for r in results[:5]:  # Top 5 as references
                metadata = r.get("metadata", {})
                references.append({
                    "source_id": metadata.get("source_id", ""),
                    "timestamp": metadata.get("start", 0),
                    "text": r.get("text", "")[:100],
                    "type": metadata.get("type", "unknown"),
                    "video_title": source_titles.get(metadata.get("source_id", ""), "")
                })

            logger.info(f"RAG response generated, {len(references)} references")

            return {
                "content": content,
                "references": references,
                "context_used": [r.get("text", "")[:200] for r in results[:3]]
            }

        except Exception as e:
            logger.error(f"RAG chat error: {e}")
            return {
                "content": f"抱歉，处理您的问题时出现错误: {str(e)}",
                "references": [],
                "context_used": []
            }

    async def chat_with_video_stream(
        self,
        query: str,
        source_ids: Optional[List[str]] = None,
        n_results: int = 15
    ) -> Generator[str, None, None]:
        """
        Stream chat response with video content.

        Note: SophNet doesn't support streaming yet, so this yields the complete response.

        Args:
            query: User's question
            source_ids: Optional list of source IDs to search
            n_results: Number of search results to retrieve

        Yields:
            Response chunks as SSE format
        """
        try:
            # Step 1: Retrieve relevant documents
            logger.info(f"RAG Stream Query: {query}")

            results = self.vector_store.search(
                query=query,
                source_ids=source_ids,
                n_results=n_results
            )

            if not results:
                yield "data: " + json.dumps({
                    "content": "抱歉，没有找到与您问题相关的视频内容。",
                    "done": True
                }) + "\n\n"
                return

            # Build source title mapping
            source_titles = {}
            for r in results:
                sid = r.get("metadata", {}).get("source_id", "")
                title = r.get("metadata", {}).get("video_title", "")
                if sid and title:
                    source_titles[sid] = title

            # Build context
            context = self._build_context(results, source_titles)

            # Send references first
            references = []
            for r in results[:5]:
                metadata = r.get("metadata", {})
                references.append({
                    "source_id": metadata.get("source_id", ""),
                    "timestamp": metadata.get("start", 0),
                    "text": r.get("text", "")[:100],
                    "type": metadata.get("type", "unknown"),
                    "video_title": source_titles.get(metadata.get("source_id", ""), "")
                })

            yield "data: " + json.dumps({"references": references}) + "\n\n"

            # Step 2: Generate response (non-streaming for now)
            messages = [
                {"role": "system", "content": self._build_system_prompt()},
                {"role": "user", "content": f"## 检索到的视频片段：\n{context}\n\n## 用户问题：\n{query}"}
            ]

            content = await self.sophnet.chat(
                messages=messages,
                model=self.model,
                temperature=0.7,
                max_tokens=1500,
            )

            # Yield the complete response as chunks to simulate streaming
            for char in content:
                yield "data: " + json.dumps({
                    "content": char,
                    "done": False
                }) + "\n\n"

            yield "data: " + json.dumps({"content": "", "done": True}) + "\n\n"

        except Exception as e:
            logger.error(f"RAG stream error: {e}")
            yield "data: " + json.dumps({
                "content": f"错误: {str(e)}",
                "done": True,
                "error": True
            }) + "\n\n"


# Singleton instance
_rag_service: Optional[RAGService] = None


def get_rag_service() -> RAGService:
    """Get or create RAGService singleton."""
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService()
    return _rag_service
