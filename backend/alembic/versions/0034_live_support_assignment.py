"""live support assignment

Revision ID: 0034_live_support_assignment
Revises: 0033_content_and_contracts
"""

from alembic import op
import sqlalchemy as sa

revision = "0034_live_support_assignment"
down_revision = "0033_content_and_contracts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("last_seen_at", sa.DateTime(timezone=True)))
    op.create_index("ix_users_last_seen_at", "users", ["last_seen_at"])
    op.add_column("support_tickets", sa.Column("assigned_staff_id", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL")))
    op.create_index("ix_support_tickets_assigned_staff_id", "support_tickets", ["assigned_staff_id"])


def downgrade() -> None:
    op.drop_index("ix_support_tickets_assigned_staff_id", table_name="support_tickets")
    op.drop_column("support_tickets", "assigned_staff_id")
    op.drop_index("ix_users_last_seen_at", table_name="users")
    op.drop_column("users", "last_seen_at")
