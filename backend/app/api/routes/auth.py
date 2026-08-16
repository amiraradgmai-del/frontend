from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from app.api.dependencies import get_auth_service, get_current_user
from app.models.auth import User
from app.schemas.auth import (
    LoginRequest,
    LogoutRequest,
    PasswordResetCompleteRequest,
    PasswordResetStartRequest,
    RefreshRequest,
    RegisterRequest,
    SignupCompleteRequest,
    SignupStartRequest,
    SignupStartResponse,
    SignupVerifyRequest,
    SignupVerifyResponse,
    TokenResponse,
    UserResponse,
)
from app.services.auth import (
    AccountLockedError,
    AuthService,
    EmailAlreadyRegisteredError,
    InactiveUserError,
    InvalidCredentialsError,
    InvalidRefreshTokenError,
    InvalidSetupTokenError,
    InvalidVerificationCodeError,
    PhoneAlreadyRegisteredError,
    TwoFactorRequiredError,
    VerificationRateLimitedError,
    user_response,
)
from app.services.captcha import CaptchaVerifier
from app.services.email import EmailDeliveryError
from app.services.site import feature_enabled
from app.services.sms import SmsDeliveryError


router = APIRouter(
    prefix="/auth",
    tags=["authentication"],
)


@router.get("/captcha/config")
def captcha_config(request: Request) -> dict[str, str | bool | None]:
    verifier = CaptchaVerifier(request.app.state.settings)
    return {
        "enabled": verifier.enabled,
        "site_key": request.app.state.settings.turnstile_site_key if verifier.enabled else None,
    }


@router.post(
    "/password-reset/start",
    status_code=status.HTTP_202_ACCEPTED,
)
def start_password_reset(
    payload: PasswordResetStartRequest,
    service: Annotated[
        AuthService,
        Depends(get_auth_service),
    ],
) -> dict[str, str]:
    try:
        service.start_password_reset(
            payload.identifier
        )
    except (
        EmailDeliveryError,
        SmsDeliveryError,
    ):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Password reset code could not be sent"
            ),
        ) from None

    return {
        "message": (
            "If the account exists, "
            "a reset code has been sent"
        )
    }


@router.post("/password-reset/complete")
def complete_password_reset(
    payload: PasswordResetCompleteRequest,
    service: Annotated[
        AuthService,
        Depends(get_auth_service),
    ],
) -> dict[str, bool]:
    if not service.complete_password_reset(
        payload.identifier,
        payload.code,
        payload.password,
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset code",
        )

    return {"ok": True}

@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(
    payload: RegisterRequest,
    service: Annotated[
        AuthService,
        Depends(get_auth_service),
    ],
) -> UserResponse:
    if service.settings.environment != "test":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Not found",
        )

    try:
        user = service.register(
            str(payload.email),
            payload.password,
            payload.full_name,
        )
    except EmailAlreadyRegisteredError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email is already registered",
        ) from None

    return user_response(user)


@router.post(
    "/signup/start",
    response_model=SignupStartResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def start_signup(
    request: Request,
    payload: SignupStartRequest,
    service: Annotated[
        AuthService,
        Depends(get_auth_service),
    ],
) -> SignupStartResponse:
    remote_ip = request.headers.get("x-forwarded-for", "").split(",")[0].strip() or (request.client.host if request.client else "")
    if not CaptchaVerifier(service.settings).verify(payload.captcha_token, remote_ip):
        raise HTTPException(status_code=422, detail="Captcha verification failed")
    if not feature_enabled(
        service.session,
        "registration_enabled",
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Registration is disabled",
        )

    try:
        expires_in, resend_after = service.start_signup(
            phone=payload.phone,
            email=(
                str(payload.email)
                if payload.email
                else None
            ),
            first_name=payload.first_name,
            last_name=payload.last_name,
            referral_code=payload.referral_code,
        )

    except PhoneAlreadyRegisteredError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Phone is already registered",
        ) from None

    except EmailAlreadyRegisteredError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email is already registered",
        ) from None

    except VerificationRateLimitedError as error:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                "Please wait before requesting "
                "another code"
            ),
            headers={
                "Retry-After": str(error.retry_after),
            },
        ) from None

    except SmsDeliveryError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Verification SMS could not be sent",
        ) from None

    return SignupStartResponse(
        message="Verification code sent",
        expires_in=expires_in,
        resend_after=resend_after,
    )


@router.post(
    "/signup/verify",
    response_model=SignupVerifyResponse,
)
def verify_signup(
    payload: SignupVerifyRequest,
    service: Annotated[
        AuthService,
        Depends(get_auth_service),
    ],
) -> SignupVerifyResponse:
    try:
        setup_token, expires_in = service.verify_signup(
            payload.phone,
            payload.code,
        )

    except InvalidVerificationCodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Invalid or expired verification code"
            ),
        ) from None

    return SignupVerifyResponse(
        setup_token=setup_token,
        expires_in=expires_in,
    )


@router.post(
    "/signup/complete",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def complete_signup(
    payload: SignupCompleteRequest,
    service: Annotated[
        AuthService,
        Depends(get_auth_service),
    ],
) -> UserResponse:
    try:
        user = service.complete_signup(
            payload.setup_token,
            payload.password,
        )

    except InvalidSetupTokenError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Invalid or expired password setup token"
            ),
        ) from None

    except PhoneAlreadyRegisteredError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Phone is already registered",
        ) from None

    except EmailAlreadyRegisteredError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email is already registered",
        ) from None

    return user_response(user)


@router.post(
    "/login",
    response_model=TokenResponse,
)
def login(
    request: Request,
    payload: LoginRequest,
    service: Annotated[
        AuthService,
        Depends(get_auth_service),
    ],
) -> TokenResponse:
    remote_ip = request.headers.get("x-forwarded-for", "").split(",")[0].strip() or (request.client.host if request.client else "")
    if not CaptchaVerifier(service.settings).verify(payload.captcha_token, remote_ip):
        raise HTTPException(status_code=422, detail="Captcha verification failed")
    try:
        return service.login(
            payload.identifier,
            payload.password,
            payload.otp_code,
            device_name=(request.headers.get("x-device-name") or request.headers.get("user-agent") or "دستگاه ناشناس")[:160],
            user_agent=request.headers.get("user-agent", ""),
            ip_address=remote_ip,
        )

    except TwoFactorRequiredError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Two-factor code required",
        ) from None

    except AccountLockedError:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Account is temporarily locked",
            headers={
                "Retry-After": str(
                    service.settings.login_lock_minutes
                    * 60
                ),
            },
        ) from None

    except (
        InvalidCredentialsError,
        InactiveUserError,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid phone, email, or password",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None


@router.post(
    "/refresh",
    response_model=TokenResponse,
)
def refresh(
    payload: RefreshRequest,
    service: Annotated[
        AuthService,
        Depends(get_auth_service),
    ],
) -> TokenResponse:
    try:
        return service.refresh(payload.refresh_token)

    except InvalidRefreshTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        ) from None


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
)
def logout(
    payload: LogoutRequest,
    service: Annotated[
        AuthService,
        Depends(get_auth_service),
    ],
) -> Response:
    service.logout(payload.refresh_token)

    return Response(
        status_code=status.HTTP_204_NO_CONTENT,
    )


@router.get("/sessions")
def sessions(
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[AuthService, Depends(get_auth_service)],
):
    return service.sessions(user)


@router.get("/security-events")
def security_events(
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[AuthService, Depends(get_auth_service)],
):
    return service.security_events(user)


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_session(
    session_id: str,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> Response:
    if not service.revoke_session(user, session_id):
        raise HTTPException(status_code=404, detail="نشست پیدا نشد.")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/sessions", status_code=status.HTTP_204_NO_CONTENT)
def revoke_all_sessions(
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> Response:
    service.revoke_other_sessions(user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
