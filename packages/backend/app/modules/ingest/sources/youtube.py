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
        Download YouTube video using yt-dlp via subprocess.
        使用subprocess调用yt-dlp命令行，确保使用正确的环境变量。

        Args:
            content_id: YouTube video ID (with or without 'yt_' prefix)
            output_path: Directory to save the video

        Returns:
            Path to downloaded video file
        """
        from pathlib import Path
        import os
        import asyncio

        # Remove prefix if present
        video_id = content_id.replace("yt_", "")

        output_dir = Path(output_path)
        output_dir.mkdir(parents=True, exist_ok=True)

        try:
            # 设置ffmpeg路径
            ffmpeg_path = r"D:\software\ffmpeg-master-latest-win64-gpl-shared\bin\ffmpeg.exe"
            if not os.path.exists(ffmpeg_path):
                raise SearchError(f"ffmpeg not found at {ffmpeg_path}")

            # 设置环境变量
            env = os.environ.copy()
            env['PATH'] = os.path.dirname(ffmpeg_path) + os.pathsep + env.get('PATH', '')

            video_url = f"https://www.youtube.com/watch?v={video_id}"
            logger.info(f"[YouTubeSearcher] Downloading from: {video_url}")
            logger.info(f"[YouTubeSearcher] Using ffmpeg at: {ffmpeg_path}")

            # 构建yt-dlp命令
            cmd = [
                'yt-dlp',
                '--ffmpeg-location', ffmpeg_path,
                '--format', 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
                '--output', str(output_dir / '%(id)s.%(ext)s'),
                '--no-playlist',
                '--newline',
                video_url
            ]

            logger.info(f"[YouTubeSearcher] Running command: {' '.join(cmd)}")

            # 运行yt-dlp
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env
            )

            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                error_msg = stderr.decode('utf-8', errors='ignore')
                logger.error(f"[YouTubeSearcher] yt-dlp failed: {error_msg}")
                raise SearchError(f"yt-dlp failed: {error_msg}")

            # Find downloaded file
            for ext in ['mp4', 'webm', 'mkv']:
                video_path = output_dir / f"{video_id}.{ext}"
                if video_path.exists():
                    logger.info(f"[YouTubeSearcher] Successfully downloaded: {video_path}")
                    return str(video_path)

            # 如果没找到，尝试glob匹配
            downloaded_files = list(output_dir.glob(f"{video_id}*"))
            if downloaded_files:
                logger.info(f"[YouTubeSearcher] Found downloaded file: {downloaded_files[0]}")
                return str(downloaded_files[0])

            # 列出目录中的所有文件进行调试
            all_files = list(output_dir.glob("*"))
            logger.error(f"[YouTubeSearcher] No file found. Directory contents: {[f.name for f in all_files]}")

            raise SearchError(f"Downloaded file not found for {video_id}")

        except ImportError:
            raise SearchError("yt-dlp is not installed. Run: pip install yt-dlp")
        except Exception as e:
            logger.error(f"[YouTubeSearcher] Download error: {e}")
            raise SearchError(f"Failed to download YouTube video: {e}")

    def _download_video(self, url: str, opts: dict) -> None:
        """Synchronous wrapper for yt-dlp download."""
        import yt_dlp
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])
