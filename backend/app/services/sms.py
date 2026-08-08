from __future__ import annotations

import json
import logging
from urllib import error, parse, request

from app.core.config import Settings


logger = logging.getLogger(__name__)


class SmsDeliveryError(RuntimeError):
    """Raised when the SMS provider rejects or cannot process a request."""


class MelipayamakSender:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def send_verification_code(self, phone: str, code: str) -> None:
        username = self.settings.melipayamak_username
        api_key = self.settings.melipayamak_api_key
        body_id = self.settings.melipayamak_body_id

        if not username or not api_key or body_id is None:
            raise SmsDeliveryError(
                "Melipayamak settings are incomplete"
            )

        payload = parse.urlencode(
            {
                "username": username,
                # Melipayamak accepts the API key in the password field.
                "password": api_key,
                "text": code,
                "to": phone,
                "bodyId": str(body_id),
            }
        ).encode("utf-8")

        http_request = request.Request(
            self.settings.melipayamak_base_url,
            data=payload,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
                "User-Agent": "ChekahTax-Backend/1.0",
            },
            method="POST",
        )

        try:
            with request.urlopen(
                http_request,
                timeout=self.settings.melipayamak_timeout_seconds,
            ) as response:
                raw_body = response.read().decode("utf-8", errors="replace")
        except error.HTTPError as exc:
            response_body = exc.read().decode("utf-8", errors="replace")
            logger.error(
                "Melipayamak HTTP error: status=%s body=%s",
                exc.code,
                response_body[:500],
            )
            raise SmsDeliveryError(
                "SMS provider returned an HTTP error"
            ) from exc
        except (error.URLError, TimeoutError, OSError) as exc:
            logger.exception("Could not connect to Melipayamak")
            raise SmsDeliveryError(
                "Could not connect to SMS provider"
            ) from exc

        try:
            result = json.loads(raw_body)
        except json.JSONDecodeError as exc:
            logger.error(
                "Invalid Melipayamak response: %s",
                raw_body[:500],
            )
            raise SmsDeliveryError(
                "SMS provider returned an invalid response"
            ) from exc

        status = self._extract_status(result)

        # Melipayamak successful responses generally return status 1.
        if status != 1:
            provider_message = self._extract_message(result)
            logger.error(
                "Melipayamak rejected SMS: status=%s message=%s",
                status,
                provider_message,
            )
            raise SmsDeliveryError(
                provider_message or "SMS provider rejected the request"
            )

    @staticmethod
    def _extract_status(result: object) -> int | None:
        if isinstance(result, dict):
            for key in (
                "RetStatus",
                "retStatus",
                "ret_status",
                "status",
                "Status",
            ):
                value = result.get(key)
                if value is not None:
                    try:
                        return int(value)
                    except (TypeError, ValueError):
                        return None

            nested = result.get("Value") or result.get("value")
            if isinstance(nested, dict):
                return MelipayamakSender._extract_status(nested)

        return None

    @staticmethod
    def _extract_message(result: object) -> str:
        if not isinstance(result, dict):
            return ""

        for key in (
            "StrRetStatus",
            "strRetStatus",
            "message",
            "Message",
            "error",
            "Error",
        ):
            value = result.get(key)
            if value:
                return str(value)

        value = result.get("Value") or result.get("value")
        if isinstance(value, str):
            return value
        if isinstance(value, dict):
            return MelipayamakSender._extract_message(value)

        return ""
