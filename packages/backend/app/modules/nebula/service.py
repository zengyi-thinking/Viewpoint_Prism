"""
Nebula service - Knowledge graph and concept extraction.
"""

import uuid
from typing import Dict, Any, Optional, List
import logging

from app.shared.storage import get_vector_store
from app.shared.perception import get_sophnet_service

logger = logging.getLogger(__name__)


class NebulaService:
    """Service for knowledge graph and highlight reel generation."""

    def __init__(self):
        """Initialize with services."""
        self.vector_store = get_vector_store()
        self.sophnet = get_sophnet_service()
        self.tasks: Dict[str, Dict[str, Any]] = {}

    def create_task(self) -> str:
        """Create a new task."""
        task_id = uuid.uuid4().hex[:8]
        self.tasks[task_id] = {
            "status": "pending",
            "progress": 0,
            "message": "Task created",
        }
        return task_id

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task status."""
        return self.tasks.get(task_id)

    def _update_task(self, task_id: str, **kwargs):
        """Update task status."""
        if task_id in self.tasks:
            self.tasks[task_id].update(kwargs)

    async def get_global_concepts(
        self,
        top_k: int = 50,
        min_length: int = 2,
        max_length: int = 10,
    ) -> List[Dict[str, Any]]:
        """Extract high-frequency concepts from all video content."""
        vector_store = get_vector_store()
        all_docs = vector_store.get_all_documents()

        from collections import Counter
        import re

        word_counts = Counter()
        for doc in all_docs:
            text = doc.get("text", "")
            words = re.findall(r'\b[a-zA-Z\u4e00-\u9fff]{2,10}\b', text)
            for word in words:
                if min_length <= len(word) <= max_length:
                    word_counts[word] += 1

        return [
            {"text": word, "value": count}
            for word, count in word_counts.most_common(top_k)
        ]

    async def build_nebula_structure(
        self,
        source_ids: List[str],
    ) -> Dict[str, Any]:
        """Build nebula 3D graph structure from sources."""
        vector_store = get_vector_store()
        all_docs = []

        for sid in source_ids:
            docs = vector_store.get_source_documents(sid)
            all_docs.extend(docs)

        if not all_docs:
            return {"nodes": [], "links": []}

        import re
        from collections import Counter, defaultdict

        entity_counter = Counter()
        entity_source_map = defaultdict(set)

        for doc in all_docs:
            text = doc.get("text", "")
            words = re.findall(r'\b[A-Z][a-zA-Z]+\b|\b[\u4e00-\u9fff]{2,5}\b', text)
            for word in words:
                entity_counter[word] += 1
                entity_source_map[word].add(doc.get("metadata", {}).get("source_id", ""))

        top_entities = [e for e, c in entity_counter.most_common(30) if c >= 2]

        nodes = []
        links = []
        entity_groups = {"character": 1, "location": 2, "item": 3, "other": 4}

        for i, entity in enumerate(top_entities):
            node_id = f"node_{i}"
            group = "other"
            if entity in ["hero", "villain", " protagonist"]:
                group = "character"
            elif entity in ["castle", "village", "city"]:
                group = "location"

            nodes.append({
                "id": node_id,
                "val": entity_counter[entity],
                "group": group,
            })

        for i in range(len(top_entities)):
            for j in range(i + 1, len(top_entities)):
                links.append({
                    "source": f"node_{i}",
                    "target": f"node_{j}",
                    "value": 1,
                })

        return {"nodes": nodes, "links": links}


_nebula_service: Optional[NebulaService] = None


def get_nebula_service() -> NebulaService:
    """Get or create NebulaService singleton."""
    global _nebula_service
    if _nebula_service is None:
        _nebula_service = NebulaService()
    return _nebula_service
