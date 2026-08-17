from __future__ import annotations

import hashlib

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.config import Settings
from app.db.base import Base
from app.main import create_app
from app.models.auth import AuditLog, PendingRegistration, RefreshToken, Role, User
from app.models.portal import UserProfile
from app.repositories.auth import seed_rbac

TEST_PASSWORD = "SecurePassword123"
TEST_SECRET = "test-secret-that-is-at-least-32-characters-long"


@pytest.fixture
def app_client(tmp_path):
    database_path = tmp_path / "auth.db"
    settings = Settings(
        environment="test",
        database_url=f"sqlite+pysqlite:///{database_path.as_posix()}",
        jwt_secret=TEST_SECRET,
        max_failed_logins=3,
        login_lock_minutes=5,
        log_level="CRITICAL",
    )
    app = create_app(settings)
    with TestClient(app) as client:
        Base.metadata.create_all(app.state.database.engine)
        with app.state.database.session() as session:
            seed_rbac(session)
        yield app, client


def register(client: TestClient, email: str = "user@example.com"):
    return client.post(
        "/auth/register",
        json={"email": email, "password": TEST_PASSWORD, "full_name": "کاربر آزمایشی"},
    )


def login(
    client: TestClient, email: str = "user@example.com", password: str = TEST_PASSWORD
):
    return client.post("/auth/login", json={"email": email, "password": password})


def test_verified_signup_requires_phone_code_before_password(app_client, monkeypatch) -> None:
    app, client = app_client
    delivered: dict[str, str] = {}

    def capture_code(_sender, phone: str, code: str) -> None:
        delivered.update(phone=phone, code=code)

    monkeypatch.setattr(
        "app.services.sms.MelipayamakSender.send_verification_code", capture_code
    )
    started = client.post(
        "/auth/signup/start",
        json={"first_name": "علی", "last_name": "محمدی", "phone": "09123456789", "email": "New@Example.com"},
    )
    assert started.status_code == 202
    assert delivered["phone"] == "09123456789"
    assert len(delivered["code"]) == 6

    with app.state.database.session() as session:
        assert session.scalar(select(User)) is None
        assert session.scalar(select(PendingRegistration)) is not None

    invalid = client.post(
        "/auth/signup/verify", json={"phone": "09123456789", "code": "000000"}
    )
    assert invalid.status_code == 400
    verified = client.post(
        "/auth/signup/verify",
        json={"phone": "09123456789", "code": delivered["code"]},
    )
    assert verified.status_code == 200

    completed = client.post(
        "/auth/signup/complete",
        json={"setup_token": verified.json()["setup_token"], "password": TEST_PASSWORD},
    )
    assert completed.status_code == 201
    assert completed.json()["full_name"] == "علی محمدی"
    assert login(client, "new@example.com").status_code == 200

    with app.state.database.session() as session:
        user = session.scalar(select(User).where(User.email == "new@example.com"))
        assert user is not None
        assert user.email_verified_at is None
        profile = session.get(UserProfile, user.id)
        assert profile is not None and profile.phone_verified is True
        assert session.scalar(select(PendingRegistration)) is None


def test_signup_resend_is_rate_limited(app_client, monkeypatch) -> None:
    _, client = app_client
    monkeypatch.setattr(
        "app.services.sms.MelipayamakSender.send_verification_code",
        lambda *_args: None,
    )
    payload = {"first_name": "علی", "last_name": "محمدی", "phone": "09123456780", "email": "rate@example.com"}
    assert client.post("/auth/signup/start", json=payload).status_code == 202
    repeated = client.post("/auth/signup/start", json=payload)
    assert repeated.status_code == 429
    assert int(repeated.headers["Retry-After"]) > 0


def test_admin_can_manage_users_but_not_remove_own_access(app_client) -> None:
    app, client = app_client
    assert register(client, "admin-manage@example.com").status_code == 201
    assert register(client, "managed@example.com").status_code == 201
    with app.state.database.session() as session:
        admin = session.scalar(select(User).where(User.email == "admin-manage@example.com"))
        admin_role = session.scalar(select(Role).where(Role.name == "system_admin"))
        assert admin is not None and admin_role is not None
        admin.roles = [admin_role]
        session.commit()
        admin_id = admin.id

    token = login(client, "admin-manage@example.com").json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    users = client.get("/users", headers=headers)
    assert users.status_code == 200
    target = next(item for item in users.json() if item["email"] == "managed@example.com")

    updated = client.patch(
        f"/users/{target['id']}",
        headers=headers,
        json={"account_tier": "pro", "is_active": False, "roles": ["tax_expert"]},
    )
    assert updated.status_code == 200
    assert updated.json()["account_tier"] == "pro"
    assert updated.json()["roles"] == ["tax_expert"]
    assert updated.json()["is_active"] is False
    assert login(client, "managed@example.com").status_code == 401

    restored = client.patch(
        f"/users/{target['id']}",
        headers=headers,
        json={"account_tier": "normal", "is_active": True, "roles": ["user"]},
    )
    assert restored.status_code == 200
    assert restored.json()["account_tier"] == "normal"
    assert restored.json()["roles"] == ["user"]
    assert restored.json()["is_active"] is True

    self_change = client.patch(
        f"/users/{admin_id}", headers=headers, json={"roles": ["user"]}
    )
    assert self_change.status_code == 409


def test_admin_user_list_tolerates_legacy_local_email(app_client) -> None:
    app, client = app_client
    assert register(client, "list-admin@example.com").status_code == 201
    with app.state.database.session() as session:
        admin = session.scalar(select(User).where(User.email == "list-admin@example.com"))
        admin_role = session.scalar(select(Role).where(Role.name == "system_admin"))
        user_role = session.scalar(select(Role).where(Role.name == "user"))
        assert admin is not None and admin_role is not None and user_role is not None
        admin.roles = [admin_role]
        session.add(
            User(
                email="legacy@tax-ai.local",
                password_hash="unused",
                full_name="Legacy User",
                roles=[user_role],
            )
        )
        session.commit()
    token = login(client, "list-admin@example.com").json()["access_token"]
    response = client.get("/users", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert "legacy@tax-ai.local" in {item["email"] for item in response.json()}


def test_register_hashes_password_and_assigns_minimal_role(app_client) -> None:
    app, client = app_client
    response = register(client, "User@Example.com")
    assert response.status_code == 201
    assert response.json()["email"] == "user@example.com"
    assert response.json()["roles"] == ["user"]
    assert response.json()["account_tier"] == "normal"
    assert response.json()["permissions"] == ["profile:read", "profile:update"]

    with app.state.database.session() as session:
        user = session.scalar(select(User))
        assert user is not None
        assert user.password_hash != TEST_PASSWORD
        assert user.password_hash.startswith("$argon2")


def test_duplicate_email_and_weak_password_are_rejected(app_client) -> None:
    _, client = app_client
    assert register(client).status_code == 201
    assert register(client, "USER@example.com").status_code == 409
    weak = client.post(
        "/auth/register",
        json={
            "email": "weak@example.com",
            "password": "short",
            "full_name": "Weak User",
        },
    )
    assert weak.status_code == 422


def test_eight_character_strong_password_is_accepted(app_client) -> None:
    _, client = app_client
    response = client.post(
        "/auth/register",
        json={
            "email": "eight@example.com",
            "password": "Valid123",
            "full_name": "کاربر هشت کاراکتری",
        },
    )
    assert response.status_code == 201


def test_account_tier_supports_normal_plus_and_pro_only(app_client) -> None:
    app, client = app_client
    register(client)
    access_token = login(client).json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    with app.state.database.session() as session:
        user = session.scalar(select(User))
        assert user is not None
        user.account_tier = "plus"
        session.commit()
    assert client.get("/users/me", headers=headers).json()["account_tier"] == "plus"

    with app.state.database.session() as session:
        user = session.scalar(select(User))
        assert user is not None
        user.account_tier = "pro"
        session.commit()
    assert client.get("/users/me", headers=headers).json()["account_tier"] == "pro"

    with app.state.database.session() as session:
        user = session.scalar(select(User))
        assert user is not None
        user.account_tier = "invalid"
        with pytest.raises(IntegrityError):
            session.commit()


def test_login_access_token_profile_and_update(app_client) -> None:
    _, client = app_client
    register(client)
    token_response = login(client)
    assert token_response.status_code == 200
    tokens = token_response.json()
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    me = client.get("/users/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["email"] == "user@example.com"

    updated = client.patch("/users/me", headers=headers, json={"full_name": "نام جدید"})
    assert updated.status_code == 200
    assert updated.json()["full_name"] == "نام جدید"


def test_refresh_token_is_hashed_rotated_and_reuse_revokes_session(app_client) -> None:
    app, client = app_client
    register(client)
    first = login(client).json()
    raw_first = first["refresh_token"]

    with app.state.database.session() as session:
        stored = session.scalar(select(RefreshToken))
        assert stored is not None
        assert stored.token_hash == hashlib.sha256(raw_first.encode()).hexdigest()
        assert raw_first not in stored.token_hash

    rotated = client.post("/auth/refresh", json={"refresh_token": raw_first})
    assert rotated.status_code == 200
    raw_second = rotated.json()["refresh_token"]
    assert raw_second != raw_first

    reuse = client.post("/auth/refresh", json={"refresh_token": raw_first})
    assert reuse.status_code == 401
    assert (
        client.post("/auth/refresh", json={"refresh_token": raw_second}).status_code
        == 401
    )


def test_logout_revokes_refresh_token_without_revealing_unknown_tokens(
    app_client,
) -> None:
    _, client = app_client
    register(client)
    raw_token = login(client).json()["refresh_token"]
    assert (
        client.post("/auth/logout", json={"refresh_token": raw_token}).status_code
        == 204
    )
    assert (
        client.post("/auth/refresh", json={"refresh_token": raw_token}).status_code
        == 401
    )
    unknown = "x" * 64
    assert (
        client.post("/auth/logout", json={"refresh_token": unknown}).status_code == 204
    )


def test_user_can_list_and_revoke_device_sessions(app_client) -> None:
    _, client = app_client
    assert register(client).status_code == 201
    first = client.post(
        "/auth/login",
        headers={"user-agent": "Firefox Test", "x-device-name": "Windows Firefox", "x-forwarded-for": "203.0.113.7"},
        json={"email": "user@example.com", "password": TEST_PASSWORD},
    ).json()
    second = client.post(
        "/auth/login",
        headers={"user-agent": "Mobile Test", "x-device-name": "Android Chrome", "x-forwarded-for": "203.0.113.8"},
        json={"email": "user@example.com", "password": TEST_PASSWORD},
    ).json()
    headers = {"Authorization": f"Bearer {second['access_token']}"}

    sessions = client.get("/auth/sessions", headers=headers)
    assert sessions.status_code == 200
    assert {item["device_name"] for item in sessions.json()} == {"Windows Firefox", "Android Chrome"}
    assert {item["ip_address"] for item in sessions.json()} == {"203.0.113.7", "203.0.113.8"}
    risk_events = client.get("/auth/security-events", headers=headers)
    assert risk_events.status_code == 200
    assert "new_login_context" in {item["category"] for item in risk_events.json()}

    first_session = next(item for item in sessions.json() if item["device_name"] == "Windows Firefox")
    assert client.delete(f"/auth/sessions/{first_session['id']}", headers=headers).status_code == 204
    second_rotated = client.post("/auth/refresh", json={"refresh_token": second["refresh_token"]})
    assert second_rotated.status_code == 200
    assert client.post("/auth/refresh", json={"refresh_token": first["refresh_token"]}).status_code == 401
    # Reuse of any explicitly revoked token is treated as theft and revokes
    # every remaining session for the account.
    assert client.post("/auth/refresh", json={"refresh_token": second_rotated.json()["refresh_token"]}).status_code == 401
    risk_events = client.get("/auth/security-events", headers=headers).json()
    assert "refresh_token_reuse" in {item["category"] for item in risk_events}


def test_captcha_is_required_when_turnstile_is_configured(app_client) -> None:
    app, client = app_client
    app.state.settings.captcha_enabled = True
    app.state.settings.turnstile_site_key = "site-key"
    app.state.settings.turnstile_secret_key = "secret-key"

    config = client.get("/auth/captcha/config")
    assert config.status_code == 200
    assert config.json() == {"enabled": True, "site_key": "site-key"}

    assert register(client).status_code == 201
    denied = client.post(
        "/auth/login",
        json={"email": "user@example.com", "password": TEST_PASSWORD},
    )
    assert denied.status_code == 422
    assert denied.json()["detail"] == "Captcha verification failed"


def test_failed_logins_temporarily_lock_account(app_client) -> None:
    _, client = app_client
    register(client)
    assert login(client, password="WrongPassword123").status_code == 401
    assert login(client, password="WrongPassword123").status_code == 401
    third = login(client, password="WrongPassword123")
    assert third.status_code == 429
    assert login(client).status_code == 429


def test_invalid_access_token_is_rejected_and_audit_has_no_credentials(
    app_client,
) -> None:
    app, client = app_client
    register(client)
    assert (
        client.get("/users/me", headers={"Authorization": "Bearer invalid"}).status_code
        == 401
    )
    login(client)

    with app.state.database.session() as session:
        audit_logs = list(session.scalars(select(AuditLog)))
        assert {item.action for item in audit_logs} >= {
            "auth.register",
            "auth.login_succeeded",
        }
        serialized = " ".join(str(item.metadata_json) for item in audit_logs)
        assert TEST_PASSWORD not in serialized
        assert "user@example.com" not in serialized


def test_rbac_is_checked_on_profile_endpoint(app_client) -> None:
    app, client = app_client
    register(client)
    token = login(client).json()["access_token"]
    with app.state.database.session() as session:
        user = session.scalar(select(User))
        assert user is not None
        user.roles.clear()
        session.commit()
    response = client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403
