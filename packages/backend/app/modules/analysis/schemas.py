"""
Analysis Pydantic schemas.
"""

from typing import List, Optional
from pydantic import BaseModel


class Viewpoint(BaseModel):
    source_id: str
    source_name: str
    title: str
    description: str
    timestamp: Optional[float] = None
    color: str


class Conflict(BaseModel):
    id: str
    topic: str
    severity: str
    viewpoint_a: Viewpoint
    viewpoint_b: Viewpoint
    verdict: str


class GraphNode(BaseModel):
    id: str
    name: str
    category: str
    timestamp: Optional[float] = None
    source_id: Optional[str] = None


class GraphLink(BaseModel):
    source: str
    target: str
    relation: Optional[str] = None


class KnowledgeGraph(BaseModel):
    nodes: List[GraphNode]
    links: List[GraphLink]


class TimelineEvent(BaseModel):
    id: str
    time: str
    timestamp: float
    title: str
    description: str
    source_id: str
    is_key_moment: bool = False
    event_type: str = "STORY"


class AnalysisResponse(BaseModel):
    conflicts: List[Conflict]
    graph: KnowledgeGraph
    timeline: List[TimelineEvent]


class SearchResult(BaseModel):
    text: str
    source_id: str
    type: str
    start: float
    end: float
    video_title: str = ""
    distance: float = 0.0


class SearchResponse(BaseModel):
    query: str
    results: List[SearchResult]
    total: int


class GenerateRequest(BaseModel):
    source_ids: List[str]
    use_cache: bool = True


class EvidenceItem(BaseModel):
    url: str
    caption: str
    related_insight_index: Optional[int] = None


class OnePagerRequest(BaseModel):
    source_ids: List[str]
    use_cache: bool = True


class OnePagerResponse(BaseModel):
    headline: str
    tldr: str
    insights: List[str]
    conceptual_image: Optional[str] = None
    evidence_items: List[EvidenceItem]
    evidence_images: List[str]
    generated_at: str
    source_ids: List[str]
    video_titles: List[str]
