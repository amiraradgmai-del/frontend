from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.security import SecurityManager
from app.db.session import Database
from app.repositories.auth import AuthRepository, seed_rbac


def bootstrap_admin(session: Session, settings: Settings) -> bool:
    if not settings.bootstrap_admin_email or not settings.bootstrap_admin_password:
        return False
    seed_rbac(session)
    repository = AuthRepository(session)
    email = settings.bootstrap_admin_email.strip().lower()
    user = repository.get_user_by_email(email)
    admin_role = repository.get_role("system_admin")
    if admin_role is None:
        raise RuntimeError("System administrator role was not seeded")
    if user is None:
        user = repository.create_user(
            email,
            SecurityManager(settings).hash_password(settings.bootstrap_admin_password),
            settings.bootstrap_admin_full_name,
            admin_role,
        )
        action = "admin.bootstrapped"
    else:
        if admin_role not in user.roles:
            user.roles.append(admin_role)
        action = "admin.bootstrap_verified"
    repository.add_audit(
        action,
        "user",
        actor_user_id=user.id,
        resource_id=user.id,
    )
    session.commit()
    return True


def main() -> None:
    settings = get_settings()
    database = Database(
        settings.database_url,
        connect_timeout_seconds=settings.readiness_timeout_seconds,
    )
    try:
        with database.session() as session:
            created = bootstrap_admin(session, settings)
            print("Admin bootstrap complete" if created else "Admin bootstrap skipped")
    finally:
        database.dispose()


if __name__ == "__main__":
    main()
