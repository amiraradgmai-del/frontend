from app.core.config import get_settings
from app.db.session import Database
from app.documents.storage import create_storage
from app.services.documents import DocumentService
from app.workers.celery_app import celery_app
from app.ai.providers import create_ai_provider
from app.services.legal_monitor import check_all_sources


@celery_app.task(name="documents.process_version")
def process_document_job(job_id: str) -> dict[str, str]:
    settings = get_settings()
    database = Database(
        settings.database_url,
        connect_timeout_seconds=settings.readiness_timeout_seconds,
    )
    try:
        with database.session() as session:
            job = DocumentService(
                session,
                settings,
                create_storage(settings),
                create_ai_provider(settings),
            ).process_job(job_id)
            return {"job_id": job.id, "status": job.status}
    finally:
        database.dispose()


@celery_app.task(name="legal_sources.check_all")
def check_legal_sources_job() -> dict[str, object]:
    settings = get_settings()
    database = Database(
        settings.database_url,
        connect_timeout_seconds=settings.readiness_timeout_seconds,
    )
    try:
        with database.session() as session:
            results = check_all_sources(session)
            return {
                "checked": len(results),
                "changes": sum(bool(item.get("changed")) for item in results),
                "failed": sum(item.get("status") == "failed" for item in results),
            }
    finally:
        database.dispose()
