"""add verified registration flow

Revision ID: 0007_add_verified_registration
Revises: 0006_add_chunk_embeddings
"""

from alembic import op
import sqlalchemy as sa

revision = "0007_add_verified_registration"
down_revision = "0006_add_chunk_embeddings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True))
    op.create_table(
        "pending_registrations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("first_name", sa.String(length=60), nullable=False),
        sa.Column("last_name", sa.String(length=60), nullable=False),
        sa.Column("code_hash", sa.String(length=64), nullable=False),
        sa.Column("code_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resend_available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("failed_attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("setup_token_hash", sa.String(length=64), nullable=True),
        sa.Column("setup_token_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("setup_token_hash"),
    )
    op.create_index("ix_pending_registrations_email", "pending_registrations", ["email"])
    op.create_index("ix_pending_registrations_code_expires_at", "pending_registrations", ["code_expires_at"])


def downgrade() -> None:
    op.drop_index("ix_pending_registrations_code_expires_at", table_name="pending_registrations")
    op.drop_index("ix_pending_registrations_email", table_name="pending_registrations")
    op.drop_table("pending_registrations")
    op.drop_column("users", "email_verified_at")
