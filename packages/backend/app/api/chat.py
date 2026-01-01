"""
Chat API endpoints for RAG-based video intelligence conversations.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
import json
import logging

from app.core import get_db
from app.api.schemas import ChatRequest, ChatResponse, ChatReference, ContextBridgeRequest, ContextBridgeResponse
from app.models import ChatMessage, Source
from app.services import get_rag_service

router = APIRouter(prefix="/chat", tags=["chat"])
logger = logging.getLogger(__name__)


@router.post("/", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Send a message and get AI response based on video sources.

    This endpoint uses RAG (Retrieval-Augmented Generation) to:
    1. Search relevant video segments in the knowledge base
    2. Generate a response with proper citations [VideoTitle MM:SS]
    """
    # Save user message
    user_message = ChatMessage(
        session_id=request.session_id,
        role="user",
        content=request.message,
    )
    db.add(user_message)
    await db.flush()

    # Get RAG service
    rag_service = get_rag_service()

    # Determine source IDs to search
    source_ids = request.source_ids if request.source_ids else None

    # If no source IDs specified, get all available sources
    if not source_ids:
        result = await db.execute(select(Source.id))
        source_ids = [row[0] for row in result.fetchall()]

    # Call RAG service
    rag_result = await rag_service.chat_with_video(
        query=request.message,
        source_ids=source_ids,
        n_results=10
    )

    # Build response
    references = [
        ChatReference(
            source_id=ref.get("source_id", ""),
            timestamp=ref.get("timestamp", 0),
            text=ref.get("text", ""),
        )
        for ref in rag_result.get("references", [])
    ]

    response = ChatResponse(
        role="assistant",
        content=rag_result.get("content", ""),
        references=references,
    )

    # Save AI response
    ai_message = ChatMessage(
        session_id=request.session_id,
        role="assistant",
        content=response.content,
        references=json.dumps([r.model_dump() for r in references]),
    )
    db.add(ai_message)

    return response


@router.post("/stream")
async def chat_stream(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Stream chat response using Server-Sent Events.

    Returns a stream of JSON messages:
    - {references: [...]} - Initial references from search
    - {content: "...", done: false} - Content chunks
    - {content: "", done: true} - End of stream
    """
    # Save user message
    user_message = ChatMessage(
        session_id=request.session_id,
        role="user",
        content=request.message,
    )
    db.add(user_message)
    await db.flush()
    await db.commit()

    # Get RAG service
    rag_service = get_rag_service()

    # Determine source IDs to search
    source_ids = request.source_ids if request.source_ids else None

    # If no source IDs specified, get all available sources
    if not source_ids:
        result = await db.execute(select(Source.id))
        source_ids = [row[0] for row in result.fetchall()]

    # Return streaming response
    return StreamingResponse(
        rag_service.chat_with_video_stream(
            query=request.message,
            source_ids=source_ids,
            n_results=10
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@router.get("/history/{session_id}", response_model=List[ChatResponse])
async def get_chat_history(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get chat history for a session."""
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at)
    )
    messages = result.scalars().all()

    responses = []
    for msg in messages:
        refs = []
        if msg.references:
            try:
                refs_data = json.loads(msg.references)
                refs = [ChatReference(**r) for r in refs_data]
            except json.JSONDecodeError:
                # Try with single quote replacement for legacy data
                try:
                    refs_data = json.loads(msg.references.replace("'", '"'))
                    refs = [ChatReference(**r) for r in refs_data]
                except:
                    pass

        responses.append(
            ChatResponse(
                role=msg.role,
                content=msg.content,
                references=refs,
            )
        )

    return responses


@router.delete("/history/{session_id}")
async def clear_chat_history(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Clear chat history for a session."""
    from sqlalchemy import delete

    await db.execute(
        delete(ChatMessage).where(ChatMessage.session_id == session_id)
    )
    await db.commit()

    return {"status": "cleared", "session_id": session_id}


@router.get("/search")
async def search_knowledge(
    q: str = Query(..., description="Search query"),
    source_ids: Optional[str] = Query(None, description="Comma-separated source IDs"),
    limit: int = Query(10, ge=1, le=50),
):
    """
    Search the video knowledge base directly.

    This is a utility endpoint to test knowledge base retrieval.
    """
    from app.services import get_vector_store

    vector_store = get_vector_store()

    source_id_list = None
    if source_ids:
        source_id_list = [s.strip() for s in source_ids.split(",") if s.strip()]

    results = vector_store.search(
        query=q,
        source_ids=source_id_list,
        n_results=limit
    )

    return {
        "query": q,
        "results": results,
        "total": len(results)
    }


@router.post("/context-bridge", response_model=ContextBridgeResponse)
async def context_bridge(
    request: ContextBridgeRequest,
):
    """
    Generate a context bridge summary when user seeks in video.

    This "Second Brain" feature helps users understand what happened
    before and what's happening now when they jump to a new timestamp.

    The response includes:
    - summary: AI-generated bridging text
    - previous_context: Brief description of prior content
    - current_context: Brief description of current content
    - timestamp_str: Formatted timestamp (MM:SS)
    """
    rag_service = get_rag_service()

    result = await rag_service.generate_context_bridge(
        source_id=request.source_id,
        target_timestamp=request.timestamp,
        previous_timestamp=request.previous_timestamp,
    )

    return ContextBridgeResponse(**result)

