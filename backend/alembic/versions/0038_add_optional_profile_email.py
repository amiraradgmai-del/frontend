"""add optional profile email

Revision ID: 0038_add_optional_profile_email
Revises: 0037_expand_user_profiles
"""

from alembic import op
import sqlalchemy as sa

revision = "0038_add_optional_profile_email"
down_revision = "0037_expand_user_profiles"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("user_profiles") as batch:
        batch.add_column(sa.Column("alternate_email", sa.String(320), nullable=False, server_default=""))


def downgrade() -> None:
    with op.batch_alter_table("user_profiles") as batch:
        batch.drop_column("alternate_email")
