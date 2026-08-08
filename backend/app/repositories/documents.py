from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, selectinload

from app.documents.text import ChunkDraft
from app.models.documents import (
    Document,
    DocumentChunk,
    DocumentProcessingJob,
    DocumentReview,
    DocumentTopic,
    DocumentVersion,
)


class DocumentRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create_document(
        self,
        *,
        title: str,
        document_type: str,
        issuing_authority: str,
        source_url: str | None,
        topics: list[str],
        created_by: str,
    ) -> Document:
        document = Document(
            title=title,
            document_type=document_type,
            issuing_authority=issuing_authority,
            source_url=source_url,
            created_by=created_by,
            topics=[DocumentTopic(topic=topic) for topic in topics],
        )
        self.session.add(document)
        self.session.flush()
        return document

    def get_document(self, document_id: str) -> Document | None:
        return self.session.scalar(
            select(Document)
            .where(Document.id == document_id, Document.deleted_at.is_(None))
            .options(selectinload(Document.topics), selectinload(Document.versions))
        )

    def list_documents(self, *, offset: int, limit: int) -> list[Document]:
        return list(
            self.session.scalars(
                select(Document)
                .where(Document.deleted_at.is_(None))
                .options(selectinload(Document.topics), selectinload(Document.versions))
                .order_by(Document.created_at.desc())
                .offset(offset)
                .limit(limit)
            )
        )

    def archive_document(self, document: Document) -> None:
        document.deleted_at = datetime.now(timezone.utc)
        self.session.flush()

    def create_version(
        self,
        document: Document,
        *,
        original_filename: str,
        storage_key: str,
        mime_type: str,
        file_size: int,
        file_hash: str,
        valid_from: date | None,
        valid_to: date | None,
        created_by: str,
    ) -> DocumentVersion:
        self.session.execute(
            select(Document.id).where(Document.id == document.id).with_for_update()
        )
        latest = self.session.scalar(
            select(func.max(DocumentVersion.version_number)).where(
                DocumentVersion.document_id == document.id
            )
        )
        version = DocumentVersion(
            document_id=document.id,
            version_number=(latest or 0) + 1,
            original_filename=original_filename,
            storage_key=storage_key,
            mime_type=mime_type,
            file_size=file_size,
            file_hash=file_hash,
            valid_from=valid_from,
            valid_to=valid_to,
            created_by=created_by,
        )
        self.session.add(version)
        self.session.flush()
        return version

    def get_version(self, version_id: str) -> DocumentVersion | None:
        return self.session.scalar(
            select(DocumentVersion)
            .where(DocumentVersion.id == version_id)
            .options(
                selectinload(DocumentVersion.chunks),
                selectinload(DocumentVersion.jobs),
                selectinload(DocumentVersion.reviews),
            )
        )

    def create_job(self, version: DocumentVersion) -> DocumentProcessingJob:
        job = DocumentProcessingJob(document_version_id=version.id)
        self.session.add(job)
        self.session.flush()
        return job

    def get_job(self, job_id: str) -> DocumentProcessingJob | None:
        return self.session.scalar(
            select(DocumentProcessingJob)
            .where(DocumentProcessingJob.id == job_id)
            .options(selectinload(DocumentProcessingJob.version))
        )

    def replace_chunks(self, version_id: str, chunks: list[ChunkDraft]) -> None:
        self.session.execute(
            delete(DocumentChunk).where(DocumentChunk.document_version_id == version_id)
        )
        self.session.add_all(
            [
                DocumentChunk(
                    document_version_id=version_id,
                    chunk_index=chunk.chunk_index,
                    content=chunk.content,
                    content_hash=chunk.content_hash,
                    page_number=chunk.page_number,
                    article_number=chunk.article_number,
                    section_title=chunk.section_title,
                    char_count=chunk.char_count,
                    token_count=chunk.token_count,
                    metadata_json={"token_count_method": "whitespace_estimate"},
                )
                for chunk in chunks
            ]
        )

    def add_review(
        self, version_id: str, reviewer_user_id: str, decision: str, note: str
    ) -> DocumentReview:
        review = DocumentReview(
            document_version_id=version_id,
            reviewer_user_id=reviewer_user_id,
            decision=decision,
            note=note,
        )
        self.session.add(review)
        return review
