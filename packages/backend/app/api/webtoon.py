"""
Webtoon API endpoints for Cinematic Blog feature.
Phase 14: Cinematic Blog - Transform video into editorial-style visual articles.
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from pydantic import BaseModel
import logging

from app.services.webtoon_service import get_webtoon_service

router = APIRouter(prefix="/webtoon", tags=["webtoon"])
logger = logging.getLogger(__name__)


# ============================================
# Request/Response Schemas
# ============================================

class VideoSegment(BaseModel):
    """Video segment reference for panel."""
    source_id: str
    start: float
    end: float


class MangaPanel(BaseModel):
    """Single manga panel data."""
    panel_number: int
    time: float
    time_formatted: str
    caption: str
    characters: str
    frame_description: Optional[str] = None
    manga_image_url: str
    original_frame_url: str
    video_segment: VideoSegment


class BlogSection(BaseModel):
    """Blog section - either text content or panel reference."""
    type: str  # 'text' or 'panel'
    content: Optional[str] = None  # For text sections
    panel_index: Optional[int] = None  # For panel sections (0-indexed)


class WebtoonTaskResponse(BaseModel):
    """Response for cinematic blog generation task status."""
    task_id: str
    status: str
    progress: int
    message: str
    panels: List[MangaPanel] = []
    total_panels: int = 0
    current_panel: int = 0
    # Cinematic Blog fields
    blog_title: Optional[str] = None
    blog_sections: Optional[List[BlogSection]] = None
    error: Optional[str] = None


class CreateWebtoonRequest(BaseModel):
    """Request to create a webtoon."""
    source_id: str
    max_panels: int = 8


# ============================================
# Webtoon Generation Endpoints
# ============================================

@router.post("/generate", response_model=WebtoonTaskResponse)
async def create_webtoon(
    request: CreateWebtoonRequest,
    background_tasks: BackgroundTasks,
):
    """
    Start AI Webtoon generation from a video source.

    Pipeline:
    1. Extract key story beats (6-12 frames)
    2. Analyze each frame with Qwen-VL
    3. Generate captions and draw prompts with DeepSeek
    4. Create manga panels with Qwen-Image

    The generation runs in background. Poll the task status endpoint for progress.
    Panels are delivered streaming-style (available as they complete).
    """
    webtoon_service = get_webtoon_service()

    # Validate panel count
    max_panels = max(6, min(12, request.max_panels))

    # Create task
    task_id = webtoon_service.create_task()

    # Start background generation
    background_tasks.add_task(
        webtoon_service.generate_webtoon,
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


@router.get("/task/{task_id}", response_model=WebtoonTaskResponse)
async def get_webtoon_status(task_id: str):
    """
    Get status of a cinematic blog generation task.

    Poll this endpoint to track progress and get streaming panels.
    When completed, includes blog_title and blog_sections for article layout.
    """
    webtoon_service = get_webtoon_service()

    status = webtoon_service.get_task_status(task_id)
    if not status:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    # Convert panels to response format
    panels = []
    for panel in status.get("panels", []):
        try:
            panels.append(MangaPanel(
                panel_number=panel["panel_number"],
                time=panel["time"],
                time_formatted=panel["time_formatted"],
                caption=panel["caption"],
                characters=panel.get("characters", ""),
                frame_description=panel.get("frame_description"),
                manga_image_url=panel["manga_image_url"],
                original_frame_url=panel["original_frame_url"],
                video_segment=VideoSegment(**panel["video_segment"]),
            ))
        except Exception as e:
            logger.warning(f"Error parsing panel: {e}")
            continue

    # Convert blog sections to response format
    blog_sections = None
    raw_sections = status.get("blog_sections", [])
    if raw_sections:
        blog_sections = []
        for section in raw_sections:
            try:
                blog_sections.append(BlogSection(
                    type=section["type"],
                    content=section.get("content"),
                    panel_index=section.get("panel_index"),
                ))
            except Exception as e:
                logger.warning(f"Error parsing blog section: {e}")
                continue

    return WebtoonTaskResponse(
        task_id=task_id,
        status=status.get("status", "pending"),
        progress=status.get("progress", 0),
        message=status.get("message", ""),
        panels=panels,
        total_panels=status.get("total_panels", 0),
        current_panel=status.get("current_panel", 0),
        blog_title=status.get("blog_title"),
        blog_sections=blog_sections,
        error=status.get("error"),
    )


@router.get("/panels/{task_id}")
async def get_webtoon_panels(
    task_id: str,
    since: int = Query(0, ge=0, description="Get panels after this index"),
):
    """
    Get only the panels from a webtoon task.

    Useful for incremental updates without full status check.
    Use 'since' parameter to get only new panels.
    """
    webtoon_service = get_webtoon_service()

    status = webtoon_service.get_task_status(task_id)
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
