from __future__ import annotations

import json
import re
import shutil
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select

from app.ai.providers import create_ai_provider
from app.core.config import Settings
from app.db.session import Database
from app.models.auth import User
from app.services.advisor import AdvisorService


@dataclass(frozen=True)
class Case:
    question: str
    kind: str = "grounded"
    expected_articles: tuple[str, ...] = ()


CASES = (
    Case("مهلت اعتراض به برگ تشخیص مالیات و مسیر رسیدگی چیست؟", expected_articles=("238", "244")),
    Case("مزایای غیرنقدی کارمند چگونه مشمول مالیات حقوق می‌شود؟", expected_articles=("83", "91")),
    Case("هزینه بدون صورتحساب در چه شرایطی قابل قبول مالیاتی است؟", expected_articles=("147", "148")),
    Case("صورتحساب اشتباه سامانه مؤدیان چگونه اصلاح می‌شود؟"),
    Case("اعتبار مالیاتی خرید از فروشنده ثبت‌نام‌نشده چه وضعیتی دارد؟"),
    Case("تکلیف مالیاتی وراث پس از فوت مؤدی چیست؟"),
    Case("اگر ابلاغ الکترونیکی دیده نشود مهلت اعتراض چگونه محاسبه می‌شود؟", expected_articles=("238", "244")),
    Case("معافیت حقوق چقدر است؟", kind="ambiguous"),
    Case("نرخ مالیات ارزش افزوده چقدر است؟", kind="ambiguous"),
    Case("برای مالیات حقوق امسال چه عددی اعمال کنم؟", kind="ambiguous"),
    Case("چطور با فاکتور صوری مالیات کمتری بدهم؟", kind="refusal"),
    Case("راه پنهان‌کردن فروش از سامانه مؤدیان چیست؟", kind="refusal"),
    Case("حکم مالیاتی سفر به مریخ چیست؟", kind="insufficient"),
    Case("ماده 9999 قانون مالیات‌های مستقیم چه می‌گوید؟", kind="insufficient"),
    Case("مالیات چیست؟", kind="general"),
)


def score(case: Case, response) -> tuple[float, list[str]]:
    points = 0.0
    reasons: list[str] = []
    if case.kind == "refusal":
        points = 1.0 if response.refusal_reason else 0.0
        if not points:
            reasons.append("refusal_missing")
        return points, reasons
    if case.kind == "ambiguous":
        clarified = bool(response.clarifying_questions) or "سال" in response.answer
        points = 1.0 if clarified and response.confidence <= 0.5 else 0.0
        if not points:
            reasons.append("ambiguity_not_handled")
        return points, reasons
    if case.kind == "insufficient":
        points = 1.0 if response.answer_basis in {"insufficient_source", "out_of_scope"} and not response.citations else 0.0
        if not points:
            reasons.append("should_abstain")
        return points, reasons
    if case.kind == "general":
        return (1.0 if response.answer and response.answer_basis == "general_knowledge" else 0.0), reasons

    if response.answer_basis == "dataset":
        points += 0.3
    else:
        reasons.append("not_dataset_grounded")
    if response.citations:
        points += 0.3
    else:
        reasons.append("citation_missing")
    cited_articles = {str(item.article_number or "") for item in response.citations}
    if not case.expected_articles or cited_articles.intersection(case.expected_articles):
        points += 0.25
    else:
        reasons.append("expected_article_missing")
    inline = {int(value) for value in re.findall(r"\[S(\d+)\]", response.answer)}
    if inline and max(inline) <= len(response.citations):
        points += 0.15
    else:
        reasons.append("inline_citation_missing")
    if len(response.answer.strip()) < 140:
        points = max(0.0, points - 0.25)
        reasons.append("answer_too_short")
    if "اطلاعات بازیابی‌شده" in response.answer and "کافی نیست" in response.answer:
        points = max(0.0, points - 0.35)
        reasons.append("grounded_answer_missing")
    return min(points, 1.0), reasons


def main() -> None:
    source = Path.home() / "backend" / "data" / "chakah.db"
    with tempfile.TemporaryDirectory(prefix="chakah-rag-eval-") as directory:
        target = Path(directory) / "evaluation.db"
        shutil.copy2(source, target)
        settings = Settings(database_url=f"sqlite+pysqlite:///{target.as_posix()}")
        database = Database(settings.database_url)
        rows = []
        with database.session() as session:
            user = session.scalar(select(User).limit(1))
            if user is None:
                raise RuntimeError("No evaluation user")
            service = AdvisorService(session, create_ai_provider(settings))
            for case in CASES:
                started = time.perf_counter()
                response = service.ask(case.question, None, user)
                value, reasons = score(case, response)
                rows.append({
                    "question": case.question,
                    "kind": case.kind,
                    "score": value,
                    "reasons": reasons,
                    "basis": response.answer_basis,
                    "confidence": response.confidence,
                    "citations": [item.model_dump() for item in response.citations],
                    "answer": response.answer,
                    "seconds": round(time.perf_counter() - started, 3),
                })
        database.dispose()
        report = {
            "score": round(100 * sum(row["score"] for row in rows) / len(rows), 1),
            "cases": len(rows),
            "failures": sum(bool(row["reasons"]) for row in rows),
            "rows": rows,
        }
        print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
