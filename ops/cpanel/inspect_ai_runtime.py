from __future__ import annotations

import time
import json
import urllib.error
import urllib.request

from app.core.config import Settings
from app.ai.providers import create_ai_provider


def timed(label: str, action) -> None:
    started = time.monotonic()
    result = action()
    print(f"{label}_seconds={time.monotonic() - started:.2f}")
    print(f"{label}_ok={bool(result)}")


def main() -> None:
    settings = Settings()
    print(f"provider={settings.ai_provider}")
    print(f"base_url={settings.gemini_base_url}")
    print(f"generation_model={settings.gemini_generation_model}")
    print(f"embedding_model={settings.gemini_embedding_model}")
    print(f"timeout_seconds={settings.gemini_timeout_seconds}")
    print(f"key_type={'avalai' if (settings.gemini_api_key or '').startswith('aa-') else 'other'}")
    request = urllib.request.Request(
        f"{settings.gemini_base_url}/models/{settings.gemini_generation_model}:generateContent",
        data=json.dumps({"contents": [{"parts": [{"text": "سلام"}]}]}).encode(),
        headers={"Content-Type": "application/json", "x-goog-api-key": settings.gemini_api_key or ""},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=settings.gemini_timeout_seconds) as response:
            print(f"raw_status={response.status}")
    except urllib.error.HTTPError as error:
        print(f"raw_status={error.code}")
        print(f"raw_error={error.read().decode('utf-8', 'replace')[:500]}")
    except Exception as error:
        print(f"raw_exception={type(error).__name__}")
    provider = create_ai_provider(settings)
    timed("embedding", lambda: provider.embed_query("تفاوت مالیات اشخاص حقیقی و حقوقی چیست؟"))
    timed("generation", lambda: provider.generate_general("تفاوت مالیات اشخاص حقیقی و حقوقی چیست؟"))


if __name__ == "__main__":
    main()
