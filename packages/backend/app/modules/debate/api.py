"""
Debate API routes.
"""

from typing import Optional, List
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel
from pathlib import Path
import logging

from app.modules.debate import (
    DebateService,
    get_debate_service,
    DebateRequest,
    DebateTaskResponse,
    DebateStatusResponse,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core import get_db
from app.modules.source.models import Source

router = APIRouter(prefix="/debate", tags=["debate"])
logger = logging.getLogger(__name__)


async def run_debate_generation(
    task_id: str,
    conflict_data: dict,
    source_a_path: str,
    time_a: float,
    source_b_path: str,
    time_b: float,
):
    """Background task for debate generation."""
    debate = get_debate_service()
    await debate.create_debate_video(
        task_id=task_id,
        conflict_data=conflict_data,
        source_a_path=Path(source_a_path),
        time_a=time_a,
        source_b_path=Path(source_b_path),
        time_b=time_b,
    )


@router.post("/generate", response_model=DebateTaskResponse)
async def create_debate_video(
    request: DebateRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Start debate video generation."""
    result_a = await db.execute(select(Source).where(Source.id == request.source_a_id))
    source_a = result_a.scalar_one_or_none()

    result_b = await db.execute(select(Source).where(Source.id == request.source_b_id))
    source_b = result_b.scalar_one_or_none()

    if not source_a:
        raise HTTPException(status_code=404, detail=f"Source A not found: {request.source_a_id}")
    if not source_b:
        raise HTTPException(status_code=404, detail=f"Source B not found: {request.source_b_id}")

    debate = get_debate_service()
    task_id = debate.create_task()

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
        run_debate_generation,
        task_id=task_id,
        conflict_data=conflict_data,
        source_a_path=source_a.file_path,
        time_a=request.time_a,
        source_b_path=source_b.file_path,
        time_b=request.time_b,
    )

    return DebateTaskResponse(
        task_id=task_id,
        status="pending",
        message="辩论视频生成任务已创建...",
    )


@router.get("/tasks/{task_id}", response_model=DebateStatusResponse)
async def get_debate_task_status(task_id: str):
    """Get debate task status."""
    debate = get_debate_service()
    status = debate.get_task_status(task_id)

    if not status:
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")

    return DebateStatusResponse(
        task_id=task_id,
        status=status.get("status", "unknown"),
        progress=status.get("progress", 0),
        message=status.get("message", ""),
        video_url=status.get("video_url"),
        script=status.get("script"),
        error=status.get("error"),
    )
