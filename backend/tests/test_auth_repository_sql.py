from sqlalchemy import select
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import joinedload, selectinload

from app.models.auth import PendingRegistration, RefreshToken, Role, User


def test_pending_registration_lock_targets_pending_table() -> None:
    statement = (
        select(PendingRegistration)
        .where(PendingRegistration.setup_token_hash == "token")
        .with_for_update(of=PendingRegistration)
    )

    sql = str(statement.compile(dialect=postgresql.dialect()))

    assert "FOR UPDATE OF pending_registrations" in sql


def test_refresh_lock_does_not_lock_joined_user_table() -> None:
    statement = (
        select(RefreshToken)
        .where(RefreshToken.token_hash == "token")
        .options(
            joinedload(RefreshToken.user)
            .selectinload(User.roles)
            .selectinload(Role.permissions)
        )
        .with_for_update(of=RefreshToken)
    )

    sql = str(statement.compile(dialect=postgresql.dialect()))

    assert "FOR UPDATE OF refresh_tokens" in sql
