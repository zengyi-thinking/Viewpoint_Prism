"""
YouTube video searcher implementation.
"""

import logging
from typing import List, Optional
import httpx

from .base import PlatformSearcher, SearchResult, ContentType, SearchError

logger = logging.getLogger(__name__)


class YouTubeSearcher(PlatformSearcher):
    """Searcher for YouTube videos using yt-dlp."""

    @property
    def platform_name(self) -> str:
        return "youtube"

    @property
    def content_type(self) -> ContentType:
        return ContentType.VIDEO

    async def search(self, query: str, max_results: int = 10) -> List[SearchResult]:
        """
        Search YouTube for videos using yt-dlp.

        Args:
            query: Search query string
            max_results: Maximum number of results

        Returns:
            List of SearchResult objects with video information
        """
        try:
            import yt_dlp

            search_url = f"ytsearch{max_results}:{query}"

            ydl_opts = {
                'format': 'best',
                'extract_flat': True,
                'quiet': True,
                'no_warnings': True,
                'extractor_args': {
                    'youtube': {
                        'player_client': ['android', 'web'],
                    }
                }
            }

            loop = __import__('asyncio').get_event_loop()
            info = await loop.run_in_executor(
                None,
                lambda: self._extract_info(search_url, ydl_opts)
            )

            results = []
            entries = info.get('entries', [])

            for entry in entries:
                try:
                    video_id = entry.get('id', '')
                    title = entry.get('title', 'Untitled')
                    description = entry.get('description', '')

                    # Duration in seconds
                    duration = entry.get('duration')

                    # Channel/Author
                    author = entry.get('channel', '')
                    if not author:
                        author = entry.get('uploader', '')

                    # View count
                    view_count = entry.get('view_count')

                    # Thumbnail
                    thumbnail = entry.get('thumbnail')

                    # URL
                    url = entry.get('webpage_url') or entry.get('url')

                    results.append(SearchResult(
                        id=f"yt_{video_id}",
                        title=title,
                        description=description[:500] if description else None,  # Truncate long descriptions
                        url=url,
                        thumbnail=thumbnail,
                        duration=duration,
                        author=author,
                        published_at=None,  # yt-dlp flat extraction doesn't include date
                        view_count=view_count,
                        platform=self.platform_name,
                        content_type=ContentType.VIDEO,
                        metadata={
                            "video_id": video_id,
                            "channel_id": entry.get('channel_id'),
                        }
                    ))

                except Exception as e:
                    logger.warning(f"[YouTubeSearcher] Error parsing entry: {e}")
                    continue

            logger.info(f"[YouTubeSearcher] Found {len(results)} videos for '{query}'")
            return results

        except ImportError:
            raise SearchError("yt-dlp is not installed")
        except Exception as e:
            raise SearchError(f"Error searching YouTube: {e}")

    def _extract_info(self, url: str, opts: dict) -> dict:
        """Synchronous wrapper for yt-dlp extract_info."""
        import yt_dlp
        with yt_dlp.YoutubeDL(opts) as ydl:
            return ydl.extract_info(url, download=False)

    async def download(self, content_id: str, output_path: str) -> str:
        """
        Download YouTube video using yt-dlp.

        Args:
            content_id: YouTube video ID (with or without 'yt_' prefix)
            output_path: Directory to save the video

        Returns:
            Path to downloaded video file
        """
        from pathlib import Path

        # Remove prefix if present
        video_id = content_id.replace("yt_", "")

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

            video_url = f"https://www.youtube.com/watch?v={video_id}"

            loop = __import__('asyncio').get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self._download_video(video_url, ydl_opts)
            )

            # Find downloaded file
            for ext in ['mp4', 'webm', 'mkv']:
                video_path = output_dir / f"{video_id}.{ext}"
                if video_path.exists():
                    logger.info(f"[YouTubeSearcher] Downloaded {video_path}")
                    return str(video_path)

            raise SearchError(f"Downloaded file not found for {video_id}")

        except ImportError:
            raise SearchError("yt-dlp is not installed")
        except Exception as e:
            raise SearchError(f"Failed to download YouTube video: {e}")

    def _download_video(self, url: str, opts: dict) -> None:
        """Synchronous wrapper for yt-dlp download."""
        import yt_dlp
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])
