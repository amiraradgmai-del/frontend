"""complete consultant marketplace

Revision ID: 0040_consultant_marketplace
Revises: 0039_add_booking_session_report
"""

from alembic import op
import sqlalchemy as sa

revision = "0040_consultant_marketplace"
down_revision = "0039_add_booking_session_report"
branch_labels = None
depends_on = None

def upgrade() -> None:
    with op.batch_alter_table("consultant_profiles") as batch:
        batch.add_column(sa.Column("boosted_until", sa.DateTime(timezone=True), nullable=True))
        batch.create_index("ix_consultant_profiles_boosted_until", ["boosted_until"])
    with op.batch_alter_table("consultation_bookings") as batch:
        batch.add_column(sa.Column("cancelled_by", sa.String(20), nullable=False, server_default=""))
        batch.add_column(sa.Column("cancellation_reason", sa.Text(), nullable=False, server_default=""))
        batch.add_column(sa.Column("refund_amount", sa.Integer(), nullable=False, server_default="0"))

def downgrade() -> None:
    with op.batch_alter_table("consultation_bookings") as batch:
        batch.drop_column("refund_amount")
        batch.drop_column("cancellation_reason")
        batch.drop_column("cancelled_by")
    with op.batch_alter_table("consultant_profiles") as batch:
        batch.drop_index("ix_consultant_profiles_boosted_until")
        batch.drop_column("boosted_until")
