"""Add chunk embeddings.

Revision ID: 0006_add_chunk_embeddings
Revises: 0005_add_consultations
Create Date: 2026-07-15
"""

from alembic import op
import sqlalchemy as sa

revision = "0006_add_chunk_embeddings"
down_revision = "0005_add_consultations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("document_chunks") as batch_op:
        batch_op.add_column(sa.Column("embedding_json", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("embedding_model", sa.String(100), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("document_chunks") as batch_op:
        batch_op.drop_column("embedding_model")
        batch_op.drop_column("embedding_json")
