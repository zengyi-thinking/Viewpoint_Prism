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


# ===== 实体相关 Schemas =====

class EntityBase(BaseModel):
    """实体基础模型"""
    name: str
    type: str
    description: Optional[str] = None


class EntityResponse(EntityBase):
    """实体响应模型"""
    id: str
    mention_count: int
    first_seen_at: str
    last_seen_at: str


class EntityMentionItem(BaseModel):
    """实体提及项"""
    id: str
    source_id: str
    timestamp: float
    context: Optional[str] = None
    confidence: float = 1.0


class EntityDetailResponse(EntityBase):
    """实体详情响应"""
    id: str
    mention_count: int
    mentions: List[EntityMentionItem]


class EntityListResponse(BaseModel):
    """实体列表响应"""
    entities: List[EntityResponse]


class EntityMentionListResponse(BaseModel):
    """实体提及列表响应"""
    entity_id: str
    mentions: List[EntityMentionItem]


class ExtractEntitiesResponse(BaseModel):
    """实体抽取响应"""
    source_id: str
    entity_count: int
    entities: List[EntityResponse]
