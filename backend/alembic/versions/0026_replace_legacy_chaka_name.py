"""replace legacy Chaka labels with Chakah

Revision ID: 0026_replace_legacy_chaka_name
Revises: 0025_chakah_branding
"""

from alembic import op


revision = "0026_replace_legacy_chaka_name"
down_revision = "0025_chakah_branding"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        WITH brand AS (
            SELECT
                chr(1670) || chr(1705) || chr(1575) AS legacy_name,
                chr(1670) || chr(1705) || chr(1575) || chr(1607) AS current_name
        )
        UPDATE users
        SET full_name = replace(full_name, brand.legacy_name, brand.current_name)
        FROM brand
        WHERE
            strpos(full_name, brand.legacy_name) > 0
            AND strpos(full_name, brand.current_name) = 0
        """
    )
    op.execute(
        """
        WITH brand AS (
            SELECT
                chr(1670) || chr(1705) || chr(1575) AS legacy_name,
                chr(1670) || chr(1705) || chr(1575) || chr(1607) AS current_name
        )
        UPDATE consultant_profiles
        SET
            professional_title = replace(professional_title, brand.legacy_name, brand.current_name),
            bio = replace(bio, brand.legacy_name, brand.current_name)
        FROM brand
        WHERE
            (
                strpos(professional_title, brand.legacy_name) > 0
                AND strpos(professional_title, brand.current_name) = 0
            )
            OR (
                strpos(bio, brand.legacy_name) > 0
                AND strpos(bio, brand.current_name) = 0
            )
        """
    )


def downgrade() -> None:
    pass
