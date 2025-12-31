"""RAG (Retrieval Augmented Generation) service."""
import logging
from typing import List, Dict, Any
import json

from app.services.intelligence import get_intelligence_service
from app.services.vector_store import get_vector_store
from app.models.models import Source

logger = logging.getLogger(__name__)


class RAGService:
    """RAG chat service with citations."""

    def __init__(self):
        self.intel = get_intelligence_service()
        self.vector_store = get_vector_store()

    def format_citation(self, source_id: str, timestamp: float) -> str:
        """Format citation as [SourceID MM:SS]."""
        mins = int(timestamp // 60)
        secs = int(timestamp % 60)
        return f"[{source_id} {mins:02d}:{secs:02d}]"

    async def chat(
        self,
        question: str,
        source_ids: List[str],
        session_id: str
    ) -> Dict[str, Any]:
        """
        RAG chat with citations.

        Returns:
            {content, references}
        """
        # Generate query embedding
        query_emb = await self.intel.generate_embeddings([question])
        if not query_emb or not query_emb[0]:
            return {
                "content": "抱歉，暂时无法回答这个问题。",
                "references": []
            }

        # Query relevant chunks
        results = self.vector_store.query(
            query_text=question,
            query_embedding=query_emb[0],
            n_results=10,
            where={"source_id": {"$in": source_ids}} if source_ids else None
        )

        if not results or not results["ids"][0]:
            return {
                "content": "没有找到相关内容，请确保已上传并分析视频。",
                "references": []
            }

        # Format context with citations
        context_parts = []
        references = []

        for i, (doc, meta) in enumerate(zip(
            results["documents"][0],
            results["metadatas"][0]
        )):
            source_id = meta.get("source_id", "unknown")
            timestamp = meta.get("timestamp", 0)
            chunk_type = meta.get("type", "asr")

            citation = self.format_citation(source_id, timestamp)
            context_parts.append(f"{i+1}. {citation} {doc}")

            references.append({
                "source_id": source_id,
                "timestamp": timestamp,
                "text": doc[:100]
            })

        context = "\n".join(context_parts)

        # Build prompt
        messages = [
            {
                "role": "system",
                "content": "你是一个视频情报助手。请基于以下检索到的片段（包含时间戳）回答用户问题。\n"
                          "**必须**在回答中引用证据来源，格式严格为：[SourceID MM:SS]。\n"
                          "如果片段中有视觉描述（Visual: ...），请结合画面信息增强回答的可信度。"
            },
            {
                "role": "user",
                "content": f"检索到的片段:\n{context}\n\n用户问题: {question}"
            }
        ]

        # LLM completion
        result = await self.intel.chat_completion(messages)
        if not result:
            return {
                "content": "生成回答时出错，请稍后重试。",
                "references": references
            }

        content = result.output["choices"][0]["message"]["content"]

        return {
            "content": content,
            "references": references
        }


# Singleton
_rag_service: RAGService | None = None


def get_rag_service() -> RAGService:
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService()
    return _rag_service
