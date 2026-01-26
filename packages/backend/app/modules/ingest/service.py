"""
Ingest service - Network video search and download.
"""

import asyncio
import uuid
from pathlib import Path
from typing import Dict, Any, Optional, List
import logging
import threading

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import get_settings
from app.modules.source.models import Source, SourceStatus

# Import extended search components
from .sources import get_searcher, SearchResult

logger = logging.getLogger(__name__)
settings = get_settings()

DATA_DIR = settings.resolve_path("data")
STATIC_DIR = settings.resolve_path(settings.upload_dir).parent
UPLOADS_DIR = settings.resolve_path(settings.upload_dir)


class IngestService:
    """Network video ingest service using yt-dlp."""

    def __init__(self):
        """Initialize ingest service."""
        self._tasks: Dict[str, Dict[str, Any]] = {}

    def search_and_download(
        self,
        platform: str,
        keyword: str,
        limit: int = 3
    ) -> Dict[str, Any]:
        """Search and download videos from network platforms."""
        if platform == 'tiktok':
            return {
                "status": "error",
                "message": "TikTok 暂不支持自动搜索，请手动上传",
                "files": []
            }

        if platform == 'bili':
            search_url = f"bilibili:search {keyword}"
        elif platform == 'yt':
            search_url = f"ytsearch{limit}:{keyword}"
        else:
            return {
                "status": "error",
                "message": f"不支持的平台: {platform}",
                "files": []
            }

        logger.info(f"[Ingest] Starting search: platform={platform}, keyword={keyword}, limit={limit}")

        download_dir = UPLOADS_DIR
        download_dir.mkdir(parents=True, exist_ok=True)

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
                info_opts = ydl_opts.copy()
                info_opts['extract_flat'] = True
                info_opts['quiet'] = True

                with yt_dlp.YoutubeDL(info_opts) as ydl_info:
                    info = ydl_info.extract_info(search_url, download=False)

                if not info or 'entries' not in info:
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

                logger.info(f"[Ingest] Found {len(entries)} results")

                for i, entry in enumerate(entries[:limit]):
                    try:
                        video_url = entry.get('url') or entry.get('webpage_url')
                        if not video_url:
                            continue

                        video_id = entry.get('id', f'unknown_{i}')
                        logger.info(f"[Ingest] Downloading: {video_id}")

                        ydl.download([video_url])

                        file_path = download_dir / f"{video_id}.mp4"

                        if not file_path.exists():
                            matching_files = list(download_dir.glob(f"{video_id}.*"))
                            if matching_files:
                                file_path = matching_files[0]
                            else:
                                continue

                        relative_path = file_path.resolve().relative_to(STATIC_DIR).as_posix()
                        downloaded_files.append({
                            "id": video_id,
                            "title": entry.get('title', f'Video_{video_id}'),
                            "file_path": str(file_path),
                            "url": f"/static/{relative_path}",
                            "platform": platform,
                            "duration": entry.get('duration'),
                        })

                    except Exception as e:
                        logger.error(f"[Ingest] Error downloading: {e}")
                        continue

                if downloaded_files:
                    return {
                        "status": "success",
                        "message": f"成功下载 {len(downloaded_files)} 个视频",
                        "files": downloaded_files
                    }
                else:
                    return {
                        "status": "error",
                        "message": "下载失败",
                        "files": []
                    }

        except ImportError:
            return {
                "status": "error",
                "message": "yt-dlp 未安装",
                "files": []
            }
        except Exception as e:
            logger.error(f"[Ingest] Error: {e}")
            return {
                "status": "error",
                "message": f"搜索/下载出错: {str(e)}",
                "files": []
            }

    async def auto_ingest_pipeline(
        self,
        files: List[Dict[str, Any]],
        db: AsyncSession
    ) -> List[str]:
        """Auto-create source records for downloaded files."""
        source_ids = []

        for file_info in files:
            try:
                file_path = Path(file_info["file_path"])
                video_id = file_info["id"]

                result = await db.execute(
                    select(Source).where(Source.title.contains(video_id))
                )
                existing = result.scalar_one_or_none()

                if existing:
                    source_ids.append(existing.id)
                    continue

                source = Source(
                    id=str(uuid.uuid4()),
                    title=file_info["title"],
                    file_path=str(file_path),
                    url=file_info["url"],
                    file_type="video",
                    platform=file_info["platform"],
                    status=SourceStatus.IMPORTED.value,
                )
                db.add(source)
                await db.flush()

                logger.info(f"[Ingest] Created source: {source.id}")
                source_ids.append(source.id)

            except Exception as e:
                logger.error(f"[Ingest] Error ingesting: {e}")
                continue

        await db.commit()
        return source_ids

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a task."""
        return self._tasks.get(task_id)

    def create_task(self) -> str:
        """Create a new task."""
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

    # ==================== Extended search methods ====================

    async def multi_platform_search(
        self,
        query: str,
        platforms: List[str],
        max_results: int = 10,
        content_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Search multiple platforms concurrently.

        Args:
            query: Search query string
            platforms: List of platform names (bilibili, youtube, arxiv)
            max_results: Maximum results per platform
            content_type: Optional filter by content type

        Returns:
            Dictionary with all search results
        """
        all_results = []
        platforms_searched = []

        # Create search tasks for each platform
        search_tasks = []
        for platform in platforms:
            try:
                searcher = get_searcher(platform)

                # Filter by content type if specified
                if content_type and content_type != "all":
                    if searcher.content_type.value != content_type:
                        logger.info(f"[Ingest] Skipping {platform}: content type mismatch")
                        continue

                search_tasks.append(self._search_platform(searcher, query, max_results))
                platforms_searched.append(platform)

            except ValueError as e:
                logger.warning(f"[Ingest] {e}")
                continue

        # Run searches concurrently
        if search_tasks:
            search_results = await asyncio.gather(*search_tasks, return_exceptions=True)

            for result in search_results:
                if isinstance(result, Exception):
                    logger.error(f"[Ingest] Search error: {result}")
                elif isinstance(result, list):
                    all_results.extend(result)

        return {
            "results": [r.to_dict() for r in all_results],
            "total_count": len(all_results),
            "platforms_searched": platforms_searched,
        }

    async def _search_platform(
        self,
        searcher,
        query: str,
        max_results: int
    ) -> List[SearchResult]:
        """Search a single platform."""
        try:
            logger.info(f"[Ingest] Searching {searcher.platform_name} for '{query}'")
            results = await searcher.search(query, max_results)
            logger.info(f"[Ingest] Found {len(results)} results from {searcher.platform_name}")
            return results
        except Exception as e:
            logger.error(f"[Ingest] Error searching {searcher.platform_name}: {e}")
            return []

    async def fetch_and_process(
        self,
        content_id: str,
        platform: str,
        auto_analyze: bool = True
    ) -> str:
        """
        Fetch content from platform and process it.

        Args:
            content_id: Content ID (with prefix, e.g., bili_12345)
            platform: Platform name
            auto_analyze: Whether to trigger auto-analysis

        Returns:
            Task ID for tracking progress
        """
        task_id = self.create_task()
        self.update_task(task_id, {
            "status": "fetching",
            "progress": 10,
            "message": f"正在获取 {platform} 内容...",
        })

        # Run fetch in background
        thread = threading.Thread(
            target=self._run_fetch_task,
            args=(task_id, content_id, platform, auto_analyze),
            daemon=True
        )
        thread.start()

        return task_id

    def _run_fetch_task(
        self,
        task_id: str,
        content_id: str,
        platform: str,
        auto_analyze: bool
    ):
        """Background task to fetch and process content."""
        import asyncio
        import traceback
        from app.core.database import async_session

        async def fetch_and_create():
            """Async function to handle the entire fetch and create process."""
            # Get searcher and download
            searcher = get_searcher(platform)
            download_dir = UPLOADS_DIR
            download_dir.mkdir(parents=True, exist_ok=True)

            # Update task status
            self.update_task(task_id, {
                "status": "downloading",
                "progress": 20,
                "message": "正在下载内容...",
            })

            # Download content
            file_path = await searcher.download(content_id, str(download_dir))

            self.update_task(task_id, {
                "status": "ingesting",
                "progress": 60,
                "message": "正在导入数据库...",
            })

            # Get content info
            content_info = await searcher.fetch_video_info(content_id)

            title = content_info.get("title", f"Content_{content_id}")
            if not title or title == "Unknown":
                title = f"{platform.upper()} {content_id}"

            # Create source record
            async with async_session() as db:
                file_path_obj = Path(file_path)

                # Check if source already exists
                result = await db.execute(
                    select(Source).where(Source.file_path == str(file_path_obj))
                )
                existing = result.scalar_one_or_none()

                if existing:
                    return existing.id

                source = Source(
                    id=str(uuid.uuid4()),
                    title=title,
                    file_path=str(file_path_obj),
                    url=content_info.get("url", ""),
                    file_type="video" if platform != "arxiv" else "document",
                    platform=platform,
                    status=SourceStatus.IMPORTED.value,
                )
                db.add(source)
                await db.flush()
                await db.commit()
                return source.id

        try:
            # Run async function in new event loop
            source_id = asyncio.run(fetch_and_create())

            self.update_task(task_id, {
                "status": "completed",
                "progress": 100,
                "message": f"成功导入内容",
                "source_ids": [source_id],
            })

        except Exception as e:
            logger.error(f"[Ingest] Fetch task failed: {e}")
            logger.error(traceback.format_exc())
            self.update_task(task_id, {
                "status": "error",
                "progress": 0,
                "message": f"获取失败: {str(e)}",
            })


_ingest_service: Optional[IngestService] = None


def get_ingest_service() -> IngestService:
    """Get or create IngestService singleton."""
    global _ingest_service
    if _ingest_service is None:
        _ingest_service = IngestService()
    return _ingest_service
