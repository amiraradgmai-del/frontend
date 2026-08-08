"""add sandbox payment otp challenges

Revision ID: 0009_add_payment_otp
Revises: 0008_add_customer_portal
"""
from alembic import op
import sqlalchemy as sa

revision = "0009_add_payment_otp"
down_revision = "0008_add_customer_portal"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "payment_otp_challenges",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("plan_code", sa.String(20), nullable=False),
        sa.Column("payment_method_id", sa.String(36), sa.ForeignKey("payment_methods.id", ondelete="CASCADE"), nullable=False),
        sa.Column("discount_code", sa.String(32), nullable=False),
        sa.Column("otp_hash", sa.String(64), nullable=False),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_payment_otp_challenges_user_id", "payment_otp_challenges", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_payment_otp_challenges_user_id", table_name="payment_otp_challenges")
    op.drop_table("payment_otp_challenges")
