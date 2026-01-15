import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core import get_settings, init_db
from app.core.router_registry import RouterRegistry

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

settings = get_settings()

# Data directories
DATA_DIR = settings.resolve_path("data")
STATIC_DIR = settings.resolve_path(settings.upload_dir).parent
UPLOADS_DIR = settings.resolve_path(settings.upload_dir)
TEMP_DIR = settings.resolve_path(settings.temp_dir)
CHROMA_DIR = settings.resolve_path(settings.chroma_db_dir)
GENERATED_DIR = DATA_DIR / "generated"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    await init_db()
    logger.info(f"Viewpoint Prism API started on {settings.host}:{settings.port}")
    logger.info(f"Uploads directory: {UPLOADS_DIR.absolute()}")
    logger.info(f"Static directory: {STATIC_DIR.absolute()}")
    logger.info(f"ChromaDB directory: {CHROMA_DIR.absolute()}")
    logger.info(f"Generated directory: {GENERATED_DIR.absolute()}")
    logger.info(f"DashScope API Key configured: {'Yes' if settings.dashscope_api_key else 'No'}")
    yield
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

# Mount static files
STATIC_DIR.mkdir(parents=True, exist_ok=True)
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Include API routers from modules (auto-discovery)
RouterRegistry(app).register_modules(prefix="/api")


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
