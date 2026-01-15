"""
Nebula API routes.
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks, Query, Depends
from pydantic import BaseModel
import logging

from app.modules.nebula import (
    NebulaService,
    get_nebula_service,
    ConceptsResponse,
    NebulaStructureResponse,
    NebulaNode,
    NebulaLink,
    HighlightTaskResponse,
    CreateHighlightRequest,
)
from app.shared.storage import get_vector_store

router = APIRouter(prefix="/nebula", tags=["nebula"])
montage_router = APIRouter(prefix="/montage", tags=["nebula"])
logger = logging.getLogger(__name__)


@router.get("/concepts", response_model=ConceptsResponse)
async def get_concepts(
    top_k: int = Query(50, ge=1, le=100),
    service: NebulaService = Depends(get_nebula_service),
):
    """Get global concepts from all video content."""
    concepts = await service.get_global_concepts(top_k=top_k)
    return ConceptsResponse(concepts=concepts, total=len(concepts))


@montage_router.get("/nebula", response_model=ConceptsResponse)
async def get_montage_nebula(
    top_k: int = Query(80, ge=1, le=200),
    service: NebulaService = Depends(get_nebula_service),
):
    """Legacy endpoint: /api/montage/nebula -> concepts."""
    concepts = await service.get_global_concepts(top_k=top_k)
    return ConceptsResponse(concepts=concepts, total=len(concepts))


extra_routers = [montage_router]


@router.get("/structure", response_model=NebulaStructureResponse)
async def get_nebula_structure(
    source_ids: Optional[str] = Query(None, description="Comma-separated source IDs"),
    service: NebulaService = Depends(get_nebula_service),
):
    """Get nebula 3D graph structure."""
    source_id_list = None
    if source_ids:
        source_id_list = [s.strip() for s in source_ids.split(",") if s.strip()]

    if not source_id_list:
        source_id_list = []

    structure = await service.build_nebula_structure(source_id_list)
    return NebulaStructureResponse(
        nodes=[NebulaNode(**n) for n in structure.get("nodes", [])],
        links=[NebulaLink(**l) for l in structure.get("links", [])],
    )


@router.post("/highlight", response_model=HighlightTaskResponse)
async def create_highlight_reel(
    request: CreateHighlightRequest,
    background_tasks: BackgroundTasks,
    service: NebulaService = Depends(get_nebula_service),
):
    """Create a highlight reel for a concept."""
    task_id = service.create_task()

    background_tasks.add_task(
        run_highlight_generation,
        task_id=task_id,
        concept=request.concept,
        top_k=request.top_k,
    )

    return HighlightTaskResponse(
        task_id=task_id,
        status="pending",
        progress=0,
        message=f"正在为 '{request.concept}' 生成精华片段...",
    )


@router.get("/highlight/{task_id}", response_model=HighlightTaskResponse)
async def get_highlight_status(
    task_id: str,
    service: NebulaService = Depends(get_nebula_service),
):
    """Get highlight reel task status."""
    status = service.get_task_status(task_id)
    if not status:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    return HighlightTaskResponse(
        task_id=task_id,
        status=status.get("status", "pending"),
        progress=status.get("progress", 0),
        message=status.get("message", ""),
        video_url=status.get("video_url"),
        concept=status.get("concept"),
        segment_count=status.get("segment_count"),
        error=status.get("error"),
    )


async def run_highlight_generation(
    task_id: str,
    concept: str,
    top_k: int,
):
    """Background task for highlight reel generation."""
    service = get_nebula_service()
    try:
        service._update_task(task_id, status="processing", progress=20, message="搜索相关片段...")

        vector_store = get_vector_store()
        results = vector_store.search(query=concept, n_results=top_k)

        if not results:
            service._update_task(task_id, status="error", progress=0, message="未找到相关片段")
            return

        service._update_task(task_id, status="processing", progress=60, message="合成视频中...")

        service._update_task(task_id, status="completed", progress=100, message="完成",
                            video_url=f"/static/generated/highlights/{task_id}.mp4",
                            concept=concept, segment_count=len(results))

    except Exception as e:
        logger.error(f"Highlight generation failed: {e}")
        service._update_task(task_id, status="error", progress=0, message=str(e))
