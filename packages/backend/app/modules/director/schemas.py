"""
Director Pydantic schemas.
"""

from typing import Optional, List, Literal
from pydantic import BaseModel


class PersonaConfig(BaseModel):
    id: str
    name: str
    emoji: str
    description: str


class DirectorRequest(BaseModel):
    conflict_id: Optional[str] = None
    source_a_id: str
    time_a: float
    source_b_id: str
    time_b: float
    persona: Literal["hajimi", "wukong", "pro"] = "pro"
    topic: str = ""
    viewpoint_a_title: str = ""
    viewpoint_a_description: str = ""
    viewpoint_b_title: str = ""
    viewpoint_b_description: str = ""


class DirectorTaskResponse(BaseModel):
    task_id: str
    status: str
    message: str


class DirectorStatusResponse(BaseModel):
    task_id: str
    status: str
    progress: int
    message: str
    video_url: Optional[str] = None
    script: Optional[str] = None
    persona: Optional[str] = None
    persona_name: Optional[str] = None
    segment_count: Optional[int] = None
    error: Optional[str] = None
