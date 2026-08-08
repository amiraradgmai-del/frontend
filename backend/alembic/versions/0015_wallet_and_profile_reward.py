"""add wallet and profile completion reward

Revision ID: 0015_wallet_profile_reward
Revises: 0014_subscription_packages
"""

from alembic import op
import sqlalchemy as sa


revision = "0015_wallet_profile_reward"
down_revision = "0014_subscription_packages"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("user_profiles", sa.Column("completion_rewarded", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.create_table(
        "wallet_accounts",
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("balance", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "wallet_transactions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("transaction_type", sa.String(20), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("reference", sa.String(40), nullable=False, unique=True),
        sa.Column("otp_hash", sa.String(64), nullable=False),
        sa.Column("otp_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_wallet_transactions_user_id", "wallet_transactions", ["user_id"])
    op.create_index("ix_wallet_transactions_transaction_type", "wallet_transactions", ["transaction_type"])
    op.create_index("ix_wallet_transactions_status", "wallet_transactions", ["status"])
    op.create_index("ix_wallet_transactions_reference", "wallet_transactions", ["reference"])
    op.create_index("ix_wallet_transactions_created_at", "wallet_transactions", ["created_at"])


def downgrade() -> None:
    op.drop_table("wallet_transactions")
    op.drop_table("wallet_accounts")
    op.drop_column("user_profiles", "completion_rewarded")
