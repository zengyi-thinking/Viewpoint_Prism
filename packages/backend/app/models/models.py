from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Float, ForeignKey, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
from enum import Enum as PyEnum
import uuid as uuid_lib

from app.core.database import Base


class Project(Base):
    """工程模型 - 定义在 models.py 中以便其他模型引用"""
    __tablename__ = "projects"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid_lib.uuid4()))
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    owner_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships - 与 auth.models 中的 User 关联
    # 注意：这些 relationship 将在 SQLAlchemy 初始化时通过 backref 自动连接
    owner = relationship("User", back_populates="owned_projects", foreign_keys=[owner_id])
    members = relationship("ProjectMember", back_populates="project", cascade="all, delete-orphan", foreign_keys="ProjectMember.project_id")
    access_history = relationship("ProjectAccessHistory", back_populates="project", cascade="all, delete-orphan", foreign_keys="ProjectAccessHistory.project_id")
    sources = relationship("Source", back_populates="project", cascade="all, delete-orphan")


class SourceStatus(str, PyEnum):
    """Video source processing status."""
    IMPORTED = "imported"  # Imported but not yet analyzed (Phase 12: Lazy Analysis)
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    ANALYZING = "analyzing"
    DONE = "done"
    ERROR = "error"


class Source(Base):
    """Video source model for storing uploaded videos."""

    __tablename__ = "sources"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid_lib.uuid4()))
    title = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)
    url = Column(String(1024), nullable=True)  # Accessible URL for frontend
    file_type = Column(String(50), default="video")  # video, pdf, audio
    platform = Column(String(50), default="local")  # tiktok, bilibili, youtube, local
    duration = Column(Float, nullable=True)  # Duration in seconds
    thumbnail = Column(String(512), nullable=True)
    status = Column(String(20), default=SourceStatus.UPLOADED.value)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=True, index=True)  # 工程关联（向后兼容）
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    evidences = relationship("Evidence", back_populates="source", cascade="all, delete-orphan")
    project = relationship("Project", back_populates="sources")


class Evidence(Base):
    """Evidence model for storing transcript segments and keyframes."""

    __tablename__ = "evidences"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid_lib.uuid4()))
    source_id = Column(String(36), ForeignKey("sources.id"), nullable=False)
    start_time = Column(Float, nullable=False)  # Start time in seconds
    end_time = Column(Float, nullable=False)  # End time in seconds
    text_content = Column(Text, nullable=True)  # Transcript text
    frame_path = Column(String(512), nullable=True)  # Keyframe image path
    embedding_id = Column(String(128), nullable=True)  # Vector DB reference
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    source = relationship("Source", back_populates="evidences")

    @property
    def project_id(self):
        """通过 source 关联获取 project_id"""
        return self.source.project_id if self.source else None


class AnalysisResult(Base):
    """Analysis result model for storing AI analysis outputs."""

    __tablename__ = "analysis_results"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid_lib.uuid4()))
    session_id = Column(String(64), nullable=False, index=True)
    result_type = Column(String(50), nullable=False)  # conflict, graph, timeline
    data = Column(Text, nullable=False)  # JSON string
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=True, index=True)  # 工程关联
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    project = relationship("Project")


class ChatMessage(Base):
    """Chat message model for storing conversation history."""

    __tablename__ = "chat_messages"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid_lib.uuid4()))
    session_id = Column(String(64), nullable=False, index=True)
    role = Column(String(20), nullable=False)  # user, assistant
    content = Column(Text, nullable=False)
    references = Column(Text, nullable=True)  # JSON string of references
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=True, index=True)  # 工程关联
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    project = relationship("Project")


# ===== 实体和关系模型 =====

class Entity(Base):
    """实体模型 - 跨视频的实体库"""
    __tablename__ = "entities"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid_lib.uuid4()))
    name = Column(String(255), nullable=False, index=True)
    type = Column(String(50), nullable=False)  # PERSON, LOCATION, ORGANIZATION, etc.
    canonical_name = Column(String(255))  # 标准化名称(处理别名)
    description = Column(Text)
    embedding_id = Column(String(128))  # Qdrant向量ID
    mention_count = Column(Integer, default=1)
    first_seen_at = Column(DateTime, default=datetime.utcnow)
    last_seen_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    mentions = relationship("EntityMention", back_populates="entity", cascade="all, delete-orphan")
    source_relations = relationship("GraphRelation", foreign_keys="GraphRelation.source_entity_id")
    target_relations = relationship("GraphRelation", foreign_keys="GraphRelation.target_entity_id")


class EntityMention(Base):
    """实体提及 - 记录实体在视频中的出现"""
    __tablename__ = "entity_mentions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid_lib.uuid4()))
    entity_id = Column(String(36), ForeignKey("entities.id"), nullable=False)
    source_id = Column(String(36), ForeignKey("sources.id"), nullable=False)
    timestamp = Column(Float, nullable=False)  # 出现时间(秒)
    context = Column(Text)  # 上下文文本
    confidence = Column(Float, default=1.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    entity = relationship("Entity", back_populates="mentions")


class GraphRelation(Base):
    """关系模型 - 标准化的关系类型"""
    __tablename__ = "graph_relations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid_lib.uuid4()))
    source_entity_id = Column(String(36), ForeignKey("entities.id"), nullable=False)
    target_entity_id = Column(String(36), ForeignKey("entities.id"), nullable=False)
    relation_type = Column(String(100), nullable=False)  # is_friend_of, is_enemy_of, etc.
    confidence = Column(Float, default=1.0)
    source_id = Column(String(36), ForeignKey("sources.id"))  # 来源视频
    evidence = Column(Text)  # 关系依据
    created_at = Column(DateTime, default=datetime.utcnow)
