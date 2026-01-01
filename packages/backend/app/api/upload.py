"""Video upload and source management API."""
import os
import uuid
import asyncio
from pathlib import Path
from typing import List
from fastapi import APIRouter, Depends, UploadFile, File, BackgroundTasks, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core import get_settings
from app.models import Source, SourceStatus
from app.services.media_processor import MediaProcessor
from app.services.intelligence import IntelligenceService
from app.services.vector_store import get_vector_store
from app.api.schemas import SourceResponse, SourceListResponse

router = APIRouter(prefix="/api/sources", tags=["sources"])
settings = get_settings()

# Service singletons
media_processor = MediaProcessor()
intelligence_service = IntelligenceService()

DATA_DIR = Path(__file__).parent.parent.parent / "data"
UPLOADS_DIR = DATA_DIR / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


@router.get("/", response_model=SourceListResponse)
async def get_sources(db: AsyncSession = Depends(get_db)):
    """Get all video sources."""
    result = await db.execute(select(Source).order_by(Source.created_at.desc()))
    sources = result.scalars().all()
    return SourceListResponse(
        sources=[SourceResponse.model_validate(s) for s in sources],
        total=len(sources)
    )


@router.post("/upload")
async def upload_video(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """Upload a video file and trigger processing."""
    # Validate file size
    if file.size and file.size > settings.max_upload_size:
        raise HTTPException(status_code=413, detail="File too large")

    # Generate unique filename
    file_id = str(uuid.uuid4())
    file_ext = os.path.splitext(file.filename)[1]
    filename = f"{file_id}{file_ext}"
    file_path = UPLOADS_DIR / filename

    # Save file
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)

    # Get video duration
    duration = media_processor.get_video_duration(str(file_path))

    # Create source record
    source = Source(
        id=file_id,
        title=file.filename or f"Video_{file_id[:8]}",
        file_path=str(file_path),
        url=f"/static/uploads/{filename}",
        duration=duration,
        status=SourceStatus.UPLOADED
    )
    db.add(source)
    await db.commit()
    await db.refresh(source)

    # Trigger background processing
    asyncio.create_task(process_video(source.id, str(file_path), db))

    return SourceResponse.model_validate(source)


@router.delete("/{source_id}")
async def delete_source(source_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a video source."""
    result = await db.execute(select(Source).where(Source.id == source_id))
    source = result.scalar_one_or_none()

    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    # Delete file
    file_path = Path(source.file_path)
    if file_path.exists():
        file_path.unlink()

    # Delete from DB
    await db.delete(source)
    await db.commit()

    return {"message": "Source deleted"}


@router.post("/{source_id}/analyze")
async def analyze_source(source_id: str, db: AsyncSession = Depends(get_db)):
    """Manually trigger analysis for IMPORTED source (Phase 12)."""
    result = await db.execute(select(Source).where(Source.id == source_id))
    source = result.scalar_one_or_none()

    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    if source.status != SourceStatus.IMPORTED:
        raise HTTPException(status_code=400, detail="Source not in IMPORTED status")

    # Trigger processing
    asyncio.create_task(process_video(source.id, source.file_path, db))

    return {"message": "Analysis started"}


@router.post("/{source_id}/reprocess")
async def reprocess_source(source_id: str, db: AsyncSession = Depends(get_db)):
    """Reprocess a video source."""
    result = await db.execute(select(Source).where(Source.id == source_id))
    source = result.scalar_one_or_none()

    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    # Clear existing data from vector store
    vector_store = get_vector_store()
    vector_store.delete_by_source(source_id)

    # Trigger processing
    asyncio.create_task(process_video(source.id, source.file_path, db))

    return {"message": "Reprocessing started"}


async def process_video(source_id: str, file_path: str, db: AsyncSession):
    """Background video processing pipeline."""
    from app.services.media_processor import MediaProcessor
    from app.services.intelligence import IntelligenceService
    from app.services.vector_store import get_vector_store
    from app.models import Source, SourceStatus
    from sqlalchemy import select

    media_processor = MediaProcessor()
    intelligence_service = IntelligenceService()
    vector_store = get_vector_store()

    try:
        # Update status to PROCESSING
        result = await db.execute(select(Source).where(Source.id == source_id))
        source = result.scalar_one_or_none()
        if source:
            source.status = SourceStatus.PROCESSING
            await db.commit()

        # Extract audio
        temp_dir = Path(settings.temp_dir)
        temp_dir.mkdir(parents=True, exist_ok=True)
        audio_path = temp_dir / f"{source_id}.wav"
        media_processor.extract_audio(file_path, str(audio_path))

        # ASR transcription
        asr_result = await intelligence_service.transcribe_audio(str(audio_path))
        asr_texts = [item["text"] for item in asr_result]

        # Extract frames
        frames = media_processor.extract_frames(
            file_path,
            str(temp_dir / "frames"),
            fps=0.5
        )

        # Analyze frames
        frame_texts = []
        for i, frame_path in enumerate(frames):
            if i >= 50:  # Limit frame count
                break
            try:
                description = await intelligence_service.analyze_frame(frame_path)
                frame_texts.append(description)
            except Exception as e:
                print(f"Frame analysis error: {e}")

        # Generate embeddings and store
        all_texts = asr_texts + frame_texts
        embeddings = await intelligence_service.generate_embeddings(all_texts)

        documents = []
        metadatas = []
        ids = []

        # Store ASR chunks
        for item in asr_result:
            documents.append(item["text"])
            metadatas.append({
                "source_id": source_id,
                "chunk_type": "asr",
                "start": item["start"],
                "end": item["end"]
            })
            ids.append(f"{source_id}_asr_{item['start']:.2f}")

        # Store frame chunks
        for i, (frame_path, text) in enumerate(zip(frames, frame_texts)):
            documents.append(text)
            metadatas.append({
                "source_id": source_id,
                "chunk_type": "frame",
                "frame_number": i
            })
            ids.append(f"{source_id}_frame_{i}")

        vector_store.add_documents(documents, embeddings, metadatas, ids)

        # Update status to DONE
        result = await db.execute(select(Source).where(Source.id == source_id))
        source = result.scalar_one_or_none()
        if source:
            source.status = SourceStatus.DONE
            await db.commit()

    except Exception as e:
        print(f"Processing error: {e}")
        result = await db.execute(select(Source).where(Source.id == source_id))
        source = result.scalar_one_or_none()
        if source:
            source.status = SourceStatus.ERROR
            await db.commit()
