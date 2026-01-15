"""
Vector Store Service - Qdrant-based storage for video intelligence.
Migrated from ChromaDB to Qdrant for better cross-platform compatibility.
"""

import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import logging
import uuid

from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.models import (
    Distance,
    VectorParams,
    PointStruct,
    KeywordIndexParams,
    KeywordIndexType,
)
from sentence_transformers import SentenceTransformer

from app.core import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

COLLECTION_NAME = "video_knowledge"
VECTOR_SIZE = 384  # MiniLM embedding size


@dataclass
class VectorStoreConfig:
    """Vector store configuration."""
    host: str = "localhost"
    port: int = 6333
    prefer_grpc: bool = False
    collection_name: str = COLLECTION_NAME
    vector_size: int = VECTOR_SIZE


class VectorStore:
    """
    Qdrant-based vector storage for video intelligence.

    Provides:
    - Vector similarity search
    - Metadata filtering
    - CRUD operations for video segments
    """

    def __init__(
        self,
        host: str = None,
        port: int = None,
        prefer_grpc: bool = False,
        persist_dir: Optional[str] = None
    ):
        """Initialize Qdrant client."""
        config = get_settings()
        host = host or getattr(config, 'vector_store_host', 'localhost')
        port = port or getattr(config, 'vector_store_port', 6333)

        self.host = host
        self.port = port
        self.collection_name = COLLECTION_NAME
        self.vector_size = VECTOR_SIZE

        # Initialize Qdrant client
        if prefer_grpc:
            self.client = QdrantClient(host=host, port=port, grpc_port=port + 1)
        else:
            self.client = QdrantClient(host=host, port=port)

        # Initialize embedding function
        self._init_embedding_function()

        # Ensure collection exists
        self._ensure_collection()

        logger.info(f"VectorStore initialized: {host}:{port}/{self.collection_name}")

    def _init_embedding_function(self):
        """Initialize sentence transformer embedding function."""
        try:
            self.embedding_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
            logger.info("Using multilingual sentence transformer embedding")
        except Exception as e:
            logger.warning(f"Multilingual model failed ({e}), falling back to English...")
            try:
                self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
                logger.info("Using English sentence transformer embedding")
            except Exception as e2:
                logger.error(f"Failed to initialize embedding: {e2}")
                self.embedding_model = None

    def _ensure_collection(self):
        """Create collection if it doesn't exist."""
        try:
            collections = self.client.get_collections()
            collection_names = [c.name for c in collections.collections]

            if self.collection_name not in collection_names:
                # Create collection with HNSW index
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.vector_size,
                        distance=Distance.COSINE,
                    ),
                )
                logger.info(f"Created collection: {self.collection_name}")

                # Create payload indexes for filtering using correct API
                self.client.create_payload_index(
                    collection_name=self.collection_name,
                    field_name="source_id",
                    field_schema=KeywordIndexParams(
                        type=KeywordIndexType.WORD,
                    ),
                )
                self.client.create_payload_index(
                    collection_name=self.collection_name,
                    field_name="type",
                    field_schema=KeywordIndexParams(
                        type=KeywordIndexType.WORD,
                    ),
                )
                logger.info("Created payload indexes")

        except Exception as e:
            logger.error(f"Failed to ensure collection: {e}")
            raise

    def _embed_text(self, text: str) -> List[float]:
        """Generate embedding for text."""
        if self.embedding_model:
            return self.embedding_model.encode(text).tolist()
        # Fallback: return zero vector
        return [0.0] * self.vector_size

    def _chunk_text(self, text: str, max_length: int = 500) -> List[str]:
        """Split text into smaller chunks."""
        if len(text) <= max_length:
            return [text] if text.strip() else []

        sentences = re.split(r'[。！？.!?]+', text)
        chunks = []
        current_chunk = ""

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            if len(current_chunk) + len(sentence) <= max_length:
                current_chunk += sentence + "。"
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence + "。"

        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks

    def add_video_data(
        self,
        source_id: str,
        transcripts: List[Dict[str, Any]],
        visual_descriptions: List[Dict[str, Any]],
        video_title: str = ""
    ) -> int:
        """
        Add video intelligence data to the vector store.

        Args:
            source_id: Source video ID
            transcripts: List of transcript segments
            visual_descriptions: List of visual descriptions
            video_title: Title of the video

        Returns:
            Number of documents added
        """
        points = []
        doc_count = 0

        # Process transcripts
        for segment in transcripts:
            text = segment.get("text", "").strip()
            if not text:
                continue

            chunks = self._chunk_text(text)
            for chunk in chunks:
                point_id = str(uuid.uuid4())
                vector = self._embed_text(chunk)

                payload = {
                    "source_id": source_id,
                    "type": "transcript",
                    "start": segment.get("start", 0),
                    "end": segment.get("end", 0),
                    "video_title": video_title,
                    "text": chunk,
                }

                points.append(PointStruct(
                    id=point_id,
                    vector=vector,
                    payload=payload
                ))
                doc_count += 1

        # Process visual descriptions
        for desc in visual_descriptions:
            text = desc.get("description", "").strip()
            if not text or text.startswith("Error:") or text.startswith("Analysis failed"):
                continue

            point_id = str(uuid.uuid4())
            vector = self._embed_text(text)
            timestamp = desc.get("timestamp", 0)

            payload = {
                "source_id": source_id,
                "type": "visual",
                "start": timestamp,
                "end": timestamp + 5,
                "video_title": video_title,
                "text": text,
                "frame_path": desc.get("frame_path", ""),
            }

            points.append(PointStruct(
                id=point_id,
                vector=vector,
                payload=payload
            ))
            doc_count += 1

        # Upload points in batches
        if points:
            try:
                self.client.upload_points(
                    collection_name=self.collection_name,
                    points=points,
                    batch_size=100,
                )
                logger.info(f"Added {doc_count} documents for source {source_id}")
            except Exception as e:
                logger.error(f"Failed to add documents: {e}")
                return 0

        return doc_count

    def search(
        self,
        query: str,
        source_ids: Optional[List[str]] = None,
        n_results: int = 10,
        doc_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for relevant video segments.

        Args:
            query: Search query
            source_ids: Filter by source IDs
            n_results: Number of results to return
            doc_type: Filter by document type (transcript/visual)

        Returns:
            List of search results with text, metadata, and score
        """
        logger.info(f"[VectorStore] Search: query='{query}', source_ids={source_ids}, n_results={n_results}, type={doc_type}")

        query_vector = self._embed_text(query)

        # Build filter
        must_conditions = []
        if source_ids:
            must_conditions.append(
                models.FieldCondition(
                    key="source_id",
                    match=models.MatchAny(any=source_ids),
                )
            )
        if doc_type:
            must_conditions.append(
                models.FieldCondition(
                    key="type",
                    match=models.MatchValue(value=doc_type),
                )
            )

        filter_obj = None
        if must_conditions:
            filter_obj = models.Filter(
                must=must_conditions
            )

        try:
            if hasattr(self.client, "query_points"):
                query_kwargs = {
                    "collection_name": self.collection_name,
                    "query": query_vector,
                    "limit": n_results,
                    "with_payload": True,
                    "with_vectors": False,
                }
                if filter_obj:
                    query_kwargs["query_filter"] = filter_obj
                results = self.client.query_points(**query_kwargs)
                points = results.points
            else:
                search_kwargs = {
                    "collection_name": self.collection_name,
                    "query_vector": query_vector,
                    "limit": n_results,
                    "with_payload": True,
                    "with_vectors": False,
                }
                if filter_obj:
                    search_kwargs["query_filter"] = filter_obj

                if hasattr(self.client, "search"):
                    points = self.client.search(**search_kwargs)
                elif hasattr(self.client, "search_points"):
                    points = self.client.search_points(**search_kwargs)
                else:
                    raise AttributeError("QdrantClient has no search method")

            if not points:
                fallback_docs = []
                if source_ids:
                    for sid in source_ids:
                        fallback_docs.extend(self.get_source_documents(sid))
                else:
                    fallback_docs = self.get_all_documents()
                fallback_docs = fallback_docs[:n_results]
                return [
                    {
                        "text": d.get("text", ""),
                        "metadata": d.get("metadata", {}),
                        "distance": 0.0,
                    }
                    for d in fallback_docs
                ]

            formatted_results = []
            for hit in points:
                formatted_results.append({
                    "text": hit.payload.get("text", ""),
                    "metadata": {
                        "source_id": hit.payload.get("source_id", ""),
                        "type": hit.payload.get("type", ""),
                        "start": hit.payload.get("start", 0),
                        "end": hit.payload.get("end", 0),
                        "video_title": hit.payload.get("video_title", ""),
                        "frame_path": hit.payload.get("frame_path", ""),
                    },
                    "distance": hit.score if hasattr(hit, 'score') else 0.0,
                })

            if formatted_results:
                logger.info(f"Search returned {len(formatted_results)} results")
            else:
                total = self.get_collection_count()
                logger.warning(f"No results for query, total_docs={total}")

            return formatted_results

        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []

    def get_all_documents(self) -> List[Dict[str, Any]]:
        """Get all documents from the vector store."""
        try:
            results = self.client.scroll(
                collection_name=self.collection_name,
                limit=10000,
                with_payload=True,
                with_vectors=False,
            )

            documents = []
            for point in results[0]:
                documents.append({
                    "text": point.payload.get("text", ""),
                    "metadata": {
                        "source_id": point.payload.get("source_id", ""),
                        "type": point.payload.get("type", ""),
                        "start": point.payload.get("start", 0),
                        "end": point.payload.get("end", 0),
                        "video_title": point.payload.get("video_title", ""),
                    },
                })

            logger.info(f"Retrieved {len(documents)} total documents")
            return documents

        except Exception as e:
            logger.error(f"Failed to get all documents: {e}")
            return []

    def get_source_documents(self, source_id: str) -> List[Dict[str, Any]]:
        """Get all documents for a specific source."""
        try:
            results = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="source_id",
                            match=models.MatchValue(value=source_id),
                        )
                    ]
                ),
                limit=10000,
                with_payload=True,
                with_vectors=False,
            )

            documents = []
            for point in results[0]:
                documents.append({
                    "text": point.payload.get("text", ""),
                    "metadata": {
                        "source_id": point.payload.get("source_id", ""),
                        "type": point.payload.get("type", ""),
                        "start": point.payload.get("start", 0),
                        "end": point.payload.get("end", 0),
                        "video_title": point.payload.get("video_title", ""),
                        "frame_path": point.payload.get("frame_path", ""),
                    },
                })

            return documents

        except Exception as e:
            logger.error(f"Failed to get source documents: {e}")
            return []

    def delete_source(self, source_id: str) -> bool:
        """Delete all documents for a source."""
        try:
            # Delete by filter
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="source_id",
                            match=models.MatchValue(value=source_id),
                        )
                    ]
                ),
            )
            logger.info(f"Deleted documents for source {source_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete source: {e}")
            return False

    def get_collection_count(self) -> int:
        """Get total number of points in collection."""
        try:
            collection_info = self.client.get_collection(self.collection_name)
            return collection_info.points_count
        except Exception as e:
            logger.error(f"Failed to get collection count: {e}")
            return 0

    def get_stats(self) -> Dict[str, Any]:
        """Get collection statistics."""
        return {
            "total_documents": self.get_collection_count(),
            "collection_name": self.collection_name,
            "host": self.host,
            "port": self.port,
        }

    def clear_collection(self) -> bool:
        """Clear all data from collection."""
        try:
            self.client.delete_collection(self.collection_name)
            self._ensure_collection()
            logger.info(f"Cleared collection {self.collection_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to clear collection: {e}")
            return False


# Singleton instance
_vector_store: Optional[VectorStore] = None


def get_vector_store() -> VectorStore:
    """Get or create VectorStore singleton."""
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store


def reset_vector_store():
    """Reset the singleton instance (useful for testing)."""
    global _vector_store
    if _vector_store is not None:
        try:
            _vector_store.client.close()
        except Exception:
            pass
    _vector_store = None
