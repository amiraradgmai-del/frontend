"""Add consultation workflow.

Revision ID: 0005_add_consultations
Revises: 0004_add_advisor_conversations
Create Date: 2026-07-15
"""

from alembic import op
import sqlalchemy as sa

revision = "0005_add_consultations"
down_revision = "0004_add_advisor_conversations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "consultation_requests",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_message_id", sa.String(36), sa.ForeignKey("chat_messages.id", ondelete="SET NULL")),
        sa.Column("assigned_to", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("subject", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", sa.String(30), server_default="submitted", nullable=False),
        sa.Column("priority", sa.String(10), server_default="normal", nullable=False),
        sa.Column("internal_note", sa.Text(), nullable=False),
        sa.Column("resolution", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("status IN ('submitted','in_review','waiting_for_user','resolved','closed')", name="ck_consultation_requests_status"),
        sa.CheckConstraint("priority IN ('normal','high')", name="ck_consultation_requests_priority"),
    )
    op.create_index("ix_consultation_requests_user_id", "consultation_requests", ["user_id"])
    op.create_index("ix_consultation_requests_assigned_to", "consultation_requests", ["assigned_to"])
    op.create_table(
        "consultation_status_history",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("consultation_id", sa.String(36), sa.ForeignKey("consultation_requests.id", ondelete="CASCADE"), nullable=False),
        sa.Column("changed_by", sa.String(36), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("from_status", sa.String(30)),
        sa.Column("to_status", sa.String(30), nullable=False),
        sa.Column("note", sa.String(1000), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_consultation_status_history_consultation_id", "consultation_status_history", ["consultation_id"])


def downgrade() -> None:
    op.drop_table("consultation_status_history")
    op.drop_table("consultation_requests")
