"""complete user document review workflow

Revision ID: 0044_user_document_workflow
Revises: 0043_grounded_legal_metadata
"""

from alembic import op
import sqlalchemy as sa

revision = "0044_user_document_workflow"
down_revision = "0043_grounded_legal_metadata"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("user_documents") as batch:
        batch.add_column(sa.Column("document_type", sa.String(60), nullable=False, server_default="other"))
        batch.add_column(sa.Column("description", sa.Text(), nullable=False, server_default=""))
        batch.add_column(sa.Column("purpose", sa.String(80), nullable=False, server_default="general_review"))
        batch.add_column(sa.Column("intended_reviewer", sa.String(40), nullable=False, server_default="support"))
        batch.add_column(sa.Column("reviewed_by", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL", name="fk_user_documents_reviewed_by"), nullable=True))
        batch.add_column(sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True))
        for name in ("document_type", "purpose", "intended_reviewer", "reviewed_by"):
            batch.create_index(f"ix_user_documents_{name}", [name])


def downgrade() -> None:
    with op.batch_alter_table("user_documents") as batch:
        for name in ("reviewed_by", "intended_reviewer", "purpose", "document_type"):
            batch.drop_index(f"ix_user_documents_{name}")
        for name in ("reviewed_at", "reviewed_by", "intended_reviewer", "purpose", "description", "document_type"):
            batch.drop_column(name)
