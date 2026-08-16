"""add grounded legal metadata

Revision ID: 0043_grounded_legal_metadata
Revises: 0042_security_risk_events
"""

from alembic import op
import sqlalchemy as sa

revision = "0043_grounded_legal_metadata"
down_revision = "0042_security_risk_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = (
        sa.Column("clause", sa.String(80), nullable=False, server_default=""),
        sa.Column("source_type", sa.String(24), nullable=False, server_default="official"),
        sa.Column("legal_status", sa.String(24), nullable=False, server_default="valid"),
        sa.Column("fiscal_year", sa.Integer(), nullable=True),
        sa.Column("approval_date", sa.Date(), nullable=True),
        sa.Column("expiry_date", sa.Date(), nullable=True),
        sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verified_by_user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL", name="fk_law_verified_by"), nullable=True),
        sa.Column("supersedes_record_id", sa.String(80), sa.ForeignKey("law_reference_records.id", ondelete="SET NULL", name="fk_law_supersedes"), nullable=True),
    )
    with op.batch_alter_table("law_reference_records") as batch:
        for column in columns:
            batch.add_column(column)
        for name in ("source_type", "legal_status", "fiscal_year", "last_verified_at", "verified_by_user_id", "supersedes_record_id"):
            batch.create_index(f"ix_law_reference_records_{name}", [name])


def downgrade() -> None:
    with op.batch_alter_table("law_reference_records") as batch:
        for name in ("supersedes_record_id", "verified_by_user_id", "last_verified_at", "fiscal_year", "legal_status", "source_type"):
            batch.drop_index(f"ix_law_reference_records_{name}")
        for name in ("supersedes_record_id", "verified_by_user_id", "last_verified_at", "expiry_date", "approval_date", "fiscal_year", "legal_status", "source_type", "clause"):
            batch.drop_column(name)
