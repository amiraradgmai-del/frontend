from app.core.config import Settings
from pydantic import ValidationError
import pytest


def test_production_disables_interactive_api_docs() -> None:
    settings = Settings(
        environment="production",
        docs_enabled=True,
        database_url="postgresql+psycopg://user:password@db/tax_ai",
        jwt_secret="test-secret-that-is-at-least-32-characters-long",
    )
    assert settings.docs_enabled is False


def test_test_environment_accepts_sqlite_url() -> None:
    settings = Settings(
        environment="test",
        database_url="sqlite+pysqlite:///:memory:",
        jwt_secret="test-secret-that-is-at-least-32-characters-long",
    )
    assert settings.database_url.startswith("sqlite")


def test_jwt_secret_must_be_at_least_32_characters() -> None:
    with pytest.raises(ValidationError):
        Settings(
            environment="test",
            database_url="sqlite+pysqlite:///:memory:",
            jwt_secret="too-short",
        )
