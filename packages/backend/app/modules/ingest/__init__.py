"""
Ingest module - Network video search and download.
"""

from .service import IngestService, get_ingest_service
from .schemas import (
    SearchRequest,
    SearchResponse,
    TaskStatusResponse,
    # Extended schemas
    ExtendedSearchRequest,
    ExtendedSearchResponse,
    SearchResultItem,
    FetchContentRequest,
    FetchContentResponse,
    PlatformEnum,
    ContentTypeEnum,
)

__all__ = [
    "IngestService",
    "get_ingest_service",
    "SearchRequest",
    "SearchResponse",
    "TaskStatusResponse",
    # Extended
    "ExtendedSearchRequest",
    "ExtendedSearchResponse",
    "SearchResultItem",
    "FetchContentRequest",
    "FetchContentResponse",
    "PlatformEnum",
    "ContentTypeEnum",
]
