"""complete consultant operations

Revision ID: 0031_consultant_operations
Revises: 0030_restore_light_palette
"""

from alembic import op
import sqlalchemy as sa


revision = "0031_consultant_operations"
down_revision = "0030_restore_light_palette"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("must_change_password", sa.Boolean(), server_default=sa.false(), nullable=False))
    op.add_column("consultant_profiles", sa.Column("bank_account_holder", sa.String(120), server_default="", nullable=False))
    op.add_column("consultant_profiles", sa.Column("bank_iban", sa.String(34), server_default="", nullable=False))
    op.add_column("consultant_profiles", sa.Column("blocked_until", sa.DateTime(timezone=True), nullable=True))
    op.add_column("consultant_profiles", sa.Column("blocked_reason", sa.Text(), server_default="", nullable=False))
    op.add_column("consultant_profiles", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_consultant_profiles_deleted_at", "consultant_profiles", ["deleted_at"])
    op.add_column("consultant_reviews", sa.Column("moderation_status", sa.String(20), server_default="published", nullable=False))
    op.create_index("ix_consultant_reviews_moderation_status", "consultant_reviews", ["moderation_status"])
    op.create_table(
        "consultant_settlements",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("consultant_id", sa.String(36), sa.ForeignKey("consultant_profiles.user_id", ondelete="CASCADE"), nullable=False),
        sa.Column("gross_amount", sa.Integer(), nullable=False),
        sa.Column("platform_fee", sa.Integer(), nullable=False),
        sa.Column("payable_amount", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), server_default="pending", nullable=False),
        sa.Column("bank_iban_snapshot", sa.String(34), server_default="", nullable=False),
        sa.Column("reference", sa.String(100), server_default="", nullable=False),
        sa.Column("admin_note", sa.Text(), server_default="", nullable=False),
        sa.Column("created_by", sa.String(36), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("paid_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("status IN ('pending','paid','rejected')", name="ck_consultant_settlements_status"),
    )
    op.create_index("ix_consultant_settlements_consultant_id", "consultant_settlements", ["consultant_id"])
    op.create_index("ix_consultant_settlements_status", "consultant_settlements", ["status"])


def downgrade() -> None:
    op.drop_table("consultant_settlements")
    op.drop_index("ix_consultant_reviews_moderation_status", table_name="consultant_reviews")
    op.drop_column("consultant_reviews", "moderation_status")
    op.drop_index("ix_consultant_profiles_deleted_at", table_name="consultant_profiles")
    for column in ("deleted_at", "blocked_reason", "blocked_until", "bank_iban", "bank_account_holder"):
        op.drop_column("consultant_profiles", column)
    op.drop_column("users", "must_change_password")
