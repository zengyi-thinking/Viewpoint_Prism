"""
Debate module - AI-powered debate video generation.
"""

from .service import DebateService, get_debate_service
from .schemas import (
    DebateRequest,
    DebateTaskResponse,
    DebateStatusResponse,
)

__all__ = [
    "DebateService",
    "get_debate_service",
    "DebateRequest",
    "DebateTaskResponse",
    "DebateStatusResponse",
]
