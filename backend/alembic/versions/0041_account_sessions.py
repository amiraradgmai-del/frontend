"""add account session metadata

Revision ID: 0041_account_sessions
Revises: 0040_consultant_marketplace
"""

from alembic import op
import sqlalchemy as sa

revision = "0041_account_sessions"
down_revision = "0040_consultant_marketplace"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("refresh_tokens") as batch:
        batch.add_column(sa.Column("device_name", sa.String(160), nullable=False, server_default="دستگاه ناشناس"))
        batch.add_column(sa.Column("user_agent", sa.String(500), nullable=False, server_default=""))
        batch.add_column(sa.Column("ip_address", sa.String(64), nullable=False, server_default=""))
        batch.add_column(sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("refresh_tokens") as batch:
        batch.drop_column("last_used_at")
        batch.drop_column("ip_address")
        batch.drop_column("user_agent")
        batch.drop_column("device_name")
