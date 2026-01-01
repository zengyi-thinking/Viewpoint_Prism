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


    async def generate_context_bridge(
        self,
        source_id: str,
        target_timestamp: float,
        previous_timestamp: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Generate a context bridge summary when user seeks to a new timestamp.

        This helps users understand what happened before and what's happening now,
        acting as a "Second Brain" feature for video navigation.

        Args:
            source_id: Video source ID
            target_timestamp: The timestamp user jumped to (in seconds)
            previous_timestamp: Optional - where user was before seeking

        Returns:
            Dict with summary, previous_context, current_context, timestamp_str
        """
        try:
            logger.info(f"Context Bridge: source_id={source_id}, target={target_timestamp}, previous={previous_timestamp}")

            # Format timestamp for display
            timestamp_str = self._format_timestamp(target_timestamp)

            # Step 1: Get events/segments before the target timestamp
            # Search for content in the range [max(0, target-300), target]
            window_start = max(0, target_timestamp - 300)  # Look back up to 5 minutes
            window_end = target_timestamp

            # Query vector store for content before target timestamp
            before_results = self.vector_store.collection.get(
                where={
                    "$and": [
                        {"source_id": {"$eq": source_id}},
                        {"start": {"$gte": window_start}},
                        {"start": {"$lt": window_end}}
                    ]
                },
                include=["documents", "metadatas"]
            )

            # Query vector store for content at/after target timestamp
            # Look ahead up to 2 minutes
            after_results = self.vector_store.collection.get(
                where={
                    "$and": [
                        {"source_id": {"$eq": source_id}},
                        {"start": {"$gte": window_end}},
                        {"start": {"$lt": window_end + 120}}
                    ]
                },
                include=["documents", "metadatas"]
            )

            # Extract and organize content
            before_content = []
            if before_results and before_results.get("documents"):
                for i, doc in enumerate(before_results["documents"][:10]):  # Max 10 items
                    meta = before_results["metadatas"][i] if before_results.get("metadatas") else {}
                    start_time = meta.get("start", 0)
                    doc_type = meta.get("type", "unknown")
                    time_str = self._format_timestamp(start_time)
                    before_content.append(f"[{time_str}] ({doc_type}): {doc[:100]}")

            after_content = []
            if after_results and after_results.get("documents"):
                for i, doc in enumerate(after_results["documents"][:5]):  # Max 5 items
                    meta = after_results["metadatas"][i] if after_results.get("metadatas") else {}
                    start_time = meta.get("start", 0)
                    doc_type = meta.get("type", "unknown")
                    time_str = self._format_timestamp(start_time)
                    after_content.append(f"[{time_str}] ({doc_type}): {doc[:100]}")

            # Build context prompt
            before_text = "\n".join(before_content) if before_content else "无此前内容"
            after_text = "\n".join(after_content) if after_content else "无后续内容"

            # If we have previous_timestamp, provide more context
            prev_context = ""
            if previous_timestamp is not None:
                jump_distance = abs(target_timestamp - previous_timestamp)
                if jump_distance > 60:
                    prev_time_str = self._format_timestamp(previous_timestamp)
                    prev_context = f"\n用户从 {prev_time_str} 跳转到当前时间点，跳过了 {int(jump_distance)} 秒的内容。"

            # Generate bridging summary using SophNet
            system_prompt = """你是视界棱镜的"哲思导师"助手。当用户在视频中跳转时，你生成简短的"前情提要"帮助用户衔接上下文。

## 你的角色：
- 不是枯燥的摘要生成器，而是引导者
- 帮助用户快速理解"之前发生了什么"和"现在到了哪里"
- 语言简洁、友好、具有引导性

## 输出格式：
用1-2句话生成转场介绍：
- 第一句：概括此前的主要内容（如果有的话）
- 第二句：说明现在进入的场景/话题

## 示例：
- "此前玩家击败了低手，获得了一些装备。现在来到了一个新的区域，面临更强大的敌人。"
- "刚才我们学习了基础操作。接下来将进入实战演练环节。"

限制：最多100字，简洁明了。"""

            user_prompt = f"""用户跳转到了视频的 {timestamp_str} 位置。{prev_context}

## 此前内容（跳转点之前）：
{before_text}

## 当前内容（跳转点附近）：
{after_text}

请生成一段简短的转场介绍，帮助用户衔接上下文。注意：如果此前内容为空，则重点介绍当前场景。"""

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]

            summary = await self.sophnet.chat(
                messages=messages,
                model=self.model,
                temperature=0.7,
                max_tokens=150,  # Short response for UX
            )

            # Clean up the summary (remove common prefixes)
            summary = summary.strip()
            for prefix in ["好的，", "当然，", "以下是", "好的："]:
                if summary.startswith(prefix):
                    summary = summary[len(prefix):].strip()

            # Build structured context strings
            previous_summary = ""
            if before_content:
                # Get a brief summary of what happened before
                if len(before_content) > 0:
                    earliest = before_content[0]
                    latest = before_content[-1]
                    previous_summary = f"从 {earliest.split(']')[0][1:]} 到 {latest.split(']')[0][1:]} 的内容"

            current_summary = ""
            if after_content:
                if len(after_content) > 0:
                    next_item = after_content[0]
                    current_summary = f"即将进入 {next_item.split(']')[0][1:]} 的内容"

            logger.info(f"Context Bridge generated: '{summary[:50]}...'")

            return {
                "summary": summary,
                "previous_context": previous_summary or "视频开头",
                "current_context": current_summary or f"{timestamp_str} 位置",
                "timestamp_str": timestamp_str,
            }

        except Exception as e:
            logger.error(f"Context bridge generation error: {e}")
            # Return a fallback response
            return {
                "summary": f"跳转到 {timestamp_str} 位置。",
                "previous_context": "未知",
                "current_context": f"{timestamp_str}",
                "timestamp_str": timestamp_str,
            }


# Singleton instance
_rag_service: Optional[RAGService] = None


def get_rag_service() -> RAGService:
    """Get or create RAGService singleton."""
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService()
    return _rag_service
