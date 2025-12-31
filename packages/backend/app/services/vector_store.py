"""ChromaDB vector store service."""
import logging
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings as ChromaSettings

from app.core import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class VectorStore:
    """ChromaDB wrapper for RAG retrieval."""

    def __init__(self):
        self.client = chromadb.PersistentClient(
            path=settings.chroma_db_dir,
            settings=ChromaSettings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        self._collection = None

    @property
    def collection(self):
        """Get or create default collection."""
        if self._collection is None:
            self._collection = self.client.get_or_create_collection(
                name="viewpoint_prism",
                metadata={"hnsw:space": "cosine"}
            )
        return self._collection

    def add_chunks(
        self,
        chunks: List[Dict[str, Any]],
        embeddings: List[List[float]]
    ):
        """Add chunks with embeddings to collection."""
        if not chunks:
            return

        ids = [c["id"] for c in chunks]
        documents = [c["text"] for c in chunks]
        metadatas = [c["metadata"] for c in chunks]

        self.collection.add(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas
        )

        logger.info(f"Added {len(chunks)} chunks to vector store")

    def query(
        self,
        query_text: str,
        query_embedding: List[float],
        n_results: int = 10,
        where: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Query similar chunks."""
        results = self.collection.query(
            query_embeddings=[query_embedding],
            query_texts=[query_text],
            n_results=n_results,
            where=where
        )
        return results

    def delete_source_chunks(self, source_id: str):
        """Delete all chunks for a source."""
        try:
            # Get all chunks with this source_id
            results = self.collection.get(
                where={"source_id": source_id}
            )

            if results and results["ids"]:
                self.collection.delete(ids=results["ids"])
                logger.info(f"Deleted {len(results['ids'])} chunks for {source_id}")

        except Exception as e:
            logger.error(f"Delete error: {e}")

    def get_collection_stats(self) -> Dict[str, Any]:
        """Get collection statistics."""
        try:
            count = self.collection.count()
            return {
                "total_chunks": count,
                "collection_name": "viewpoint_prism"
            }
        except Exception as e:
            logger.error(f"Stats error: {e}")
            return {"total_chunks": 0, "collection_name": "viewpoint_prism"}


# Singleton
_vector_store: Optional[VectorStore] = None


def get_vector_store() -> VectorStore:
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store
