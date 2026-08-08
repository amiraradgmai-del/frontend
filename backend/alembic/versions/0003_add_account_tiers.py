"""Add normal, plus and pro account tiers.

Revision ID: 0003_add_account_tiers
Revises: 7202ab9905c7
Create Date: 2026-07-14
"""

from alembic import op
import sqlalchemy as sa

revision = "0003_add_account_tiers"
down_revision = "7202ab9905c7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(
            sa.Column(
                "account_tier",
                sa.String(length=16),
                server_default="normal",
                nullable=False,
            )
        )
        batch_op.create_check_constraint(
            "ck_users_account_tier",
            "account_tier IN ('normal', 'plus', 'pro')",
        )


def downgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_constraint("ck_users_account_tier", type_="check")
        batch_op.drop_column("account_tier")
