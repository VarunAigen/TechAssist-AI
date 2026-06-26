"""SQLAlchemy ORM models for the multi-tenant RAG Knowledge Assistant.

All tables include a tenant_id column for data isolation between companies.
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Text, Float, Boolean, DateTime,
    ForeignKey, JSON, BigInteger, UniqueConstraint, Index,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


class Tenant(Base):
    """Company/organization — the top-level isolation unit."""

    __tablename__ = "tenants"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    plan = Column(String(50), nullable=False, default="free")  # free | pro | enterprise
    max_documents = Column(Integer, default=20)
    max_users = Column(Integer, default=5)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    users = relationship("User", back_populates="tenant", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="tenant", cascade="all, delete-orphan")
    chat_sessions = relationship("ChatSession", back_populates="tenant", cascade="all, delete-orphan")
    queries = relationship("Query", back_populates="tenant", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="tenant", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Tenant {self.slug} ({self.plan})>"


class User(Base):
    """User account — belongs to a single tenant."""

    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("tenant_id", "email", name="uq_user_tenant_email"),
        Index("ix_user_email", "email"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    email = Column(String(255), nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default="bd_rep")  # super_admin | tenant_admin | bd_rep
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    last_login = Column(DateTime, nullable=True)

    # Relationships
    tenant = relationship("Tenant", back_populates="users")
    chat_sessions = relationship("ChatSession", back_populates="user", cascade="all, delete-orphan")
    queries = relationship("Query", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user")

    def __repr__(self):
        return f"<User {self.email} ({self.role})>"


class Document(Base):
    """Ingested document — belongs to a tenant's knowledge base."""

    __tablename__ = "documents"
    __table_args__ = (
        Index("ix_document_tenant", "tenant_id"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    filename = Column(String(500), nullable=False)
    original_name = Column(String(500), nullable=False)
    file_type = Column(String(20), nullable=False)
    file_size = Column(Integer, default=0)
    chunk_count = Column(Integer, default=0)
    version = Column(Integer, default=1)
    uploaded_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    tenant = relationship("Tenant", back_populates="documents")
    uploader = relationship("User", foreign_keys=[uploaded_by])

    def __repr__(self):
        return f"<Document {self.filename} (tenant={self.tenant_id})>"


class ChatSession(Base):
    """Chat conversation session — groups related queries."""

    __tablename__ = "chat_sessions"
    __table_args__ = (
        Index("ix_session_tenant_user", "tenant_id", "user_id"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), default="New Chat")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    tenant = relationship("Tenant", back_populates="chat_sessions")
    user = relationship("User", back_populates="chat_sessions")
    queries = relationship("Query", back_populates="session", cascade="all, delete-orphan",
                           order_by="Query.created_at")

    def __repr__(self):
        return f"<ChatSession {self.id}: {self.title}>"


class Query(Base):
    """Single question/answer pair within a chat session."""

    __tablename__ = "queries"
    __table_args__ = (
        Index("ix_query_tenant", "tenant_id"),
        Index("ix_query_session", "session_id"),
        Index("ix_query_user", "user_id"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    session_id = Column(Integer, ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=True)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    confidence_tier = Column(String(10), nullable=False)  # HIGH | MEDIUM | LOW
    confidence_score = Column(Float, nullable=False)
    sources = Column(JSON, nullable=True)  # Stored as JSON (not eval'd string)
    is_bridge_response = Column(Boolean, default=False)
    rating = Column(Integer, default=0)  # 1 = thumbs up, -1 = thumbs down, 0 = unrated
    response_time_ms = Column(Float, nullable=True)
    is_resolved = Column(Boolean, default=False, nullable=False)
    resolved_answer = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    tenant = relationship("Tenant", back_populates="queries")
    user = relationship("User", back_populates="queries")
    session = relationship("ChatSession", back_populates="queries")

    def __repr__(self):
        return f"<Query {self.id}: {self.question[:50]}>"


class AuditLog(Base):
    """Audit trail — tracks all user actions for compliance."""

    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_tenant", "tenant_id"),
        Index("ix_audit_tenant_created", "tenant_id", "created_at"),
        Index("ix_audit_user", "user_id"),
    )

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action = Column(String(50), nullable=False)  # login | query | upload | delete | rate | export
    resource_type = Column(String(50), nullable=True)  # document | query | user | session
    resource_id = Column(Integer, nullable=True)
    details = Column(JSON, nullable=True)
    ip_address = Column(String(45), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    tenant = relationship("Tenant", back_populates="audit_logs")
    user = relationship("User", back_populates="audit_logs")

    def __repr__(self):
        return f"<AuditLog {self.action} by user={self.user_id}>"
