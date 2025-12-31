"""Chat routes for RAG conversation."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any

from app.services.rag_service import get_rag_service

router = APIRouter()


class ChatRequest(BaseModel):
    session_id: str
    message: str
    source_ids: List[str] = []


@router.post("/")
async def chat(request: ChatRequest):
    """RAG chat with video sources."""
    try:
        rag = get_rag_service()

        result = await rag.chat(
            question=request.message,
            source_ids=request.source_ids,
            session_id=request.session_id
        )

        return result

    except Exception as e:
        raise HTTPException(500, f"Chat failed: {str(e)}")


@router.get("/sessions/{session_id}/history")
async def get_chat_history(session_id: str):
    """Get chat session history."""
    # In real app, query from DB
    return {"messages": []}
