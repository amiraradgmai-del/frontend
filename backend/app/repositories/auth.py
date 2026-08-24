from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select, text, update
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models.auth import (
    AuditLog,
    FailedLoginAttempt,
    PendingRegistration,
    Permission,
    RefreshToken,
    SecurityRiskEvent,
    Role,
    User,
)
from app.models.portal import UserProfile


ROLE_PERMISSIONS = {
    "user": {
        "profile:read", "profile:update", "financial_statements:view",
        "financial_statements:upload", "financial_statements:map",
        "financial_statements:adjust", "financial_statements:calculate",
        "financial_statements:finalize", "financial_statements:export",
    },
    "tax_expert": {
        "profile:read",
        "profile:update",
        "consultations:handle",
        "financial_statements:view", "financial_statements:upload",
        "financial_statements:map", "financial_statements:adjust",
        "financial_statements:calculate", "financial_statements:finalize",
        "financial_statements:export",
    },
    "company_expert": {
        "profile:read",
        "profile:update",
        "consultations:handle",
        "financial_statements:view", "financial_statements:upload",
        "financial_statements:map", "financial_statements:adjust",
        "financial_statements:calculate", "financial_statements:finalize",
        "financial_statements:export",
    },
    "content_manager": {
        "profile:read",
        "profile:update",
        "documents:manage",
        "documents:review",
        "feedback:read",
        "user_documents:manage",
    },
    "admin": {
        "profile:read",
        "profile:update",
        "consultations:manage",
        "tickets:manage",
        "user_documents:manage",
        "notifications:manage",
        "payments:manage",
        "site:manage",
        "financial_statements:view", "financial_statements:upload",
        "financial_statements:map", "financial_statements:adjust",
        "financial_statements:calculate", "financial_statements:finalize",
        "financial_statements:export", "financial_statements:manage_mapping",
    },
    "system_admin": {
        "profile:read",
        "profile:update",
        "documents:manage",
        "documents:review",
        "feedback:read",
        "consultations:manage",
        "users:manage",
        "audit:read",
        "payments:manage",
        "subscriptions:manage",
        "tickets:manage",
        "user_documents:manage",
        "chats:manage",
        "site:manage",
        "notifications:manage",
        "financial_statements:view", "financial_statements:upload",
        "financial_statements:map", "financial_statements:adjust",
        "financial_statements:calculate", "financial_statements:finalize",
        "financial_statements:export", "financial_statements:manage_mapping",
    },
    "support_admin": {
        "profile:read",
        "profile:update",
        "consultations:manage",
        "tickets:manage",
        "user_documents:manage",
    },
    "consultant": {
        "profile:read",
        "profile:update",
        "consultations:handle",
        "tickets:manage",
        "documents:review",
        "financial_statements:view", "financial_statements:upload",
        "financial_statements:map", "financial_statements:adjust",
        "financial_statements:calculate", "financial_statements:finalize",
        "financial_statements:export",
    },
}


def seed_rbac(session: Session) -> None:
    if (
        session.bind is not None
        and session.bind.dialect.name == "postgresql"
    ):
        # Identifiers cannot be bound as SQL parameters. Keep these statements
        # fully static instead of interpolating table names, even from a trusted
        # internal list, so dynamic SQL cannot accidentally spread from here.
        sequence_reset_statements = (
            text(
                "SELECT setval("
                "pg_get_serial_sequence('permissions', 'id'), "
                "COALESCE(MAX(id), 1), MAX(id) IS NOT NULL"
                ") FROM permissions"
            ),
            text(
                "SELECT setval("
                "pg_get_serial_sequence('roles', 'id'), "
                "COALESCE(MAX(id), 1), MAX(id) IS NOT NULL"
                ") FROM roles"
            ),
        )
        for statement in sequence_reset_statements:
            session.execute(statement)

    permission_objects: dict[str, Permission] = {}

    for code in sorted(
        set().union(*ROLE_PERMISSIONS.values())
    ):
        permission = session.scalar(
            select(Permission).where(
                Permission.code == code
            )
        )

        if permission is None:
            permission = Permission(
                code=code,
                description=code.replace(":", " "),
            )
            session.add(permission)

        permission_objects[code] = permission

    session.flush()

    for role_name, permission_codes in (
        ROLE_PERMISSIONS.items()
    ):
        role = session.scalar(
            select(Role).where(Role.name == role_name)
        )

        if role is None:
            role = Role(
                name=role_name,
                description=f"Built-in {role_name} role",
            )
            session.add(role)

        role.permissions = [
            permission_objects[code]
            for code in sorted(permission_codes)
        ]

    session.commit()


class AuthRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_user_by_email(
        self,
        email: str,
    ) -> User | None:
        statement = (
            select(User)
            .where(User.email == email)
            .options(
                selectinload(User.roles).selectinload(
                    Role.permissions
                )
            )
        )
        return self.session.scalar(statement)

    def get_user_by_phone(
        self,
        phone: str,
    ) -> User | None:
        statement = (
            select(User)
            .join(
                UserProfile,
                UserProfile.user_id == User.id,
            )
            .where(UserProfile.phone == phone)
            .options(
                selectinload(User.roles).selectinload(
                    Role.permissions
                )
            )
        )
        return self.session.scalar(statement)

    def get_user_by_id(
        self,
        user_id: str,
    ) -> User | None:
        statement = (
            select(User)
            .where(User.id == user_id)
            .options(
                selectinload(User.roles).selectinload(
                    Role.permissions
                )
            )
        )
        return self.session.scalar(statement)

    def list_users(
        self,
        *,
        offset: int,
        limit: int,
    ) -> list[User]:
        statement = (
            select(User)
            .options(
                selectinload(User.roles).selectinload(
                    Role.permissions
                )
            )
            .order_by(User.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(
            self.session.scalars(statement).unique()
        )

    def get_roles(
        self,
        names: list[str],
    ) -> list[Role]:
        return list(
            self.session.scalars(
                select(Role)
                .where(Role.name.in_(names))
                .options(
                    selectinload(
                        Role.permissions
                    )
                )
            ).unique()
        )

    def get_pending_registration(
        self,
        phone: str,
        *,
        for_update: bool = False,
    ) -> PendingRegistration | None:
        statement = select(
            PendingRegistration
        ).where(
            PendingRegistration.phone == phone
        )

        if for_update:
            statement = statement.with_for_update()

        return self.session.scalar(statement)

    def get_pending_by_setup_token(
        self,
        token_hash: str,
    ) -> PendingRegistration | None:
        return self.session.scalar(
            select(PendingRegistration)
            .where(
                PendingRegistration.setup_token_hash
                == token_hash
            )
            .with_for_update(
                of=PendingRegistration
            )
        )

    def save_pending_registration(
        self,
        *,
        phone: str,
        email: str | None,
        first_name: str,
        last_name: str,
        referral_code: str,
        code_hash: str,
        code_expires_at: datetime,
        resend_available_at: datetime,
    ) -> PendingRegistration:
        pending = self.get_pending_registration(
            phone,
            for_update=True,
        )

        if pending is None:
            pending = PendingRegistration(
                phone=phone,
                email=email,
            )
            self.session.add(pending)

        pending.phone = phone
        pending.email = email
        pending.first_name = first_name
        pending.last_name = last_name
        pending.referral_code = (
            referral_code.strip().upper()
        )
        pending.code_hash = code_hash
        pending.code_expires_at = (
            code_expires_at
        )
        pending.resend_available_at = (
            resend_available_at
        )
        pending.failed_attempts = 0
        pending.verified_at = None
        pending.setup_token_hash = None
        pending.setup_token_expires_at = None

        self.session.flush()
        return pending

    def delete_pending_registration(
        self,
        pending: PendingRegistration,
    ) -> None:
        self.session.delete(pending)

    def get_role(
        self,
        name: str,
    ) -> Role | None:
        return self.session.scalar(
            select(Role)
            .where(Role.name == name)
            .options(
                selectinload(Role.permissions)
            )
        )

    def create_user(
        self,
        email: str | None,
        password_hash: str,
        full_name: str,
        role: Role,
    ) -> User:
        user = User(
            email=email,
            password_hash=password_hash,
            full_name=full_name,
            roles=[role],
        )
        self.session.add(user)
        self.session.flush()
        return user

    def record_failed_login(
        self,
        user: User,
        reason: str,
    ) -> None:
        self.session.add(
            FailedLoginAttempt(
                user_id=user.id,
                reason=reason,
            )
        )

    def add_audit(
        self,
        action: str,
        resource_type: str,
        *,
        actor_user_id: str | None = None,
        resource_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.session.add(
            AuditLog(
                actor_user_id=actor_user_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                metadata_json=metadata or {},
            )
        )

    def create_refresh_token(
        self,
        user_id: str,
        token_hash: str,
        expires_at: datetime,
        *,
        device_name: str = "دستگاه ناشناس",
        user_agent: str = "",
        ip_address: str = "",
        last_used_at: datetime | None = None,
    ) -> RefreshToken:
        token = RefreshToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            device_name=device_name,
            user_agent=user_agent,
            ip_address=ip_address,
            last_used_at=last_used_at,
        )
        self.session.add(token)
        self.session.flush()
        return token

    def get_refresh_token_for_update(
        self,
        token_hash: str,
    ) -> RefreshToken | None:
        statement = (
            select(RefreshToken)
            .where(
                RefreshToken.token_hash
                == token_hash
            )
            .options(
                joinedload(
                    RefreshToken.user
                )
                .selectinload(User.roles)
                .selectinload(Role.permissions)
            )
            .with_for_update(of=RefreshToken)
        )
        return self.session.scalar(statement)

    def active_sessions(self, user_id: str, now: datetime) -> list[RefreshToken]:
        return list(self.session.scalars(
            select(RefreshToken).where(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked_at.is_(None),
                RefreshToken.expires_at > now,
            ).order_by(RefreshToken.last_used_at.desc(), RefreshToken.created_at.desc())
        ))

    def revoke_session(self, user_id: str, session_id: str, revoked_at: datetime) -> bool:
        token = self.session.scalar(select(RefreshToken).where(
            RefreshToken.id == session_id,
            RefreshToken.user_id == user_id,
            RefreshToken.revoked_at.is_(None),
        ))
        if token is None:
            return False
        token.revoked_at = revoked_at
        return True

    def revoke_all_refresh_tokens(
        self,
        user_id: str,
        revoked_at: datetime,
    ) -> None:
        self.session.execute(
            update(RefreshToken)
            .where(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked_at.is_(
                    None
                ),
            )
            .values(revoked_at=revoked_at)
        )

    def add_risk_event(
        self,
        category: str,
        severity: str,
        risk_score: int,
        *,
        user_id: str | None = None,
        ip_address: str = "",
        device_name: str = "",
        details: dict[str, Any] | None = None,
    ) -> SecurityRiskEvent:
        event = SecurityRiskEvent(
            user_id=user_id,
            category=category,
            severity=severity,
            risk_score=max(0, min(100, risk_score)),
            ip_address=ip_address[:64],
            device_name=device_name[:160],
            details_json=details or {},
        )
        self.session.add(event)
        return event
