from __future__ import annotations

from pathlib import Path

from sqlalchemy import select

import app.models  # noqa: F401
from app.bootstrap import bootstrap_admin
from app.core.config import get_settings
from app.db.base import Base
from app.db.session import Database
from app.models.portal import SubscriptionPlan
from app.repositories.auth import seed_rbac


PLANS = (
    {
        "id": "plan-normal",
        "code": "normal",
        "title": "عادی",
        "description": "برای شروع و استفاده روزمره",
        "price": 0,
        "duration_days": 3650,
        "benefits": ["۱۰ پرسش در ماه", "۵ جست‌وجوی قانون", "۱۰ محاسبه", "۱ نامه", "تقویم نامحدود"],
        "is_active": True,
        "sort_order": 1,
    },
    {
        "id": "plan-plus",
        "code": "plus",
        "title": "پلاس",
        "description": "برای مؤدیان و کسب‌وکارهای کوچک",
        "price": 149_000,
        "duration_days": 30,
        "benefits": ["۱۰۰ پرسش در ماه", "۱۰۰ جست‌وجوی قانون", "۵ سند", "۲ درخواست مشاور"],
        "is_active": True,
        "sort_order": 2,
    },
    {
        "id": "plan-pro",
        "code": "pro",
        "title": "حرفه‌ای",
        "description": "برای شرکت‌ها و متخصصان مالی",
        "price": 549_000,
        "duration_days": 30,
        "benefits": ["۱۰۰۰ پرسش در ماه", "۱۰۰۰ جست‌وجوی قانون", "۲۰ سند", "۱۰ درخواست مشاور"],
        "is_active": True,
        "sort_order": 3,
    },
)


def main() -> None:
    settings = get_settings()
    if settings.database_url.startswith("sqlite:////"):
        database_path = Path("/" + settings.database_url.removeprefix("sqlite:////"))
        database_path.parent.mkdir(parents=True, exist_ok=True)
    if settings.storage_backend == "local":
        Path(settings.local_storage_path).mkdir(parents=True, exist_ok=True)
    database = Database(settings.database_url)
    Base.metadata.create_all(database.engine)
    with database.session() as session:
        seed_rbac(session)
        for payload in PLANS:
            if session.scalar(select(SubscriptionPlan).where(SubscriptionPlan.code == payload["code"])) is None:
                session.add(SubscriptionPlan(**payload))
        session.commit()
        bootstrap_admin(session, settings)
    database.dispose()


if __name__ == "__main__":
    main()
