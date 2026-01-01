from fastapi import APIRouter
from app.api import upload, chat, analysis, creative, ingest, montage

router = APIRouter()

# Include all sub-routers
router.include_router(upload.router)
router.include_router(chat.router)
router.include_router(analysis.router)
router.include_router(creative.router)
router.include_router(ingest.router)
router.include_router(montage.router)
