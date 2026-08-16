from app.core.config import Settings
from app.services.captcha import CaptchaVerifier


def settings(**values) -> Settings:
    return Settings(
        environment="test",
        database_url="sqlite+pysqlite:///:memory:",
        jwt_secret="test-secret-that-is-at-least-32-characters-long",
        captcha_enabled=True,
        turnstile_site_key="site-key",
        turnstile_secret_key="secret-key",
        **values,
    )


def test_captcha_fails_closed_on_empty_token_and_network_error(monkeypatch) -> None:
    verifier = CaptchaVerifier(settings())
    assert verifier.verify("") is False

    def unavailable(*_args, **_kwargs):
        raise OSError("offline")

    monkeypatch.setattr("urllib.request.urlopen", unavailable)
    assert verifier.verify("provided-token", "203.0.113.10") is False


def test_captcha_accepts_only_explicit_success(monkeypatch) -> None:
    class Response:
        def __enter__(self): return self
        def __exit__(self, *_args): return None
        def read(self): return b'{"success": true}'

    monkeypatch.setattr("urllib.request.urlopen", lambda *_args, **_kwargs: Response())
    assert CaptchaVerifier(settings()).verify("valid-token") is True
