"""
Ingest API routes.
"""

from typing import Optional, List
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
import logging
import threading

from app.modules.ingest import (
    IngestService,
    get_ingest_service,
    SearchRequest,
    SearchResponse,
    TaskStatusResponse,
    # Extended schemas
    ExtendedSearchRequest,
    ExtendedSearchResponse,
    FetchContentRequest,
    FetchContentResponse,
)

router = APIRouter(prefix="/ingest", tags=["ingest"])
logger = logging.getLogger(__name__)


def run_search_task(
    task_id: str,
    platform: str,
    keyword: str,
    limit: int
):
    """Background task to run network search."""
    import traceback
    from app.core.database import async_session
    from sqlalchemy import select
    from app.modules.source.models import Source

    logger.info(f"[Ingest] Background task started: {task_id}")

    try:
        def run_search():
            ingest = get_ingest_service()
            return ingest.search_and_download(platform, keyword, limit)

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(
            asyncio.to_thread(run_search)
        )
        loop.close()

        if result["status"] == "error":
            logger.error(f"[Ingest] Search failed: {result['message']}")
            ingest = get_ingest_service()
            ingest.update_task(task_id, {
                "status": "error",
                "progress": 0,
                "message": result["message"],
            })
            return

        downloaded_files = result.get("files", [])
        logger.info(f"[Ingest] Downloaded {len(downloaded_files)} files")

        ingest = get_ingest_service()
        ingest.update_task(task_id, {
            "status": "ingesting",
            "progress": 60,
            "message": f"正在导入 {len(downloaded_files)} 个视频...",
        })

        async def ingest_files():
            async with async_session() as db:
                ingest = get_ingest_service()
                source_ids = await ingest.auto_ingest_pipeline(downloaded_files, db)
                ingest.update_task(task_id, {
                    "status": "completed",
                    "progress": 100,
                    "message": f"成功导入 {len(source_ids)} 个视频",
                    "source_ids": source_ids,
                })

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(ingest_files())
        loop.close()

    except Exception as e:
        logger.error(f"[Ingest] Background task failed: {e}")
        logger.error(traceback.format_exc())
        ingest = get_ingest_service()
        ingest.update_task(task_id, {
            "status": "error",
            "progress": 0,
            "message": f"搜索失败: {str(e)}",
        })


@router.post("/search", response_model=SearchResponse)
async def search_network(
    request: SearchRequest,
    background_tasks: BackgroundTasks,
):
    """Search and download videos from network platforms."""
    valid_platforms = ['bili', 'yt', 'tiktok']
    if request.platform not in valid_platforms:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的平台: {request.platform}"
        )

    if not request.keyword or len(request.keyword.strip()) == 0:
        raise HTTPException(status_code=400, detail="搜索关键词不能为空")

    ingest = get_ingest_service()
    task_id = ingest.create_task()
    ingest.update_task(task_id, {
        "status": "searching",
        "progress": 10,
        "message": f"正在搜索: {request.keyword}...",
    })

    thread = threading.Thread(
        target=run_search_task,
        args=(task_id, request.platform, request.keyword, request.limit),
        daemon=True
    )
    thread.start()

    return SearchResponse(
        status="started",
        message=f"正在搜索 '{request.keyword}'...",
        task_id=task_id,
    )


@router.get("/tasks/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """Get status of a search task."""
    ingest = get_ingest_service()
    task = ingest.get_task_status(task_id)

    if not task:
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")

    return TaskStatusResponse(
        task_id=task_id,
        status=task.get("status", "unknown"),
        progress=task.get("progress", 0),
        message=task.get("message", ""),
        source_ids=task.get("source_ids"),
        error=task.get("error"),
    )


@router.get("/platforms")
async def list_supported_platforms():
    """List supported network platforms."""
    return {
        "platforms": [
            {"id": "bili", "name": "Bilibili", "supported": True, "description": "哔哩哔哩"},
            {"id": "yt", "name": "YouTube", "supported": True, "description": "YouTube"},
            {"id": "tiktok", "name": "TikTok", "supported": False, "description": "暂不支持"},
        ]
    }


# ==================== Extended API endpoints ====================

@router.post("/search/extended", response_model=ExtendedSearchResponse)
async def extended_search(request: ExtendedSearchRequest):
    """
    Extended search supporting multiple platforms and content types.

    Searches multiple platforms concurrently and returns combined results.
    Supports filtering by content type (video, paper, article).
    """
    if not request.query or len(request.query.strip()) == 0:
        raise HTTPException(status_code=400, detail="搜索关键词不能为空")

    # Convert platform enums to strings
    platform_names = [p.value for p in request.platforms]
    content_type = request.content_type.value

    logger.info(f"[Ingest] Extended search: query='{request.query}', platforms={platform_names}")

    try:
        ingest = get_ingest_service()
        result = await ingest.multi_platform_search(
            query=request.query,
            platforms=platform_names,
            max_results=request.max_results,
            content_type=content_type
        )

        return ExtendedSearchResponse(
            query=request.query,
            results=result["results"],
            total_count=result["total_count"],
            platforms_searched=result["platforms_searched"],
            content_type_filter=content_type,
        )

    except Exception as e:
        logger.error(f"[Ingest] Extended search error: {e}")
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")


@router.post("/fetch", response_model=FetchContentResponse)
async def fetch_content(request: FetchContentRequest):
    """
    Fetch and import specific content from a platform.

    Downloads the content and creates a source record in the database.
    Returns a task ID for tracking progress.
    """
    import os
    import traceback

    # Set ffmpeg path
    ffmpeg_path = r"D:\software\ffmpeg-master-latest-win64-gpl-shared\bin\ffmpeg.exe"
    if os.path.exists(ffmpeg_path):
        os.environ['PATH'] = os.path.dirname(ffmpeg_path) + os.pathsep + os.environ.get('PATH', '')

    ingest = get_ingest_service()

    # Create task
    task_id = ingest.create_task()
    ingest.update_task(task_id, {
        "status": "fetching",
        "progress": 10,
        "message": f"正在获取 {request.platform.value} 内容...",
    })

    # 直接await（同步等待，临时方案）
    try:
        await ingest._run_fetch_task_async(
            task_id,
            request.content_id,
            request.platform.value,
            request.auto_analyze
        )
    except Exception as e:
        error_msg = str(e) if str(e) else repr(e)
        logger.error(f"[Ingest] Fetch failed: {error_msg}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"导入失败: {error_msg}")

    return FetchContentResponse(
        task_id=task_id,
        status="started",
        message=f"正在获取内容..."
    )


@router.get("/platforms/extended")
async def list_extended_platforms():
    """List all supported platforms for extended search."""
    return {
        "platforms": [
            {
                "id": "bilibili",
                "name": "Bilibili",
                "content_type": "video",
                "supported": True,
                "description": "哔哩哔哩视频搜索"
            },
            {
                "id": "youtube",
                "name": "YouTube",
                "content_type": "video",
                "supported": True,
                "description": "YouTube视频搜索"
            },
            {
                "id": "arxiv",
                "name": "arXiv",
                "content_type": "paper",
                "supported": True,
                "description": "arXiv学术论文搜索"
            },
        ]
    }
