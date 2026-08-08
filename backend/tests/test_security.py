import jwt
import pytest

from app.core.config import Settings
from app.core.security import SecurityManager, TokenValidationError


def settings() -> Settings:
    return Settings(
        environment="test",
        database_url="sqlite+pysqlite:///:memory:",
        jwt_secret="test-secret-that-is-at-least-32-characters-long",
    )


def test_access_token_contains_required_claims() -> None:
    manager = SecurityManager(settings())
    token, expires_in = manager.create_access_token("user-id")
    payload = manager.decode_access_token(token)
    assert payload["sub"] == "user-id"
    assert payload["type"] == "access"
    assert payload["jti"]
    assert expires_in == 900


def test_access_token_rejects_wrong_signature_and_wrong_type() -> None:
    manager = SecurityManager(settings())
    token, _ = manager.create_access_token("user-id")
    with pytest.raises(TokenValidationError):
        manager.decode_access_token(token + "broken")

    payload = jwt.decode(
        token,
        settings().jwt_secret,
        algorithms=[settings().jwt_algorithm],
        audience=settings().jwt_audience,
        issuer=settings().jwt_issuer,
    )
    payload["type"] = "refresh"
    wrong_type = jwt.encode(
        payload, settings().jwt_secret, algorithm=settings().jwt_algorithm
    )
    with pytest.raises(TokenValidationError):
        manager.decode_access_token(wrong_type)
