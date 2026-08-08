"""add real payment gateway fields

Revision ID: 0036_zarinpal_gateway
Revises: 0035_ticket_attachments
"""

from alembic import op
import sqlalchemy as sa


revision = "0036_zarinpal_gateway"
down_revision = "0035_ticket_attachments"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("payments", sa.Column("gateway_name", sa.String(length=30), server_default="internal", nullable=False))
    op.add_column("payments", sa.Column("gateway_authority", sa.String(length=100), nullable=True))
    op.add_column("payments", sa.Column("package_code", sa.String(length=20), server_default="silver", nullable=False))
    op.add_column("payments", sa.Column("card_pan", sa.String(length=40), nullable=True))
    op.add_column("payments", sa.Column("card_hash", sa.String(length=128), nullable=True))
    op.add_column("payments", sa.Column("failure_reason", sa.String(length=500), nullable=True))
    op.create_index("ix_payments_gateway_authority", "payments", ["gateway_authority"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_payments_gateway_authority", table_name="payments")
    op.drop_column("payments", "failure_reason")
    op.drop_column("payments", "card_hash")
    op.drop_column("payments", "card_pan")
    op.drop_column("payments", "package_code")
    op.drop_column("payments", "gateway_authority")
    op.drop_column("payments", "gateway_name")
