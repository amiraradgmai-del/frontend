"""add consultant profile review payload

Revision ID: 0028_consultant_profile_review
Revises: 0027_lively_site_palette
"""

from alembic import op
import sqlalchemy as sa


revision = "0028_consultant_profile_review"
down_revision = "0027_lively_site_palette"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "consultant_verification_requests",
        sa.Column("profile_payload", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
    )


def downgrade() -> None:
    op.drop_column("consultant_verification_requests", "profile_payload")
