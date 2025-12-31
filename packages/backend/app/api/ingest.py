"""Network search and ingest routes."""
import uuid
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, Any

from app.services.crawler import get_crawler_service

router = APIRouter()

# In-memory task storage
_tasks: Dict[str, Dict[str, Any]] = {}


class SearchRequest(BaseModel):
    platform: str = "bilibili"
    keyword: str
    limit: int = 3


@router.post("/search")
async def network_search(request: SearchRequest):
    """Search and download videos from platform."""
    task_id = str(uuid.uuid4())

    # Initialize task
    _tasks[task_id] = {
        "status": "searching",
        "progress": 10,
        "message": f"Searching {request.platform} for '{request.keyword}'..."
    }

    # Start search
    crawler = get_crawler_service()

    try:
        results = crawler.search_and_download(
            platform=request.platform,
            keyword=request.keyword,
            limit=request.limit
        )

        _tasks[task_id] = {
            "status": "completed",
            "progress": 100,
            "message": f"Found {len(results)} videos",
            "files": results
        }

    except Exception as e:
        _tasks[task_id] = {
            "status": "error",
            "progress": 0,
            "error": str(e)
        }

    return {"task_id": task_id}


@router.get("/tasks/{task_id}")
async def get_search_task_status(task_id: str):
    """Get search task status."""
    if task_id in _tasks:
        return _tasks[task_id]
    else:
        raise HTTPException(404, "Task not found")
