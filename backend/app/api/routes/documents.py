
from datetime import date
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from kombu.exceptions import OperationalError as BrokerOperationalError

from app.api.dependencies import get_document_service, require_permissions
from app.documents.validation import FileValidationError, validate_upload
from app.models.auth import User
from app.schemas.documents import (
    DocumentCreateRequest,
    DocumentResponse,
    ProcessingJobResponse,
    ReviewRequest,
    VersionResponse,
)
from app.services.documents import (
    DocumentNotFoundError,
    DocumentService,
    InvalidDocumentStateError,
    document_response,
    job_response,
    version_response,
)
from app.workers.tasks import process_document_job

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])


def translate_service_error(error: Exception) -> HTTPException:
    if isinstance(error, DocumentNotFoundError):
        return HTTPException(status_code=404, detail="Document or version not found")
    return HTTPException(status_code=409, detail=str(error) or "Invalid document state")


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
def create_document(
    payload: DocumentCreateRequest,
    user: Annotated[User, Depends(require_permissions("documents:manage"))],
    service: Annotated[DocumentService, Depends(get_document_service)],
) -> DocumentResponse:
    document = service.create_document(
        title=payload.title,
        document_type=payload.document_type,
        issuing_authority=payload.issuing_authority,
        source_url=str(payload.source_url) if payload.source_url else None,
        topics=payload.topics,
        user=user,
    )
    return document_response(document)


@router.get("", response_model=list[DocumentResponse])
def list_documents(
    user: Annotated[User, Depends(require_permissions("documents:manage"))],
    service: Annotated[DocumentService, Depends(get_document_service)],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[DocumentResponse]:
    del user
    return [
        document_response(item)
        for item in service.list_documents(offset=offset, limit=limit)
    ]


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(
    document_id: str,
    user: Annotated[User, Depends(require_permissions("documents:manage"))],
    service: Annotated[DocumentService, Depends(get_document_service)],
) -> DocumentResponse:
    del user
    try:
        return document_response(service.get_document(document_id))
    except (DocumentNotFoundError, InvalidDocumentStateError) as error:
        raise translate_service_error(error) from None


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def archive_document(
    document_id: str,
    user: Annotated[User, Depends(require_permissions("documents:manage"))],
    service: Annotated[DocumentService, Depends(get_document_service)],
) -> None:
    try:
        service.archive_document(document_id, user)
    except (DocumentNotFoundError, InvalidDocumentStateError) as error:
        raise translate_service_error(error) from None


@router.get("/{document_id}/versions", response_model=list[VersionResponse])
def list_versions(
    document_id: str,
    user: Annotated[User, Depends(require_permissions("documents:manage"))],
    service: Annotated[DocumentService, Depends(get_document_service)],
) -> list[VersionResponse]:
    del user
    try:
        document = service.get_document(document_id)
        return [version_response(item) for item in document.versions]
    except (DocumentNotFoundError, InvalidDocumentStateError) as error:
        raise translate_service_error(error) from None


@router.post(
    "/{document_id}/versions",
    response_model=VersionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_version(
    document_id: str,
    user: Annotated[User, Depends(require_permissions("documents:manage"))],
    service: Annotated[DocumentService, Depends(get_document_service)],
    file: Annotated[UploadFile, File()],
    valid_from: Annotated[date | None, Form()] = None,
    valid_to: Annotated[date | None, Form()] = None,
) -> VersionResponse:
    data = await file.read(service.settings.max_upload_bytes + 1)
    await file.close()
    try:
        validated = validate_upload(
            file.filename or "",
            file.content_type,
            data,
            service.settings.max_upload_bytes,
        )
        version = service.upload_version(
            document_id,
            validated,
            valid_from=valid_from,
            valid_to=valid_to,
            user=user,
        )
        return version_response(version)
    except FileValidationError as error:
        raise HTTPException(
            status_code=422, detail={"code": error.code, "message": str(error)}
        ) from None
    except (DocumentNotFoundError, InvalidDocumentStateError) as error:
        raise translate_service_error(error) from None


@router.post(
    "/versions/{version_id}/process",
    response_model=ProcessingJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def queue_processing(
    request: Request,
    version_id: str,
    user: Annotated[User, Depends(require_permissions("documents:manage"))],
    service: Annotated[DocumentService, Depends(get_document_service)],
) -> ProcessingJobResponse:
    try:
        job = service.request_processing(version_id, user)
        if request.app.state.settings.task_execution_mode == "inline":
            process_document_job(job.id)
        else:
            process_document_job.delay(job.id)
        return job_response(job)
    except BrokerOperationalError:
        service.mark_queue_failed(job.id)
        raise HTTPException(
            status_code=503, detail="Document worker is unavailable"
        ) from None
    except (DocumentNotFoundError, InvalidDocumentStateError) as error:
        raise translate_service_error(error) from None


@router.get("/versions/{version_id}/status", response_model=VersionResponse)
def version_status(
    version_id: str,
    user: Annotated[User, Depends(require_permissions("documents:manage"))],
    service: Annotated[DocumentService, Depends(get_document_service)],
) -> VersionResponse:
    del user
    version = service.repository.get_version(version_id)
    if version is None:
        raise HTTPException(status_code=404, detail="Document version not found")
    return version_response(version)


@router.post("/versions/{version_id}/review", response_model=VersionResponse)
def review_version(
    version_id: str,
    payload: ReviewRequest,
    user: Annotated[User, Depends(require_permissions("documents:review"))],
    service: Annotated[DocumentService, Depends(get_document_service)],
) -> VersionResponse:
    try:
        version = service.review_version(
            version_id, decision=payload.decision, note=payload.note, user=user
        )
        return version_response(version)
    except (DocumentNotFoundError, InvalidDocumentStateError) as error:
        raise translate_service_error(error) from None
