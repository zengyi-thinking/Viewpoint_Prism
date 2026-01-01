"""
Ingest API - Network Video Search and Download
Phase 11: Activate Network Search

Endpoints:
- POST /api/ingest/search - Search and download videos from network platforms
"""

import asyncio
import uuid
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional, List
import logging

from app.core import get_db
from app.services import get_crawler_service

router = APIRouter(prefix="/ingest", tags=["ingest"])
logger = logging.getLogger(__name__)


class SearchRequest(BaseModel):
    """Request model for network search."""
    platform: str  # 'bili', 'yt', or 'tiktok'
    keyword: str
    limit: Optional[int] = 3


class SearchResponse(BaseModel):
    """Response model for network search."""
    status: str
    message: str
    task_id: Optional[str] = None
    source_ids: Optional[List[str]] = None


def run_search_task(
    task_id: str,
    platform: str,
    keyword: str,
    limit: int
):
    """
    Background task to run network search and auto-ingest.

    This runs in a thread pool since search_and_download is synchronous.
    """
    import traceback
    from app.core.database import async_session
    from sqlalchemy import select
    from app.models import Source

    logger.info(f"[Ingest] Background search task started: {task_id}")

    try:
        # Run the sync search in thread pool
        def run_search():
            crawler = get_crawler_service()
            return crawler.search_and_download(platform, keyword, limit)

        # Run in thread pool to avoid blocking
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        result = loop.run_until_complete(
            asyncio.to_thread(run_search)
        )
        loop.close()

        if result["status"] == "error":
            logger.error(f"[Ingest] Search failed: {result['message']}")
            crawler = get_crawler_service()
            crawler.update_task(task_id, {
                "status": "error",
                "progress": 0,
                "message": result["message"],
            })
            return

        downloaded_files = result.get("files", [])
        logger.info(f"[Ingest] Downloaded {len(downloaded_files)} files")

        # Update task: downloading done, now ingesting
        crawler = get_crawler_service()
        crawler.update_task(task_id, {
            "status": "ingesting",
            "progress": 60,
            "message": f"正在导入 {len(downloaded_files)} 个视频到系统...",
        })

        # Auto-ingest: create database records and trigger processing
        async def ingest_files():
            async with async_session() as db:
                crawler = get_crawler_service()
                source_ids = await crawler.auto_ingest_pipeline(downloaded_files, db)

                # Update final status
                crawler.update_task(task_id, {
                    "status": "completed",
                    "progress": 100,
                    "message": f"成功搜索并导入 {len(source_ids)} 个视频",
                    "source_ids": source_ids,
                })
                logger.info(f"[Ingest] Task {task_id} completed: {len(source_ids)} sources created")

        # Run ingest in new loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(ingest_files())
        loop.close()

    except Exception as e:
        logger.error(f"[Ingest] Background task FAILED: {e}")
        logger.error(traceback.format_exc())
        crawler = get_crawler_service()
        crawler.update_task(task_id, {
            "status": "error",
            "progress": 0,
            "message": f"搜索失败: {str(e)}",
        })


@router.post("/search", response_model=SearchResponse)
async def search_network(
    request: SearchRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Search and download videos from network platforms.

    Args:
        platform: 'bili' (Bilibili), 'yt' (YouTube), or 'tiktok' (not supported)
        keyword: Search keyword
        limit: Maximum number of videos to download (default: 3)

    Returns:
        Task ID for tracking search progress

    Process:
        1. Search platform with keyword using yt-dlp
        2. Download top results
        3. Auto-create source records in database
        4. Trigger intelligence pipeline processing
    """
    # Validate platform
    valid_platforms = ['bili', 'yt', 'tiktok']
    if request.platform not in valid_platforms:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的平台: {request.platform}. 支持的平台: {', '.join(valid_platforms)}"
        )

    # Validate keyword
    if not request.keyword or len(request.keyword.strip()) == 0:
        raise HTTPException(
            status_code=400,
            detail="搜索关键词不能为空"
        )

    # Create task
    crawler = get_crawler_service()
    task_id = crawler.create_task()

    # Update initial status
    crawler.update_task(task_id, {
        "status": "searching",
        "progress": 10,
        "message": f"正在从 {request.platform} 搜索: {request.keyword}...",
    })

    # Start background task
    import threading
    thread = threading.Thread(
        target=run_search_task,
        args=(task_id, request.platform, request.keyword, request.limit),
        daemon=True
    )
    thread.start()
    logger.info(f"[Ingest] Started background search task: {task_id}")

    return SearchResponse(
        status="started",
        message=f"正在从 {request.platform} 搜索 '{request.keyword}'...",
        task_id=task_id,
    )


@router.get("/tasks/{task_id}")
async def get_search_task_status(task_id: str):
    """
    Get status of a search task.

    Args:
        task_id: Task ID from search endpoint

    Returns:
        Task status with progress and created source IDs (if completed)
    """
    crawler = get_crawler_service()
    task = crawler.get_task_status(task_id)

    if not task:
        raise HTTPException(
            status_code=404,
            detail=f"任务不存在: {task_id}"
        )

    return task


@router.get("/platforms")
async def list_supported_platforms():
    """List supported network platforms."""
    return {
        "platforms": [
            {
                "id": "bili",
                "name": "Bilibili",
                "supported": True,
                "description": "哔哩哔哩视频搜索"
            },
            {
                "id": "yt",
                "name": "YouTube",
                "supported": True,
                "description": "YouTube 视频搜索"
            },
            {
                "id": "tiktok",
                "name": "TikTok",
                "supported": False,
                "description": "暂不支持，请手动上传"
            },
            {
                "id": "local",
                "name": "Local",
                "supported": True,
                "description": "本地视频上传"
            }
        ]
    }
