from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from kombu.exceptions import OperationalError as BrokerOperationalError
from sqlalchemy import select

from app.core.config import Settings
from app.db.base import Base
from app.main import create_app
from app.models.auth import Role, User
from app.models.documents import DocumentChunk, DocumentVersion
from app.repositories.auth import seed_rbac
from app.services.documents import DocumentService

TEST_PASSWORD = "SecurePassword123"


@pytest.fixture
def document_client(tmp_path):
    settings = Settings(
        environment="test",
        database_url=f"sqlite+pysqlite:///{(tmp_path / 'documents.db').as_posix()}",
        jwt_secret="test-secret-that-is-at-least-32-characters-long",
        local_storage_path=str(tmp_path / "storage"),
        minimum_extracted_chars=20,
        log_level="CRITICAL",
    )
    app = create_app(settings)
    with TestClient(app) as client:
        Base.metadata.create_all(app.state.database.engine)
        with app.state.database.session() as session:
            seed_rbac(session)
        yield app, client


def register_and_login(client: TestClient, app, *, manager: bool) -> dict[str, str]:
    email = "manager@example.com" if manager else "normal@example.com"
    response = client.post(
        "/auth/register",
        json={"email": email, "password": TEST_PASSWORD, "full_name": "کاربر اسناد"},
    )
    assert response.status_code == 201
    if manager:
        with app.state.database.session() as session:
            user = session.scalar(select(User).where(User.email == email))
            role = session.scalar(select(Role).where(Role.name == "content_manager"))
            assert user is not None and role is not None
            user.roles = [role]
            session.commit()
    token = client.post(
        "/auth/login", json={"email": email, "password": TEST_PASSWORD}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def create_document(client: TestClient, headers: dict[str, str]) -> dict:
    response = client.post(
        "/api/v1/documents",
        headers=headers,
        json={
            "title": "قانون آزمایشی مالیات",
            "document_type": "law",
            "issuing_authority": "مرجع آزمایشی",
            "source_url": "https://example.test/law",
            "topics": ["مالیات بر ارزش افزوده", "مهلت‌های مالیاتی"],
        },
    )
    assert response.status_code == 201
    return response.json()


def test_normal_user_cannot_manage_documents(document_client) -> None:
    app, client = document_client
    headers = register_and_login(client, app, manager=False)
    response = client.post(
        "/api/v1/documents",
        headers=headers,
        json={
            "title": "سند غیرمجاز",
            "document_type": "law",
            "issuing_authority": "مرجع",
        },
    )
    assert response.status_code == 403


def test_manager_can_archive_document_without_hard_delete(document_client) -> None:
    app, client = document_client
    headers = register_and_login(client, app, manager=True)
    document = create_document(client, headers)
    archived = client.delete(f"/api/v1/documents/{document['id']}", headers=headers)
    assert archived.status_code == 204
    assert client.get("/api/v1/documents", headers=headers).json() == []
    assert client.get(f"/api/v1/documents/{document['id']}", headers=headers).status_code == 404

    with app.state.database.session() as session:
        from app.models.documents import Document

        stored = session.get(Document, document["id"])
        assert stored is not None
        assert stored.deleted_at is not None


def test_document_upload_version_process_review_lifecycle(document_client) -> None:
    app, client = document_client
    headers = register_and_login(client, app, manager=True)
    document = create_document(client, headers)
    text = "ماده ۱- مؤدی باید تکالیف قانونی را انجام دهد. " + ("توضیح معتبر. " * 80)
    upload = client.post(
        f"/api/v1/documents/{document['id']}/versions",
        headers=headers,
        files={"file": ("law.txt", text.encode("utf-8"), "text/plain")},
        data={"valid_from": "2026-01-01"},
    )
    assert upload.status_code == 201, upload.text
    version = upload.json()
    assert version["version_number"] == 1
    assert version["status"] == "uploaded"
    listed_versions = client.get(
        f"/api/v1/documents/{document['id']}/versions", headers=headers
    )
    assert listed_versions.status_code == 200
    assert listed_versions.json()[0]["id"] == version["id"]

    with patch("app.api.routes.documents.process_document_job.delay") as delay:
        queued = client.post(
            f"/api/v1/documents/versions/{version['id']}/process", headers=headers
        )
    assert queued.status_code == 202, queued.text
    job_id = queued.json()["id"]
    delay.assert_called_once_with(job_id)

    with app.state.database.session() as session:
        job = DocumentService(
            session, app.state.settings, app.state.storage
        ).process_job(job_id)
        assert job.status == "succeeded"

    status_response = client.get(
        f"/api/v1/documents/versions/{version['id']}/status", headers=headers
    )
    assert status_response.status_code == 200
    assert status_response.json()["status"] == "needs_review"
    assert status_response.json()["chunk_count"] >= 1

    reviewed = client.post(
        f"/api/v1/documents/versions/{version['id']}/review",
        headers=headers,
        json={"decision": "approved", "note": "متن با منبع تطبیق داده شد"},
    )
    assert reviewed.status_code == 200
    assert reviewed.json()["status"] == "ready"
    assert reviewed.json()["review_status"] == "approved"

    with app.state.database.session() as session:
        chunks = list(session.scalars(select(DocumentChunk)))
        stored_version = session.scalar(select(DocumentVersion))
        assert chunks
        assert stored_version is not None
        assert stored_version.extracted_text
        assert all(chunk.content_hash for chunk in chunks)


def test_invalid_file_and_validity_range_are_rejected(document_client) -> None:
    app, client = document_client
    headers = register_and_login(client, app, manager=True)
    document = create_document(client, headers)
    fake_pdf = client.post(
        f"/api/v1/documents/{document['id']}/versions",
        headers=headers,
        files={"file": ("fake.pdf", b"not a pdf", "application/pdf")},
    )
    assert fake_pdf.status_code == 422
    assert fake_pdf.json()["detail"]["code"] == "invalid_pdf"

    invalid_dates = client.post(
        f"/api/v1/documents/{document['id']}/versions",
        headers=headers,
        files={"file": ("law.txt", "متن معتبر قانون".encode(), "text/plain")},
        data={"valid_from": "2026-12-01", "valid_to": "2026-01-01"},
    )
    assert invalid_dates.status_code == 409


def test_broker_failure_marks_job_and_version_failed_for_retry(document_client) -> None:
    app, client = document_client
    headers = register_and_login(client, app, manager=True)
    document = create_document(client, headers)
    upload = client.post(
        f"/api/v1/documents/{document['id']}/versions",
        headers=headers,
        files={
            "file": (
                "law.txt",
                "ماده ۱ متن معتبر برای پردازش".encode(),
                "text/plain",
            )
        },
    ).json()
    with patch(
        "app.api.routes.documents.process_document_job.delay",
        side_effect=BrokerOperationalError("redis unavailable"),
    ):
        response = client.post(
            f"/api/v1/documents/versions/{upload['id']}/process", headers=headers
        )
    assert response.status_code == 503
    version = client.get(
        f"/api/v1/documents/versions/{upload['id']}/status", headers=headers
    ).json()
    assert version["status"] == "failed"
    assert version["error_code"] == "broker_unavailable"
