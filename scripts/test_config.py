"""
Test Configuration - Viewpoint Prism Integration Tests
"""

import os
import sys
from pathlib import Path

# Add backend to path for imports
BACKEND_DIR = Path(__file__).parent.parent / "packages" / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Video directory configuration
# Uses the existing test video in data/uploads
VIDEO_DIR = BACKEND_DIR / "data" / "uploads"

# Minimum video size to consider (1MB)
MIN_VIDEO_SIZE_MB = 1

# Test configuration
CONFIG = {
    "video_dir": VIDEO_DIR,
    "min_video_size_mb": MIN_VIDEO_SIZE_MB,
    "log_level": "INFO",
    "timeout_seconds": 300,
}


def find_test_video() -> Path | None:
    """
    Find a suitable test video file.

    Returns:
        Path to the first MP4 file that meets size requirements, or None if not found.
    """
    if not VIDEO_DIR.exists():
        print(f"[Config] Video directory not found: {VIDEO_DIR}")
        return None

    for video_path in VIDEO_DIR.glob("*.mp4"):
        size_mb = video_path.stat().st_size / (1024 * 1024)
        if size_mb >= MIN_VIDEO_SIZE_MB:
            print(f"[Config] Found test video: {video_path.name} ({size_mb:.1f} MB)")
            return video_path

    print(f"[Config] No suitable test video found in {VIDEO_DIR}")
    return None


def get_all_test_videos() -> list[Path]:
    """
    Get all test video files.

    Returns:
        List of paths to all MP4 files.
    """
    if not VIDEO_DIR.exists():
        return []

    return sorted(VIDEO_DIR.glob("*.mp4"))


def setup_logging(log_level: str = "INFO"):
    """Configure logging for tests."""
    import logging

    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


if __name__ == "__main__":
    print("=" * 60)
    print("Viewpoint Prism Test Configuration")
    print("=" * 60)
    print(f"Video Directory: {VIDEO_DIR}")
    print(f"Minimum Video Size: {MIN_VIDEO_SIZE_MB} MB")
    print("-" * 60)

    video = find_test_video()
    if video:
        print(f"Primary test video: {video}")
    else:
        print("No test video found!")

    all_videos = get_all_test_videos()
    print(f"Total videos in directory: {len(all_videos)}")

    print("=" * 60)
