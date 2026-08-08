from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import struct
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash

from app.core.config import Settings


class TokenValidationError(ValueError):
    pass


class SecurityManager:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.password_hash = PasswordHash.recommended()
        self._dummy_hash = self.password_hash.hash(secrets.token_urlsafe(32))

    def hash_password(self, password: str) -> str:
        return self.password_hash.hash(password)

    def verify_password(self, password: str, password_hash: str) -> bool:
        return self.password_hash.verify(password, password_hash)

    def consume_dummy_password_check(self, password: str) -> None:
        self.password_hash.verify(password, self._dummy_hash)

    def create_access_token(self, user_id: str) -> tuple[str, int]:
        now = datetime.now(timezone.utc)
        expires_in = self.settings.access_token_minutes * 60
        payload: dict[str, Any] = {
            "sub": user_id,
            "jti": str(uuid.uuid4()),
            "type": "access",
            "iat": now,
            "exp": now + timedelta(seconds=expires_in),
            "iss": self.settings.jwt_issuer,
            "aud": self.settings.jwt_audience,
        }
        token = jwt.encode(
            payload, self.settings.jwt_secret, algorithm=self.settings.jwt_algorithm
        )
        return token, expires_in

    def decode_access_token(self, token: str) -> dict[str, Any]:
        try:
            payload = jwt.decode(
                token,
                self.settings.jwt_secret,
                algorithms=[self.settings.jwt_algorithm],
                audience=self.settings.jwt_audience,
                issuer=self.settings.jwt_issuer,
                options={"require": ["exp", "iat", "sub", "jti", "iss", "aud", "type"]},
            )
        except InvalidTokenError as error:
            raise TokenValidationError("Invalid access token") from error
        if payload.get("type") != "access":
            raise TokenValidationError("Invalid token type")
        return payload

    @staticmethod
    def new_refresh_token() -> str:
        return secrets.token_urlsafe(48)

    @staticmethod
    def hash_refresh_token(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def hash_verification_code(self, email: str, code: str) -> str:
        value = f"{self.settings.jwt_secret}:{email}:{code}"
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    def two_factor_secret(self, user_id: str) -> str:
        digest = hmac.new(self.settings.jwt_secret.encode(), f"2fa:{user_id}".encode(), hashlib.sha256).digest()[:20]
        return base64.b32encode(digest).decode().rstrip("=")

    def verify_totp(self, user_id: str, code: str) -> bool:
        if not code.isdigit() or len(code) != 6:
            return False
        secret = self.two_factor_secret(user_id)
        padded = secret + "=" * ((8 - len(secret) % 8) % 8)
        key = base64.b32decode(padded)
        counter = int(time.time() // 30)
        for offset in (-1, 0, 1):
            digest = hmac.new(key, struct.pack(">Q", counter + offset), hashlib.sha1).digest()
            index = digest[-1] & 0x0F
            value = (struct.unpack(">I", digest[index:index + 4])[0] & 0x7FFFFFFF) % 1000000
            if hmac.compare_digest(f"{value:06d}", code):
                return True
        return False

    @staticmethod
    def new_setup_token() -> str:
        return secrets.token_urlsafe(48)
