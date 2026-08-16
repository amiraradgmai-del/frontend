import json
from unittest.mock import patch

from app.ai.providers import GeminiProvider, cosine_similarity


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


def test_gemini_embedding_is_normalized_and_failures_fall_back():
    payload = {"embedding": {"values": [3, 4, 0]}}
    with patch("urllib.request.urlopen", return_value=FakeResponse(payload)):
        vector = provider().embed_query("پرسش")
    assert vector is not None
    assert round(cosine_similarity(vector, vector), 6) == 1

    with patch("urllib.request.urlopen", side_effect=TimeoutError):
        assert provider().embed_query("پرسش تازه و بدون کش") is None
