"""apply Chakah branding and official logo

Revision ID: 0025_chakah_branding
Revises: 0024_repair_persian
"""

from copy import deepcopy

from alembic import op
import sqlalchemy as sa


revision = "0025_chakah_branding"
down_revision = "0024_repair_persian"
branch_labels = None
depends_on = None


def branded(configuration: dict) -> dict:
    result = deepcopy(configuration or {})
    branding = dict(result.get("branding") or {})
    branding["site_name"] = "چکاه"
    branding["logo_url"] = "/brand/chakah-logo.png"
    result["branding"] = branding
    seo = dict(result.get("seo") or {})
    seo["default_title"] = "چکاه | دستیار هوشمند مالیاتی"
    result["seo"] = seo
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
                draft_json=branded(row["draft_json"]),
                published_json=branded(row["published_json"]),
            )
        )


def downgrade() -> None:
    pass
