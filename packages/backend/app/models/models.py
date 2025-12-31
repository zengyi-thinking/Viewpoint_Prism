"""SQLAlchemy database models."""
import uuid
from datetime import datetime
from sqlalchemy import String, Float, DateTime, Text, JSON, Integer
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Enum as SQLEnum
import enum
from app.core.database import Base


class SourceStatus(str, enum.Enum):
    """Source processing status."""
    UPLOADED = "uploaded"
    IMPORTED = "imported"       # Phase 12: Lazy Analysis
    PROCESSING = "processing"
    ANALYZING = "analyzing"
    DONE = "done"
    ERROR = "error"


class Source(Base):
    """Video source model."""
    __tablename__ = "sources"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title: Mapped[str] = mapped_column(String, index=True)
    file_path: Mapped[str] = mapped_column(String, unique=True)
    url: Mapped[str] = mapped_column(String, default="")
    file_type: Mapped[str] = mapped_column(String, default="video")
    platform: Mapped[str] = mapped_column(String, default="local")
    duration: Mapped[float | None] = mapped_column(Float, nullable=True)
    thumbnail: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(SQLEnum(SourceStatus), default=SourceStatus.UPLOADED)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Evidence(Base):
    """Evidence chunk (ASR/frame)."""
    __tablename__ = "evidences"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    source_id: Mapped[str] = mapped_column(String, index=True)
    chunk_type: Mapped[str] = mapped_column(String)  # 'asr' or 'frame'
    timestamp: Mapped[float] = mapped_column(Float)
    content: Mapped[str] = mapped_column(Text)
    metadata: Mapped[dict] = mapped_column(JSON, default={})


class AnalysisResult(Base):
    """Cached analysis results."""
    __tablename__ = "analysis_results"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    source_ids: Mapped[list] = mapped_column(JSON)
    conflicts: Mapped[dict] = mapped_column(JSON, default={})
    graph: Mapped[dict] = mapped_column(JSON, default={"nodes": [], "links": []})
    timeline: Mapped[list] = mapped_column(JSON, default=[])
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ChatMessage(Base):
    """Chat message history."""
    __tablename__ = "chat_messages"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id: Mapped[str] = mapped_column(String, index=True)
    role: Mapped[str] = mapped_column(String)  # 'user' or 'assistant'
    content: Mapped[str] = mapped_column(Text)
    references: Mapped[list] = mapped_column(JSON, default=[])
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
