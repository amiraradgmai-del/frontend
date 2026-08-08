"""add booking session report

Revision ID: 0039_add_booking_session_report
Revises: 0038_add_optional_profile_email
"""

from alembic import op
import sqlalchemy as sa

revision = "0039_add_booking_session_report"
down_revision = "0038_add_optional_profile_email"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("consultation_bookings") as batch:
        batch.add_column(sa.Column("session_report", sa.Text(), nullable=False, server_default=""))


def downgrade() -> None:
    with op.batch_alter_table("consultation_bookings") as batch:
        batch.drop_column("session_report")
