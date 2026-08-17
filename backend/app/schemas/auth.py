from __future__ import annotations

import re
from datetime import datetime
from typing import Literal

from pydantic import AliasChoices, BaseModel, EmailStr, Field, field_validator


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=2, max_length=120)

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        if not any(char.islower() for char in value):
            raise ValueError("Password must include a lowercase letter")
        if not any(char.isupper() for char in value):
            raise ValueError("Password must include an uppercase letter")
        if not any(char.isdigit() for char in value):
            raise ValueError("Password must include a digit")
        return value

    @field_validator("full_name")
    @classmethod
    def normalize_full_name(cls, value: str) -> str:
        return " ".join(value.split())


class SignupStartRequest(BaseModel):
    first_name: str = Field(min_length=2, max_length=60)
    last_name: str = Field(min_length=2, max_length=60)
    phone: str = Field(pattern=r"^09\d{9}$")
    email: EmailStr | None = None
    referral_code: str = Field(default="", max_length=16)
    captcha_token: str = Field(default="", max_length=4096)

    @field_validator("first_name", "last_name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = (
            value.replace("ي", "ی")
            .replace("ك", "ک")
            .replace("\u200f", "")
            .strip()
        )
        normalized = " ".join(normalized.split())
        if not re.fullmatch(r"[\u0600-\u06FF\u200c -]+", normalized):
            raise ValueError("Name must contain Persian letters only")

        letters = re.sub(r"[\s\u200c-]", "", normalized)
        if len(letters) < 2 or len(set(letters)) == 1:
            raise ValueError("Please enter a real Persian name")

        blocked_names = {
            "تست",
            "کاربر",
            "ناشناس",
            "نام",
            "فیک",
            "الکی",
            "هیچکس",
        }
        if letters in blocked_names:
            raise ValueError("Please enter a real Persian name")
        return normalized

    @field_validator("phone")
    @classmethod
    def normalize_phone(cls, value: str) -> str:
        return value.strip()

    @field_validator("email", mode="before")
    @classmethod
    def empty_email_to_none(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        normalized = value.strip().lower()
        return normalized or None


class SignupStartResponse(BaseModel):
    message: str
    expires_in: int
    resend_after: int


class SignupVerifyRequest(BaseModel):
    phone: str = Field(pattern=r"^09\d{9}$")
    code: str = Field(pattern=r"^\d{6}$")


class SignupVerifyResponse(BaseModel):
    setup_token: str
    expires_in: int


class SignupCompleteRequest(BaseModel):
    setup_token: str = Field(min_length=40, max_length=256)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        if not any(char.islower() for char in value):
            raise ValueError("Password must include a lowercase letter")
        if not any(char.isupper() for char in value):
            raise ValueError("Password must include an uppercase letter")
        if not any(char.isdigit() for char in value):
            raise ValueError("Password must include a digit")
        return value


class PasswordResetStartRequest(BaseModel):
    identifier: str = Field(min_length=3, max_length=320)

    @field_validator("identifier")
    @classmethod
    def normalize_identifier(cls, value: str) -> str:
        normalized = value.strip()

        if normalized.startswith("09"):
            if not re.fullmatch(r"09\d{9}", normalized):
                raise ValueError("Invalid phone number")
            return normalized

        if not re.fullmatch(
            r"[^\s@]+@[^\s@]+\.[^\s@]+",
            normalized,
        ):
            raise ValueError("Invalid email or phone number")

        return normalized.lower()


class PasswordResetCompleteRequest(BaseModel):
    identifier: str = Field(min_length=3, max_length=320)
    code: str = Field(pattern=r"^\d{6}$")
    password: str = Field(min_length=8, max_length=128)

    @field_validator("identifier")
    @classmethod
    def normalize_identifier(cls, value: str) -> str:
        normalized = value.strip()

        if normalized.startswith("09"):
            if not re.fullmatch(r"09\d{9}", normalized):
                raise ValueError("Invalid phone number")
            return normalized

        if not re.fullmatch(
            r"[^\s@]+@[^\s@]+\.[^\s@]+",
            normalized,
        ):
            raise ValueError("Invalid email or phone number")

        return normalized.lower()

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        if not any(char.islower() for char in value):
            raise ValueError("Password must include a lowercase letter")
        if not any(char.isupper() for char in value):
            raise ValueError("Password must include an uppercase letter")
        if not any(char.isdigit() for char in value):
            raise ValueError("Password must include a digit")
        return value

class LoginRequest(BaseModel):
    identifier: str = Field(
        min_length=3,
        max_length=320,
        validation_alias=AliasChoices("identifier", "email"),
    )
    password: str = Field(min_length=1, max_length=128)
    otp_code: str = Field(
        default="",
        max_length=6,
        pattern=r"^$|^[0-9]{6}$",
    )
    captcha_token: str = Field(default="", max_length=4096)

    @field_validator("identifier")
    @classmethod
    def normalize_identifier(cls, value: str) -> str:
        normalized = value.strip()

        if not normalized:
            raise ValueError("Email or phone is required")

        if normalized.startswith("09"):
            if not re.fullmatch(r"09\d{9}", normalized):
                raise ValueError("Invalid phone number")
            return normalized

        if "@" not in normalized:
            raise ValueError("Invalid email or phone number")

        return normalized.lower()


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=40, max_length=256)


class LogoutRequest(RefreshRequest):
    pass


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class UserResponse(BaseModel):
    id: str
    email: str | None
    full_name: str
    account_tier: Literal["normal", "plus", "pro"]
    is_active: bool
    two_factor_enabled: bool
    roles: list[str]
    permissions: list[str]
    created_at: datetime


class UpdateProfileRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)

    @field_validator("full_name")
    @classmethod
    def normalize_full_name(cls, value: str) -> str:
        return " ".join(value.split())


class AdminUserUpdateRequest(BaseModel):
    account_tier: Literal["normal", "plus", "pro"] | None = None
    is_active: bool | None = None
    roles: list[
        Literal[
            "user",
            "admin",
            "tax_expert",
            "company_expert",
            "system_admin",
        ]
    ] | None = Field(
        default=None,
        min_length=1,
        max_length=7,
    )

    @field_validator("roles")
    @classmethod
    def unique_roles(
        cls,
        value: list[str] | None,
    ) -> list[str] | None:
        return sorted(set(value)) if value is not None else None
