"""
Platform searchers for multi-source content ingestion.
"""

from .base import PlatformSearcher, SearchResult, SearchError
from .bilibili import BilibiliSearcher
from .youtube import YouTubeSearcher
from .arxiv import ArxivSearcher

__all__ = [
    "PlatformSearcher",
    "SearchResult",
    "SearchError",
    "BilibiliSearcher",
    "YouTubeSearcher",
    "ArxivSearcher",
]

# Platform registry
SEARCHER_REGISTRY = {
    "bilibili": BilibiliSearcher,
    "youtube": YouTubeSearcher,
    "arxiv": ArxivSearcher,
}


def get_searcher(platform: str) -> PlatformSearcher:
    """Get searcher instance for platform."""
    searcher_class = SEARCHER_REGISTRY.get(platform.lower())
    if not searcher_class:
        raise ValueError(f"Unsupported platform: {platform}")
    return searcher_class()
