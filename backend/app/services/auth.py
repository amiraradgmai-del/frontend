from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.security import SecurityManager
from app.models.auth import PasswordResetToken, RefreshToken, SecurityRiskEvent, User
from app.models.portal import UserProfile
from app.repositories.auth import AuthRepository
from app.schemas.auth import TokenResponse, UserResponse
from app.services.email import EmailDeliveryError, EmailSender
from app.services.sms import MelipayamakSender, SmsDeliveryError


class AuthServiceError(Exception):
    pass


class EmailAlreadyRegisteredError(AuthServiceError):
    pass


class PhoneAlreadyRegisteredError(AuthServiceError):
    pass


class InvalidCredentialsError(AuthServiceError):
    pass


class AccountLockedError(AuthServiceError):
    pass


class InvalidRefreshTokenError(AuthServiceError):
    pass


class InactiveUserError(AuthServiceError):
    pass


class TwoFactorRequiredError(AuthServiceError):
    pass


class VerificationRateLimitedError(AuthServiceError):
    def __init__(self, retry_after: int) -> None:
        self.retry_after = retry_after


class InvalidVerificationCodeError(AuthServiceError):
    pass


class InvalidSetupTokenError(AuthServiceError):
    pass


class UserNotFoundError(AuthServiceError):
    pass


class InvalidUserManagementError(AuthServiceError):
    pass


def as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def user_response(user: User) -> UserResponse:
    roles = sorted(role.name for role in user.roles)
    permissions = sorted(
        {permission.code for role in user.roles for permission in role.permissions}
    )
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        account_tier=user.account_tier,
        is_active=user.is_active,
        two_factor_enabled=user.two_factor_enabled,
        roles=roles,
        permissions=permissions,
        created_at=user.created_at,
    )


class AuthService:
    def __init__(
        self,
        session: Session,
        settings: Settings,
        security: SecurityManager,
        email_sender: EmailSender | None = None,
    ) -> None:
        self.session = session
        self.settings = settings
        self.security = security
        self.email_sender = email_sender or EmailSender(settings)
        self.sms_sender = MelipayamakSender(settings)
        self.repository = AuthRepository(session)

    def start_password_reset(
        self,
        identifier: str,
    ) -> None:
        normalized_identifier = identifier.strip()
        is_phone = normalized_identifier.startswith("09")

        if is_phone:
            user = self.repository.get_user_by_phone(
                normalized_identifier
            )
        else:
            normalized_identifier = normalized_identifier.lower()
            user = self.repository.get_user_by_email(
                normalized_identifier
            )

        if user is None or not user.is_active:
            return

        now = datetime.now(timezone.utc)

        self.session.query(PasswordResetToken).filter(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.used_at.is_(None),
        ).update({"used_at": now})

        code = f"{secrets.randbelow(1_000_000):06d}"

        token = PasswordResetToken(
            user_id=user.id,
            token_hash=self.security.hash_verification_code(
                normalized_identifier,
                code,
            ),
            expires_at=now + timedelta(minutes=10),
        )
        self.session.add(token)

        try:
            if is_phone:
                self.sms_sender.send_verification_code(
                    normalized_identifier,
                    code,
                )
            else:
                self.email_sender.send_password_reset_code(
                    normalized_identifier,
                    user.full_name,
                    code,
                )
        except (EmailDeliveryError, SmsDeliveryError):
            self.session.rollback()
            raise

        self.repository.add_audit(
            "auth.password_reset_code_sent",
            "user",
            actor_user_id=user.id,
            resource_id=user.id,
            metadata={
                "delivery_method": (
                    "sms" if is_phone else "email"
                )
            },
        )

        self.session.commit()

    def complete_password_reset(
        self,
        identifier: str,
        code: str,
        password: str,
    ) -> bool:
        normalized_identifier = identifier.strip()
        is_phone = normalized_identifier.startswith("09")

        if is_phone:
            user = self.repository.get_user_by_phone(
                normalized_identifier
            )
        else:
            normalized_identifier = normalized_identifier.lower()
            user = self.repository.get_user_by_email(
                normalized_identifier
            )

        if user is None or not user.is_active:
            return False

        now = datetime.now(timezone.utc)
        token_hash = self.security.hash_verification_code(
            normalized_identifier,
            code,
        )

        token = self.session.scalar(
            select(PasswordResetToken)
            .where(
                PasswordResetToken.user_id == user.id,
                PasswordResetToken.token_hash == token_hash,
                PasswordResetToken.used_at.is_(None),
                PasswordResetToken.expires_at >= now,
            )
            .with_for_update(of=PasswordResetToken)
        )

        if token is None:
            return False

        user.password_hash = self.security.hash_password(
            password
        )
        token.used_at = now

        self.repository.revoke_all_refresh_tokens(
            user.id,
            now,
        )

        self.repository.add_audit(
            "auth.password_reset",
            "user",
            actor_user_id=user.id,
            resource_id=user.id,
            metadata={
                "identifier_type": (
                    "phone" if is_phone else "email"
                )
            },
        )

        self.session.commit()
        return True
    def start_signup(
        self,
        phone: str,
        email: str | None,
        first_name: str,
        last_name: str,
        referral_code: str = "",
    ) -> tuple[int, int]:
        now = datetime.now(timezone.utc)
        normalized_phone = phone.strip()
        normalized_email = email.strip().lower() if email else None

        if self.repository.get_user_by_phone(normalized_phone) is not None:
            raise PhoneAlreadyRegisteredError

        if normalized_email and self.repository.get_user_by_email(normalized_email) is not None:
            raise EmailAlreadyRegisteredError

        existing = self.repository.get_pending_registration(
            normalized_phone,
            for_update=True,
        )
        if existing and as_utc(existing.resend_available_at) > now:
            retry_after = int(
                (as_utc(existing.resend_available_at) - now).total_seconds()
            ) + 1
            raise VerificationRateLimitedError(retry_after)

        code = f"{secrets.randbelow(1_000_000):06d}"
        expires_at = now + timedelta(
            minutes=self.settings.verification_code_minutes
        )
        resend_at = now + timedelta(
            seconds=self.settings.verification_resend_seconds
        )

        self.repository.save_pending_registration(
            phone=normalized_phone,
            email=normalized_email,
            first_name=first_name,
            last_name=last_name,
            referral_code=referral_code,
            code_hash=self.security.hash_verification_code(
                normalized_phone,
                code,
            ),
            code_expires_at=expires_at,
            resend_available_at=resend_at,
        )

        try:
            self.sms_sender.send_verification_code(normalized_phone, code)
        except SmsDeliveryError:
            self.session.rollback()
            raise

        self.repository.add_audit(
            "auth.phone_verification_sent",
            "pending_registration",
            resource_id=normalized_phone,
        )
        self.session.commit()

        return (
            self.settings.verification_code_minutes * 60,
            self.settings.verification_resend_seconds,
        )

    def verify_signup(
        self,
        phone: str,
        code: str,
    ) -> tuple[str, int]:
        now = datetime.now(timezone.utc)
        normalized_phone = phone.strip()

        pending = self.repository.get_pending_registration(
            normalized_phone,
            for_update=True,
        )

        valid = bool(
            pending
            and pending.failed_attempts < self.settings.verification_max_attempts
            and as_utc(pending.code_expires_at) > now
            and secrets.compare_digest(
                pending.code_hash,
                self.security.hash_verification_code(normalized_phone, code),
            )
        )

        if not valid:
            if pending:
                pending.failed_attempts += 1
                self.session.commit()
            raise InvalidVerificationCodeError

        setup_token = self.security.new_setup_token()
        pending.verified_at = now
        pending.setup_token_hash = self.security.hash_refresh_token(setup_token)
        pending.setup_token_expires_at = now + timedelta(
            minutes=self.settings.password_setup_minutes
        )

        self.repository.add_audit(
            "auth.phone_verified",
            "pending_registration",
            resource_id=pending.id,
        )
        self.session.commit()

        return setup_token, self.settings.password_setup_minutes * 60

    def complete_signup(
        self,
        setup_token: str,
        password: str,
    ) -> User:
        now = datetime.now(timezone.utc)
        pending = self.repository.get_pending_by_setup_token(
            self.security.hash_refresh_token(setup_token)
        )

        if (
            pending is None
            or pending.verified_at is None
            or pending.setup_token_expires_at is None
            or as_utc(pending.setup_token_expires_at) <= now
        ):
            raise InvalidSetupTokenError

        if self.repository.get_user_by_phone(pending.phone) is not None:
            raise PhoneAlreadyRegisteredError

        if pending.email and self.repository.get_user_by_email(pending.email) is not None:
            raise EmailAlreadyRegisteredError

        role = self.repository.get_role("user")
        if role is None:
            raise RuntimeError("Built-in RBAC roles have not been seeded")

        try:
            user = self.repository.create_user(
                pending.email,
                self.security.hash_password(password),
                f"{pending.first_name} {pending.last_name}",
                role,
            )
            user.email_verified_at = None

            referrer = None
            if pending.referral_code:
                referrer = self.session.scalar(
                    select(UserProfile).where(
                        UserProfile.referral_code == pending.referral_code
                    )
                )

            profile = UserProfile(
                user_id=user.id,
                phone=pending.phone,
                phone_verified=True,
                phone_verified_at=pending.verified_at,
                referral_code=user.id.replace("-", "")[:10].upper(),
                referred_by_user_id=referrer.user_id if referrer else None,
                reward_points=100 if referrer else 0,
            )
            self.session.add(profile)

            if referrer:
                referrer.reward_points += 250

            self.repository.delete_pending_registration(pending)
            self.repository.add_audit(
                "auth.register",
                "user",
                actor_user_id=user.id,
                resource_id=user.id,
                metadata={
                    "phone_verified": True,
                    "email_provided": bool(user.email),
                },
            )
            self.session.commit()

        except IntegrityError as error:
            self.session.rollback()
            if pending.email:
                raise EmailAlreadyRegisteredError from error
            raise PhoneAlreadyRegisteredError from error

        return user

    def register(
        self,
        email: str,
        password: str,
        full_name: str,
    ) -> User:
        normalized_email = email.strip().lower()
        if self.repository.get_user_by_email(normalized_email) is not None:
            raise EmailAlreadyRegisteredError

        role = self.repository.get_role("user")
        if role is None:
            raise RuntimeError("Built-in RBAC roles have not been seeded")

        try:
            user = self.repository.create_user(
                normalized_email,
                self.security.hash_password(password),
                full_name,
                role,
            )
            self.repository.add_audit(
                "auth.register",
                "user",
                actor_user_id=user.id,
                resource_id=user.id,
            )
            self.session.commit()
        except IntegrityError as error:
            self.session.rollback()
            raise EmailAlreadyRegisteredError from error

        return user

    def login(
        self,
        identifier: str,
        password: str,
        otp_code: str = "",
        *,
        device_name: str = "دستگاه ناشناس",
        user_agent: str = "",
        ip_address: str = "",
    ) -> TokenResponse:
        now = datetime.now(timezone.utc)
        normalized_identifier = identifier.strip()

        if normalized_identifier.startswith("09"):
            user = self.repository.get_user_by_phone(normalized_identifier)
        else:
            user = self.repository.get_user_by_email(
                normalized_identifier.lower()
            )

        if user is None:
            self.security.consume_dummy_password_check(password)
            raise InvalidCredentialsError

        if not user.is_active:
            raise InactiveUserError

        if user.locked_until and as_utc(user.locked_until) > now:
            raise AccountLockedError

        if not self.security.verify_password(password, user.password_hash):
            user.failed_login_count += 1
            self.repository.record_failed_login(user, "invalid_password")

            if user.failed_login_count >= self.settings.max_failed_logins:
                user.locked_until = now + timedelta(
                    minutes=self.settings.login_lock_minutes
                )

            self.repository.add_audit(
                "auth.login_failed",
                "user",
                actor_user_id=user.id,
                resource_id=user.id,
            )
            if user.failed_login_count >= 2:
                self.repository.add_risk_event(
                    "repeated_login_failure",
                    "high" if user.failed_login_count >= self.settings.max_failed_logins else "medium",
                    min(90, 25 + user.failed_login_count * 15),
                    user_id=user.id,
                    ip_address=ip_address,
                    device_name=device_name,
                    details={"failed_attempts": user.failed_login_count},
                )
            self.session.commit()

            if user.locked_until:
                raise AccountLockedError

            raise InvalidCredentialsError

        if user.two_factor_enabled and not self.security.verify_totp(
            user.id,
            otp_code,
        ):
            raise TwoFactorRequiredError

        user.failed_login_count = 0
        user.locked_until = None
        user.last_seen_at = now

        known_sessions = self.repository.active_sessions(user.id, now)
        known_ips = {item.ip_address for item in known_sessions if item.ip_address}
        known_devices = {item.device_name for item in known_sessions if item.device_name}
        if known_sessions and (
            (ip_address and ip_address not in known_ips)
            or (device_name and device_name not in known_devices)
        ):
            self.repository.add_risk_event(
                "new_login_context",
                "medium",
                45,
                user_id=user.id,
                ip_address=ip_address,
                device_name=device_name,
                details={
                    "new_ip": bool(ip_address and ip_address not in known_ips),
                    "new_device": bool(device_name and device_name not in known_devices),
                },
            )
        response, _ = self._issue_tokens(
            user, now, device_name=device_name, user_agent=user_agent, ip_address=ip_address
        )
        self.repository.add_audit(
            "auth.login_succeeded",
            "user",
            actor_user_id=user.id,
            resource_id=user.id,
        )
        self.session.commit()
        return response

    def refresh(self, raw_token: str) -> TokenResponse:
        now = datetime.now(timezone.utc)
        token_hash = self.security.hash_refresh_token(raw_token)
        stored = self.repository.get_refresh_token_for_update(token_hash)

        if stored is None:
            raise InvalidRefreshTokenError

        if stored.revoked_at is not None:
            self.repository.revoke_all_refresh_tokens(stored.user_id, now)
            self.repository.add_risk_event(
                "refresh_token_reuse",
                "critical",
                100,
                user_id=stored.user_id,
                ip_address=stored.ip_address,
                device_name=stored.device_name,
                details={"token_id": stored.id},
            )
            self.repository.add_audit(
                "auth.refresh_reuse_detected",
                "refresh_token",
                actor_user_id=stored.user_id,
                resource_id=stored.id,
            )
            self.session.commit()
            raise InvalidRefreshTokenError

        if as_utc(stored.expires_at) <= now or not stored.user.is_active:
            stored.revoked_at = now
            self.session.commit()
            raise InvalidRefreshTokenError

        response, replacement = self._issue_tokens(
            stored.user,
            now,
            device_name=stored.device_name,
            user_agent=stored.user_agent,
            ip_address=stored.ip_address,
        )
        stored.user.last_seen_at = now
        stored.revoked_at = now
        stored.replaced_by_id = replacement.id
        stored.last_used_at = now

        self.repository.add_audit(
            "auth.refresh_rotated",
            "refresh_token",
            actor_user_id=stored.user_id,
            resource_id=stored.id,
        )
        self.session.commit()
        return response

    def logout(self, raw_token: str) -> None:
        now = datetime.now(timezone.utc)
        stored = self.repository.get_refresh_token_for_update(
            self.security.hash_refresh_token(raw_token)
        )

        if stored and stored.revoked_at is None:
            stored.revoked_at = now
            self.repository.add_audit(
                "auth.logout",
                "refresh_token",
                actor_user_id=stored.user_id,
                resource_id=stored.id,
            )
            self.session.commit()

    def sessions(self, user: User) -> list[dict[str, object]]:
        now = datetime.now(timezone.utc)
        return [
            {
                "id": item.id,
                "device_name": item.device_name,
                "ip_address": item.ip_address,
                "created_at": item.created_at,
                "last_used_at": item.last_used_at or item.created_at,
                "expires_at": item.expires_at,
            }
            for item in self.repository.active_sessions(user.id, now)
        ]

    def security_events(self, user: User) -> list[dict[str, object]]:
        items = self.session.scalars(
            select(SecurityRiskEvent).where(SecurityRiskEvent.user_id == user.id)
            .order_by(SecurityRiskEvent.created_at.desc()).limit(50)
        )
        return [{
            "id": item.id,
            "category": item.category,
            "severity": item.severity,
            "risk_score": item.risk_score,
            "ip_address": item.ip_address,
            "device_name": item.device_name,
            "status": item.status,
            "created_at": item.created_at,
        } for item in items]

    def revoke_session(self, user: User, session_id: str) -> bool:
        now = datetime.now(timezone.utc)
        revoked = self.repository.revoke_session(user.id, session_id, now)
        if revoked:
            self.repository.add_audit(
                "auth.session_revoked", "refresh_token",
                actor_user_id=user.id, resource_id=session_id,
            )
            self.session.commit()
        return revoked

    def revoke_other_sessions(self, user: User, keep_session_id: str | None = None) -> int:
        now = datetime.now(timezone.utc)
        sessions = self.repository.active_sessions(user.id, now)
        revoked = 0
        for item in sessions:
            if keep_session_id and item.id == keep_session_id:
                continue
            item.revoked_at = now
            revoked += 1
        self.repository.add_audit(
            "auth.other_sessions_revoked", "user",
            actor_user_id=user.id, resource_id=user.id, metadata={"count": revoked},
        )
        self.session.commit()
        return revoked

    def update_profile(
        self,
        user: User,
        full_name: str,
    ) -> User:
        user.full_name = full_name
        self.repository.add_audit(
            "profile.updated",
            "user",
            actor_user_id=user.id,
            resource_id=user.id,
        )
        self.session.commit()
        return user

    def list_users(
        self,
        *,
        offset: int,
        limit: int,
    ) -> list[User]:
        return self.repository.list_users(offset=offset, limit=limit)

    def manage_user(
        self,
        target_id: str,
        actor: User,
        *,
        account_tier: str | None,
        is_active: bool | None,
        roles: list[str] | None,
    ) -> User:
        target = self.repository.get_user_by_id(target_id)
        if target is None:
            raise UserNotFoundError

        if target.id == actor.id and is_active is False:
            raise InvalidUserManagementError(
                "You cannot deactivate your own account"
            )

        protected_roles = {"system_admin", "admin"}
        if (
            target.id == actor.id
            and roles is not None
            and not protected_roles.intersection(roles)
        ):
            raise InvalidUserManagementError(
                "You cannot remove your own admin role"
            )

        if roles is not None:
            role_objects = self.repository.get_roles(roles)
            if len(role_objects) != len(roles):
                raise InvalidUserManagementError("Unknown role")
            target.roles = role_objects

        if account_tier is not None:
            target.account_tier = account_tier

        if is_active is not None:
            target.is_active = is_active
            if not is_active:
                self.repository.revoke_all_refresh_tokens(
                    target.id,
                    datetime.now(timezone.utc),
                )

        self.repository.add_audit(
            "user.managed",
            "user",
            actor_user_id=actor.id,
            resource_id=target.id,
            metadata={
                "account_tier": account_tier,
                "is_active": is_active,
                "roles": roles,
            },
        )
        self.session.commit()
        return self.repository.get_user_by_id(target.id) or target

    def _issue_tokens(
        self,
        user: User,
        now: datetime,
        *,
        device_name: str = "دستگاه ناشناس",
        user_agent: str = "",
        ip_address: str = "",
    ) -> tuple[TokenResponse, RefreshToken]:
        access_token, expires_in = self.security.create_access_token(user.id)
        raw_refresh_token = self.security.new_refresh_token()
        stored = self.repository.create_refresh_token(
            user.id,
            self.security.hash_refresh_token(raw_refresh_token),
            now + timedelta(days=self.settings.refresh_token_days),
            device_name=device_name[:160] or "دستگاه ناشناس",
            user_agent=user_agent[:500],
            ip_address=ip_address[:64],
            last_used_at=now,
        )
        return (
            TokenResponse(
                access_token=access_token,
                refresh_token=raw_refresh_token,
                expires_in=expires_in,
            ),
            stored,
        )
