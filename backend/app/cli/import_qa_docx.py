from __future__ import annotations

import argparse
import hashlib
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree

from sqlalchemy import select

from app.core.config import Settings
from app.db.session import Database
from app.models.portal import LawReferenceRecord, LegalCategory

WORD_NAMESPACE = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
QUESTION_PATTERN = re.compile(r"^س[ؤو]ال\s*([۰-۹0-9]+)\s*[:：\-]\s*(.+)$")
ANSWER_PATTERN = re.compile(r"^پاسخ مورد انتظار\s*[:：\-]?\s*(.*)$")
REMOVED_METADATA_MARKERS = (
    "منبع تدوین:",
    "شناسه منبع:",
)


def paragraphs_from_docx(path: Path) -> list[str]:
    with zipfile.ZipFile(path) as archive:
        document = ElementTree.fromstring(archive.read("word/document.xml"))
    paragraphs: list[str] = []
    for paragraph in document.findall(".//w:body/w:p", WORD_NAMESPACE):
        text = "".join(
            node.text or "" for node in paragraph.findall(".//w:t", WORD_NAMESPACE)
        ).strip()
        if text:
            paragraphs.append(text)
    return paragraphs


def question_answers(path: Path) -> list[tuple[str, str, str]]:
    items: list[tuple[str, str, str]] = []
    number = ""
    question = ""
    answer_parts: list[str] = []

    def append_current() -> None:
        if question and answer_parts:
            items.append((number, question, "\n".join(answer_parts).strip()))

    for paragraph in paragraphs_from_docx(path):
        question_match = QUESTION_PATTERN.match(paragraph)
        if question_match:
            append_current()
            number, question = question_match.groups()
            answer_parts = []
            continue
        answer_match = ANSWER_PATTERN.match(paragraph)
        if question and answer_match:
            answer_parts = [answer_match.group(1).strip()]
            continue
        if question and answer_parts:
            answer_parts.append(paragraph)
    append_current()
    return [
        (number, question, clean_answer(answer))
        for number, question, answer in items
        if clean_answer(answer)
    ]


def clean_answer(answer: str) -> str:
    cleaned = answer
    for marker in REMOVED_METADATA_MARKERS:
        cleaned = cleaned.split(marker, 1)[0]
    return cleaned.strip()


def stable_id(number: str, question: str, answer: str) -> str:
    content = f"{number}\n{question.strip()}\n{answer.strip()}"
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()[:24]
    return f"qa-{digest}"


def import_questions(path: Path) -> tuple[int, int, int]:
    items = question_answers(path)
    database = Database(Settings().database_url)
    created = 0
    updated = 0
    with database.session() as session:
        category_id = session.scalar(
            select(LegalCategory.id).where(LegalCategory.code == "other")
        )
        for number, question, answer in items:
            record_id = stable_id(number, question, answer)
            record = session.get(LawReferenceRecord, record_id)
            values = {
                "source_id": "curated-tax-qa",
                "law_name": "راهنمای کاربردی مالیاتی",
                "chapter": "پرسش‌های کاربردی",
                "article_number": "",
                "official_text": f"پرسش: {question}\nپاسخ: {answer}",
                "source_url": "",
                "keywords": question[:500],
                "category_id": category_id,
                "source_info": f"پرسش {number}",
                "is_active": True,
            }
            if record is None:
                session.add(LawReferenceRecord(id=record_id, **values))
                created += 1
            else:
                for key, value in values.items():
                    setattr(record, key, value)
                updated += 1
        session.commit()
    return len(items), created, updated


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Import curated tax questions and answers from a DOCX file."
    )
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    if not args.path.is_file():
        raise SystemExit(f"Document not found: {args.path}")
    total, created, updated = import_questions(args.path)
    print(f"parsed={total} created={created} updated={updated}")


if __name__ == "__main__":
    main()
