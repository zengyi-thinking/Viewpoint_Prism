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

    async def fetch_video_info(self, content_id: str) -> dict:
        """Fetch video information from Bilibili."""
        bvid = content_id.replace("bili_", "")
        video_url = f"https://www.bilibili.com/video/{bvid}"

        try:
            import yt_dlp

            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': True,
            }

            def extract_info():
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    return ydl.extract_info(video_url, download=False)

            loop = __import__('asyncio').get_event_loop()
            info = await loop.run_in_executor(None, extract_info)

            return {
                "id": info.get('id', bvid),
                "title": info.get('title', f"Video_{bvid}"),
                "url": info.get('webpage_url') or video_url,
                "description": info.get('description', ''),
                "thumbnail": info.get('thumbnail', ''),
                "duration": info.get('duration'),
                "author": info.get('uploader') or info.get('channel', ''),
            }

        except Exception as e:
            logger.warning(f"[BilibiliSearcher] Failed to fetch video info: {e}")
            return {
                "id": bvid,
                "title": f"Bilibili_{bvid}",
                "url": video_url,
            }

    async def download(self, content_id: str, output_path: str) -> str:
        """
        Download Bilibili video using yt-dlp via subprocess.
        使用subprocess调用yt-dlp命令行，确保使用正确的环境变量。

        Args:
            content_id: Bilibili video ID (with or without 'bili_' prefix)
            output_path: Directory to save the video

        Returns:
            Path to downloaded video file
        """
        from pathlib import Path
        import subprocess
        import json
        import os
        import asyncio

        # Remove prefix if present
        bvid = content_id.replace("bili_", "")

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

            video_url = f"https://www.bilibili.com/video/{bvid}"
            logger.info(f"[BilibiliSearcher] Downloading from: {video_url}")
            logger.info(f"[BilibiliSearcher] Using ffmpeg at: {ffmpeg_path}")

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

            logger.info(f"[BilibiliSearcher] Running command: {' '.join(cmd)}")
            logger.info(f"[BilibiliSearcher] PATH contains ffmpeg: {os.path.dirname(ffmpeg_path) in env.get('PATH', '')}")

            # 运行yt-dlp
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env
            )

            logger.info(f"[BilibiliSearcher] Process PID: {process.pid}")
            stdout, stderr = await process.communicate()
            logger.info(f"[BilibiliSearcher] Process finished, return code: {process.returncode}")

            stdout_str = stdout.decode('utf-8', errors='ignore')
            stderr_str = stderr.decode('utf-8', errors='ignore')

            logger.info(f"[BilibiliSearcher] yt-dlp stdout: {stdout_str[:500]}")
            logger.error(f"[BilibiliSearcher] yt-dlp stderr: {stderr_str[:500]}")
            logger.info(f"[BilibiliSearcher] yt-dlp return code: {process.returncode}")

            if process.returncode != 0:
                error_msg = stderr_str or stdout_str or "Unknown error"
                logger.error(f"[BilibiliSearcher] yt-dlp failed: {error_msg}")
                raise SearchError(f"yt-dlp failed: {error_msg}")

            # Find downloaded file
            possible_extensions = ['mp4', 'flv', 'webm', 'mkv']
            for ext in possible_extensions:
                video_path = output_dir / f"{bvid}.{ext}"
                if video_path.exists():
                    logger.info(f"[BilibiliSearcher] Successfully downloaded: {video_path}")
                    return str(video_path)

            # 如果没找到，列出目录中的所有文件
            downloaded_files = list(output_dir.glob(f"{bvid}*"))
            if downloaded_files:
                logger.info(f"[BilibiliSearcher] Found downloaded file: {downloaded_files[0]}")
                return str(downloaded_files[0])

            # 列出目录中的所有文件进行调试
            all_files = list(output_dir.glob("*"))
            logger.error(f"[BilibiliSearcher] No file found. Directory contents: {[f.name for f in all_files]}")

            raise SearchError(f"Downloaded file not found for {bvid}")

        except ImportError:
            raise SearchError("yt-dlp is not installed. Run: pip install yt-dlp")
        except Exception as e:
            logger.error(f"[BilibiliSearcher] Download error: {e}")
            raise SearchError(f"Failed to download Bilibili video: {e}")
