"""harden site configuration history

Revision ID: 0013_site_config_history
Revises: 0012_roles_site_config
"""

import uuid

from alembic import op
import sqlalchemy as sa


revision = "0013_site_config_history"
down_revision = "0012_roles_site_config"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    configuration = connection.execute(
        sa.text("SELECT published_json FROM site_configurations WHERE id = 1")
    ).scalar_one_or_none()
    if configuration is not None:
        exists = connection.execute(
            sa.text("SELECT 1 FROM site_configuration_versions WHERE version = 1 LIMIT 1")
        ).scalar_one_or_none()
        if exists is None:
            connection.execute(
                sa.text("INSERT INTO site_configuration_versions (id, version, configuration_json, note, created_at) VALUES (:id, 1, :configuration, :note, CURRENT_TIMESTAMP)").bindparams(
                    sa.bindparam("configuration", type_=sa.JSON())
                ),
                {
                    "id": str(uuid.uuid4()),
                    "configuration": configuration,
                    "note": "نسخه اولیه سامانه",
                },
            )


def downgrade() -> None:
    op.execute(
        sa.text("DELETE FROM site_configuration_versions WHERE version = 1 AND note = :note").bindparams(
            note="نسخه اولیه سامانه"
        )
    )
