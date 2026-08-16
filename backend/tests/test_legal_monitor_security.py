import socket

import pytest

from app.services.legal_monitor import validate_public_source_url


@pytest.mark.parametrize(
    "url",
    [
        "http://example.com/law",
        "file:///etc/passwd",
        "https://user:pass@example.com/law",
        "https://127.0.0.1/admin",
        "https://[::1]/admin",
    ],
)
def test_legal_monitor_rejects_unsafe_urls(url: str) -> None:
    with pytest.raises(ValueError):
        validate_public_source_url(url)


def test_legal_monitor_rejects_dns_to_private_address(monkeypatch) -> None:
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *args, **kwargs: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.8", 443))],
    )
    with pytest.raises(ValueError):
        validate_public_source_url("https://legal.example.test/law")
