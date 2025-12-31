"""Video upload and management routes."""
import os
import uuid
import shutil
from pathlib import Path
from typing import List
from fastapi import APIRouter, UploadFile, BackgroundTasks, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.models import Source, SourceStatus
from app.services.media_processor import MediaProcessor
from app.services.intelligence import get_intelligence_service
from app.services.vector_store import get_vector_store
from app.core import get_settings

router = APIRouter()
settings = get_settings()


@router.get("/")
async def get_sources():
    """Get all video sources."""
    # Simplified - in real app, query DB
    return {"sources": []}


@router.post("/upload")
async def upload_video(
    file: UploadFile,
    background_tasks: BackgroundTasks
):
    """Upload a video file."""
    try:
        # Validate file
        if not file.filename.lower().endswith((".mp4", ".mov", ".avi", ".mkv")):
            raise HTTPException(400, "Unsupported file format")

        # Read file
        content = await file.read()
        if len(content) > settings.max_upload_size:
            raise HTTPException(400, "File too large")

        # Generate ID
        source_id = str(uuid.uuid4())

        # Save file
        upload_dir = Path(settings.upload_dir)
        upload_dir.mkdir(parents=True, exist_ok=True)

        file_path = upload_dir / f"{source_id}.{file.filename.split('.')[-1]}"

        with open(file_path, "wb") as f:
            f.write(content)

        # Get video info
        media = MediaProcessor()
        duration = media.get_video_duration(str(file_path))

        # Create source record
        source = Source(
            id=source_id,
            title=file.filename,
            file_path=str(file_path),
            url=f"/static/uploads/{source_id}.{file.filename.split('.')[-1]}",
            file_type="video",
            platform="local",
            duration=duration,
            status=SourceStatus.IMPORTED  # Phase 12: Start as IMPORTED
        )

        # In real app, save to DB here
        # For now, return mock response

        return {
            "id": source_id,
            "title": file.filename,
            "status": "imported",
            "duration": duration
        }

    except Exception as e:
        raise HTTPException(500, f"Upload failed: {str(e)}")


@router.delete("/{source_id}")
async def delete_source(source_id: str):
    """Delete a video source."""
    try:
        # In real app, delete from DB and files
        return {"message": "Deleted"}
    except Exception as e:
        raise HTTPException(500, f"Delete failed: {str(e)}")


@router.post("/{source_id}/reprocess")
async def reprocess_source(source_id: str, background_tasks: BackgroundTasks):
    """Reprocess a video source."""
    try:
        # Trigger reprocessing
        return {"message": "Reprocessing started"}
    except Exception as e:
        raise HTTPException(500, f"Reprocess failed: {str(e)}")


@router.post("/{source_id}/analyze")
async def analyze_source(source_id: str, background_tasks: BackgroundTasks):
    """Trigger analysis for imported source."""
    try:
        # Phase 12: Manual analysis trigger
        # Add background task to process
        return {"message": "Analysis started"}
    except Exception as e:
        raise HTTPException(500, f"Analysis failed: {str(e)}")
