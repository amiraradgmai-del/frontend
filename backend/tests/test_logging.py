import json
import logging

from app.core.logging import JsonFormatter, redact


def test_redact_masks_sensitive_nested_values_and_bearer_tokens() -> None:
    value = {
        "user": {"password": "secret", "national_id": "0010350829"},
        "authorization": "Bearer abc.def.ghi",
    }
    masked = redact(value)
    assert masked["user"]["password"] == "[REDACTED]"
    assert masked["user"]["national_id"] == "[REDACTED]"
    assert masked["authorization"] == "[REDACTED]"


def test_json_formatter_does_not_emit_secret_extra_fields() -> None:
    record = logging.LogRecord("test", logging.INFO, __file__, 1, "login", (), None)
    record.api_key = "top-secret"
    payload = json.loads(JsonFormatter().format(record))
    assert payload["api_key"] == "[REDACTED]"
