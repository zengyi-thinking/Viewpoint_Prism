"""
Creative API endpoints for AI-powered content generation.
Phase 6: The Alchemist - AI Debate Video Generator
Phase 7: Entity Supercut - Knowledge Graph Video Compilation
Phase 10: AI Director - Dynamic Audio Narrative
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional, List, Literal
from pathlib import Path
import logging

from app.core import get_db
from app.models import Source
from app.services.creator import get_creator_service
from app.services.director import get_director_service

router = APIRouter(prefix="/create", tags=["creative"])
logger = logging.getLogger(__name__)


# Request/Response Schemas
class DebateRequest(BaseModel):
    """Request for debate video generation."""
    conflict_id: str
    source_a_id: str
    time_a: float
    source_b_id: str
    time_b: float
    # Conflict data for script generation
    topic: str = ""
    viewpoint_a_title: str = ""
    viewpoint_a_description: str = ""
    viewpoint_b_title: str = ""
    viewpoint_b_description: str = ""


class TaskResponse(BaseModel):
    """Response for task creation."""
    task_id: str
    status: str
    message: str


class TaskStatusResponse(BaseModel):
    """Response for task status query."""
    task_id: str
    status: str
    progress: int
    message: str
    video_url: Optional[str] = None
    script: Optional[str] = None
    error: Optional[str] = None


async def run_debate_generation(
    task_id: str,
    conflict_data: dict,
    source_a_id: str,
    source_a_path: str,
    time_a: float,
    source_b_id: str,
    source_b_path: str,
    time_b: float,
):
    """Background task for debate video generation."""
    creator = get_creator_service()
    await creator.create_debate_video(
        task_id=task_id,
        conflict_data=conflict_data,
        source_a_id=source_a_id,
        source_a_path=Path(source_a_path),
        time_a=time_a,
        source_b_id=source_b_id,
        source_b_path=Path(source_b_path),
        time_b=time_b,
    )


@router.post("/debate", response_model=TaskResponse)
async def create_debate_video(
    request: DebateRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Start debate video generation task.

    This is a long-running task that:
    1. Generates AI script based on conflict viewpoints
    2. Creates TTS voiceover
    3. Composes split-screen comparison video

    Returns immediately with task_id for progress tracking.
    """
    # Validate sources exist
    result_a = await db.execute(select(Source).where(Source.id == request.source_a_id))
    source_a = result_a.scalar_one_or_none()

    result_b = await db.execute(select(Source).where(Source.id == request.source_b_id))
    source_b = result_b.scalar_one_or_none()

    if not source_a:
        raise HTTPException(status_code=404, detail=f"Source A not found: {request.source_a_id}")
    if not source_b:
        raise HTTPException(status_code=404, detail=f"Source B not found: {request.source_b_id}")

    # Create task
    creator = get_creator_service()
    task_id = creator.create_task()

    # Prepare conflict data for script generation
    conflict_data = {
        "topic": request.topic,
        "viewpoint_a": {
            "title": request.viewpoint_a_title,
            "description": request.viewpoint_a_description,
            "source_id": request.source_a_id,
        },
        "viewpoint_b": {
            "title": request.viewpoint_b_title,
            "description": request.viewpoint_b_description,
            "source_id": request.source_b_id,
        },
    }

    # Start background task
    background_tasks.add_task(
        run_debate_generation,
        task_id=task_id,
        conflict_data=conflict_data,
        source_a_id=request.source_a_id,
        source_a_path=source_a.file_path,
        time_a=request.time_a,
        source_b_id=request.source_b_id,
        source_b_path=source_b.file_path,
        time_b=request.time_b,
    )

    logger.info(f"Started debate generation task: {task_id}")

    return TaskResponse(
        task_id=task_id,
        status="pending",
        message="任务已创建，正在排队处理...",
    )


@router.get("/tasks/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """
    Get status of a creative generation task.

    Returns current progress, status, and result URL when complete.
    """
    creator = get_creator_service()
    status = creator.get_task_status(task_id)

    if not status:
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")

    return TaskStatusResponse(
        task_id=task_id,
        status=status.get("status", "unknown"),
        progress=status.get("progress", 0),
        message=status.get("message", ""),
        video_url=status.get("video_url"),
        script=status.get("script"),
        error=status.get("error"),
    )


@router.get("/tasks")
async def list_tasks():
    """List all tasks (for debugging)."""
    creator = get_creator_service()
    return {
        "tasks": [
            {
                "task_id": tid,
                "status": status.get("status"),
                "progress": status.get("progress"),
            }
            for tid, status in creator._tasks.items()
        ]
    }


# ========================================
# Phase 7: Entity Supercut API Endpoints
# ========================================

class SupercutRequest(BaseModel):
    """Request for entity supercut video generation."""
    entity_name: str
    top_k: int = 5  # Maximum number of clips


class EntityStatsResponse(BaseModel):
    """Response for entity statistics."""
    entity_name: str
    video_count: int
    occurrence_count: int


class SupercutClipInfo(BaseModel):
    """Information about a clip in the supercut."""
    source_id: str
    video_title: str
    timestamp: str
    score: float


class SupercutStatusResponse(BaseModel):
    """Response for supercut task status."""
    task_id: str
    status: str
    progress: int
    message: str
    video_url: Optional[str] = None
    entity_name: Optional[str] = None
    clip_count: Optional[int] = None
    clips: Optional[List[SupercutClipInfo]] = None
    error: Optional[str] = None


async def run_supercut_generation(
    task_id: str,
    entity_name: str,
    top_k: int,
):
    """Background task for supercut video generation."""
    creator = get_creator_service()
    await creator.create_entity_supercut(
        task_id=task_id,
        entity_name=entity_name,
        top_k=top_k,
    )


@router.post("/supercut", response_model=TaskResponse)
async def create_supercut_video(
    request: SupercutRequest,
    background_tasks: BackgroundTasks,
):
    """
    Start entity supercut video generation task.

    This is a long-running task that:
    1. Searches ChromaDB for clips mentioning the entity
    2. Trims and watermarks each clip
    3. Concatenates clips into a single video

    Returns immediately with task_id for progress tracking.
    """
    if not request.entity_name.strip():
        raise HTTPException(status_code=400, detail="Entity name cannot be empty")

    # Create task
    creator = get_creator_service()
    task_id = creator.create_task()

    # Start background task
    background_tasks.add_task(
        run_supercut_generation,
        task_id=task_id,
        entity_name=request.entity_name,
        top_k=request.top_k,
    )

    logger.info(f"Started supercut generation task for '{request.entity_name}': {task_id}")

    return TaskResponse(
        task_id=task_id,
        status="pending",
        message=f"正在为 '{request.entity_name}' 生成混剪视频...",
    )


@router.get("/entity/{entity_name}/stats", response_model=EntityStatsResponse)
async def get_entity_stats(entity_name: str):
    """
    Get statistics for an entity.

    Returns the number of videos and occurrences for the entity.
    Used by the frontend to display Entity Card information.
    """
    creator = get_creator_service()
    stats = await creator.get_entity_stats(entity_name)

    return EntityStatsResponse(
        entity_name=stats["entity_name"],
        video_count=stats["video_count"],
        occurrence_count=stats["occurrence_count"],
    )


# ========================================
# Phase 8: Smart Digest API Endpoints
# ========================================

class DigestRequest(BaseModel):
    """Request for video digest generation."""
    source_id: str
    include_types: List[str] = ["STORY", "COMBAT"]


class DigestStatusResponse(BaseModel):
    """Response for digest task status."""
    task_id: str
    status: str
    progress: int
    message: str
    video_url: Optional[str] = None
    source_id: Optional[str] = None
    segment_count: Optional[int] = None
    include_types: Optional[List[str]] = None
    total_duration: Optional[float] = None
    error: Optional[str] = None


async def run_digest_generation(
    task_id: str,
    source_id: str,
    source_path: str,
    timeline_events: list,
    include_types: list,
):
    """Background task for digest video generation."""
    creator = get_creator_service()
    await creator.create_video_digest(
        task_id=task_id,
        source_id=source_id,
        source_path=Path(source_path),
        timeline_events=timeline_events,
        include_types=include_types,
    )


@router.post("/digest", response_model=TaskResponse)
async def create_digest_video(
    request: DigestRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Start video digest generation task.

    This is a long-running task that:
    1. Filters timeline events by selected types (STORY, COMBAT)
    2. Trims and concatenates selected segments with fade transitions
    3. Outputs a condensed "best of" video

    Returns immediately with task_id for progress tracking.
    """
    # Validate source exists
    result = await db.execute(select(Source).where(Source.id == request.source_id))
    source = result.scalar_one_or_none()

    if not source:
        raise HTTPException(status_code=404, detail=f"Source not found: {request.source_id}")

    # Get timeline events from analysis service
    from app.services import get_analysis_service
    analysis_service = get_analysis_service()

    # Get cached timeline or generate new one
    timeline_result = await analysis_service.generate_timeline(request.source_id, use_cache=True)
    timeline_events = timeline_result.get("timeline", [])

    if not timeline_events:
        raise HTTPException(status_code=400, detail="No timeline events found. Please generate analysis first.")

    # Create task
    creator = get_creator_service()
    task_id = creator.create_task()

    # Start background task
    background_tasks.add_task(
        run_digest_generation,
        task_id=task_id,
        source_id=request.source_id,
        source_path=source.file_path,
        timeline_events=timeline_events,
        include_types=request.include_types,
    )

    logger.info(f"Started digest generation task for source '{request.source_id}': {task_id}")

    return TaskResponse(
        task_id=task_id,
        status="pending",
        message=f"正在生成浓缩视频 (类型: {', '.join(request.include_types)})...",
    )


# ========================================
# Phase 10: AI Director Cut API Endpoints
# ========================================

class DirectorCutRequest(BaseModel):
    """Request for AI director cut video generation."""
    conflict_id: str
    source_a_id: str
    time_a: float
    source_b_id: str
    time_b: float
    persona: Literal["hajimi", "wukong", "pro"] = "pro"
    # Conflict data for script generation
    topic: str = ""
    viewpoint_a_title: str = ""
    viewpoint_a_description: str = ""
    viewpoint_b_title: str = ""
    viewpoint_b_description: str = ""


class DirectorStatusResponse(BaseModel):
    """Response for director cut task status."""
    task_id: str
    status: str
    progress: int
    message: str
    video_url: Optional[str] = None
    script: Optional[str] = None
    persona: Optional[str] = None
    persona_name: Optional[str] = None
    segment_count: Optional[int] = None
    error: Optional[str] = None


async def run_director_generation(
    task_id: str,
    conflict_data: dict,
    source_a_id: str,
    source_a_path: str,
    time_a: float,
    source_b_id: str,
    source_b_path: str,
    time_b: float,
    persona: str,
):
    """Background task for director cut video generation."""
    director = get_director_service()
    await director.create_director_cut(
        task_id=task_id,
        conflict_data=conflict_data,
        source_a_id=source_a_id,
        source_a_path=Path(source_a_path),
        time_a=time_a,
        source_b_id=source_b_id,
        source_b_path=Path(source_b_path),
        time_b=time_b,
        persona=persona,
    )


@router.post("/director_cut", response_model=TaskResponse)
async def create_director_cut_video(
    request: DirectorCutRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Start AI director cut video generation task.

    This is a long-running task that:
    1. Generates dynamic narrative script with LLM
    2. Creates persona-specific TTS voiceovers
    3. Composes video with dynamic audio mixing (original vs voiceover)

    Features:
    - Smart audio mixing: Original audio for highlights, AI narration for commentary
    - Multi-persona: Hajimi (cute cat), Wukong (fierce monkey), Pro (analyst)

    Returns immediately with task_id for progress tracking.
    """
    # Validate sources exist
    result_a = await db.execute(select(Source).where(Source.id == request.source_a_id))
    source_a = result_a.scalar_one_or_none()

    result_b = await db.execute(select(Source).where(Source.id == request.source_b_id))
    source_b = result_b.scalar_one_or_none()

    if not source_a:
        raise HTTPException(status_code=404, detail=f"Source A not found: {request.source_a_id}")
    if not source_b:
        raise HTTPException(status_code=404, detail=f"Source B not found: {request.source_b_id}")

    # Create task
    director = get_director_service()
    task_id = director.create_task()

    # Prepare conflict data
    conflict_data = {
        "topic": request.topic,
        "viewpoint_a": {
            "title": request.viewpoint_a_title,
            "description": request.viewpoint_a_description,
            "source_id": request.source_a_id,
        },
        "viewpoint_b": {
            "title": request.viewpoint_b_title,
            "description": request.viewpoint_b_description,
            "source_id": request.source_b_id,
        },
    }

    # Persona display names
    persona_names = {
        "hajimi": "🐱 哈基米",
        "wukong": "🐵 大圣",
        "pro": "🎙️ 专业解说",
    }

    # Start background task
    background_tasks.add_task(
        run_director_generation,
        task_id=task_id,
        conflict_data=conflict_data,
        source_a_id=request.source_a_id,
        source_a_path=source_a.file_path,
        time_a=request.time_a,
        source_b_id=request.source_b_id,
        source_b_path=source_b.file_path,
        time_b=request.time_b,
        persona=request.persona,
    )

    logger.info(f"Started director cut task ({request.persona}): {task_id}")

    return TaskResponse(
        task_id=task_id,
        status="pending",
        message=f"{persona_names.get(request.persona, '导演')} 正在准备创作...",
    )


@router.get("/director/tasks/{task_id}", response_model=DirectorStatusResponse)
async def get_director_task_status(task_id: str):
    """
    Get status of a director cut generation task.

    Returns current progress, status, and result URL when complete.
    """
    director = get_director_service()
    status = director.get_task_status(task_id)

    if not status:
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")

    return DirectorStatusResponse(
        task_id=task_id,
        status=status.get("status", "unknown"),
        progress=status.get("progress", 0),
        message=status.get("message", ""),
        video_url=status.get("video_url"),
        script=status.get("script"),
        persona=status.get("persona"),
        persona_name=status.get("persona_name"),
        segment_count=status.get("segment_count"),
        error=status.get("error"),
    )


@router.get("/personas")
async def get_available_personas():
    """Get list of available director personas."""
    return {
        "personas": [
            {
                "id": "hajimi",
                "name": "哈基米",
                "emoji": "🐱",
                "description": "可爱猫娘解说，活泼激萌风格",
            },
            {
                "id": "wukong",
                "name": "大圣",
                "emoji": "🐵",
                "description": "齐天大圣风格，狂傲不羁",
            },
            {
                "id": "pro",
                "name": "专业解说",
                "emoji": "🎙️",
                "description": "专业分析师，冷静客观",
            },
        ]
    }
