import json
from unittest.mock import patch

from app.core.config import Settings
from app.services.zarinpal import ZarinpalGateway


class FakeResponse:
    def __init__(self, payload: dict):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return None

    def read(self):
        return json.dumps(self.payload).encode()


def settings() -> Settings:
    return Settings(
        environment="test",
        database_url="sqlite+pysqlite:///:memory:",
        jwt_secret="test-secret-that-is-at-least-32-characters-long",
        payment_provider="zarinpal",
        zarinpal_merchant_id="00000000-0000-0000-0000-000000000000",
    )


def test_create_payment_returns_authority_and_redirect_url():
    response = {"data": {"code": 100, "authority": "A000000000000000000000000000000001"}, "errors": []}
    with patch("app.services.zarinpal.urlopen", return_value=FakeResponse(response)):
        authority, url = ZarinpalGateway(settings()).create_payment(
            amount_toman=100_000,
            description="اشتراک",
            email="user@example.com",
            mobile=None,
            order_id="order-1",
        )
    assert authority.startswith("A")
    assert url.endswith(authority)


def test_verify_accepts_already_verified_payment():
    response = {"data": {"code": 101, "ref_id": 12345, "card_pan": "603799******1234", "card_hash": "hash"}, "errors": []}
    with patch("app.services.zarinpal.urlopen", return_value=FakeResponse(response)):
        result = ZarinpalGateway(settings()).verify_payment(
            amount_toman=100_000,
            authority="A000000000000000000000000000000001",
        )
    assert result.code == 101
    assert result.reference_id == "12345"
