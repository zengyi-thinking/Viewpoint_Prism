"""
Chat API routes.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import json
import logging

from app.core import get_db
from app.models import ChatMessage, Source
from app.modules.chat import (
    ChatService,
    get_chat_service,
    ChatRequest,
    ChatResponse,
    ChatReference,
    ContextBridgeRequest,
    ContextBridgeResponse,
)

router = APIRouter(prefix="/chat", tags=["chat"])
logger = logging.getLogger(__name__)


@router.post("/", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
    service: ChatService = Depends(get_chat_service),
):
    """Send message and get AI response."""
    user_message = ChatMessage(
        session_id=request.session_id,
        role="user",
        content=request.message,
    )
    db.add(user_message)
    await db.flush()

    # 获取 source_ids
    source_ids = request.source_ids if request.source_ids else None
    if not source_ids:
        result = await db.execute(select(Source.id))
        source_ids = [row[0] for row in result.fetchall()]

    logger.info(f"[Chat] Using source_ids: {source_ids}")

    # 检查向量数据库中的数据
    vector_store = service.vector_store
    for sid in source_ids:
        docs = vector_store.get_source_documents(sid)
        logger.info(f"[Chat] Source {sid} has {len(docs)} documents in vector store")

    rag_result = await service.chat_with_video(
        query=request.message,
        source_ids=source_ids,
        n_results=10,
    )

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
    service: ChatService = Depends(get_chat_service),
):
    """Stream chat response."""
    user_message = ChatMessage(
        session_id=request.session_id,
        role="user",
        content=request.message,
    )
    db.add(user_message)
    await db.commit()

    source_ids = request.source_ids if request.source_ids else None
    if not source_ids:
        result = await db.execute(select(Source.id))
        source_ids = [row[0] for row in result.fetchall()]

    return StreamingResponse(
        service.chat_with_video_stream(
            query=request.message,
            source_ids=source_ids,
            n_results=10,
        ),
        media_type="text/event-stream",
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
                pass

        responses.append(ChatResponse(
            role=msg.role,
            content=msg.content,
            references=refs,
        ))

    return responses


@router.delete("/history/{session_id}")
async def clear_chat_history(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Clear chat history."""
    from sqlalchemy import delete

    await db.execute(
        delete(ChatMessage).where(ChatMessage.session_id == session_id)
    )
    await db.commit()

    return {"status": "cleared", "session_id": session_id}


@router.post("/context-bridge", response_model=ContextBridgeResponse)
async def context_bridge(
    request: ContextBridgeRequest,
    service: ChatService = Depends(get_chat_service),
):
    """Generate context bridge when seeking in video."""
    result = await service.generate_context_bridge(
        source_id=request.source_id,
        target_timestamp=request.timestamp,
        previous_timestamp=request.previous_timestamp,
    )

    return ContextBridgeResponse(**result)
