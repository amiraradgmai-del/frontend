from __future__ import annotations

import time
import sys
from pathlib import Path

sys.path.insert(0, str((Path(__file__).resolve().parents[2] / "backend").resolve()))

from app.ai.providers import create_ai_provider
from app.core.config import get_settings


def main() -> None:
    settings = get_settings()
    provider = create_ai_provider(settings)
    started = time.perf_counter()
    answer = provider.generate(
        "مالیات چیست؟",
        ["مالیات پرداخت قانونی اشخاص و کسب‌وکارها بر اساس درآمد، دارایی یا مصرف است."],
    )
    elapsed = time.perf_counter() - started
    print(f"general_model={settings.gemini_general_model}")
    print(f"seconds={elapsed:.2f}")
    print(f"ok={bool(answer)}")


if __name__ == "__main__":
    main()
