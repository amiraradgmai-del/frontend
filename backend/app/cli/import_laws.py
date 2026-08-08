from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from sqlalchemy import select

from app.core.config import Settings
from app.db.session import Database
from app.models.portal import LawReferenceRecord, LegalCategory


def rows_from(path: Path):
    if path.suffix.lower() == ".jsonl":
        with path.open(encoding="utf-8") as source:
            for line in source:
                if line.strip():
                    yield json.loads(line)
        return
    with path.open(encoding="utf-8-sig", newline="") as source:
        yield from csv.DictReader(source)


def category_code(law_name: str) -> str:
    title = law_name.replace("\u200c", " ")
    if "ارزش افزوده" in title:
        return "vat"
    if "پایانه" in title or "مودیان" in title or "مؤدیان" in title:
        return "tax-procedure"
    if "مالیات های مستقیم" in title or "مالیات‌های مستقیم" in title:
        return "direct-tax"
    if "بودجه" in title or "برنامه پنجساله" in title:
        return "regulation"
    return "other"


def import_records(path: Path) -> tuple[int, int]:
    database = Database(Settings().database_url)
    created = 0
    updated = 0
    with database.session() as session:
        categories = {item.code: item.id for item in session.scalars(select(LegalCategory)).all()}
        for row in rows_from(path):
            record_id = str(row["record_id"]).strip()
            item = session.get(LawReferenceRecord, record_id)
            values = {
                "source_id": str(row["source_id"]).strip(),
                "law_name": str(row["law_name"]).strip(),
                "chapter": str(row.get("chapter", "")).strip(),
                "article_number": str(row.get("article_number", "")).strip(),
                "official_text": str(row["official_text"]).strip(),
                "source_url": str(row.get("source_url", "")).strip(),
                "keywords": str(row.get("keywords", "")).strip(),
                "category_id": categories.get(category_code(str(row["law_name"]))),
                "source_info": "",
                "is_active": str(row.get("validity_status", "")).strip().lower() != "repealed",
            }
            if item is None:
                session.add(LawReferenceRecord(id=record_id, **values))
                created += 1
            else:
                for key, value in values.items():
                    setattr(item, key, value)
                updated += 1
        session.commit()
    return created, updated


def main() -> None:
    parser = argparse.ArgumentParser(description="Import legal records into the Chaka knowledge base.")
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    if not args.path.is_file():
        raise SystemExit(f"Dataset not found: {args.path}")
    created, updated = import_records(args.path)
    print(f"created={created} updated={updated}")


if __name__ == "__main__":
    main()
