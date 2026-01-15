"""
AI types for perception module.
"""

from typing import List, Optional
from pydantic import BaseModel


class ChatMessage(BaseModel):
    """Chat message for LLM."""
    role: str
    content: str


class FrameAnalysis(BaseModel):
    """Video frame analysis result."""
    timestamp: float
    description: str
    frame_path: str


class SpeechResult(BaseModel):
    """Speech-to-text result."""
    timestamp: float
    text: str
    duration: float


class EmbeddingResult(BaseModel):
    """Text embedding result."""
    embedding: List[float]
    dimensions: int


class ImageGenerationResult(BaseModel):
    """Image generation result."""
    image_path: str
    image_url: str
