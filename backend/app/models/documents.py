from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

PROCESSING_STATUSES = (
    "uploaded",
    "queued",
    "extracting",
    "extracted",
    "chunking",
    "embedding",
    "needs_review",
    "ready",
    "failed",
)
REVIEW_STATUSES = ("pending", "approved", "rejected")
LIFECYCLE_STATUSES = ("draft", "active", "amended", "repealed", "archived")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def new_uuid() -> str:
    return str(uuid.uuid4())


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    title: Mapped[str] = mapped_column(String(300), index=True)
    document_type: Mapped[str] = mapped_column(String(50), index=True)
    issuing_authority: Mapped[str] = mapped_column(String(200))
    source_url: Mapped[str | None] = mapped_column(String(1000))
    created_by: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    versions: Mapped[list[DocumentVersion]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="DocumentVersion.version_number",
    )
    topics: Mapped[list[DocumentTopic]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )


class DocumentVersion(Base):
    __tablename__ = "document_versions"
    __table_args__ = (
        UniqueConstraint(
            "document_id", "version_number", name="uq_document_version_number"
        ),
        CheckConstraint(
            "status IN ('uploaded','queued','extracting','extracted','chunking','embedding','needs_review','ready','failed')",
            name="ck_document_versions_status",
        ),
        CheckConstraint(
            "review_status IN ('pending','approved','rejected')",
            name="ck_document_versions_review_status",
        ),
        CheckConstraint(
            "lifecycle_status IN ('draft','active','amended','repealed','archived')",
            name="ck_document_versions_lifecycle_status",
        ),
        CheckConstraint(
            "valid_to IS NULL OR valid_from IS NULL OR valid_to >= valid_from",
            name="ck_document_versions_validity_range",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    version_number: Mapped[int] = mapped_column(Integer)
    original_filename: Mapped[str] = mapped_column(String(255))
    storage_key: Mapped[str] = mapped_column(String(500), unique=True)
    mime_type: Mapped[str] = mapped_column(String(100))
    file_size: Mapped[int] = mapped_column(Integer)
    file_hash: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(
        String(32), default="uploaded", server_default="uploaded"
    )
    extracted_text: Mapped[str | None] = mapped_column(Text)
    valid_from: Mapped[date | None] = mapped_column(Date)
    valid_to: Mapped[date | None] = mapped_column(Date)
    lifecycle_status: Mapped[str] = mapped_column(
        String(20), default="draft", server_default="draft"
    )
    review_status: Mapped[str] = mapped_column(
        String(20), default="pending", server_default="pending"
    )
    error_code: Mapped[str | None] = mapped_column(String(64))
    created_by: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="RESTRICT")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    document: Mapped[Document] = relationship(back_populates="versions")
    chunks: Mapped[list[DocumentChunk]] = relationship(
        back_populates="version",
        cascade="all, delete-orphan",
        order_by="DocumentChunk.chunk_index",
    )
    jobs: Mapped[list[DocumentProcessingJob]] = relationship(
        back_populates="version", cascade="all, delete-orphan"
    )
    reviews: Mapped[list[DocumentReview]] = relationship(
        back_populates="version", cascade="all, delete-orphan"
    )


class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    __table_args__ = (
        UniqueConstraint(
            "document_version_id", "chunk_index", name="uq_version_chunk_index"
        ),
        Index("ix_chunks_article_number", "article_number"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    document_version_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("document_versions.id", ondelete="CASCADE"), index=True
    )
    chunk_index: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(String(64), index=True)
    page_number: Mapped[int | None] = mapped_column(Integer)
    article_number: Mapped[str | None] = mapped_column(String(50))
    section_title: Mapped[str | None] = mapped_column(String(300))
    char_count: Mapped[int] = mapped_column(Integer)
    token_count: Mapped[int] = mapped_column(Integer)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    embedding_json: Mapped[list[float] | None] = mapped_column(JSON)
    embedding_model: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )

    version: Mapped[DocumentVersion] = relationship(back_populates="chunks")


class DocumentTopic(Base):
    __tablename__ = "document_topics"

    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id", ondelete="CASCADE"), primary_key=True
    )
    topic: Mapped[str] = mapped_column(String(100), primary_key=True)

    document: Mapped[Document] = relationship(back_populates="topics")


class DocumentRelation(Base):
    __tablename__ = "document_relations"
    __table_args__ = (
        UniqueConstraint(
            "source_version_id",
            "target_version_id",
            "relation_type",
            name="uq_document_relation",
        ),
        CheckConstraint(
            "relation_type IN ('amends','repeals','supersedes','related')",
            name="ck_document_relations_type",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    source_version_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("document_versions.id", ondelete="CASCADE"), index=True
    )
    target_version_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("document_versions.id", ondelete="CASCADE"), index=True
    )
    relation_type: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )


class DocumentProcessingJob(Base):
    __tablename__ = "document_processing_jobs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('queued','running','succeeded','failed')",
            name="ck_document_jobs_status",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    document_version_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("document_versions.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(
        String(20), default="queued", server_default="queued"
    )
    attempts: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    error_code: Mapped[str | None] = mapped_column(String(64))
    queued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    version: Mapped[DocumentVersion] = relationship(back_populates="jobs")


class DocumentReview(Base):
    __tablename__ = "document_reviews"
    __table_args__ = (
        CheckConstraint(
            "decision IN ('approved','rejected')", name="ck_document_reviews_decision"
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    document_version_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("document_versions.id", ondelete="CASCADE"), index=True
    )
    reviewer_user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    decision: Mapped[str] = mapped_column(String(20))
    note: Mapped[str] = mapped_column(String(1000), default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )

    version: Mapped[DocumentVersion] = relationship(back_populates="reviews")
