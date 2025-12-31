"""API routes module initialization."""
from fastapi import APIRouter
from app.api import upload, chat, analysis, creative, ingest

api_router = APIRouter()

api_router.include_router(upload.router, prefix="/sources", tags=["sources"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(analysis.router, prefix="/analysis", tags=["analysis"])
api_router.include_router(creative.router, prefix="/create", tags=["creative"])
api_router.include_router(ingest.router, prefix="/ingest", tags=["ingest"])

__all__ = ["api_router"]
