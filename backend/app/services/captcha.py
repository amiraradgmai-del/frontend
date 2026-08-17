from __future__ import annotations

import json
import logging
import urllib.error
import urllib.parse
import urllib.request

from app.core.config import Settings

logger = logging.getLogger(__name__)


class CaptchaVerifier:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @property
    def enabled(self) -> bool:
        return bool(
            self.settings.captcha_enabled
            and self.settings.turnstile_site_key
            and self.settings.turnstile_secret_key
        )

    def verify(self, token: str, remote_ip: str = "") -> bool:
        if not self.enabled:
            return True
        if not token.strip():
            return False
        payload = urllib.parse.urlencode({
            "secret": self.settings.turnstile_secret_key or "",
            "response": token.strip(),
            "remoteip": remote_ip,
        }).encode("utf-8")
        request = urllib.request.Request(
            self.settings.turnstile_verify_url,
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.settings.turnstile_timeout_seconds) as response:
                result = json.loads(response.read().decode("utf-8"))
            return result.get("success") is True
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as error:
            logger.warning("captcha_verification_failed", extra={"error_type": type(error).__name__})
            return False
