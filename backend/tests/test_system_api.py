from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import Settings
from app.main import create_app


def build_test_app():
    return create_app(
        Settings(
            environment="test",
            database_url="sqlite+pysqlite:///:memory:",
            log_level="CRITICAL",
            jwt_secret="test-secret-that-is-at-least-32-characters-long",
        )
    )


def test_health_check_does_not_depend_on_database() -> None:
    with TestClient(build_test_app()) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["X-Request-ID"]


def test_readiness_checks_database_connection() -> None:
    with TestClient(build_test_app()) as client:
        response = client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready", "database": "up"}


def test_readiness_returns_503_when_database_is_down() -> None:
    app = build_test_app()
    with TestClient(app) as client:

        def fail_ping() -> None:
            raise SQLAlchemyError("database unavailable")

        app.state.database.ping = fail_ping
        response = client.get("/ready")
    assert response.status_code == 503
    assert response.json() == {"status": "not_ready", "database": "down"}


def test_status_exposes_only_public_service_metadata() -> None:
    with TestClient(build_test_app()) as client:
        response = client.get("/api/v1/status")
    assert response.status_code == 200
    assert response.json() == {
        "service": "Tax AI Advisor API",
        "version": "0.1.0",
        "environment": "test",
        "status": "operational",
    }
    assert "database" not in response.text.lower()


def test_invalid_request_id_is_replaced() -> None:
    with TestClient(build_test_app()) as client:
        response = client.get(
            "/health", headers={"X-Request-ID": "invalid id with spaces"}
        )
    assert response.headers["X-Request-ID"] != "invalid id with spaces"


def test_security_headers_are_set() -> None:
    with TestClient(build_test_app()) as client:
        response = client.get("/health")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert response.headers["Content-Security-Policy"] == (
        "default-src 'none'; frame-ancestors 'none'; base-uri 'none'"
    )
