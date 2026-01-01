from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


# === Source Schemas ===

class SourceBase(BaseModel):
    title: str
    file_type: str = "video"
    platform: str = "local"


class SourceCreate(SourceBase):
    pass


class SourceResponse(BaseModel):
    id: str
    title: str
    file_path: str
    url: str
    file_type: str
    platform: str
    duration: Optional[float] = None
    thumbnail: Optional[str] = None
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class SourceListResponse(BaseModel):
    sources: List[SourceResponse]
    total: int


# === Chat Schemas ===

class ChatRequest(BaseModel):
    session_id: str
    message: str
    source_ids: List[str] = []


class ChatReference(BaseModel):
    source_id: str
    timestamp: float
    text: str


class ChatResponse(BaseModel):
    role: str
    content: str
    references: List[ChatReference] = []


# === Analysis Schemas ===

class Viewpoint(BaseModel):
    source_id: str
    source_name: str
    title: str
    description: str
    timestamp: Optional[float] = None
    color: str  # "red" or "blue"


class Conflict(BaseModel):
    id: str
    topic: str
    severity: str  # "critical", "warning", "info"
    viewpoint_a: Viewpoint
    viewpoint_b: Viewpoint
    verdict: str


class GraphNode(BaseModel):
    id: str
    name: str
    category: str  # "boss", "item", "location", "character"
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
    event_type: str = "STORY"  # STORY, COMBAT, EXPLORE


class AnalysisResponse(BaseModel):
    conflicts: List[Conflict]
    graph: KnowledgeGraph
    timeline: List[TimelineEvent]
