from __future__ import annotations

import json
import shutil
import tempfile
import time
from pathlib import Path

from sqlalchemy import select

from app.ai.providers import create_ai_provider
from app.core.config import Settings
from app.db.session import Database
from app.models.auth import User
from app.services.advisor import AdvisorService


QUESTIONS = (
    "مالیات چیست؟",
    "مالیات چند نوع است؟",
    "تفاوت شخص حقیقی و شخص حقوقی در مالیات چیست؟",
    "اظهارنامه مالیاتی چیست؟",
    "آیا هر واریزی بانکی درآمد محسوب می‌شود؟",
    "برای اثبات قرض بودن واریزی بانکی چه مدارکی لازم است؟",
    "جریمه دیرکرد اظهارنامه چگونه بررسی می‌شود؟",
    "معافیت مالیاتی شرکت دانش‌بنیان چگونه بررسی می‌شود؟",
    "مالیات دستگاه کارتخوان چگونه محاسبه می‌شود؟",
    "اگر صورت‌حساب ناقص باشد چه اقدامی باید انجام دهم؟",
    "مهلت اعتراض به برگ تشخیص چقدر است؟",
    "تکلیف مالیاتی وراث پس از فوت چیست؟",
)


def main() -> None:
    source = Path.home() / "backend" / "data" / "chakah.db"
    with tempfile.TemporaryDirectory(prefix="chakah-qa-") as directory:
        target = Path(directory) / "quality.db"
        shutil.copy2(source, target)
        settings = Settings(
            database_url=f"sqlite+pysqlite:///{target.as_posix()}",
            ai_provider="disabled",
        )
        database = Database(settings.database_url)
        results = []
        with database.session() as session:
            user = session.scalar(select(User).limit(1))
            if user is None:
                raise RuntimeError("No user is available for isolated quality evaluation")
            service = AdvisorService(session, create_ai_provider(settings))
            for question in QUESTIONS:
                started = time.perf_counter()
                response = service.ask(question, None, user)
                results.append(
                    {
                        "question": question,
                        "seconds": round(time.perf_counter() - started, 3),
                        "basis": response.answer_basis,
                        "confidence": response.confidence,
                        "answer": response.answer,
                    }
                )
        database.dispose()
        print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
