"""
Chat module - RAG-based intelligent conversation.
"""

from .service import ChatService, get_chat_service
from .schemas import (
    ChatRequest,
    ChatResponse,
    ChatReference,
    ContextBridgeRequest,
    ContextBridgeResponse,
)

__all__ = [
    "ChatService",
    "get_chat_service",
    "ChatRequest",
    "ChatResponse",
    "ChatReference",
    "ContextBridgeRequest",
    "ContextBridgeResponse",
]
