"""
Analysis API endpoints for AI-powered video analysis.
Generates conflicts, timelines, and knowledge graphs.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from pydantic import BaseModel
import logging

from app.core import get_db
from app.api.schemas import (
    AnalysisResponse,
    Conflict,
    Viewpoint,
    KnowledgeGraph,
    GraphNode,
    GraphLink,
    TimelineEvent,
)
from app.models import AnalysisResult, Source
from app.services import get_vector_store, get_analysis_service

router = APIRouter(prefix="/analysis", tags=["analysis"])
logger = logging.getLogger(__name__)


def parse_timestamp(value) -> Optional[float]:
    """
    Parse timestamp from various formats.
    Handles: float, int, 'MM:SS', 'HH:MM:SS', or None.
    """
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            # Try direct float conversion first
            return float(value)
        except ValueError:
            # Try MM:SS or HH:MM:SS format
            parts = value.split(':')
            if len(parts) == 2:  # MM:SS
                return int(parts[0]) * 60 + int(parts[1])
            elif len(parts) == 3:  # HH:MM:SS
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    return None


# Search schemas
class SearchResult(BaseModel):
    """Single search result."""
    text: str
    source_id: str
    type: str
    start: float
    end: float
    video_title: str = ""
    distance: float = 0.0


class SearchResponse(BaseModel):
    """Search response with results."""
    query: str
    results: List[SearchResult]
    total: int


class GenerateRequest(BaseModel):
    """Request for analysis generation."""
    source_ids: List[str]
    use_cache: bool = True


def get_mock_analysis(source_ids: List[str]) -> AnalysisResponse:
    """Generate mock analysis data for demonstration."""
    source_a = source_ids[0] if len(source_ids) > 0 else "source-a"
    source_b = source_ids[1] if len(source_ids) > 1 else "source-b"

    mock_conflicts = [
        Conflict(
            id="conflict-1",
            topic="策略分歧：虎先锋",
            severity="critical",
            viewpoint_a=Viewpoint(
                source_id=source_a,
                source_name="Source A",
                title="硬刚打法",
                description="建议使用铜头铁臂弹反。收益高但风险极大。",
                timestamp=120.0,
                color="red",
            ),
            viewpoint_b=Viewpoint(
                source_id=source_b,
                source_name="Source B",
                title="逃课流",
                description="使用定风珠打断 BOSS 技能。全程无伤。",
                timestamp=200.0,
                color="blue",
            ),
            verdict="视觉分析确认 Source B 保持满血通关。强烈推荐新手使用。",
        ),
    ]

    mock_graph = KnowledgeGraph(
        nodes=[
            GraphNode(id="node-1", name="虎先锋", category="boss", timestamp=0),
            GraphNode(id="node-2", name="定风珠", category="item", timestamp=200),
            GraphNode(id="node-3", name="黄风大圣", category="boss"),
            GraphNode(id="node-4", name="隐雪洞", category="location"),
        ],
        links=[
            GraphLink(source="node-1", target="node-2", relation="weak_to"),
            GraphLink(source="node-2", target="node-3", relation="obtained_from"),
            GraphLink(source="node-1", target="node-4", relation="found_in"),
        ],
    )

    mock_timeline = [
        TimelineEvent(
            id="event-1",
            time="00:15",
            timestamp=15.0,
            title="遭遇战开始",
            description="检测到 BOSS 进场动画。",
            source_id=source_a,
            is_key_moment=False,
        ),
        TimelineEvent(
            id="event-2",
            time="03:20",
            timestamp=200.0,
            title="关键道具使用",
            description="定风珠激活，BOSS 进入硬直。",
            source_id=source_b,
            is_key_moment=True,
        ),
    ]

    return AnalysisResponse(
        conflicts=mock_conflicts,
        graph=mock_graph,
        timeline=mock_timeline,
    )


@router.post("/generate", response_model=AnalysisResponse)
async def generate_analysis(
    request: GenerateRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Generate comprehensive analysis (conflicts, graph, timeline) for selected sources.

    Uses AI to analyze video content and generate:
    - Conflicts: Viewpoint differences between sources
    - Timeline: Key events with timestamps
    - Graph: Knowledge graph of entities and relationships
    """
    source_ids = request.source_ids

    if not source_ids:
        raise HTTPException(status_code=400, detail="No source IDs provided")

    # Verify sources exist
    valid_source_ids = []
    for source_id in source_ids:
        result = await db.execute(select(Source).where(Source.id == source_id))
        if result.scalar_one_or_none():
            valid_source_ids.append(source_id)

    if not valid_source_ids:
        raise HTTPException(status_code=404, detail="No valid sources found")

    # Get analysis service
    analysis_service = get_analysis_service()

    # Generate all analysis concurrently
    import asyncio

    conflicts_task = analysis_service.generate_conflicts(valid_source_ids, request.use_cache)
    timeline_task = analysis_service.generate_timeline(valid_source_ids[0], request.use_cache)
    graph_task = analysis_service.generate_graph(valid_source_ids, request.use_cache)

    conflicts_result, timeline_result, graph_result = await asyncio.gather(
        conflicts_task, timeline_task, graph_task
    )

    # Parse conflicts
    conflicts = []
    for c in conflicts_result.get("conflicts", []):
        try:
            conflicts.append(Conflict(
                id=c.get("id", ""),
                topic=c.get("topic", ""),
                severity=c.get("severity", "info"),
                viewpoint_a=Viewpoint(**c.get("viewpoint_a", {})),
                viewpoint_b=Viewpoint(**c.get("viewpoint_b", {})),
                verdict=c.get("verdict", ""),
            ))
        except Exception as e:
            logger.warning(f"Failed to parse conflict: {e}")

    # Parse timeline
    timeline = []
    for t in timeline_result.get("timeline", []):
        try:
            timeline.append(TimelineEvent(
                id=t.get("id", ""),
                time=t.get("time", "00:00"),
                timestamp=float(t.get("timestamp", 0)),
                title=t.get("title", ""),
                description=t.get("description", ""),
                source_id=t.get("source_id", valid_source_ids[0]),
                is_key_moment=t.get("is_key_moment", False),
                event_type=t.get("event_type", "STORY"),
            ))
        except Exception as e:
            logger.warning(f"Failed to parse timeline event: {e}")

    # Parse graph
    nodes = []
    links = []
    for n in graph_result.get("nodes", []):
        try:
            # Parse timestamp with MM:SS format support
            ts = parse_timestamp(n.get("timestamp"))
            nodes.append(GraphNode(
                id=n.get("id", ""),
                name=n.get("name", ""),
                category=n.get("category", "concept"),
                timestamp=ts,
                source_id=n.get("source_id"),
            ))
        except Exception as e:
            logger.warning(f"Failed to parse graph node: {e}")

    for l in graph_result.get("links", []):
        try:
            links.append(GraphLink(
                source=l.get("source", ""),
                target=l.get("target", ""),
                relation=l.get("relation"),
            ))
        except Exception as e:
            logger.warning(f"Failed to parse graph link: {e}")

    graph = KnowledgeGraph(nodes=nodes, links=links)

    return AnalysisResponse(
        conflicts=conflicts if conflicts else get_mock_analysis(valid_source_ids).conflicts,
        graph=graph if nodes else get_mock_analysis(valid_source_ids).graph,
        timeline=timeline if timeline else get_mock_analysis(valid_source_ids).timeline,
    )


@router.get("/conflicts")
async def get_conflicts(
    source_ids: str = Query(..., description="Comma-separated source IDs"),
    use_cache: bool = Query(True, description="Use cached results"),
):
    """
    Generate conflict analysis between video sources.

    Identifies viewpoint differences, strategy conflicts, and information discrepancies.
    """
    source_id_list = [s.strip() for s in source_ids.split(",") if s.strip()]

    if not source_id_list:
        raise HTTPException(status_code=400, detail="No source IDs provided")

    analysis_service = get_analysis_service()
    result = await analysis_service.generate_conflicts(source_id_list, use_cache)

    return result


@router.get("/timeline/{source_id}")
async def get_timeline(
    source_id: str,
    use_cache: bool = Query(True, description="Use cached results"),
):
    """
    Generate smart timeline for a video.

    Extracts key events and moments with timestamps.
    """
    analysis_service = get_analysis_service()
    result = await analysis_service.generate_timeline(source_id, use_cache)

    return result


@router.get("/graph")
async def get_graph(
    source_ids: str = Query(..., description="Comma-separated source IDs"),
    use_cache: bool = Query(True, description="Use cached results"),
):
    """
    Generate knowledge graph from video content.

    Extracts entities (characters, items, locations) and their relationships.
    """
    source_id_list = [s.strip() for s in source_ids.split(",") if s.strip()]

    if not source_id_list:
        raise HTTPException(status_code=400, detail="No source IDs provided")

    analysis_service = get_analysis_service()
    result = await analysis_service.generate_graph(source_id_list, use_cache)

    return result


@router.delete("/cache")
async def clear_cache(
    source_ids: Optional[str] = Query(None, description="Comma-separated source IDs, or all if empty"),
):
    """Clear analysis cache for specific sources or all."""
    analysis_service = get_analysis_service()

    source_id_list = None
    if source_ids:
        source_id_list = [s.strip() for s in source_ids.split(",") if s.strip()]

    analysis_service.clear_cache(source_id_list)

    return {"status": "cache_cleared", "source_ids": source_id_list}


@router.get("/mock", response_model=AnalysisResponse)
async def get_mock_analysis_endpoint():
    """Get mock analysis data for UI testing."""
    return get_mock_analysis(["mock-source-a", "mock-source-b"])


@router.get("/search/query", response_model=SearchResponse)
async def search_knowledge(
    q: str = Query(..., description="Search query"),
    source_ids: Optional[str] = Query(None, description="Comma-separated source IDs to filter"),
    doc_type: Optional[str] = Query(None, description="Filter by type: 'transcript' or 'visual'"),
    limit: int = Query(10, ge=1, le=50, description="Maximum results"),
):
    """
    Search the video knowledge base.

    Searches through transcripts and visual descriptions stored in ChromaDB.
    """
    vector_store = get_vector_store()

    source_id_list = None
    if source_ids:
        source_id_list = [s.strip() for s in source_ids.split(",") if s.strip()]

    raw_results = vector_store.search(
        query=q,
        source_ids=source_id_list,
        n_results=limit,
        doc_type=doc_type,
    )

    results = []
    for r in raw_results:
        metadata = r.get("metadata", {})
        results.append(SearchResult(
            text=r.get("text", ""),
            source_id=metadata.get("source_id", ""),
            type=metadata.get("type", ""),
            start=metadata.get("start", 0),
            end=metadata.get("end", 0),
            video_title=metadata.get("video_title", ""),
            distance=r.get("distance", 0),
        ))

    return SearchResponse(
        query=q,
        results=results,
        total=len(results),
    )


@router.get("/stats")
async def get_knowledge_stats():
    """Get statistics about the knowledge base."""
    vector_store = get_vector_store()
    stats = vector_store.get_stats()
    return {
        "status": "ok",
        "knowledge_base": stats,
    }


# One-Pager Report schemas
class OnePagerData(BaseModel):
    """One-Pager Executive Summary data."""
    headline: str
    tldr: str
    insights: List[str]
    conceptual_image: Optional[str] = None
    evidence_images: List[str] = []
    generated_at: str
    source_ids: List[str]  # Changed: support multiple sources
    video_titles: List[str]  # Changed: list of video titles


class OnePagerRequest(BaseModel):
    """Request for one-pager generation."""
    source_ids: List[str]  # Changed: support multiple sources
    use_cache: bool = True


@router.post("/one-pager", response_model=OnePagerData)
async def generate_one_pager(
    request: OnePagerRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Generate One-Pager Executive Summary for selected videos.

    Creates a magazine-style decision brief with:
    - Compelling headline (15 chars max)
    - TL;DR summary (50 chars max)
    - 3 key insights
    - AI-generated conceptual illustration
    - Video screenshot evidence from all selected sources
    """
    if not request.source_ids:
        raise HTTPException(status_code=400, detail="No source IDs provided")

    # Verify sources exist
    valid_source_ids = []
    for source_id in request.source_ids:
        result = await db.execute(select(Source).where(Source.id == source_id))
        if result.scalar_one_or_none():
            valid_source_ids.append(source_id)

    if not valid_source_ids:
        raise HTTPException(status_code=404, detail="No valid sources found")

    # Get analysis service
    analysis_service = get_analysis_service()

    # Generate one-pager for all selected sources
    one_pager_result = await analysis_service.generate_executive_summary(
        source_ids=valid_source_ids,
        use_cache=request.use_cache,
    )

    # Check for error message
    if "message" in one_pager_result and "error" in one_pager_result.get("message", ""):
        raise HTTPException(status_code=500, detail=one_pager_result.get("message"))

    # Return as OnePagerData
    return OnePagerData(
        headline=one_pager_result.get("headline", "视频概览"),
        tldr=one_pager_result.get("tldr", "暂无摘要"),
        insights=one_pager_result.get("insights", []),
        conceptual_image=one_pager_result.get("conceptual_image"),
        evidence_images=one_pager_result.get("evidence_images", []),
        generated_at=one_pager_result.get("generated_at", ""),
        source_ids=one_pager_result.get("source_ids", valid_source_ids),
        video_titles=one_pager_result.get("video_titles", []),
    )


# Dynamic session ID route must be LAST to avoid matching static routes
@router.get("/{session_id}", response_model=AnalysisResponse)
async def get_analysis(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get cached analysis results for a session."""
    import json

    result = await db.execute(
        select(AnalysisResult).where(AnalysisResult.session_id == session_id)
    )
    results = result.scalars().all()

    if not results:
        return get_mock_analysis(["mock-source-a", "mock-source-b"])

    conflicts = []
    graph = KnowledgeGraph(nodes=[], links=[])
    timeline = []

    for r in results:
        data = json.loads(r.data)
        if r.result_type == "conflict":
            conflicts = [Conflict(**c) for c in data]
        elif r.result_type == "graph":
            graph = KnowledgeGraph(**data)
        elif r.result_type == "timeline":
            timeline = [TimelineEvent(**t) for t in data]

    return AnalysisResponse(
        conflicts=conflicts,
        graph=graph,
        timeline=timeline,
    )
