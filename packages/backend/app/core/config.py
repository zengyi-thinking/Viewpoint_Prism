"""Application configuration management."""
from pydantic_settings import BaseSettings
from typing import Optional
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    # API Keys
    dashscope_api_key: str = ""
    modelscope_api_key: str = ""

    # Database
    database_url: str = "sqlite+aiosqlite:///./data/viewpoint_prism.db"

    # File Storage
    upload_dir: str = "data/uploads"
    temp_dir: str = "data/temp"
    max_upload_size: int = 1073741824  # 1GB

    # ChromaDB
    chroma_db_dir: str = "data/chromadb"

    # AI Services
    asr_model: str = "paraformer-v2"
    vl_model: str = "qwen-vl-max"
    llm_model: str = "qwen2.5-72b-instruct"

    # Task Settings
    max_concurrent_frames: int = 10

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
