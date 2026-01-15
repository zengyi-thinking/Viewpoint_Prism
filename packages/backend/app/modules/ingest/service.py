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


_ingest_service: Optional[IngestService] = None


def get_ingest_service() -> IngestService:
    """Get or create IngestService singleton."""
    global _ingest_service
    if _ingest_service is None:
        _ingest_service = IngestService()
    return _ingest_service
