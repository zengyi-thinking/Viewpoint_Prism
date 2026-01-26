"""
Base classes for platform searchers.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict, Optional, Any
from enum import Enum


class ContentType(str, Enum):
    """Content type enumeration."""
    VIDEO = "video"
    ARTICLE = "article"
    PAPER = "paper"


@dataclass
class SearchResult:
    """
    Unified search result format across all platforms.

    Attributes:
        id: Unique identifier for the content
        title: Content title
        description: Content description or abstract
        url: Original URL
        thumbnail: Thumbnail URL (for videos)
        duration: Duration in seconds (for videos)
        author: Author or creator name
        published_at: Publication date (ISO format)
        view_count: View count (for videos)
        platform: Platform name
        content_type: Type of content (video/article/paper)
        metadata: Additional platform-specific metadata
    """
    id: str
    title: str
    description: Optional[str] = None
    url: str = ""
    thumbnail: Optional[str] = None
    duration: Optional[int] = None  # seconds
    author: Optional[str] = None
    published_at: Optional[str] = None  # ISO format
    view_count: Optional[int] = None
    platform: str = ""
    content_type: ContentType = ContentType.VIDEO
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "url": self.url,
            "thumbnail": self.thumbnail,
            "duration": self.duration,
            "author": self.author,
            "published_at": self.published_at,
            "view_count": self.view_count,
            "platform": self.platform,
            "content_type": self.content_type.value,
            "metadata": self.metadata or {},
        }


class SearchError(Exception):
    """Custom exception for search errors."""
    pass


class PlatformSearcher(ABC):
    """
    Abstract base class for platform searchers.

    All platform-specific searchers should inherit from this class
    and implement the required methods.
    """

    @property
    @abstractmethod
    def platform_name(self) -> str:
        """Return the platform name."""
        pass

    @property
    @abstractmethod
    def content_type(self) -> ContentType:
        """Return the default content type for this platform."""
        pass

    @abstractmethod
    async def search(self, query: str, max_results: int = 10) -> List[SearchResult]:
        """
        Search for content on the platform.

        Args:
            query: Search query string
            max_results: Maximum number of results to return

        Returns:
            List of SearchResult objects

        Raises:
            SearchError: If search fails
        """
        pass

    async def fetch_video_info(self, content_id: str) -> Dict[str, Any]:
        """
        Fetch detailed information for a single content item.

        Args:
            content_id: Content identifier

        Returns:
            Dictionary with detailed content information
        """
        # Default implementation - override if platform provides detailed info API
        return {}

    async def download(self, content_id: str, output_path: str) -> str:
        """
        Download content to local storage.

        Args:
            content_id: Content identifier
            output_path: Directory to save the downloaded file

        Returns:
            Path to the downloaded file

        Raises:
            SearchError: If download fails
        """
        raise NotImplementedError(f"Download not implemented for {self.platform_name}")
