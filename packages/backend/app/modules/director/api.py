"""
Director API routes.
"""

from typing import Literal
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel
from pathlib import Path
import logging

from app.modules.director import (
    DirectorService,
    get_director_service,
    DirectorRequest,
    DirectorTaskResponse,
    DirectorStatusResponse,
    PersonaConfig,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core import get_db
from app.modules.source.models import Source

router = APIRouter(prefix="/director", tags=["director"])
logger = logging.getLogger(__name__)


PERSONAS = [
    {"id": "hajimi", "name": "哈基米", "emoji": "🐱", "description": "可爱猫娘，活泼激萌"},
    {"id": "wukong", "name": "大圣", "emoji": "🐵", "description": "齐天大圣，狂傲不羁"},
    {"id": "pro", "name": "专业解说", "emoji": "🎙️", "description": "专业分析，冷静客观"},
]


async def run_director_generation(
    task_id: str,
    conflict_data: dict,
    source_a_path: str,
    time_a: float,
    source_b_path: str,
    time_b: float,
    persona: str,
):
    """Background task for director cut generation."""
    director = get_director_service()
    await director.create_director_cut(
        task_id=task_id,
        conflict_data=conflict_data,
        source_a_path=Path(source_a_path),
        time_a=time_a,
        source_b_path=Path(source_b_path),
        time_b=time_b,
        persona=persona,
    )


@router.post("/cut", response_model=DirectorTaskResponse)
async def create_director_cut(
    request: DirectorRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Start AI director cut video generation."""
    result_a = await db.execute(select(Source).where(Source.id == request.source_a_id))
    source_a = result_a.scalar_one_or_none()

    result_b = await db.execute(select(Source).where(Source.id == request.source_b_id))
    source_b = result_b.scalar_one_or_none()

    if not source_a:
        raise HTTPException(status_code=404, detail=f"Source A not found: {request.source_a_id}")
    if not source_b:
        raise HTTPException(status_code=404, detail=f"Source B not found: {request.source_b_id}")

    director = get_director_service()
    task_id = director.create_task()

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

    background_tasks.add_task(
        run_director_generation,
        task_id=task_id,
        conflict_data=conflict_data,
        source_a_path=source_a.file_path,
        time_a=request.time_a,
        source_b_path=source_b.file_path,
        time_b=request.time_b,
        persona=request.persona,
    )

    return DirectorTaskResponse(
        task_id=task_id,
        status="pending",
        message=f"{PERSONAS[{'hajimi': 0, 'wukong': 1, 'pro': 2}[request.persona]]['name']} 正在准备创作...",
    )


@router.get("/tasks/{task_id}", response_model=DirectorStatusResponse)
async def get_director_task_status(task_id: str):
    """Get director task status."""
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
    """Get list of available personas."""
    return {"personas": PERSONAS}
