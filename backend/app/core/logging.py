from __future__ import annotations

import json
import logging
import re
import sys
import time
import uuid
from collections.abc import Mapping
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


SENSITIVE_KEYS = frozenset(
    {
        "password",
        "password_hash",
        "access_token",
        "refresh_token",
        "authorization",
        "api_key",
        "secret",
        "national_id",
        "kod_meli",
        "account_number",
        "card_number",
        "s3_access_key",
        "s3_secret_key",
    }
)

_BEARER_PATTERN = re.compile(r"(?i)bearer\s+[a-z0-9._~+/=-]+")
_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


def redact(value: Any, key: str | None = None) -> Any:
    if key and key.lower() in SENSITIVE_KEYS:
        return "[REDACTED]"

    if isinstance(value, Mapping):
        return {
            str(item_key): redact(item_value, str(item_key))
            for item_key, item_value in value.items()
        }

    if isinstance(value, (list, tuple)):
        return [redact(item) for item in value]

    if isinstance(value, str):
        return _BEARER_PATTERN.sub("Bearer [REDACTED]", value)

    return value


class JsonFormatter(logging.Formatter):
    _standard_attributes = frozenset(
        logging.makeLogRecord({}).__dict__
    )

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": self.formatTime(
                record,
                "%Y-%m-%dT%H:%M:%S%z",
            ),
            "level": record.levelname,
            "logger": record.name,
            "message": redact(record.getMessage()),
        }

        for key, value in record.__dict__.items():
            if (
                key not in self._standard_attributes
                and not key.startswith("_")
            ):
                payload[key] = redact(value, key)

        if record.exc_info:
            payload["exception"] = self.formatException(
                record.exc_info
            )

        return json.dumps(
            payload,
            ensure_ascii=False,
            default=str,
        )


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        incoming_id = request.headers.get("X-Request-ID", "")

        request_id = (
            incoming_id
            if _REQUEST_ID_PATTERN.fullmatch(incoming_id)
            else uuid.uuid4().hex
        )

        started_at = time.perf_counter()

        response = await call_next(request)

        duration_ms = round(
            (time.perf_counter() - started_at) * 1000,
            2,
        )

        response.headers["X-Request-ID"] = request_id

        logging.getLogger("tax_ai.http").info(
            "request_completed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            },
        )

        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = (
            "strict-origin-when-cross-origin"
        )
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), "
            "geolocation=(), payment=()"
        )

        path = request.url.path

        if (
            path == "/docs"
            or path == "/redoc"
            or path == "/openapi.json"
        ):
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' "
                "https://cdn.jsdelivr.net; "
                "style-src 'self' 'unsafe-inline' "
                "https://cdn.jsdelivr.net; "
                "img-src 'self' data: "
                "https://fastapi.tiangolo.com; "
                "font-src 'self' https://cdn.jsdelivr.net; "
                "connect-src 'self'; "
                "frame-ancestors 'none'; "
                "base-uri 'none'"
            )
        else:
            response.headers["Content-Security-Policy"] = (
                "default-src 'none'; "
                "frame-ancestors 'none'; "
                "base-uri 'none'"
            )

        return response