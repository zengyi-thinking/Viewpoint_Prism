import logging
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core import get_settings, init_db
from app.api import router as api_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

settings = get_settings()

# Data directories
DATA_DIR = Path(__file__).parent.parent / "data"
UPLOADS_DIR = DATA_DIR / "uploads"
TEMP_DIR = DATA_DIR / "temp"
CHROMA_DIR = DATA_DIR / "chromadb"
GENERATED_DIR = DATA_DIR / "generated"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup: Create directories and init database
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    await init_db()
    logger.info(f"Viewpoint Prism API started on {settings.host}:{settings.port}")
    logger.info(f"Uploads directory: {UPLOADS_DIR.absolute()}")
    logger.info(f"ChromaDB directory: {CHROMA_DIR.absolute()}")
    logger.info(f"Generated directory: {GENERATED_DIR.absolute()}")
    logger.info(f"DashScope API Key configured: {'Yes' if settings.dashscope_api_key else 'No'}")
    logger.info("RELOAD 2026-01-01 22:08:00")  # Trigger reload for montage routes
    yield
    # Shutdown
    logger.info("Viewpoint Prism API shutting down...")


app = FastAPI(
    title="Viewpoint Prism API",
    description="Multi-source video intelligence analysis system",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for serving uploaded videos
# Create the directory first to avoid mount error
DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(DATA_DIR)), name="static")

# Include API routes
app.include_router(api_router, prefix="/api")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "Viewpoint Prism API",
        "version": "0.1.0",
        "status": "running",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
