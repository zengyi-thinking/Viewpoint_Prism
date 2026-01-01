from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from pathlib import Path
import aiofiles
import uuid
import subprocess
import json
import logging
import asyncio
import threading

from app.core import get_db
from app.api.schemas import SourceResponse, SourceListResponse
from app.models import Source, SourceStatus
from app.services import get_media_processor, get_intelligence_service, get_vector_store

router = APIRouter(prefix="/sources", tags=["sources"])
logger = logging.getLogger(__name__)

# Data directories (relative to backend package)
DATA_DIR = Path(__file__).parent.parent.parent / "data"
UPLOADS_DIR = DATA_DIR / "uploads"


def get_video_duration(file_path: str) -> float:
    """Extract video duration using ffprobe."""
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                str(file_path)
            ],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            return float(data.get("format", {}).get("duration", 0))
    except Exception as e:
        print(f"Failed to get video duration: {e}")
    return 0.0


def process_video_task(source_id: str, file_path: str):
    """Background task to process uploaded video through the Intelligence Pipeline.

    Pipeline stages:
    1. Extract audio and frames (FFmpeg)
    2. Speech-to-text (DashScope Paraformer)
    3. Visual analysis (DashScope Qwen-VL)
    4. Store in vector database (ChromaDB)
    """
    import traceback
    logger.info(f"[Pipeline] Background task started for {source_id}")
    try:
        # Run the async pipeline in a new event loop
        asyncio.run(_process_video_async(source_id, file_path))
        logger.info(f"[Pipeline] Background task completed for {source_id}")
    except Exception as e:
        logger.error(f"[Pipeline] Background task FAILED for {source_id}: {e}")
        logger.error(traceback.format_exc())


async def _process_video_async(source_id: str, file_path: str):
    """Async implementation of the video processing pipeline."""
    from app.core.database import async_session

    logger.info(f"[Pipeline] Starting processing for source {source_id}")

    async with async_session() as db:
        # Get the source record
        result = await db.execute(select(Source).where(Source.id == source_id))
        source = result.scalar_one_or_none()

        if not source:
            logger.error(f"[Pipeline] Source {source_id} not found")
            return

        video_path = Path(file_path)
        video_title = source.title

        try:
            # ========== Stage 1: Processing ==========
            source.status = SourceStatus.PROCESSING.value
            await db.commit()
            logger.info(f"[Pipeline] Stage 1: Media extraction for {source_id}")

            # Get services
            media_processor = get_media_processor()
            intelligence = get_intelligence_service()
            vector_store = get_vector_store()

            # Extract audio and frames concurrently
            media_result = await media_processor.process_video(
                video_path=video_path,
                source_id=source_id,
                frame_interval=5  # Extract frame every 5 seconds
            )

            duration = media_result.get("duration")
            audio_path = media_result.get("audio_path")
            frame_paths = media_result.get("frame_paths", [])

            # Update duration
            if duration:
                source.duration = duration
                await db.commit()

            logger.info(f"[Pipeline] Extracted: duration={duration}s, audio={audio_path is not None}, frames={len(frame_paths)}")

            # ========== Stage 2: AI Analysis ==========
            source.status = SourceStatus.ANALYZING.value
            await db.commit()
            logger.info(f"[Pipeline] Stage 2: AI analysis for {source_id}")

            transcripts = []
            visual_descriptions = []

            # Run ASR and VLM concurrently
            async def run_asr():
                if audio_path:
                    return await intelligence.transcribe_audio(audio_path)
                return []

            async def run_vlm():
                if frame_paths:
                    return await intelligence.analyze_frames(frame_paths, frame_interval=5)
                return []

            transcripts, visual_descriptions = await asyncio.gather(
                run_asr(),
                run_vlm()
            )

            logger.info(f"[Pipeline] Analysis complete: {len(transcripts)} transcripts, {len(visual_descriptions)} visual descriptions")

            # ========== Stage 3: Vector Storage ==========
            logger.info(f"[Pipeline] Stage 3: Storing in vector database for {source_id}")

            doc_count = vector_store.add_video_data(
                source_id=source_id,
                transcripts=transcripts,
                visual_descriptions=visual_descriptions,
                video_title=video_title
            )

            logger.info(f"[Pipeline] Stored {doc_count} documents in vector database")

            # Check if vector storage succeeded
            if doc_count == 0:
                # Check if we had any content to store
                total_content = len(transcripts) + len(visual_descriptions)
                if total_content > 0:
                    # We had content but failed to store - this is an error
                    logger.error(f"[Pipeline] ERROR: Had {total_content} items but stored 0 documents!")
                    raise Exception(f"Vector storage failed: {total_content} items produced but 0 documents stored")
                else:
                    # No content was produced - warn but mark as done
                    logger.warning(f"[Pipeline] WARNING: No transcripts or visual descriptions generated")

            # ========== Complete ==========
            source.status = SourceStatus.DONE.value
            await db.commit()

            logger.info(f"[Pipeline] SUCCESS: Processed video {source_id} - duration={duration}s, docs={doc_count}")

        except Exception as e:
            logger.exception(f"[Pipeline] ERROR processing video {source_id}: {e}")
            source.status = SourceStatus.ERROR.value
            await db.commit()


@router.post("/upload", response_model=SourceResponse)
async def upload_video(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Upload a video file for processing."""

    # Validate file type
    allowed_types = [
        "video/mp4",
        "video/webm",
        "video/quicktime",
        "video/x-msvideo",
        "video/x-matroska",
    ]

    content_type = file.content_type or ""
    if content_type not in allowed_types and not content_type.startswith("video/"):
        raise HTTPException(
            status_code=400,
            detail=f"File type {content_type} not supported. Please upload a video file.",
        )

    # Generate unique ID and directory
    source_id = str(uuid.uuid4())
    source_dir = UPLOADS_DIR / source_id
    source_dir.mkdir(parents=True, exist_ok=True)

    # Save file with original extension
    file_ext = Path(file.filename).suffix if file.filename else ".mp4"
    file_name = f"video{file_ext}"
    file_path = source_dir / file_name

    # Write file to disk
    async with aiofiles.open(file_path, "wb") as f:
        content = await file.read()
        await f.write(content)

    # Construct accessible URL
    relative_path = f"uploads/{source_id}/{file_name}"
    video_url = f"/static/{relative_path}"

    # Create database record
    # Phase 12: Lazy Analysis - Set status to IMPORTED, don't auto-trigger analysis
    source = Source(
        id=source_id,
        title=file.filename or f"Video_{source_id[:8]}",
        file_path=str(file_path),
        url=video_url,
        file_type="video",
        platform="local",
        status=SourceStatus.IMPORTED.value,  # Changed from UPLOADED to IMPORTED
    )
    db.add(source)
    await db.flush()
    await db.refresh(source)

    # Phase 12: Lazy Analysis - Don't auto-trigger background processing
    # User will trigger analysis manually by clicking the checkbox
    logger.info(f"Video {source_id} imported successfully. Status: IMPORTED (awaiting manual analysis)")

    return SourceResponse(
        id=source.id,
        title=source.title,
        file_path=source.file_path,
        url=source.url,
        file_type=source.file_type,
        platform=source.platform,
        duration=source.duration,
        thumbnail=source.thumbnail,
        status=source.status,
        created_at=source.created_at,
    )


@router.get("/", response_model=SourceListResponse)
async def list_sources(
    db: AsyncSession = Depends(get_db),
):
    """List all uploaded video sources."""
    result = await db.execute(select(Source).order_by(Source.created_at.desc()))
    sources = result.scalars().all()

    source_responses = [
        SourceResponse(
            id=s.id,
            title=s.title,
            file_path=s.file_path,
            url=s.url,
            file_type=s.file_type,
            platform=s.platform,
            duration=s.duration,
            thumbnail=s.thumbnail,
            status=s.status,
            created_at=s.created_at,
        )
        for s in sources
    ]

    return SourceListResponse(sources=source_responses, total=len(source_responses))


@router.get("/{source_id}", response_model=SourceResponse)
async def get_source(
    source_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific source by ID."""
    result = await db.execute(select(Source).where(Source.id == source_id))
    source = result.scalar_one_or_none()

    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    return SourceResponse(
        id=source.id,
        title=source.title,
        file_path=source.file_path,
        url=source.url,
        file_type=source.file_type,
        platform=source.platform,
        duration=source.duration,
        thumbnail=source.thumbnail,
        status=source.status,
        created_at=source.created_at,
    )


@router.delete("/{source_id}")
async def delete_source(
    source_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Delete a video source and all associated data."""
    result = await db.execute(select(Source).where(Source.id == source_id))
    source = result.scalar_one_or_none()

    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    # Delete from vector store
    try:
        vector_store = get_vector_store()
        vector_store.delete_source(source_id)
        logger.info(f"Deleted vector data for source {source_id}")
    except Exception as e:
        logger.warning(f"Failed to delete vector data: {e}")

    # Delete file and directory
    source_dir = UPLOADS_DIR / source_id
    if source_dir.exists():
        import shutil
        shutil.rmtree(source_dir)

    # Delete temp files
    temp_dir = DATA_DIR / "temp" / source_id
    if temp_dir.exists():
        import shutil
        shutil.rmtree(temp_dir)

    await db.delete(source)
    return {"status": "deleted", "id": source_id}


@router.get("/debug/chromadb")
async def debug_chromadb():
    """
    Debug endpoint to check ChromaDB status.

    Returns count of documents and unique sources.
    """
    try:
        vector_store = get_vector_store()
        total_docs = vector_store.collection.count()

        # Get unique source IDs
        results = vector_store.collection.get(include=['metadatas'])
        source_ids = set()
        for m in (results.get('metadatas') or []):
            if m and 'source_id' in m:
                source_ids.add(m['source_id'])

        return {
            "total_documents": total_docs,
            "unique_sources": list(source_ids),
            "source_count": len(source_ids),
            "status": "ok" if total_docs > 0 else "empty"
        }
    except Exception as e:
        return {
            "error": str(e),
            "status": "error"
        }


@router.post("/{source_id}/reprocess")
async def reprocess_source(
    source_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Reprocess a video source through the Intelligence Pipeline.

    Use this when video processing failed or data needs to be re-indexed.
    """
    result = await db.execute(select(Source).where(Source.id == source_id))
    source = result.scalar_one_or_none()

    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    # Check if video file exists
    video_path = Path(source.file_path)
    if not video_path.exists():
        raise HTTPException(
            status_code=400,
            detail=f"Video file not found at {source.file_path}"
        )

    # Delete existing vector data for this source
    try:
        vector_store = get_vector_store()
        vector_store.delete_source(source_id)
        logger.info(f"Cleared existing vector data for source {source_id}")
    except Exception as e:
        logger.warning(f"Failed to clear vector data: {e}")

    # Reset status and start reprocessing
    source.status = SourceStatus.UPLOADED.value
    await db.commit()

    # Start background processing
    thread = threading.Thread(
        target=process_video_task,
        args=(source_id, str(video_path)),
        daemon=True
    )
    thread.start()
    logger.info(f"Started reprocessing for source {source_id}")

    return {
        "status": "reprocessing",
        "id": source_id,
        "message": f"重新处理视频 {source.title}，请稍候..."
    }


@router.post("/{source_id}/analyze")
async def analyze_source(
    source_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Manually trigger analysis for an imported video source.
    Phase 12: Lazy Analysis - User clicks checkbox to trigger analysis.

    This endpoint is called when user clicks the checkbox on an IMPORTED source.
    """
    result = await db.execute(select(Source).where(Source.id == source_id))
    source = result.scalar_one_or_none()

    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    # Check if video file exists
    video_path = Path(source.file_path)
    if not video_path.exists():
        raise HTTPException(
            status_code=400,
            detail=f"Video file not found at {source.file_path}"
        )

    # Check current status
    if source.status == SourceStatus.DONE.value:
        return {
            "status": "already_analyzed",
            "id": source_id,
            "message": f"视频 {source.title} 已经分析完成"
        }

    if source.status in [SourceStatus.PROCESSING.value, SourceStatus.ANALYZING.value]:
        return {
            "status": "already_processing",
            "id": source_id,
            "message": f"视频 {source.title} 正在分析中..."
        }

    # Update status to UPLOADED (ready for pipeline)
    source.status = SourceStatus.UPLOADED.value
    await db.commit()

    # Start background processing
    thread = threading.Thread(
        target=process_video_task,
        args=(source_id, str(video_path)),
        daemon=True
    )
    thread.start()
    logger.info(f"Started manual analysis for source {source_id}")

    return {
        "status": "analyzing",
        "id": source_id,
        "message": f"开始分析视频 {source.title}..."
    }
