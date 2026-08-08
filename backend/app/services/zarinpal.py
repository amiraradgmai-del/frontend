from __future__ import annotations

import json
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.core.config import Settings


class ZarinpalError(RuntimeError):
    def __init__(self, message: str, code: int | None = None):
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class ZarinpalVerification:
    code: int
    reference_id: str
    card_pan: str | None
    card_hash: str | None


class ZarinpalGateway:
    def __init__(self, settings: Settings):
        self.settings = settings

    def create_payment(
        self,
        *,
        amount_toman: int,
        description: str,
        email: str,
        mobile: str | None,
        order_id: str,
    ) -> tuple[str, str]:
        response = self._post(
            "request.json",
            {
                "merchant_id": self.settings.zarinpal_merchant_id,
                "amount": amount_toman,
                "currency": "IRT",
                "description": description[:500],
                "callback_url": self.settings.zarinpal_callback_url,
                "metadata": {
                    "email": email,
                    "mobile": mobile or "",
                    "order_id": order_id,
                },
            },
        )
        data = response.get("data") or {}
        code = int(data.get("code") or 0)
        authority = str(data.get("authority") or "")
        if code != 100 or not authority:
            raise ZarinpalError(self._message(response), code)
        return authority, f"{self.settings.zarinpal_start_pay_url}/{authority}"

    def verify_payment(self, *, amount_toman: int, authority: str) -> ZarinpalVerification:
        response = self._post(
            "verify.json",
            {
                "merchant_id": self.settings.zarinpal_merchant_id,
                "amount": amount_toman,
                "authority": authority,
            },
        )
        data = response.get("data") or {}
        code = int(data.get("code") or 0)
        if code not in (100, 101):
            raise ZarinpalError(self._message(response), code)
        return ZarinpalVerification(
            code=code,
            reference_id=str(data.get("ref_id") or ""),
            card_pan=data.get("card_pan"),
            card_hash=data.get("card_hash"),
        )

    def _post(self, endpoint: str, payload: dict) -> dict:
        request = Request(
            f"{self.settings.zarinpal_api_base_url}/{endpoint}",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.settings.zarinpal_timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            try:
                body = json.loads(error.read().decode("utf-8"))
            except (ValueError, UnicodeDecodeError):
                body = {}
            raise ZarinpalError(self._message(body) or "خطای ارتباط با درگاه پرداخت") from error
        except (URLError, TimeoutError, ValueError) as error:
            raise ZarinpalError("ارتباط با درگاه پرداخت برقرار نشد") from error

    @staticmethod
    def _message(response: dict) -> str:
        errors = response.get("errors")
        if isinstance(errors, dict):
            return str(errors.get("message") or "درخواست درگاه پرداخت نامعتبر است")
        data = response.get("data")
        if isinstance(data, dict):
            return str(data.get("message") or "درخواست درگاه پرداخت نامعتبر است")
        return "درخواست درگاه پرداخت نامعتبر است"
