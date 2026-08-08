"""restore the light site palette

Revision ID: 0030_restore_light_palette
Revises: 0029_dark_site_palette
"""

from copy import deepcopy

from alembic import op
import sqlalchemy as sa


revision = "0030_restore_light_palette"
down_revision = "0029_dark_site_palette"
branch_labels = None
depends_on = None


def with_light_palette(configuration: dict) -> dict:
    result = deepcopy(configuration or {})
    theme = dict(result.get("theme") or {})
    theme["primary_color"] = "#2563eb"
    theme["accent_color"] = "#f97316"
    theme["background_color"] = "#fffaf5"
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
                draft_json=with_light_palette(row["draft_json"]),
                published_json=with_light_palette(row["published_json"]),
            )
        )


def downgrade() -> None:
    pass
