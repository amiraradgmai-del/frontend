"""extend wallet transaction ledger"""

from alembic import op
import sqlalchemy as sa

revision = "0019_wallet_ledger"
down_revision = "0018_consultant_verification"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "wallet_transactions",
        sa.Column("related_type", sa.String(40), nullable=False, server_default=""),
    )
    op.add_column(
        "wallet_transactions", sa.Column("related_id", sa.String(64))
    )
    op.add_column(
        "wallet_transactions",
        sa.Column("failure_reason", sa.Text(), nullable=False, server_default=""),
    )
    op.add_column(
        "wallet_transactions",
        sa.Column("processed_at", sa.DateTime(timezone=True)),
    )
    op.create_index(
        "ix_wallet_transactions_related_id",
        "wallet_transactions",
        ["related_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_wallet_transactions_related_id", table_name="wallet_transactions"
    )
    op.drop_column("wallet_transactions", "processed_at")
    op.drop_column("wallet_transactions", "failure_reason")
    op.drop_column("wallet_transactions", "related_id")
    op.drop_column("wallet_transactions", "related_type")
