"""
Crawler Service - Network Video Search and Download
Phase 11: Activate Network Search

Features:
1. Search videos from Bilibili/YouTube using yt-dlp
2. Auto-download and trigger intelligence pipeline
"""

import asyncio
import uuid
import subprocess
import threading
from pathlib import Path
from typing import Dict, Any, Optional, List
import logging

from app.core import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Data directories
DATA_DIR = Path(__file__).parent.parent.parent / "data"
UPLOADS_DIR = DATA_DIR / "uploads"


class CrawlerService:
    """Network video crawler service using yt-dlp."""

    def __init__(self):
        """Initialize crawler service."""
        self._tasks: Dict[str, Dict[str, Any]] = {}

    def search_and_download(
        self,
        platform: str,
        keyword: str,
        limit: int = 3
    ) -> Dict[str, Any]:
        """
        Search and download videos from network platforms.

        Args:
            platform: 'bili' (Bilibili) or 'yt' (YouTube)
            keyword: Search keyword
            limit: Maximum number of videos to download

        Returns:
            Result dict with status and downloaded file paths
        """
        # TikTok not supported
        if platform == 'tiktok':
            return {
                "status": "error",
                "message": "TikTok 暂不支持自动搜索，请手动上传",
                "files": []
            }

        # Build search URL for yt-dlp
        # Note: YouTube search works well, Bilibili search may not be supported
        if platform == 'bili':
            # Bilibili search is experimental - try webv2 format
            search_url = f"bilibili:search {keyword}"
        elif platform == 'yt':
            search_url = f"ytsearch{limit}:{keyword}"
        else:
            return {
                "status": "error",
                "message": f"不支持的平台: {platform}",
                "files": []
            }

        logger.info(f"[Crawler] Starting search: platform={platform}, keyword={keyword}, limit={limit}")

        # Download directory
        download_dir = UPLOADS_DIR
        download_dir.mkdir(parents=True, exist_ok=True)

        # yt-dlp configuration
        ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': str(download_dir / '%(id)s.%(ext)s'),
            'noplaylist': True,
            'quiet': False,
            'no_warnings': False,
            'extract_flat': False,
        }

        downloaded_files = []

        try:
            import yt_dlp

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Search and download
                logger.info(f"[Crawler] Searching with URL: {search_url}")

                # First, get search results without downloading
                info_opts = ydl_opts.copy()
                info_opts['extract_flat'] = True  # Faster - don't extract full info
                info_opts['quiet'] = True

                with yt_dlp.YoutubeDL(info_opts) as ydl_info:
                    info = ydl_info.extract_info(search_url, download=False)

                if not info or 'entries' not in info:
                    logger.warning(f"[Crawler] No search results found for: {keyword}")
                    return {
                        "status": "error",
                        "message": f"未找到与 '{keyword}' 相关的视频",
                        "files": []
                    }

                entries = info.get('entries', [])
                if not entries:
                    return {
                        "status": "error",
                        "message": f"未找到与 '{keyword}' 相关的视频",
                        "files": []
                    }

                logger.info(f"[Crawler] Found {len(entries)} results, downloading top {min(limit, len(entries))}")

                # Download top results
                for i, entry in enumerate(entries[:limit]):
                    try:
                        video_url = entry.get('url') or entry.get('webpage_url')
                        if not video_url:
                            logger.warning(f"[Crawler] No URL for entry {i}")
                            continue

                        video_id = entry.get('id', f'unknown_{i}')
                        logger.info(f"[Crawler] Downloading video {i+1}/{limit}: {video_id}")

                        # Download this video
                        ydl.download([video_url])

                        # Construct expected file path
                        # yt-dlp saves as {id}.mp4
                        file_path = download_dir / f"{video_id}.mp4"

                        # Check if file exists (might have different extension)
                        if not file_path.exists():
                            # Try to find any file with this ID
                            matching_files = list(download_dir.glob(f"{video_id}.*"))
                            if matching_files:
                                file_path = matching_files[0]
                            else:
                                logger.warning(f"[Crawler] Downloaded file not found for {video_id}")
                                continue

                        downloaded_files.append({
                            "id": video_id,
                            "title": entry.get('title', f'Video_{video_id}'),
                            "file_path": str(file_path),
                            "url": f"/static/uploads/{video_id}.mp4",
                            "platform": platform,
                            "duration": entry.get('duration'),
                        })

                        logger.info(f"[Crawler] Downloaded: {file_path}")

                    except Exception as e:
                        logger.error(f"[Crawler] Error downloading video {i}: {e}")
                        continue

                if downloaded_files:
                    logger.info(f"[Crawler] Successfully downloaded {len(downloaded_files)} videos")
                    return {
                        "status": "success",
                        "message": f"成功下载 {len(downloaded_files)} 个视频",
                        "files": downloaded_files
                    }
                else:
                    return {
                        "status": "error",
                        "message": "下载失败，请检查网络连接或稍后重试",
                        "files": []
                    }

        except ImportError:
            logger.error("[Crawler] yt-dlp not installed")
            return {
                "status": "error",
                "message": "yt-dlp 未安装，请联系管理员安装依赖",
                "files": []
            }
        except Exception as e:
            logger.error(f"[Crawler] Search/download error: {e}")
            return {
                "status": "error",
                "message": f"搜索/下载出错: {str(e)}",
                "files": []
            }

    async def auto_ingest_pipeline(
        self,
        files: List[Dict[str, Any]],
        db_session
    ) -> List[str]:
        """
        Auto-create source records for downloaded files.
        Phase 12: Lazy Analysis - Don't auto-trigger processing.

        Args:
            files: List of file info dicts from search_and_download
            db_session: Database session

        Returns:
            List of created source IDs
        """
        from sqlalchemy import select
        from app.models import Source, SourceStatus

        source_ids = []

        for file_info in files:
            try:
                file_path = Path(file_info["file_path"])
                video_id = file_info["id"]

                # Check if source already exists
                result = await db_session.execute(
                    select(Source).where(Source.title.contains(video_id))
                )
                existing = result.scalar_one_or_none()

                if existing:
                    logger.info(f"[Crawler] Source {video_id} already exists, skipping")
                    source_ids.append(existing.id)
                    continue

                # Phase 12: Create source with IMPORTED status, don't auto-trigger analysis
                source = Source(
                    id=str(uuid.uuid4()),
                    title=file_info["title"],
                    file_path=str(file_path),
                    url=file_info["url"],
                    file_type="video",
                    platform=file_info["platform"],
                    status=SourceStatus.IMPORTED.value,  # Changed from UPLOADED to IMPORTED
                )
                db_session.add(source)
                await db_session.flush()
                await db_session.refresh(source)

                logger.info(f"[Crawler] Created source {source.id} for {file_info['title']} (IMPORTED, awaiting manual analysis)")

                source_ids.append(source.id)

            except Exception as e:
                logger.error(f"[Crawler] Error ingesting file {file_info}: {e}")
                continue

        await db_session.commit()
        return source_ids

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a crawler task."""
        return self._tasks.get(task_id)

    def create_task(self) -> str:
        """Create a new task and return its ID."""
        task_id = str(uuid.uuid4())[:8]
        self._tasks[task_id] = {
            "status": "pending",
            "progress": 0,
            "message": "等待开始...",
        }
        return task_id

    def update_task(self, task_id: str, status: Dict[str, Any]):
        """Update task status."""
        self._tasks[task_id] = status


# Singleton instance
_crawler_service: Optional[CrawlerService] = None


def get_crawler_service() -> CrawlerService:
    """Get or create CrawlerService singleton."""
    global _crawler_service
    if _crawler_service is None:
        _crawler_service = CrawlerService()
    return _crawler_service
