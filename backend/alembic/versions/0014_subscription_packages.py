"""add subscription packages

Revision ID: 0014_subscription_packages
Revises: 0013_site_config_history
"""

from alembic import op
import sqlalchemy as sa


revision = "0014_subscription_packages"
down_revision = "0013_site_config_history"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "user_subscriptions",
        sa.Column("package_code", sa.String(20), nullable=False, server_default="silver"),
    )


def downgrade() -> None:
    op.drop_column("user_subscriptions", "package_code")
