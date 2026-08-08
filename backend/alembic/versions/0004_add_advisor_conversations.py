"""Add advisor conversations, citations and feedback.

Revision ID: 0004_add_advisor_conversations
Revises: f1d3869b502b
Create Date: 2026-07-15
"""

from alembic import op
import sqlalchemy as sa

revision = "0004_add_advisor_conversations"
down_revision = "f1d3869b502b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "conversations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(160), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_conversations_user_id", "conversations", ["user_id"])
    op.create_table(
        "chat_messages",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("conversation_id", sa.String(36), sa.ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float()),
        sa.Column("needs_expert", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("disclaimer", sa.String(500)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("role IN ('user','assistant')", name="ck_chat_messages_role"),
    )
    op.create_index("ix_chat_messages_conversation_id", "chat_messages", ["conversation_id"])
    op.create_table(
        "message_citations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("message_id", sa.String(36), sa.ForeignKey("chat_messages.id", ondelete="CASCADE"), nullable=False),
        sa.Column("chunk_id", sa.String(36), sa.ForeignKey("document_chunks.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("quote", sa.Text(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
    )
    op.create_index("ix_message_citations_message_id", "message_citations", ["message_id"])
    op.create_index("ix_message_citations_chunk_id", "message_citations", ["chunk_id"])
    op.create_table(
        "message_feedback",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("message_id", sa.String(36), sa.ForeignKey("chat_messages.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("rating", sa.String(20), nullable=False),
        sa.Column("comment", sa.String(1000), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("rating IN ('helpful','not_helpful')", name="ck_message_feedback_rating"),
        sa.UniqueConstraint("message_id", "user_id", name="uq_message_feedback_user"),
    )
    op.create_index("ix_message_feedback_message_id", "message_feedback", ["message_id"])
    op.create_index("ix_message_feedback_user_id", "message_feedback", ["user_id"])
    op.create_table(
        "retrieval_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("message_id", sa.String(36), sa.ForeignKey("chat_messages.id", ondelete="CASCADE"), nullable=False),
        sa.Column("chunk_id", sa.String(36), sa.ForeignKey("document_chunks.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("selected", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.create_index("ix_retrieval_logs_message_id", "retrieval_logs", ["message_id"])
    op.create_index("ix_retrieval_logs_chunk_id", "retrieval_logs", ["chunk_id"])


def downgrade() -> None:
    op.drop_table("retrieval_logs")
    op.drop_table("message_feedback")
    op.drop_table("message_citations")
    op.drop_table("chat_messages")
    op.drop_table("conversations")
