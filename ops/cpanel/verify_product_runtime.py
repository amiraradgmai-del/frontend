from __future__ import annotations

import json

from sqlalchemy import func, inspect, select

from app.core.config import get_settings
from app.db.session import Database
from app.documents.storage import EncryptedObjectStorage, create_storage
from app.models.portal import LegalCategory
from app.api.routes.legal import ensure_default_categories


def main() -> None:
    settings = get_settings()
    database = Database(settings.database_url)
    try:
        columns = {item["name"] for item in inspect(database.engine).get_columns("user_documents")}
        with database.session() as session:
            ensure_default_categories(session)
            category_count = session.scalar(select(func.count(LegalCategory.id))) or 0
        print(json.dumps({
            "document_workflow_schema": {"document_type", "description", "purpose", "intended_reviewer", "reviewed_by", "reviewed_at"} <= columns,
            "legal_category_count": category_count,
            "storage_encryption_active": isinstance(create_storage(settings), EncryptedObjectStorage),
        }, sort_keys=True))
    finally:
        database.dispose()


if __name__ == "__main__":
    main()
