"""expand user profiles

Revision ID: 0037_expand_user_profiles
Revises: de9a2fbc69cb
Create Date: 2026-08-01
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0037_expand_user_profiles"
down_revision: str | Sequence[str] | None = "de9a2fbc69cb"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("user_profiles") as batch:
        batch.add_column(sa.Column("alternate_phone", sa.String(20), nullable=False, server_default=""))
        batch.add_column(sa.Column("postal_code", sa.String(10), nullable=False, server_default=""))
        batch.add_column(sa.Column("address", sa.String(500), nullable=False, server_default=""))
        batch.add_column(sa.Column("birth_date", sa.Date(), nullable=True))
        batch.add_column(sa.Column("business_type", sa.String(80), nullable=False, server_default=""))
        batch.add_column(sa.Column("economic_code", sa.String(20), nullable=False, server_default=""))
        batch.add_column(sa.Column("website", sa.String(300), nullable=False, server_default=""))
        batch.add_column(sa.Column("preferred_contact_method", sa.String(20), nullable=False, server_default="phone"))
        batch.add_column(sa.Column("marketing_notifications", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch.add_column(sa.Column("service_notifications", sa.Boolean(), nullable=False, server_default=sa.true()))


def downgrade() -> None:
    with op.batch_alter_table("user_profiles") as batch:
        for column in (
            "service_notifications", "marketing_notifications", "preferred_contact_method",
            "website", "economic_code", "business_type", "birth_date", "address",
            "postal_code", "alternate_phone",
        ):
            batch.drop_column(column)
