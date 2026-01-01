"""Creative video generation routes."""
import uuid
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel

from app.services.creator import get_creator_service
from app.services.director import get_director_service

router = APIRouter()

# In-memory task storage (in real app, use DB)
_tasks: Dict[str, Dict[str, Any]] = {}


class DebateRequest(BaseModel):
    conflict_id: str
    viewpoint_a: Dict[str, Any]
    viewpoint_b: Dict[str, Any]


class DirectorRequest(BaseModel):
    conflict_id: str
    conflict: Dict[str, Any]
    persona: str = "pro"


class SupercutRequest(BaseModel):
    entity_name: str


class DigestRequest(BaseModel):
    source_id: str
    include_types: List[str] = ["STORY", "COMBAT"]


@router.post("/debate")
async def create_debate(request: DebateRequest):
    """Generate AI debate video."""
    task_id = str(uuid.uuid4())

    # Initialize task
    _tasks[task_id] = {
        "status": "pending",
        "progress": 0,
        "message": "Debate task created"
    }

    # Start generation
    creator = get_creator_service()

    try:
        result = await creator.generate_debate(
            request.conflict,
            task_id
        )

        if "error" in result:
            _tasks[task_id] = {
                "status": "error",
                "progress": 0,
                "error": result["error"]
            }
        else:
            _tasks[task_id] = {
                "status": "completed",
                "progress": 100,
                "message": "Debate video generated",
                "video_url": result.get("video_url")
            }

    except Exception as e:
        _tasks[task_id] = {
            "status": "error",
            "progress": 0,
            "error": str(e)
        }

    return {"task_id": task_id}


@router.post("/director_cut")
async def create_director_cut(request: DirectorRequest):
    """Generate AI director cut."""
    task_id = str(uuid.uuid4())

    _tasks[task_id] = {
        "status": "pending",
        "progress": 0,
        "message": "Director task created"
    }

    director = get_director_service()

    try:
        result = await director.generate_director_cut(
            request.conflict,
            request.persona,
            task_id
        )

        if "error" in result:
            _tasks[task_id] = {
                "status": "error",
                "progress": 0,
                "error": result["error"]
            }
        else:
            _tasks[task_id] = {
                "status": "completed",
                "progress": 100,
                "message": "Director cut generated",
                "video_url": result.get("video_url"),
                "script": result.get("script"),
                "persona": result.get("persona"),
                "persona_name": result.get("persona_name")
            }

    except Exception as e:
        _tasks[task_id] = {
            "status": "error",
            "progress": 0,
            "error": str(e)
        }

    return {"task_id": task_id}


@router.post("/supercut")
async def create_supercut(request: SupercutRequest):
    """Generate entity supercut."""
    task_id = str(uuid.uuid4())

    _tasks[task_id] = {
        "status": "pending",
        "progress": 0,
        "message": "Supercut task created"
    }

    # Mock implementation
    _tasks[task_id] = {
        "status": "completed",
        "progress": 100,
        "message": "Supercut generated",
        "video_url": "/static/generated/supercut_demo.mp4"
    }

    return {"task_id": task_id}


@router.post("/digest")
async def create_digest(request: DigestRequest):
    """Generate smart digest."""
    task_id = str(uuid.uuid4())

    _tasks[task_id] = {
        "status": "pending",
        "progress": 0,
        "message": "Digest task created"
    }

    # Mock implementation
    _tasks[task_id] = {
        "status": "completed",
        "progress": 100,
        "message": "Digest generated",
        "video_url": "/static/generated/digest_demo.mp4"
    }

    return {"task_id": task_id}


@router.get("/tasks/{task_id}")
async def get_task_status(task_id: str):
    """Get task status."""
    if task_id in _tasks:
        return _tasks[task_id]
    else:
        raise HTTPException(404, "Task not found")


@router.get("/tasks")
async def list_tasks():
    """List all tasks."""
    return {"tasks": list(_tasks.keys())}
