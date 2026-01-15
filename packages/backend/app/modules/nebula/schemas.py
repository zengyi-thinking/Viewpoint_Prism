"""
Nebula Pydantic schemas.
"""

from typing import List, Optional
from pydantic import BaseModel


class ConceptItem(BaseModel):
    text: str
    value: int


class ConceptsResponse(BaseModel):
    concepts: List[ConceptItem]
    total: int


class NebulaNode(BaseModel):
    id: str
    val: int
    group: str


class NebulaLink(BaseModel):
    source: str
    target: str
    value: int


class NebulaStructureResponse(BaseModel):
    nodes: List[NebulaNode]
    links: List[NebulaLink]


class HighlightTaskResponse(BaseModel):
    task_id: str
    status: str
    progress: int
    message: str
    video_url: Optional[str] = None
    concept: Optional[str] = None
    segment_count: Optional[int] = None
    error: Optional[str] = None


class CreateHighlightRequest(BaseModel):
    concept: str
    top_k: int = 10
