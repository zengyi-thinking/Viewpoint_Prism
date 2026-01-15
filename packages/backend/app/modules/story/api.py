"""
Story API routes - Webtoon / Cinematic Blog.
"""

from typing import List
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
import logging

from app.modules.story import (
    StoryService,
    get_story_service,
    WebtoonTaskResponse,
    CreateWebtoonRequest,
    MangaPanel,
    VideoSegment,
)

router = APIRouter(prefix="/story", tags=["story"])
legacy_router = APIRouter(prefix="/webtoon", tags=["story"])
logger = logging.getLogger(__name__)


@router.post("/generate", response_model=WebtoonTaskResponse)
async def create_story(
    request: CreateWebtoonRequest,
    background_tasks: BackgroundTasks,
):
    """Start story/webtoon generation from video."""
    max_panels = max(6, min(12, request.max_panels))

    story = get_story_service()
    task_id = story.create_task()

    background_tasks.add_task(
        story.generate_webtoon,
        task_id=task_id,
        source_id=request.source_id,
        max_panels=max_panels,
    )

    return WebtoonTaskResponse(
        task_id=task_id,
        status="pending",
        progress=0,
        message=f"正在绘制故事流... (共 {max_panels} 格)",
        total_panels=max_panels,
    )


@legacy_router.post("/generate", response_model=WebtoonTaskResponse)
async def create_webtoon(
    request: CreateWebtoonRequest,
    background_tasks: BackgroundTasks,
):
    """Legacy endpoint: /api/webtoon/generate."""
    return await create_story(request, background_tasks)


@router.get("/task/{task_id}", response_model=WebtoonTaskResponse)
async def get_story_status(task_id: str):
    """Get story generation task status."""
    story = get_story_service()
    status = story.get_task_status(task_id)

    if not status:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    panels = []
    for panel in status.get("panels", []):
        try:
            panels.append(MangaPanel(
                panel_number=panel["panel_number"],
                time=panel["time"],
                time_formatted=panel["time_formatted"],
                caption=panel["caption"],
                characters=panel.get("characters", ""),
                manga_image_url=panel["manga_image_url"],
                original_frame_url=panel["original_frame_url"],
                video_segment=VideoSegment(**panel["video_segment"]),
            ))
        except Exception as e:
            logger.warning(f"Error parsing panel: {e}")

    return WebtoonTaskResponse(
        task_id=task_id,
        status=status.get("status", "pending"),
        progress=status.get("progress", 0),
        message=status.get("message", ""),
        panels=panels,
        total_panels=status.get("total_panels", 0),
        current_panel=status.get("current_panel", 0),
        blog_title=status.get("blog_title"),
        blog_sections=status.get("blog_sections"),
        error=status.get("error"),
    )


@legacy_router.get("/task/{task_id}", response_model=WebtoonTaskResponse)
async def get_webtoon_status(task_id: str):
    """Legacy endpoint: /api/webtoon/task/{task_id}."""
    return await get_story_status(task_id)


@router.get("/panels/{task_id}")
async def get_story_panels(
    task_id: str,
    since: int = 0,
):
    """Get only panels from a story task (incremental)."""
    story = get_story_service()
    status = story.get_task_status(task_id)

    if not status:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    all_panels = status.get("panels", [])
    new_panels = all_panels[since:]

    return {
        "task_id": task_id,
        "total_panels": len(all_panels),
        "since": since,
        "panels": new_panels,
        "has_more": status.get("status") not in ["completed", "error"],
    }


extra_routers = [legacy_router]
