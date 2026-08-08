"""apply the dark site palette

Revision ID: 0029_dark_site_palette
Revises: 0028_consultant_profile_review
"""

from copy import deepcopy

from alembic import op
import sqlalchemy as sa


revision = "0029_dark_site_palette"
down_revision = "0028_consultant_profile_review"
branch_labels = None
depends_on = None


def with_dark_palette(configuration: dict) -> dict:
    result = deepcopy(configuration or {})
    theme = dict(result.get("theme") or {})
    theme["primary_color"] = "#5B8CFF"
    theme["accent_color"] = "#8B5CF6"
    theme["background_color"] = "#09090B"
    result["theme"] = theme
    return result


def upgrade() -> None:
    connection = op.get_bind()
    configurations = sa.table(
        "site_configurations",
        sa.column("id", sa.Integer),
        sa.column("draft_json", sa.JSON),
        sa.column("published_json", sa.JSON),
    )
    for row in connection.execute(sa.select(configurations)).mappings():
        connection.execute(
            configurations.update()
            .where(configurations.c.id == row["id"])
            .values(
                draft_json=with_dark_palette(row["draft_json"]),
                published_json=with_dark_palette(row["published_json"]),
            )
        )


def downgrade() -> None:
    pass
