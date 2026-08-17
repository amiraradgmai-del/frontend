"""add legal center

Revision ID: 0020_legal_center
Revises: 0019_wallet_ledger
"""

from alembic import op
import sqlalchemy as sa

revision = "0020_legal_center"
down_revision = "0019_wallet_ledger"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "legal_categories",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("title", sa.String(120), nullable=False),
        sa.Column("description", sa.String(500), nullable=False, server_default=""),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_legal_categories_code", "legal_categories", ["code"], unique=True)
    op.create_table(
        "legal_external_sources",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("base_url", sa.String(1000), nullable=False),
        sa.Column("source_type", sa.String(40), nullable=False, server_default="website"),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_checked_at", sa.DateTime(timezone=True)),
        sa.Column("last_status", sa.String(30), nullable=False, server_default="not_checked"),
        sa.Column("last_error", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_legal_external_sources_is_enabled", "legal_external_sources", ["is_enabled"])
    op.create_table(
        "legal_update_candidates",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("source_id", sa.String(36), sa.ForeignKey("legal_external_sources.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("article_number", sa.String(50), nullable=False, server_default=""),
        sa.Column("proposed_text", sa.Text(), nullable=False),
        sa.Column("source_url", sa.String(1000), nullable=False, server_default=""),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="pending"),
        sa.Column("reviewer_user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("review_note", sa.Text(), nullable=False, server_default=""),
        sa.Column("reviewed_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_legal_update_candidates_source_id", "legal_update_candidates", ["source_id"])
    op.create_index("ix_legal_update_candidates_status", "legal_update_candidates", ["status"])
    with op.batch_alter_table("law_reference_records") as batch_op:
        batch_op.add_column(sa.Column("category_id", sa.String(36)))
        batch_op.add_column(sa.Column("publication_date", sa.Date()))
        batch_op.add_column(sa.Column("effective_date", sa.Date()))
        batch_op.add_column(sa.Column("source_info", sa.String(500), nullable=False, server_default=""))
        batch_op.add_column(sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()))
        batch_op.add_column(sa.Column("archived_at", sa.DateTime(timezone=True)))
        batch_op.add_column(sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
        batch_op.create_foreign_key(
            "fk_law_reference_records_category_id",
            "legal_categories",
            ["category_id"],
            ["id"],
            ondelete="SET NULL",
        )
    op.create_index("ix_law_reference_records_category_id", "law_reference_records", ["category_id"])
    op.create_index("ix_law_reference_records_is_active", "law_reference_records", ["is_active"])
    categories = [
        ("direct-tax", "مالیات‌های مستقیم", 10), ("vat", "مالیات بر ارزش افزوده", 20),
        ("tax-procedure", "دادرسی و آیین مالیاتی", 30), ("insurance", "بیمه و تأمین اجتماعی", 40),
        ("commercial", "قوانین تجاری", 50), ("labor", "قانون کار", 60),
        ("accounting", "حسابداری و گزارشگری", 70), ("circular", "بخشنامه‌ها", 80),
        ("regulation", "آیین‌نامه‌ها", 90), ("directive", "دستورالعمل‌ها", 100), ("other", "سایر", 110),
    ]
    category_table = sa.table("legal_categories", sa.column("id"), sa.column("code"), sa.column("title"), sa.column("description"), sa.column("sort_order"), sa.column("is_active"), sa.column("created_at"))
    from datetime import datetime, timezone
    import uuid
    now = datetime.now(timezone.utc)
    op.bulk_insert(category_table, [{"id": str(uuid.uuid4()), "code": code, "title": title, "description": "", "sort_order": order, "is_active": True, "created_at": now} for code, title, order in categories])


def downgrade() -> None:
    op.drop_index("ix_law_reference_records_is_active", table_name="law_reference_records")
    op.drop_index("ix_law_reference_records_category_id", table_name="law_reference_records")
    with op.batch_alter_table("law_reference_records") as batch_op:
        for column in ("updated_at", "archived_at", "is_active", "source_info", "effective_date", "publication_date", "category_id"):
            batch_op.drop_column(column)
    op.drop_table("legal_update_candidates")
    op.drop_table("legal_external_sources")
    op.drop_table("legal_categories")
