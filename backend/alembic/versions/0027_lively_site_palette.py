"""apply the lively site palette

Revision ID: 0027_lively_site_palette
Revises: 0026_replace_legacy_chaka_name
"""

from copy import deepcopy

from alembic import op
import sqlalchemy as sa


revision = "0027_lively_site_palette"
down_revision = "0026_replace_legacy_chaka_name"
branch_labels = None
depends_on = None


def with_lively_palette(configuration: dict) -> dict:
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
                draft_json=with_lively_palette(row["draft_json"]),
                published_json=with_lively_palette(row["published_json"]),
            )
        )


def downgrade() -> None:
    pass
