"""replace legacy Chaka labels with Chakah

Revision ID: 0026_replace_legacy_chaka_name
Revises: 0025_chakah_branding
"""

from alembic import op
import sqlalchemy as sa


revision = "0026_replace_legacy_chaka_name"
down_revision = "0025_chakah_branding"
branch_labels = None
depends_on = None


def upgrade() -> None:
    legacy_name = "".join(chr(value) for value in (1670, 1705, 1575))
    current_name = legacy_name + chr(1607)
    parameters = {
        "legacy": legacy_name,
        "current": current_name,
        "legacy_pattern": f"%{legacy_name}%",
        "current_pattern": f"%{current_name}%",
    }
    bind = op.get_bind()
    bind.execute(
        sa.text(
            "UPDATE users SET full_name = replace(full_name, :legacy, :current) "
            "WHERE full_name LIKE :legacy_pattern AND full_name NOT LIKE :current_pattern"
        ),
        parameters,
    )
    for column in ("professional_title", "bio"):
        bind.execute(
            sa.text(
                f"UPDATE consultant_profiles SET {column} = replace({column}, :legacy, :current) "
                f"WHERE {column} LIKE :legacy_pattern AND {column} NOT LIKE :current_pattern"
            ),
            parameters,
        )


def downgrade() -> None:
    pass
