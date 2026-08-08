"""add tools security and reminders

Revision ID: 0010_tools_security
Revises: 0009_add_payment_otp
"""
from alembic import op
import sqlalchemy as sa

revision = "0010_tools_security"
down_revision = "0009_add_payment_otp"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("two_factor_enabled", sa.Boolean(), server_default="false", nullable=False))
    op.create_table(
        "tax_reminders",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.String(1000), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("category", sa.String(40), nullable=False),
        sa.Column("is_done", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("notify_days_before", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_tax_reminders_user_id", "tax_reminders", ["user_id"])
    op.create_index("ix_tax_reminders_due_date", "tax_reminders", ["due_date"])


def downgrade() -> None:
    op.drop_index("ix_tax_reminders_due_date", table_name="tax_reminders")
    op.drop_index("ix_tax_reminders_user_id", table_name="tax_reminders")
    op.drop_table("tax_reminders")
    op.drop_column("users", "two_factor_enabled")
