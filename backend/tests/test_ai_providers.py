import json
import urllib.error
from unittest.mock import patch

from app.ai.providers import GeminiProvider, cosine_similarity
from app.ai import providers as provider_module


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def read(self):
        return json.dumps(self.payload).encode()


def provider():
    return GeminiProvider(
        api_key="test-api-key-that-is-long-enough",
        base_url="https://api.avalai.ir/v1beta",
        generation_model="gemini-2.5-flash",
        general_model="gemini-2.5-flash-lite",
        advanced_model="gemini-3.5-flash",
        embedding_model="gemini-embedding-001",
        timeout_seconds=2,
        embedding_dimensions=3,
    )


def test_gemini_generation_uses_structured_response():
    payload = {
        "candidates": [
            {"content": {"parts": [{"text": '{"answer":"پاسخ مستند"}'}]}}
        ]
    }
    with patch("urllib.request.urlopen", return_value=FakeResponse(payload)) as call:
        answer = provider().generate("پرسش", ["منبع معتبر"])
    assert answer == "پاسخ مستند"
    request = call.call_args.args[0]
    sent = json.loads(request.data)
    assert sent["generationConfig"]["responseMimeType"] == "application/json"
    assert "منبع معتبر" in sent["contents"][0]["parts"][0]["text"]
    assert request.headers["X-goog-api-key"] == "test-api-key-that-is-long-enough"
    assert request.full_url.endswith("models/gemini-2.5-flash-lite:generateContent")


def test_general_and_complex_questions_use_expected_models():
    payload = {"candidates": [{"content": {"parts": [{"text": '{"answer":"ok"}'}]}}]}
    with patch("urllib.request.urlopen", return_value=FakeResponse(payload)) as call:
        assert provider().generate_general("مالیات چیست؟") == "ok"
    assert call.call_args.args[0].full_url.endswith("models/gemini-2.5-flash-lite:generateContent")

    with patch("urllib.request.urlopen", return_value=FakeResponse(payload)) as call:
        assert provider().generate("ریسک جرائم این اظهارنامه را تحلیل و با سناریوی اصلاح مقایسه کن", ["متن"]) == "ok"
    assert call.call_args.args[0].full_url.endswith("models/gemini-3.5-flash:generateContent")


def test_gemini_embedding_is_normalized_and_failures_fall_back():
    payload = {"embedding": {"values": [3, 4, 0]}}
    with patch("urllib.request.urlopen", return_value=FakeResponse(payload)):
        vector = provider().embed_query("پرسش")
    assert vector is not None
    assert round(cosine_similarity(vector, vector), 6) == 1

    with patch("urllib.request.urlopen", side_effect=TimeoutError):
        assert provider().embed_query("پرسش تازه") is None


def test_quota_error_opens_fast_circuit_breaker():
    provider_module._provider_blocked_until.clear()
    quota_error = urllib.error.HTTPError("https://api.test", 429, "quota", {}, None)
    with patch("urllib.request.urlopen", side_effect=quota_error) as call:
        assert provider().generate_general("پرسش سهمیه اول") is None
        assert provider().generate_general("پرسش سهمیه دوم") is None
    assert call.call_count == 1
    provider_module._provider_blocked_until.clear()
