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
    database_url: str = f"sqlite+aiosqlite:///{(PROJECT_ROOT / 'data' / 'viewpoint_prism.db').as_posix()}"

    # ChromaDB
    chroma_db_dir: str = "data/chromadb"

    # ========== SophNet AI Services ==========
    # Primary AI service provider - supports LLM, VLM, TTS, Image, Embedding
    sophnet_api_key: str = ""
    sophnet_project_id: str = ""
    sophnet_tts_easyllm_id: str = ""
    sophnet_embedding_easyllm_id: str = ""

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

    def resolve_path(self, path_value: str) -> Path:
        """Resolve a path against the project root."""
        path = Path(path_value)
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        return path

    class Config:
        env_file = str(ENV_FILE)
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
