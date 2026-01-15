"""
Story Pydantic schemas.
"""

from typing import List, Optional
from pydantic import BaseModel


class VideoSegment(BaseModel):
    source_id: str
    start: float
    end: float


class MangaPanel(BaseModel):
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
    type: str
    content: Optional[str] = None
    panel_index: Optional[int] = None


class WebtoonTaskResponse(BaseModel):
    task_id: str
    status: str
    progress: int
    message: str
    panels: List[MangaPanel] = []
    total_panels: int = 0
    current_panel: int = 0
    blog_title: Optional[str] = None
    blog_sections: Optional[List[BlogSection]] = None
    error: Optional[str] = None


class CreateWebtoonRequest(BaseModel):
    source_id: str
    max_panels: int = 8
