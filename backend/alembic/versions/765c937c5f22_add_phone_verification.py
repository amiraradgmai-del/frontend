"""add phone verification

Revision ID: 765c937c5f22
Revises: 0035_ticket_attachments
Create Date: 2026-07-28 09:26:26.779198
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "765c937c5f22"
down_revision: Union[str, None] = "0035_ticket_attachments"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "user_profiles",
        sa.Column(
            "phone_verified",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "user_profiles",
        sa.Column(
            "phone_verified_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    op.create_table(
        "phone_verification_challenges",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("phone", sa.String(length=20), nullable=False),
        sa.Column("code_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "attempts",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_sent_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        op.f("ix_phone_verification_challenges_user_id"),
        "phone_verification_challenges",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_phone_verification_challenges_phone"),
        "phone_verification_challenges",
        ["phone"],
        unique=False,
    )
    op.create_index(
        op.f("ix_phone_verification_challenges_created_at"),
        "phone_verification_challenges",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_phone_verification_challenges_created_at"),
        table_name="phone_verification_challenges",
    )
    op.drop_index(
        op.f("ix_phone_verification_challenges_phone"),
        table_name="phone_verification_challenges",
    )
    op.drop_index(
        op.f("ix_phone_verification_challenges_user_id"),
        table_name="phone_verification_challenges",
    )
    op.drop_table("phone_verification_challenges")

    op.drop_column("user_profiles", "phone_verified_at")
    op.drop_column("user_profiles", "phone_verified")
