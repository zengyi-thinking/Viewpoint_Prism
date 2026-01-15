"""
Chat service - RAG-based conversation with video content.
"""

import json
import logging
from typing import List, Dict, Any, Optional, Generator
from pathlib import Path

from app.shared.perception import get_sophnet_service
from app.shared.storage import get_vector_store

logger = logging.getLogger(__name__)


class ChatService:
    """RAG-based chat service for video intelligence."""

    def __init__(self):
        """Initialize with services."""
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
        """Build context string from search results."""
        if not results:
            return "没有找到相关的视频片段。"

        context_parts = []
        for i, r in enumerate(results, 1):
            metadata = r.get("metadata", {})
            source_id = metadata.get("source_id", "unknown")
            start_time = metadata.get("start", 0)
            video_title = source_titles.get(source_id, metadata.get("video_title", "Unknown"))
            text = r.get("text", "")

            context_parts.append(
                f"[{i}] [{video_title} {self._format_timestamp(start_time)}]\n{text}"
            )

        return "\n\n".join(context_parts)

    async def chat_with_video(
        self,
        query: str,
        source_ids: List[str],
        n_results: int = 10
    ) -> Dict[str, Any]:
        """Chat with video content using RAG."""
        vector_store = get_vector_store()

        source_titles = {}
        for sid in source_ids:
            docs = vector_store.get_source_documents(sid)
            if docs:
                source_titles[sid] = docs[0].get("metadata", {}).get("video_title", f"Source {sid}")

        results = vector_store.search(query=query, source_ids=source_ids, n_results=n_results)
        if not results:
            # Fallback to recent documents when query has no direct matches.
            fallback_docs = []
            for sid in source_ids:
                docs = vector_store.get_source_documents(sid)
                docs.sort(key=lambda x: x.get("metadata", {}).get("start", 0))
                fallback_docs.extend(docs[:3])
            results = fallback_docs[:n_results]

        context = self._build_context(results, source_titles)

        prompt = f"""根据以下视频内容回答用户的问题。如果内容不相关，请说明。

=== 视频内容 ===
{context}

=== 用户问题 ===
{query}

请给出回答，并在引用相关片段时使用 [视频标题 MM:SS] 格式。"""

        response = await self.sophnet.chat(
            messages=[{"role": "user", "content": prompt}],
            model=self.model,
        )

        references = [
            {
                "source_id": r.get("metadata", {}).get("source_id", ""),
                "timestamp": r.get("metadata", {}).get("start", 0),
                "text": r.get("text", "")[:200],
            }
            for r in results[:5]
        ]

        return {
            "content": response,
            "references": references,
        }

    async def chat_with_video_stream(
        self,
        query: str,
        source_ids: List[str],
        n_results: int = 10
    ) -> Generator[str, None, None]:
        """Stream chat response."""
        vector_store = get_vector_store()
        results = vector_store.search(query=query, source_ids=source_ids, n_results=n_results)
        if not results:
            fallback_docs = []
            for sid in source_ids:
                docs = vector_store.get_source_documents(sid)
                docs.sort(key=lambda x: x.get("metadata", {}).get("start", 0))
                fallback_docs.extend(docs[:3])
            results = fallback_docs[:n_results]

        source_titles = {}
        for sid in source_ids:
            docs = vector_store.get_source_documents(sid)
            if docs:
                source_titles[sid] = docs[0].get("metadata", {}).get("video_title", f"Source {sid}")

        context = self._build_context(results, source_titles)

        yield json.dumps({"references": results[:5]}) + "\n"

        prompt = f"""根据以下视频内容回答用户的问题。

=== 视频内容 ===
{context}

=== 用户问题 ===
{query}

请给出回答。"""

        response = await self.sophnet.chat(
            messages=[{"role": "user", "content": prompt}],
            model=self.model,
        )

        yield json.dumps({"content": response, "done": True}) + "\n"

    async def generate_context_bridge(
        self,
        source_id: str,
        target_timestamp: float,
        previous_timestamp: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Generate context bridge when user seeks in video."""
        vector_store = get_vector_store()
        docs = vector_store.get_source_documents(source_id)

        if not docs:
            return {
                "summary": "No content available",
                "previous_context": "",
                "current_context": "",
                "timestamp_str": self._format_timestamp(target_timestamp),
            }

        target_doc = None
        for doc in docs:
            start = doc.get("metadata", {}).get("start", 0)
            if abs(start - target_timestamp) < 5:
                target_doc = doc
                break

        current_context = ""
        if target_doc:
            current_context = target_doc.get("text", "")[:300]

        previous_context = ""
        if previous_timestamp:
            for doc in docs:
                start = doc.get("metadata", {}).get("start", 0)
                if abs(start - previous_timestamp) < 5:
                    previous_context = doc.get("text", "")[:300]
                    break

        if not previous_context:
            docs_before = [d for d in docs if d.get("metadata", {}).get("start", 0) < target_timestamp]
            if docs_before:
                previous_context = docs_before[-1].get("text", "")[:300]

        summary = f"从 {previous_context[:50] if previous_context else '开始'} 到现在..."

        return {
            "summary": summary,
            "previous_context": previous_context,
            "current_context": current_context,
            "timestamp_str": self._format_timestamp(target_timestamp),
        }


_chat_service: Optional[ChatService] = None


def get_chat_service() -> ChatService:
    """Get or create ChatService singleton."""
    global _chat_service
    if _chat_service is None:
        _chat_service = ChatService()
    return _chat_service
