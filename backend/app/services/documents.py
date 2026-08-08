from __future__ import annotations

import hashlib
import uuid
from datetime import date, datetime, timezone

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.documents.storage import ObjectStorage
from app.documents.text import (
    ExtractionError,
    build_chunks,
    extract_pages,
    normalize_persian,
)
from app.documents.validation import ValidatedUpload
from app.models.auth import User
from app.models.documents import Document, DocumentProcessingJob, DocumentVersion
from app.repositories.auth import AuthRepository
from app.repositories.documents import DocumentRepository
from app.schemas.documents import (
    DocumentResponse,
    ProcessingJobResponse,
    VersionResponse,
)
from app.ai.providers import DisabledAIProvider, EmbeddingProvider


class DocumentServiceError(Exception):
    pass


class DocumentNotFoundError(DocumentServiceError):
    pass


class InvalidDocumentStateError(DocumentServiceError):
    pass


def document_response(document: Document) -> DocumentResponse:
    return DocumentResponse(
        id=document.id,
        title=document.title,
        document_type=document.document_type,
        issuing_authority=document.issuing_authority,
        source_url=document.source_url,
        topics=sorted(topic.topic for topic in document.topics),
        created_by=document.created_by,
        created_at=document.created_at,
        version_count=len(document.versions),
    )


def version_response(version: DocumentVersion) -> VersionResponse:
    return VersionResponse(
        id=version.id,
        document_id=version.document_id,
        version_number=version.version_number,
        original_filename=version.original_filename,
        mime_type=version.mime_type,
        file_size=version.file_size,
        file_hash=version.file_hash,
        status=version.status,
        lifecycle_status=version.lifecycle_status,
        review_status=version.review_status,
        valid_from=version.valid_from,
        valid_to=version.valid_to,
        chunk_count=len(version.chunks),
        error_code=version.error_code,
        created_at=version.created_at,
        processed_at=version.processed_at,
    )


def job_response(job: DocumentProcessingJob) -> ProcessingJobResponse:
    return ProcessingJobResponse(
        id=job.id,
        document_version_id=job.document_version_id,
        status=job.status,
        attempts=job.attempts,
        error_code=job.error_code,
        queued_at=job.queued_at,
        started_at=job.started_at,
        finished_at=job.finished_at,
    )


class DocumentService:
    def __init__(
        self,
        session: Session,
        settings: Settings,
        storage: ObjectStorage,
        embedding_provider: EmbeddingProvider | None = None,
    ) -> None:
        self.session = session
        self.settings = settings
        self.storage = storage
        self.repository = DocumentRepository(session)
        self.audit = AuthRepository(session)
        self.embedding_provider = embedding_provider or DisabledAIProvider()

    def create_document(
        self,
        *,
        title: str,
        document_type: str,
        issuing_authority: str,
        source_url: str | None,
        topics: list[str],
        user: User,
    ) -> Document:
        document = self.repository.create_document(
            title=title,
            document_type=document_type,
            issuing_authority=issuing_authority,
            source_url=source_url,
            topics=topics,
            created_by=user.id,
        )
        self.audit.add_audit(
            "document.created",
            "document",
            actor_user_id=user.id,
            resource_id=document.id,
        )
        self.session.commit()
        return document

    def list_documents(self, *, offset: int, limit: int) -> list[Document]:
        return self.repository.list_documents(offset=offset, limit=limit)

    def get_document(self, document_id: str) -> Document:
        document = self.repository.get_document(document_id)
        if document is None:
            raise DocumentNotFoundError
        return document

    def archive_document(self, document_id: str, user: User) -> None:
        document = self.get_document(document_id)
        self.repository.archive_document(document)
        self.audit.add_audit(
            "document.archived",
            "document",
            actor_user_id=user.id,
            resource_id=document.id,
        )
        self.session.commit()

    def upload_version(
        self,
        document_id: str,
        upload: ValidatedUpload,
        *,
        valid_from: date | None,
        valid_to: date | None,
        user: User,
    ) -> DocumentVersion:
        document = self.get_document(document_id)
        if valid_from and valid_to and valid_to < valid_from:
            raise InvalidDocumentStateError("Invalid validity date range")
        file_hash = hashlib.sha256(upload.data).hexdigest()
        storage_key = f"documents/{document.id}/{uuid.uuid4().hex}{upload.extension}"
        self.storage.put(storage_key, upload.data, upload.mime_type)
        try:
            version = self.repository.create_version(
                document,
                original_filename=upload.filename,
                storage_key=storage_key,
                mime_type=upload.mime_type,
                file_size=len(upload.data),
                file_hash=file_hash,
                valid_from=valid_from,
                valid_to=valid_to,
                created_by=user.id,
            )
            self.audit.add_audit(
                "document.version_uploaded",
                "document_version",
                actor_user_id=user.id,
                resource_id=version.id,
                metadata={"file_size": len(upload.data), "mime_type": upload.mime_type},
            )
            self.session.commit()
        except Exception:
            self.session.rollback()
            self.storage.delete(storage_key)
            raise
        return version

    def request_processing(self, version_id: str, user: User) -> DocumentProcessingJob:
        version = self.repository.get_version(version_id)
        if version is None:
            raise DocumentNotFoundError
        if version.status not in {"uploaded", "failed"}:
            raise InvalidDocumentStateError(
                "Version cannot be queued in its current state"
            )
        version.status = "queued"
        version.error_code = None
        job = self.repository.create_job(version)
        self.audit.add_audit(
            "document.processing_queued",
            "document_version",
            actor_user_id=user.id,
            resource_id=version.id,
            metadata={"job_id": job.id},
        )
        self.session.commit()
        return job

    def process_job(self, job_id: str) -> DocumentProcessingJob:
        job = self.repository.get_job(job_id)
        if job is None:
            raise DocumentNotFoundError
        if job.status not in {"queued", "failed"}:
            raise InvalidDocumentStateError(
                "Job cannot be processed in its current state"
            )
        now = datetime.now(timezone.utc)
        job.status = "running"
        job.attempts += 1
        job.started_at = now
        job.error_code = None
        version = job.version
        version.status = "extracting"
        version.error_code = None
        self.session.commit()

        try:
            data = self.storage.get(version.storage_key)
            extension = "." + version.original_filename.rsplit(".", 1)[-1].lower()
            pages = extract_pages(data, extension)
            full_text = normalize_persian("\n".join(page.text for page in pages))
            if len(full_text) < self.settings.minimum_extracted_chars and hasattr(self.embedding_provider, "extract_document_text"):
                extracted = self.embedding_provider.extract_document_text(data, version.mime_type)
                if extracted:
                    full_text = normalize_persian(extracted)
                    pages = type(pages)([type(pages[0])(1, full_text)]) if pages else []
            if len(full_text) < self.settings.minimum_extracted_chars:
                raise ExtractionError(
                    "insufficient_text",
                    "Document has too little extractable text and may require OCR",
                )
            version.extracted_text = full_text
            version.status = "extracted"
            self.session.commit()

            version.status = "chunking"
            self.session.commit()
            chunks = build_chunks(
                pages,
                max_chars=self.settings.chunk_max_chars,
                overlap_chars=self.settings.chunk_overlap_chars,
            )
            if not chunks:
                raise ExtractionError("no_chunks", "No usable chunks were generated")
            self.repository.replace_chunks(version.id, chunks)
            self.session.flush()
            stored_chunks = self.repository.get_version(version.id).chunks
            vectors = self.embedding_provider.embed_documents(
                [chunk.content for chunk in stored_chunks]
            )
            if vectors:
                for chunk, vector in zip(stored_chunks, vectors):
                    chunk.embedding_json = vector
                    chunk.embedding_model = self.embedding_provider.model_name
            version.status = "needs_review"
            version.review_status = "pending"
            version.processed_at = datetime.now(timezone.utc)
            job.status = "succeeded"
            job.finished_at = version.processed_at
            self.session.commit()
        except Exception as error:
            self.session.rollback()
            failed_job = self.repository.get_job(job_id)
            if failed_job is None:
                raise
            error_code = (
                error.code
                if isinstance(error, ExtractionError)
                else "processing_failed"
            )
            failed_job.status = "failed"
            failed_job.error_code = error_code
            failed_job.finished_at = datetime.now(timezone.utc)
            failed_job.version.status = "failed"
            failed_job.version.error_code = error_code
            self.session.commit()
        return self.repository.get_job(job_id) or job

    def mark_queue_failed(self, job_id: str) -> None:
        job = self.repository.get_job(job_id)
        if job is None:
            return
        now = datetime.now(timezone.utc)
        job.status = "failed"
        job.error_code = "broker_unavailable"
        job.finished_at = now
        job.version.status = "failed"
        job.version.error_code = "broker_unavailable"
        self.session.commit()

    def review_version(
        self, version_id: str, *, decision: str, note: str, user: User
    ) -> DocumentVersion:
        version = self.repository.get_version(version_id)
        if version is None:
            raise DocumentNotFoundError
        if version.status != "needs_review":
            raise InvalidDocumentStateError("Only processed versions can be reviewed")
        self.repository.add_review(version.id, user.id, decision, note)
        version.review_status = decision
        if decision == "approved":
            version.status = "ready"
            version.lifecycle_status = "active"
        self.audit.add_audit(
            "document.reviewed",
            "document_version",
            actor_user_id=user.id,
            resource_id=version.id,
            metadata={"decision": decision},
        )
        self.session.commit()
        return version
