from pathlib import Path
from pydantic_settings import BaseSettings
from functools import lru_cache

# Project root directory (where .env is located)
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
ENV_FILE = PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Environment
    env: str = "development"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # Database
    database_url: str = "sqlite+aiosqlite:///./data/viewpoint_prism.db"

    # ChromaDB
    chroma_db_dir: str = "data/chromadb"

    # ========== SophNet AI Services ==========
    # Primary AI service provider - supports LLM, VLM, TTS, Image, Embedding
    sophnet_api_key: str = "pA3uYXtPw3vV3sb3khjGTe8D5Jbi7Bm1Ohk6rGSyXParemqqszyOG5v5-onI62EkR1q-9pqjCgSC-3jQUoiETg"
    sophnet_project_id: str = "5U57ROU7TqfeNINZnKzYZ5"
    sophnet_tts_easyllm_id: str = "7RUpfZakZM7tIygXY5AGgA"
    sophnet_embedding_easyllm_id: str = "6yXUAJl2jrJJLtgiKPq8vH"

    # ========== Legacy AI Services (for backward compatibility) ==========
    # DashScope API (Alibaba Cloud - Qwen-VL & Paraformer) - DEPRECATED
    dashscope_api_key: str = ""

    # ModelScope API (for LLM inference) - DEPRECATED
    modelscope_api_key: str = ""
    modelscope_model: str = "Qwen/Qwen2.5-Coder-32B-Instruct"

    # Upload and Temp directories
    upload_dir: str = "data/uploads"
    temp_dir: str = "data/temp"
    max_upload_size: int = 1073741824  # 1GB

    class Config:
        env_file = str(ENV_FILE)
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
