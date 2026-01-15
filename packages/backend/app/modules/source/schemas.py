"""
Source Pydantic schemas.
"""

from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime
from enum import Enum


class SourceStatus(str, Enum):
    IMPORTED = "imported"
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    ANALYZING = "analyzing"
    DONE = "done"
    ERROR = "error"


class SourceBase(BaseModel):
    title: str
    file_type: str = "video"
    platform: str = "local"


class SourceCreate(SourceBase):
    pass


class SourceResponse(BaseModel):
    id: str
    title: str
    file_path: str
    url: str
    file_type: str
    platform: str
    duration: Optional[float] = None
    thumbnail: Optional[str] = None
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class SourceListResponse(BaseModel):
    sources: List[SourceResponse]
    total: int
