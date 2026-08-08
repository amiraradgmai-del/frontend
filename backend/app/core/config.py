from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="TAX_AI_",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Tax AI Advisor API"
    app_version: str = "0.1.0"

    environment: Literal[
        "development",
        "test",
        "staging",
        "production",
    ] = "development"

    log_level: Literal[
        "DEBUG",
        "INFO",
        "WARNING",
        "ERROR",
        "CRITICAL",
    ] = "INFO"

    docs_enabled: bool = True

    database_url: str

    readiness_timeout_seconds: float = Field(
        default=2.0,
        ge=0.1,
        le=10.0,
    )

    jwt_secret: str = Field(min_length=32)

    jwt_algorithm: Literal[
        "HS256",
        "HS384",
        "HS512",
    ] = "HS256"

    jwt_issuer: str = "tax-ai-advisor"
    jwt_audience: str = "tax-ai-advisor-api"

    access_token_minutes: int = Field(
        default=15,
        ge=1,
        le=60,
    )

    refresh_token_days: int = Field(
        default=30,
        ge=1,
        le=90,
    )

    max_failed_logins: int = Field(
        default=5,
        ge=3,
        le=20,
    )

    login_lock_minutes: int = Field(
        default=15,
        ge=1,
        le=1440,
    )

    verification_code_minutes: int = Field(
        default=10,
        ge=2,
        le=30,
    )

    verification_resend_seconds: int = Field(
        default=60,
        ge=30,
        le=600,
    )

    verification_max_attempts: int = Field(
        default=5,
        ge=3,
        le=10,
    )

    password_setup_minutes: int = Field(
        default=20,
        ge=5,
        le=60,
    )

    wallet_daily_withdrawal_limit: int = Field(
        default=15_000_000,
        ge=100_000,
        le=1_000_000_000,
    )

    public_site_url: str = "http://localhost:3000"

    payment_provider: Literal[
        "sandbox",
        "zarinpal",
    ] = "sandbox"

    zarinpal_merchant_id: str | None = None

    zarinpal_callback_url: str = (
        "http://localhost:8000/"
        "api/v1/portal/payments/zarinpal/callback"
    )

    zarinpal_api_base_url: str = (
        "https://payment.zarinpal.com/pg/v4/payment"
    )

    zarinpal_start_pay_url: str = (
        "https://payment.zarinpal.com/pg/StartPay"
    )

    zarinpal_timeout_seconds: float = Field(
        default=15.0,
        ge=2.0,
        le=60.0,
    )

    # تنظیمات ایمیل
    email_delivery_mode: Literal[
        "console",
        "smtp",
    ] = "console"

    smtp_host: str | None = None

    smtp_port: int = Field(
        default=587,
        ge=1,
        le=65535,
    )

    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from_email: str | None = None
    smtp_from_name: str = "Tax AI Advisor"
    smtp_use_tls: bool = True

    # تنظیمات ملی‌پیامک
    melipayamak_username: str | None = None
    melipayamak_api_key: str | None = None
    melipayamak_body_id: int | None = None

    melipayamak_base_url: str = (
        "https://rest.payamak-panel.com/"
        "api/SendSMS/BaseServiceNumber"
    )

    melipayamak_timeout_seconds: float = Field(
        default=15.0,
        ge=2.0,
        le=60.0,
    )

    max_upload_bytes: int = Field(
        default=20 * 1024 * 1024,
        ge=1024,
        le=100 * 1024 * 1024,
    )

    storage_backend: Literal[
        "local",
        "s3",
    ] = "local"

    local_storage_path: str = "./storage"

    s3_endpoint_url: str | None = None
    s3_bucket: str = "tax-ai-documents"
    s3_access_key: str | None = None
    s3_secret_key: str | None = None
    s3_region: str = "us-east-1"

    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"

    task_execution_mode: Literal[
        "queue",
        "inline",
    ] = "queue"

    chunk_max_chars: int = Field(
        default=1400,
        ge=500,
        le=4000,
    )

    chunk_overlap_chars: int = Field(
        default=160,
        ge=0,
        le=500,
    )

    minimum_extracted_chars: int = Field(
        default=40,
        ge=1,
        le=1000,
    )

    ai_provider: Literal[
        "disabled",
        "gemini",
    ] = "gemini"

    gemini_api_key: str | None = None

    gemini_base_url: str = (
        "https://generativelanguage.googleapis.com/v1beta"
    )

    gemini_generation_model: str = "gemini-2.5-flash"
    gemini_general_model: str = "gemini-2.5-flash-lite"
    gemini_advanced_model: str = "gemini-3.5-flash"
    gemini_embedding_model: str = "gemini-embedding-001"

    gemini_timeout_seconds: float = Field(
        default=8.0,
        ge=1.0,
        le=60.0,
    )

    embedding_dimensions: int = Field(
        default=768,
        ge=128,
        le=3072,
    )

    bootstrap_admin_email: str | None = None
    bootstrap_admin_password: str | None = None
    bootstrap_admin_full_name: str = "مدیر سامانه"

    @field_validator("docs_enabled")
    @classmethod
    def disable_docs_in_production_by_default(
        cls,
        value: bool,
        info,
    ):
        environment = info.data.get("environment")

        if environment == "production" and value:
            return False

        return value

    @field_validator(
        "gemini_api_key",
        mode="before",
    )
    @classmethod
    def normalize_gemini_api_key(cls, value):
        if value is None or not str(value).strip():
            return None

        cleaned = str(value).strip()

        if len(cleaned) < 20:
            raise ValueError(
                "Gemini API key is too short"
            )

        return cleaned

    @field_validator(
        "gemini_base_url",
    )
    @classmethod
    def normalize_gemini_base_url(
        cls,
        value: str,
    ):
        return value.strip().rstrip("/")

    @field_validator(
        "public_site_url",
        "zarinpal_callback_url",
        "zarinpal_api_base_url",
        "zarinpal_start_pay_url",
        "melipayamak_base_url",
    )
    @classmethod
    def normalize_urls(
        cls,
        value: str,
    ):
        return value.strip().rstrip("/")

    @field_validator(
        "zarinpal_merchant_id",
        mode="before",
    )
    @classmethod
    def normalize_zarinpal_merchant_id(
        cls,
        value,
    ):
        if value is None or not str(value).strip():
            return None

        return str(value).strip()

    @field_validator(
        "bootstrap_admin_email",
        "bootstrap_admin_password",
        mode="before",
    )
    @classmethod
    def normalize_optional_bootstrap_value(
        cls,
        value,
    ):
        if value is None or not str(value).strip():
            return None

        return str(value).strip()

    @field_validator(
        "smtp_host",
        "smtp_username",
        "smtp_password",
        "smtp_from_email",
        "melipayamak_username",
        "melipayamak_api_key",
        mode="before",
    )
    @classmethod
    def normalize_optional_secret_value(
        cls,
        value,
    ):
        if value is None or not str(value).strip():
            return None

        return str(value).strip()

    @model_validator(mode="after")
    def validate_storage_settings(self):
        if self.chunk_overlap_chars >= self.chunk_max_chars:
            raise ValueError(
                "chunk_overlap_chars must be smaller "
                "than chunk_max_chars"
            )

        if self.storage_backend == "s3" and not all(
            (
                self.s3_endpoint_url,
                self.s3_access_key,
                self.s3_secret_key,
                self.s3_bucket,
            )
        ):
            raise ValueError(
                "S3 storage requires endpoint, bucket, "
                "access key and secret key"
            )

        if bool(self.bootstrap_admin_email) != bool(
            self.bootstrap_admin_password
        ):
            raise ValueError(
                "Bootstrap admin email and password "
                "must be set together"
            )

        if self.bootstrap_admin_password:
            password = self.bootstrap_admin_password

            if len(password) < 12 or not all(
                (
                    any(char.islower() for char in password),
                    any(char.isupper() for char in password),
                    any(char.isdigit() for char in password),
                )
            ):
                raise ValueError(
                    "Bootstrap admin password must be strong"
                )

        if self.email_delivery_mode == "smtp" and not all(
            (
                self.smtp_host,
                self.smtp_username,
                self.smtp_password,
                self.smtp_from_email,
            )
        ):
            raise ValueError(
                "SMTP delivery requires host, username, "
                "password and from email"
            )

        if self.payment_provider == "zarinpal":
            if (
                not self.zarinpal_merchant_id
                or len(self.zarinpal_merchant_id) != 36
            ):
                raise ValueError(
                    "Zarinpal payment requires a "
                    "36-character merchant id"
                )

            if (
                not self.zarinpal_callback_url.startswith(
                    "https://"
                )
                and self.environment == "production"
            ):
                raise ValueError(
                    "Zarinpal callback URL must use HTTPS "
                    "in production"
                )

        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
