"""
Ingest Pydantic schemas.
"""

from typing import Optional, List
from pydantic import BaseModel


class SearchRequest(BaseModel):
    platform: str
    keyword: str
    limit: int = 3


class SearchResponse(BaseModel):
    status: str
    message: str
    task_id: Optional[str] = None


class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    progress: int
    message: str
    source_ids: Optional[List[str]] = None
    error: Optional[str] = None
