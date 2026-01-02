"""
Montage API endpoints for Highlight Nebula feature.
Phase 12+: Unified Knowledge Graph + Concept Supercut = Highlight Nebula
"""

import asyncio
from typing import List, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from pydantic import BaseModel
import logging

from app.services import get_montage_service

router = APIRouter(prefix="/montage", tags=["montage"])
logger = logging.getLogger(__name__)


# ============================================
# Request/Response Schemas
# ============================================

class ConceptItem(BaseModel):
    """Single concept with frequency count."""
    text: str
    value: int


class ConceptsResponse(BaseModel):
    """Response for global concepts extraction."""
    concepts: List[ConceptItem]
    total: int


class NebulaNode(BaseModel):
    """Node in the nebula graph."""
    id: str
    val: int
    group: str


class NebulaLink(BaseModel):
    """Link in the nebula graph."""
    source: str
    target: str
    value: int


class NebulaStructureResponse(BaseModel):
    """Response for nebula 3D graph structure."""
    nodes: List[NebulaNode]
    links: List[NebulaLink]


class SegmentInfo(BaseModel):
    """Segment info in highlight reel."""
    source_id: str
    video_title: str
    timestamp: str
    score: float


class HighlightTaskResponse(BaseModel):
    """Response for highlight reel task status."""
    task_id: str
    status: str
    progress: int
    message: str
    video_url: Optional[str] = None
    concept: Optional[str] = None
    segment_count: Optional[int] = None
    segments: Optional[List[SegmentInfo]] = None
    error: Optional[str] = None


class CreateHighlightRequest(BaseModel):
    """Request to create a highlight reel."""
    concept: str
    top_k: int = 10
    max_duration: float = 90.0


# ============================================
# Nebula Structure Endpoints
# ============================================

@router.get("/nebula", response_model=NebulaStructureResponse)
async def get_nebula_structure(
    top_k: int = Query(80, ge=20, le=200, description="Number of nodes to return"),
    min_length: int = Query(2, ge=1, le=5, description="Minimum word length"),
):
    """
    Get 3D nebula graph structure with nodes and co-occurrence links.

    Returns data suitable for react-force-graph-3d visualization.
    Nodes are colored by group: person (red), location (gold), tech (cyan), concept (blue).
    """
    montage_service = get_montage_service()

    structure = await montage_service.get_nebula_structure(
        top_k=top_k,
        min_length=min_length,
    )

    return NebulaStructureResponse(
        nodes=[NebulaNode(**n) for n in structure["nodes"]],
        links=[NebulaLink(**l) for l in structure["links"]],
    )


# ============================================
# Legacy Concepts Endpoint (for backward compatibility)
# ============================================

@router.get("/concepts", response_model=ConceptsResponse)
async def get_global_concepts(
    top_k: int = Query(50, ge=10, le=200, description="Number of concepts to return"),
    min_length: int = Query(2, ge=1, le=5, description="Minimum word length"),
):
    """
    Get high-frequency concepts from all video content.

    Returns a list of concepts with their frequencies.
    """
    montage_service = get_montage_service()

    concepts = await montage_service.get_global_concepts(
        top_k=top_k,
        min_length=min_length,
    )

    return ConceptsResponse(
        concepts=[ConceptItem(**c) for c in concepts],
        total=len(concepts),
    )


# ============================================
# Highlight Reel Endpoints
# ============================================

@router.post("/highlight", response_model=HighlightTaskResponse)
async def create_highlight_reel(
    request: CreateHighlightRequest,
    background_tasks: BackgroundTasks,
):
    """
    Create a highlight reel video for a concept.

    Pipeline:
    1. RAG search for relevant video segments
    2. LLM sorts segments into logical narrative (Definition -> Core -> Caveats -> Summary)
    3. FFmpeg composes video with xfade transitions

    The video generation runs in background. Poll the task status endpoint for progress.
    """
    montage_service = get_montage_service()

    # Create task
    task_id = montage_service.create_task()

    # Start background generation
    background_tasks.add_task(
        montage_service.create_concept_supercut,
        task_id=task_id,
        concept=request.concept,
        top_k=request.top_k,
        max_duration=request.max_duration,
    )

    return HighlightTaskResponse(
        task_id=task_id,
        status="pending",
        progress=0,
        message=f"正在点亮 '{request.concept}' 的高光时刻...",
    )


@router.get("/highlight/{task_id}", response_model=HighlightTaskResponse)
async def get_highlight_status(task_id: str):
    """
    Get status of a highlight reel generation task.

    Poll this endpoint to track progress during video generation.
    """
    montage_service = get_montage_service()

    status = montage_service.get_task_status(task_id)
    if not status:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    # Filter out segments for pending/in-progress tasks to avoid validation issues
    if status.get("status") not in ("completed", "error"):
        status = {k: v for k, v in status.items() if k != "segments"}

    # Debug: log the status dict
    logger.info(f"Task {task_id} status: {status}")
    logger.info(f"Task {task_id} segments: {status.get('segments')}")

    return HighlightTaskResponse(
        task_id=task_id,
        **status,
    )


# Debug endpoint - return raw task status
@router.get("/highlight/{task_id}/debug")
async def get_task_debug(task_id: str):
    """Get raw task status for debugging."""
    montage_service = get_montage_service()
    status = montage_service.get_task_status(task_id)
    if not status:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    return {"task_id": task_id, "raw_status": status}


# Legacy supercut endpoints (for backward compatibility)
@router.post("/supercut", response_model=HighlightTaskResponse, include_in_schema=False)
async def create_supercut_legacy(
    request: CreateHighlightRequest,
    background_tasks: BackgroundTasks,
):
    """Legacy endpoint - redirects to highlight."""
    return await create_highlight_reel(request, background_tasks)


@router.get("/supercut/{task_id}", response_model=HighlightTaskResponse, include_in_schema=False)
async def get_supercut_status_legacy(task_id: str):
    """Legacy endpoint - redirects to highlight."""
    return await get_highlight_status(task_id)


@router.get("/search")
async def search_concept_segments(
    concept: str = Query(..., description="Concept to search for"),
    top_k: int = Query(10, ge=1, le=50, description="Maximum segments"),
):
    """
    Search for video segments related to a concept.

    Returns segment info without creating a video.
    Useful for previewing what segments would be included in a highlight reel.
    """
    montage_service = get_montage_service()

    segments = await montage_service.search_concept_segments(
        concept=concept,
        top_k=top_k,
    )

    return {
        "concept": concept,
        "segments": [
            {
                "source_id": seg["source_id"],
                "video_title": seg["video_title"],
                "start": seg["start"],
                "end": seg["end"],
                "text": seg["text"],
                "score": round(seg["score"], 3),
            }
            for seg in segments
        ],
        "total": len(segments),
    }
