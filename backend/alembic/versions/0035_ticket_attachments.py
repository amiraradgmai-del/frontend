"""ticket attachments

Revision ID: 0035_ticket_attachments
Revises: 0034_live_support_assignment
"""
from alembic import op
import sqlalchemy as sa

revision = "0035_ticket_attachments"
down_revision = "0034_live_support_assignment"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column("ticket_messages", sa.Column("attachment_name", sa.String(255), server_default="", nullable=False))
    op.add_column("ticket_messages", sa.Column("attachment_key", sa.String(500), server_default="", nullable=False))
    op.add_column("ticket_messages", sa.Column("attachment_mime", sa.String(100), server_default="", nullable=False))

def downgrade() -> None:
    op.drop_column("ticket_messages", "attachment_mime")
    op.drop_column("ticket_messages", "attachment_key")
    op.drop_column("ticket_messages", "attachment_name")
