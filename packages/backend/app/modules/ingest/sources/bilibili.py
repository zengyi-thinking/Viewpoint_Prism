"""
Bilibili video searcher implementation.
"""

import logging
from typing import List
import httpx
from dataclasses import dataclass

from .base import PlatformSearcher, SearchResult, ContentType, SearchError

logger = logging.getLogger(__name__)


class BilibiliSearcher(PlatformSearcher):
    """Searcher for Bilibili videos."""

    BILIBILI_SEARCH_API = "https://api.bilibili.com/x/web-interface/search/type"

    @property
    def platform_name(self) -> str:
        return "bilibili"

    @property
    def content_type(self) -> ContentType:
        return ContentType.VIDEO

    async def search(self, query: str, max_results: int = 10) -> List[SearchResult]:
        """
        Search Bilibili for videos.

        Args:
            query: Search query string
            max_results: Maximum number of results

        Returns:
            List of SearchResult objects with video information
        """
        try:
            # Build search parameters
            params = {
                "search_type": "video",
                "keyword": query,
                "page": 1,
            }

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://www.bilibili.com",
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    self.BILIBILI_SEARCH_API,
                    params=params,
                    headers=headers
                )
                response.raise_for_status()
                data = response.json()

            if data.get("code") != 0:
                raise SearchError(f"Bilibili API error: {data.get('message', 'Unknown error')}")

            results = []
            items = data.get("data", {}).get("result", [])

            for item in items[:max_results]:
                try:
                    # Extract video information
                    bvid = item.get("bvid", "")
                    title = item.get("title", "").replace("<em class=\"keyword\">", "").replace("</em>", "")
                    description = item.get("description", "")

                    # Parse duration (format: MM:SS or HH:MM:SS)
                    duration_str = item.get("duration", "")
                    duration = self._parse_duration(duration_str)

                    # Author information
                    author = item.get("author", "")

                    # View count
                    view_count = item.get("play", 0)

                    # Thumbnail
                    thumbnail = item.get("pic", "")

                    # Publish date (timestamp)
                    pubdate = item.get("pubdate", 0)

                    results.append(SearchResult(
                        id=f"bili_{bvid}",
                        title=title,
                        description=description,
                        url=f"https://www.bilibili.com/video/{bvid}",
                        thumbnail=thumbnail,
                        duration=duration,
                        author=author,
                        published_at=None,  # Bilibili API returns timestamp, need conversion
                        view_count=view_count,
                        platform=self.platform_name,
                        content_type=ContentType.VIDEO,
                        metadata={
                            "bvid": bvid,
                            "pubdate": pubdate,
                            "cid": item.get("cid", ""),
                        }
                    ))

                except Exception as e:
                    logger.warning(f"[BilibiliSearcher] Error parsing item: {e}")
                    continue

            logger.info(f"[BilibiliSearcher] Found {len(results)} videos for '{query}'")
            return results

        except httpx.HTTPError as e:
            raise SearchError(f"HTTP error searching Bilibili: {e}")
        except Exception as e:
            raise SearchError(f"Error searching Bilibili: {e}")

    def _parse_duration(self, duration_str: str) -> int:
        """Parse duration string (MM:SS or HH:MM:SS) to seconds."""
        try:
            parts = duration_str.split(":")
            if len(parts) == 2:
                return int(parts[0]) * 60 + int(parts[1])
            elif len(parts) == 3:
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
            return 0
        except (ValueError, AttributeError):
            return 0

    async def download(self, content_id: str, output_path: str) -> str:
        """
        Download Bilibili video using yt-dlp.

        Args:
            content_id: Bilibili video ID (with or without 'bili_' prefix)
            output_path: Directory to save the video

        Returns:
            Path to downloaded video file
        """
        from pathlib import Path

        # Remove prefix if present
        bvid = content_id.replace("bili_", "")

        output_dir = Path(output_path)
        output_dir.mkdir(parents=True, exist_ok=True)

        try:
            import yt_dlp

            ydl_opts = {
                'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
                'outtmpl': str(output_dir / '%(id)s.%(ext)s'),
                'noplaylist': True,
                'quiet': False,
                'no_warnings': False,
            }

            video_url = f"https://www.bilibili.com/video/{bvid}"

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_url, download=True)
                video_id = info.get('id', bvid)

            # Find downloaded file
            for ext in ['mp4', 'flv', 'webm']:
                video_path = output_dir / f"{video_id}.{ext}"
                if video_path.exists():
                    logger.info(f"[BilibiliSearcher] Downloaded {video_path}")
                    return str(video_path)

            raise SearchError(f"Downloaded file not found for {bvid}")

        except ImportError:
            raise SearchError("yt-dlp is not installed")
        except Exception as e:
            raise SearchError(f"Failed to download Bilibili video: {e}")
