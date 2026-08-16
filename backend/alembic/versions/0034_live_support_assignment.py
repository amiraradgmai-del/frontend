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
    with op.batch_alter_table("support_tickets") as batch_op:
        batch_op.add_column(sa.Column("assigned_staff_id", sa.String(36)))
        batch_op.create_foreign_key(
            "fk_support_tickets_assigned_staff_id",
            "users",
            ["assigned_staff_id"],
            ["id"],
            ondelete="SET NULL",
        )
    op.create_index("ix_support_tickets_assigned_staff_id", "support_tickets", ["assigned_staff_id"])


def downgrade() -> None:
    op.drop_index("ix_support_tickets_assigned_staff_id", table_name="support_tickets")
    with op.batch_alter_table("support_tickets") as batch_op:
        batch_op.drop_column("assigned_staff_id")
    op.drop_index("ix_users_last_seen_at", table_name="users")
    op.drop_column("users", "last_seen_at")
