
from collections.abc import Generator
from dataclasses import replace
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import SecurityManager, TokenValidationError
from app.models.auth import User
from app.repositories.auth import AuthRepository
from app.services.auth import AuthService
from app.services.documents import DocumentService
from app.services.advisor import AdvisorService
from app.services.consultations import ConsultationService
from app.services.site import get_ai_policy
from app.ai.providers import GeminiProvider

bearer_scheme = HTTPBearer(auto_error=False)


def get_session(request: Request) -> Generator[Session, None, None]:
    with request.app.state.database.session() as session:
        yield session


def get_security(request: Request) -> SecurityManager:
    return request.app.state.security


def get_auth_service(
    request: Request,
    session: Annotated[Session, Depends(get_session)],
    security: Annotated[SecurityManager, Depends(get_security)],
) -> AuthService:
    return AuthService(session, request.app.state.settings, security)


def get_document_service(
    request: Request,
    session: Annotated[Session, Depends(get_session)],
) -> DocumentService:
    return DocumentService(
        session,
        request.app.state.settings,
        request.app.state.storage,
        request.app.state.ai_provider,
    )


def get_advisor_service(
    request: Request,
    session: Annotated[Session, Depends(get_session)],
) -> AdvisorService:
    provider = request.app.state.ai_provider
    if isinstance(provider, GeminiProvider):
        provider = replace(
            provider,
            generation_model=get_ai_policy(session).generation_model,
        )
    return AdvisorService(session, provider)


def get_consultation_service(
    session: Annotated[Session, Depends(get_session)],
) -> ConsultationService:
    return ConsultationService(session)


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    session: Annotated[Session, Depends(get_session)],
    security: Annotated[SecurityManager, Depends(get_security)],
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired access token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise unauthorized
    try:
        payload = security.decode_access_token(credentials.credentials)
    except TokenValidationError:
        raise unauthorized from None
    user = AuthRepository(session).get_user_by_id(str(payload["sub"]))
    if user is None or not user.is_active:
        raise unauthorized
    return user


def permission_codes(user: User) -> set[str]:
    return {permission.code for role in user.roles for permission in role.permissions}


def is_system_admin(user: User) -> bool:
    return any(role.name == "system_admin" for role in user.roles)


def require_permissions(*required: str):
    def check(user: Annotated[User, Depends(get_current_user)]) -> User:
        if is_system_admin(user):
            return user
        if not set(required).issubset(permission_codes(user)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return user

    return check
