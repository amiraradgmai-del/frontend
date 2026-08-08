from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.dependencies import get_auth_service, require_permissions
from app.models.auth import User
from app.schemas.auth import AdminUserUpdateRequest, UpdateProfileRequest, UserResponse
from app.services.auth import (
    AuthService,
    InvalidUserManagementError,
    UserNotFoundError,
    user_response,
)

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserResponse)
def me(
    user: Annotated[User, Depends(require_permissions("profile:read"))],
) -> UserResponse:
    return user_response(user)


@router.patch("/me", response_model=UserResponse)
def update_me(
    payload: UpdateProfileRequest,
    user: Annotated[User, Depends(require_permissions("profile:update"))],
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> UserResponse:
    return user_response(service.update_profile(user, payload.full_name))


@router.get("", response_model=list[UserResponse])
def list_users(
    user: Annotated[User, Depends(require_permissions("users:manage"))],
    service: Annotated[AuthService, Depends(get_auth_service)],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[UserResponse]:
    del user
    return [user_response(item) for item in service.list_users(offset=offset, limit=limit)]


@router.patch("/{user_id}", response_model=UserResponse)
def manage_user(
    user_id: str,
    payload: AdminUserUpdateRequest,
    actor: Annotated[User, Depends(require_permissions("users:manage"))],
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> UserResponse:
    try:
        return user_response(
            service.manage_user(
                user_id,
                actor,
                account_tier=payload.account_tier,
                is_active=payload.is_active,
                roles=payload.roles,
            )
        )
    except UserNotFoundError:
        raise HTTPException(status_code=404, detail="User not found") from None
    except InvalidUserManagementError as error:
        raise HTTPException(status_code=409, detail=str(error)) from None
