"""
Ingest Pydantic schemas.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


# ==================== Legacy schemas (for backward compatibility) ====================

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


# ==================== New extended schemas ====================

class PlatformEnum(str, Enum):
    """Supported platforms."""
    BILIBILI = "bilibili"
    YOUTUBE = "youtube"
    ARXIV = "arxiv"


class ContentTypeEnum(str, Enum):
    """Content types."""
    VIDEO = "video"
    ARTICLE = "article"
    PAPER = "paper"
    ALL = "all"


class ExtendedSearchRequest(BaseModel):
    """Extended search request supporting multiple platforms."""
    query: str = Field(..., description="Search query string")
    platforms: List[PlatformEnum] = Field(
        default=[PlatformEnum.BILIBILI],
        description="List of platforms to search"
    )
    max_results: int = Field(default=10, ge=1, le=50, description="Max results per platform")
    content_type: ContentTypeEnum = Field(
        default=ContentTypeEnum.ALL,
        description="Filter by content type"
    )


class SearchResultItem(BaseModel):
    """Single search result item."""
    id: str
    title: str
    description: Optional[str] = None
    url: str
    thumbnail: Optional[str] = None
    duration: Optional[int] = None  # seconds
    author: Optional[str] = None
    published_at: Optional[str] = None  # ISO format
    view_count: Optional[int] = None
    platform: str
    content_type: str
    metadata: Optional[Dict[str, Any]] = None


class ExtendedSearchResponse(BaseModel):
    """Extended search response with grouped results."""
    query: str
    results: List[SearchResultItem]
    total_count: int
    platforms_searched: List[str]
    content_type_filter: Optional[str] = None


class FetchContentRequest(BaseModel):
    """Request to fetch and import specific content."""
    content_id: str = Field(..., description="Content ID (e.g., bili_12345, arxiv_1234.5678)")
    platform: PlatformEnum = Field(..., description="Source platform")
    auto_analyze: bool = Field(default=True, description="Auto-analyze after import")


class FetchContentResponse(BaseModel):
    """Response for content fetch request."""
    task_id: str
    status: str
    message: str
