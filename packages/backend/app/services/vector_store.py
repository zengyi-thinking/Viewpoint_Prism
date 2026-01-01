"""
Vector Store Service
Handles storage and retrieval of video knowledge using ChromaDB.
"""

import re
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging
import chromadb
from chromadb.config import Settings as ChromaSettings
from chromadb.utils import embedding_functions

from app.core import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Collection name for video knowledge
COLLECTION_NAME = "video_knowledge"

# Use local sentence-transformers embedding (privacy-friendly, no cloud API)
try:
    embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="paraphrase-multilingual-MiniLM-L12-v2"  # Support Chinese and English
    )
    logger.info("Using local sentence-transformers embedding (multilingual)")
except Exception as e:
    logger.warning(f"Multilingual model failed ({e}), falling back to English-only...")
    try:
        embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )
        logger.info("Using local sentence-transformers embedding (English)")
    except Exception as e2:
        logger.error(f"Failed to initialize embedding function: {e2}")
        embedding_function = None


class VectorStore:
    """ChromaDB-based vector storage for video intelligence."""

    def __init__(self, persist_dir: Optional[str] = None):
        """
        Initialize ChromaDB client.

        Args:
            persist_dir: Directory for persistent storage
        """
        if persist_dir:
            self.persist_dir = persist_dir
        else:
            # Use absolute path based on backend package location
            backend_dir = Path(__file__).parent.parent.parent
            self.persist_dir = str(backend_dir / "data" / "chromadb")
        Path(self.persist_dir).mkdir(parents=True, exist_ok=True)

        # Initialize ChromaDB with persistent storage
        self.client = chromadb.PersistentClient(
            path=self.persist_dir,
            settings=ChromaSettings(
                anonymized_telemetry=False,
                allow_reset=True,
            )
        )

        # Get or create the collection with embedding function
        if embedding_function:
            self.collection = self.client.get_or_create_collection(
                name=COLLECTION_NAME,
                metadata={"description": "Video knowledge base for Viewpoint Prism"},
                embedding_function=embedding_function
            )
        else:
            logger.warning("No embedding function available, using default")
            self.collection = self.client.get_or_create_collection(
                name=COLLECTION_NAME,
                metadata={"description": "Video knowledge base for Viewpoint Prism"}
            )

        logger.info(f"VectorStore initialized with {self.collection.count()} documents")

    def _chunk_text(self, text: str, max_length: int = 500) -> List[str]:
        """
        Split text into smaller chunks for embedding.

        Args:
            text: Text to chunk
            max_length: Maximum characters per chunk

        Returns:
            List of text chunks
        """
        if len(text) <= max_length:
            return [text] if text.strip() else []

        # Split by sentences (Chinese and English)
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
            source_id: Unique video source identifier
            transcripts: ASR transcript segments [{"start", "end", "text"}]
            visual_descriptions: Frame analysis results [{"timestamp", "description"}]
            video_title: Title of the video

        Returns:
            Number of documents added
        """
        documents = []
        metadatas = []
        ids = []

        doc_index = 0

        # Process transcripts
        for segment in transcripts:
            text = segment.get("text", "").strip()
            if not text:
                continue

            # Chunk long segments
            chunks = self._chunk_text(text)
            for chunk in chunks:
                doc_id = f"{source_id}_transcript_{doc_index}"
                documents.append(chunk)
                metadatas.append({
                    "source_id": source_id,
                    "type": "transcript",
                    "start": segment.get("start", 0),
                    "end": segment.get("end", 0),
                    "video_title": video_title,
                })
                ids.append(doc_id)
                doc_index += 1

        # Process visual descriptions
        for desc in visual_descriptions:
            text = desc.get("description", "").strip()
            if not text or text.startswith("Error:") or text.startswith("Analysis failed"):
                continue

            doc_id = f"{source_id}_visual_{doc_index}"
            timestamp = desc.get("timestamp", 0)

            documents.append(text)
            metadatas.append({
                "source_id": source_id,
                "type": "visual",
                "start": timestamp,
                "end": timestamp + 5,  # Assume 5s frame interval
                "video_title": video_title,
                "frame_path": desc.get("frame_path", ""),
            })
            ids.append(doc_id)
            doc_index += 1

        # Add to collection
        if documents:
            try:
                self.collection.add(
                    documents=documents,
                    metadatas=metadatas,
                    ids=ids,
                )
                logger.info(f"Added {len(documents)} documents for source {source_id}")
            except Exception as e:
                logger.error(f"Failed to add documents: {e}")
                return 0

        return len(documents)

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
            source_ids: Optional filter by source IDs
            n_results: Maximum number of results
            doc_type: Optional filter by type ("transcript" or "visual")

        Returns:
            List of search results with metadata
        """
        # Build where filter
        where_filter = None
        if source_ids or doc_type:
            conditions = []
            if source_ids:
                conditions.append({"source_id": {"$in": source_ids}})
            if doc_type:
                conditions.append({"type": doc_type})

            if len(conditions) == 1:
                where_filter = conditions[0]
            else:
                where_filter = {"$and": conditions}

        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                where=where_filter,
                include=["documents", "metadatas", "distances"]
            )

            # Format results
            formatted_results = []
            if results["documents"] and results["documents"][0]:
                for i, doc in enumerate(results["documents"][0]):
                    formatted_results.append({
                        "text": doc,
                        "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                        "distance": results["distances"][0][i] if results["distances"] else 0,
                    })

            if formatted_results:
                logger.info(f"Search returned {len(formatted_results)} results for: {query[:50]}...")
            else:
                # Enhanced debug logging when no results found
                total_docs = self.collection.count()
                logger.warning(f"Search returned 0 results for query='{query[:50]}...', total_docs_in_db={total_docs}, filter={where_filter}")

            return formatted_results

        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []

    def get_source_documents(self, source_id: str) -> List[Dict[str, Any]]:
        """
        Get all documents for a specific source.

        Args:
            source_id: Source identifier

        Returns:
            List of documents with metadata
        """
        try:
            results = self.collection.get(
                where={"source_id": source_id},
                include=["documents", "metadatas"]
            )

            documents = []
            if results["documents"]:
                for i, doc in enumerate(results["documents"]):
                    documents.append({
                        "text": doc,
                        "metadata": results["metadatas"][i] if results["metadatas"] else {},
                    })

            return documents

        except Exception as e:
            logger.error(f"Failed to get source documents: {e}")
            return []

    def delete_source(self, source_id: str) -> bool:
        """
        Delete all documents for a source.

        Args:
            source_id: Source identifier

        Returns:
            True if successful
        """
        try:
            # Get all document IDs for this source
            results = self.collection.get(
                where={"source_id": source_id},
                include=[]
            )

            if results["ids"]:
                self.collection.delete(ids=results["ids"])
                logger.info(f"Deleted {len(results['ids'])} documents for source {source_id}")

            return True

        except Exception as e:
            logger.error(f"Failed to delete source: {e}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        """Get collection statistics."""
        return {
            "total_documents": self.collection.count(),
            "persist_directory": self.persist_dir,
        }


# Singleton instance
_vector_store: Optional[VectorStore] = None


def get_vector_store() -> VectorStore:
    """Get or create VectorStore singleton."""
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store
