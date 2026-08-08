"""add automated legal source monitoring

Revision ID: 0021_legal_source_monitor
Revises: 0020_legal_center
"""

from datetime import datetime, timezone
import uuid

from alembic import op
import sqlalchemy as sa

revision = "0021_legal_source_monitor"
down_revision = "0020_legal_center"
branch_labels = None
depends_on = None


SOURCES = [
    ("قانون مالیات‌های مستقیم", "https://regulation.tax.gov.ir/lwvi?lid=txs5000060569&ty=qh"),
    ("قانون مالیات بر ارزش افزوده ۱۴۰۰", "https://regulation.tax.gov.ir/lwvi?lid=txs5000060480&ty=qh"),
    ("قانون پایانه‌های فروشگاهی و سامانه مؤدیان", "https://regulation.tax.gov.ir/lwvi?lid=txs5000060481&ty=qh"),
    ("قانون تسهیل تکالیف مؤدیان", "https://regulation.tax.gov.ir/lwvi?lid=txs5000061625&ty=qh"),
    ("قانون مالیات بر ارزش افزوده ۱۳۸۷", "https://regulation.tax.gov.ir/lwvi?lid=txs5000061766&ty=qh"),
    ("قانون مالیات بر سوداگری و سفته‌بازی", "https://regulation.tax.gov.ir/lwvi?lid=txs5000112488&ty=qh"),
    ("قانون برنامه پنج‌ساله هفتم پیشرفت", "https://regulation.tax.gov.ir/lwvi?lid=txs5000088895&ty=qh"),
    ("قانون بودجه سال ۱۴۰۵", "https://regulation.tax.gov.ir/lwvi?lid=txs5000136402&ty=qh"),
    ("قانون برنامه پنج‌ساله ششم توسعه", "https://regulation.tax.gov.ir/lwvi?lid=txs5000088169&ty=qh"),
    ("قانون بودجه سال ۱۴۰۴", "https://regulation.tax.gov.ir/lwvi?lid=txs5000106321&ty=qh"),
]


def upgrade() -> None:
    op.add_column("legal_external_sources", sa.Column("content_hash", sa.String(64), nullable=False, server_default=""))
    op.add_column("legal_external_sources", sa.Column("last_title", sa.String(300), nullable=False, server_default=""))
    op.add_column("legal_external_sources", sa.Column("last_content_length", sa.Integer(), nullable=False, server_default="0"))
    table = sa.table(
        "legal_external_sources",
        sa.column("id"), sa.column("title"), sa.column("base_url"),
        sa.column("source_type"), sa.column("is_enabled"), sa.column("last_status"),
        sa.column("last_error"), sa.column("content_hash"), sa.column("last_title"),
        sa.column("last_content_length"), sa.column("created_at"),
    )
    now = datetime.now(timezone.utc)
    op.bulk_insert(table, [
        {
            "id": str(uuid.uuid4()), "title": title, "base_url": url,
            "source_type": "official_website", "is_enabled": True,
            "last_status": "not_checked", "last_error": "", "content_hash": "",
            "last_title": "", "last_content_length": 0, "created_at": now,
        }
        for title, url in SOURCES
    ])


def downgrade() -> None:
    op.execute(
        "DELETE FROM legal_external_sources WHERE source_type = 'official_website'"
    )
    op.drop_column("legal_external_sources", "last_content_length")
    op.drop_column("legal_external_sources", "last_title")
    op.drop_column("legal_external_sources", "content_hash")
