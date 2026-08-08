from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl, field_validator

DocumentStatus = Literal[
    "uploaded",
    "queued",
    "extracting",
    "extracted",
    "chunking",
    "embedding",
    "needs_review",
    "ready",
    "failed",
]


class DocumentCreateRequest(BaseModel):
    title: str = Field(min_length=3, max_length=300)
    document_type: str = Field(min_length=2, max_length=50)
    issuing_authority: str = Field(min_length=2, max_length=200)
    source_url: HttpUrl | None = None
    topics: list[str] = Field(default_factory=list, max_length=10)

    @field_validator("title", "document_type", "issuing_authority")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        return " ".join(value.split())

    @field_validator("topics")
    @classmethod
    def normalize_topics(cls, value: list[str]) -> list[str]:
        topics = sorted({" ".join(item.split()) for item in value if item.strip()})
        if any(len(item) > 100 for item in topics):
            raise ValueError("Each topic must be at most 100 characters")
        return topics


class DocumentResponse(BaseModel):
    id: str
    title: str
    document_type: str
    issuing_authority: str
    source_url: str | None
    topics: list[str]
    created_by: str
    created_at: datetime
    version_count: int


class VersionResponse(BaseModel):
    id: str
    document_id: str
    version_number: int
    original_filename: str
    mime_type: str
    file_size: int
    file_hash: str
    status: DocumentStatus
    lifecycle_status: str
    review_status: str
    valid_from: date | None
    valid_to: date | None
    chunk_count: int
    error_code: str | None
    created_at: datetime
    processed_at: datetime | None


class ProcessingJobResponse(BaseModel):
    id: str
    document_version_id: str
    status: Literal["queued", "running", "succeeded", "failed"]
    attempts: int
    error_code: str | None
    queued_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


class ReviewRequest(BaseModel):
    decision: Literal["approved", "rejected"]
    note: str = Field(default="", max_length=1000)
