"""Web crawler service using yt-dlp."""
import logging
import subprocess
import json
from pathlib import Path
from typing import Dict, Any, List, Optional

from app.core import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class CrawlerService:
    """yt-dlp wrapper for video search and download."""

    def __init__(self):
        self.upload_dir = Path(settings.upload_dir)
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    def search_and_download(
        self,
        platform: str,
        keyword: str,
        limit: int = 3
    ) -> List[Dict[str, Any]]:
        """Search and download videos from platform."""

        results = []

        # Build search URL
        if platform.lower() == "bilibili":
            search_query = f"bilibilisearch{limit}:{keyword}"
        elif platform.lower() in ["youtube", "yt"]:
            search_query = f"ytsearch{limit}:{keyword}"
        elif platform.lower() in ["tiktok", "douyin"]:
            search_query = f"tiktoksearch{limit}:{keyword}"
        else:
            return [{"error": f"Unsupported platform: {platform}"}]

        # yt-dlp options
        ydl_opts = {
            "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "outtmpl": str(self.upload_dir / "%(id)s.%(ext)s"),
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
        }

        try:
            import yt_dlp

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Search
                search_cmd = [f"ytsearch{limit}:{keyword}"]
                info = ydl.extract_info(search_query, download=False, process=True)

                if not info or "entries" not in info:
                    return [{"error": "No results found"}]

                # Download each result
                for entry in info["entries"][:limit]:
                    try:
                        video_id = entry.get("id", "")
                        title = entry.get("title", "Unknown")

                        # Download
                        ydl.download([f"ytsearch:{title}"])

                        # Find downloaded file
                        downloaded_file = list(self.upload_dir.glob(f"{video_id}.*"))
                        if downloaded_file:
                            results.append({
                                "id": video_id,
                                "title": title,
                                "file_path": str(downloaded_file[0]),
                                "platform": platform,
                                "url": entry.get("webpage_url", ""),
                                "duration": entry.get("duration", 0)
                            })

                    except Exception as e:
                        logger.error(f"Download error for {entry}: {e}")
                        results.append({"error": f"Failed: {str(e)}"})

            return results

        except ImportError:
            # Fallback to subprocess
            return self._subprocess_download(search_query, limit)
        except Exception as e:
            logger.error(f"Crawler error: {e}")
            return [{"error": str(e)}]

    def _subprocess_download(
        self,
        search_query: str,
        limit: int
    ) -> List[Dict[str, Any]]:
        """Fallback subprocess method."""
        results = []

        cmd = [
            "yt-dlp",
            f"ytsearch{limit}:{search_query}",
            "--format", "best[ext=mp4]/best",
            "-o", str(self.upload_dir / "%(id)s.%(ext)s"),
            "--print", "%(id)s||%(title)s||%(duration)s||%(webpage_url)s"
        ]

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )

            for line in proc.stdout.strip().split("\n"):
                parts = line.split("||")
                if len(parts) == 4:
                    results.append({
                        "id": parts[0],
                        "title": parts[1],
                        "file_path": str(self.upload_dir / f"{parts[0]}.mp4"),
                        "platform": "web",
                        "duration": float(parts[2]) if parts[2] else 0,
                        "url": parts[3]
                    })

        except Exception as e:
            logger.error(f"Subprocess crawler error: {e}")

        return results

    def get_video_info(self, url: str) -> Dict[str, Any]:
        """Get video info without downloading."""
        cmd = [
            "yt-dlp",
            "--dump-json",
            "--skip-download",
            url
        ]

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            return json.loads(proc.stdout)

        except Exception as e:
            logger.error(f"Info extraction error: {e}")
            return {}


# Singleton
_crawler_service: Optional[CrawlerService] = None


def get_crawler_service() -> CrawlerService:
    global _crawler_service
    if _crawler_service is None:
        _crawler_service = CrawlerService()
    return _crawler_service
