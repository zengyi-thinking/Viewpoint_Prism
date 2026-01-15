"""
Debate Pydantic schemas.
"""

from typing import Optional, List
from pydantic import BaseModel


class DebateRequest(BaseModel):
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


class DebateTaskResponse(BaseModel):
    task_id: str
    status: str
    message: str


class DebateStatusResponse(BaseModel):
    task_id: str
    status: str
    progress: int
    message: str
    video_url: Optional[str] = None
    script: Optional[str] = None
    error: Optional[str] = None
