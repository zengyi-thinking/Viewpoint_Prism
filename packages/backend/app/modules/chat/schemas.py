"""
Chat Pydantic schemas.
"""

from typing import List, Optional
from pydantic import BaseModel


class ChatRequest(BaseModel):
    session_id: str
    message: str
    source_ids: List[str] = []


class ChatReference(BaseModel):
    source_id: str
    timestamp: float
    text: str


class ChatResponse(BaseModel):
    role: str
    content: str
    references: List[ChatReference] = []


class ContextBridgeRequest(BaseModel):
    source_id: str
    timestamp: float
    previous_timestamp: Optional[float] = None


class ContextBridgeResponse(BaseModel):
    summary: str
    previous_context: str
    current_context: str
    timestamp_str: str
