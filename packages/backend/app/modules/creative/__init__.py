"""
Creative API routes - Legacy compatibility wrapper.
Phase 6: Debate, Phase 7: Supercut, Phase 8: Digest, Phase 10: Director Cut
"""

from typing import Optional, List
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
import logging

from app.modules.debate import get_debate_service
from app.modules.director import get_director_service
from app.modules.nebula import get_nebula_service

router = APIRouter(prefix="/create", tags=["creative"])
logger = logging.getLogger(__name__)


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


class EntityStatsResponse(BaseModel):
    """Response for entity statistics."""
    entity_name: str
    video_count: int
    occurrence_count: int


class SupercutRequest(BaseModel):
    """Request for entity supercut video generation."""
    entity_name: str
    top_k: int = 5


class DigestRequest(BaseModel):
    """Request for video digest generation."""
    source_id: str
    include_types: List[str] = ["STORY", "COMBAT"]


# Debate endpoints (compatibility with /api/create/debate -> /api/debate/generate)
class DebateRequest(BaseModel):
    """Request for debate video generation."""
    conflict_id: str
    source_a_id: str
    time_a: float
    source_b_id: str
    time_b: float
    topic: str = ""
    viewpoint_a_title: str = ""
    viewpoint_a_description: str = ""
    viewpoint_b_title: str = ""
    viewpoint_b_description: str = ""


async def run_debate_generation(task_id: str, conflict_data: dict, source_a_path: str, time_a: float, source_b_path: str, time_b: float):
    """Background task for debate video generation."""
    from pathlib import Path
    debate = get_debate_service()
    await debate.create_debate_video(
        task_id=task_id, conflict_data=conflict_data,
        source_a_path=Path(source_a_path), time_a=time_a,
        source_b_path=Path(source_b_path), time_b=time_b,
    )


@router.post("/debate", response_model=TaskResponse)
async def create_debate_video(request: DebateRequest, background_tasks: BackgroundTasks):
    """Start debate video generation."""
    debate = get_debate_service()
    task_id = debate.create_task()
    
    conflict_data = {
        "topic": request.topic,
        "viewpoint_a": {"title": request.viewpoint_a_title, "description": request.viewpoint_a_description, "source_id": request.source_a_id},
        "viewpoint_b": {"title": request.viewpoint_b_title, "description": request.viewpoint_b_description, "source_id": request.source_b_id},
    }
    
    background_tasks.add_task(run_debate_generation, task_id, conflict_data, "", request.time_a, "", request.time_b)
    return TaskResponse(task_id=task_id, status="pending", message="辩论视频生成任务已创建...")


@router.get("/tasks", response_model=List[dict])
async def list_tasks():
    """List all tasks."""
    debate = get_debate_service()
    return [{"task_id": tid, "status": s.get("status")} for tid, s in debate._tasks.items()]


@router.get("/tasks/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """Get status of a creative generation task."""
    debate = get_debate_service()
    status = debate.get_task_status(task_id)
    if not status:
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")
    return TaskStatusResponse(task_id=task_id, status=status.get("status", "unknown"), progress=status.get("progress", 0), message=status.get("message", ""), video_url=status.get("video_url"), script=status.get("script"), error=status.get("error"))


# Director endpoints (compatibility with /api/create/director_cut -> /api/director/cut)
class DirectorRequest(BaseModel):
    """Request for AI director cut video generation."""
    conflict_id: str
    source_a_id: str
    time_a: float
    source_b_id: str
    time_b: float
    persona: str = "pro"
    topic: str = ""
    viewpoint_a_title: str = ""
    viewpoint_a_description: str = ""
    viewpoint_b_title: str = ""
    viewpoint_b_description: str = ""


PERSONAS = [
    {"id": "hajimi", "name": "哈基米", "emoji": "🐱", "description": "可爱猫娘，活泼激萌"},
    {"id": "wukong", "name": "大圣", "emoji": "🐵", "description": "齐天大圣，狂傲不羁"},
    {"id": "pro", "name": "专业解说", "emoji": "🎙️", "description": "专业分析，冷静客观"},
]


@router.get("/personas")
async def get_personas():
    """Get available director personas."""
    return {"personas": PERSONAS}


async def run_director_generation(task_id: str, conflict_data: dict, source_a_path: str, time_a: float, source_b_path: str, time_b: float, persona: str):
    """Background task for director cut generation."""
    from pathlib import Path
    director = get_director_service()
    await director.create_director_cut(
        task_id=task_id, conflict_data=conflict_data,
        source_a_path=Path(source_a_path), time_a=time_a,
        source_b_path=Path(source_b_path), time_b=time_b,
        persona=persona,
    )


@router.post("/director_cut", response_model=TaskResponse)
async def create_director_cut(request: DirectorRequest, background_tasks: BackgroundTasks):
    """Start AI director cut video generation."""
    director = get_director_service()
    task_id = director.create_task()
    
    conflict_data = {
        "topic": request.topic,
        "viewpoint_a": {"title": request.viewpoint_a_title, "description": request.viewpoint_a_description, "source_id": request.source_a_id},
        "viewpoint_b": {"title": request.viewpoint_b_title, "description": request.viewpoint_b_description, "source_id": request.source_b_id},
    }
    
    background_tasks.add_task(run_director_generation, task_id, conflict_data, "", request.time_a, "", request.time_b, request.persona)
    return TaskResponse(task_id=task_id, status="pending", message="导演剪辑生成任务已创建...")


@router.get("/director/tasks/{task_id}", response_model=TaskStatusResponse)
async def get_director_task_status(task_id: str):
    """Get status of director cut generation task."""
    director = get_director_service()
    status = director.get_task_status(task_id)
    if not status:
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")
    return TaskStatusResponse(task_id=task_id, status=status.get("status", "unknown"), progress=status.get("progress", 0), message=status.get("message", ""), video_url=status.get("video_url"), script=status.get("script"), error=status.get("error"))


# Entity Supercut endpoints
@router.get("/entity/{entity_name}/stats", response_model=EntityStatsResponse)
async def get_entity_stats(entity_name: str):
    """Get statistics for an entity."""
    nebula = get_nebula_service()
    stats = {"entity_name": entity_name, "video_count": 0, "occurrence_count": 0}
    return EntityStatsResponse(**stats)


@router.post("/supercut", response_model=TaskResponse)
async def create_supercut_video(request: SupercutRequest):
    """Start entity supercut video generation."""
    return TaskResponse(task_id="supercut-demo", status="pending", message=f"正在为 '{request.entity_name}' 生成混剪视频...")


# Digest endpoint
@router.post("/digest", response_model=TaskResponse)
async def create_digest_video(request: DigestRequest):
    """Start video digest generation."""
    return TaskResponse(task_id="digest-demo", status="pending", message=f"正在生成浓缩视频...")
