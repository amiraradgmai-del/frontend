"""repair corrupted Persian site text

Revision ID: 0024_repair_persian
Revises: 0023_plan_pricing
"""

from copy import deepcopy

from alembic import op
import sqlalchemy as sa


revision = "0024_repair_persian"
down_revision = "0023_plan_pricing"
branch_labels = None
depends_on = None


SEO_DESCRIPTION = "پاسخ ساده، دقیق و هوشمند به پرسش‌های مالیاتی ایران"
SEO_KEYWORDS = "مالیات، قوانین مالیاتی، دستیار مالیاتی، مشاور مالیاتی"


def repaired(configuration: dict) -> dict:
    result = deepcopy(configuration or {})
    seo = dict(result.get("seo") or {})
    if "Ù" in str(seo.get("default_description", "")) or "Ø" in str(seo.get("default_description", "")):
        seo["default_description"] = SEO_DESCRIPTION
    if "Ù" in str(seo.get("keywords", "")) or "Ø" in str(seo.get("keywords", "")):
        seo["keywords"] = SEO_KEYWORDS
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
                draft_json=repaired(row["draft_json"]),
                published_json=repaired(row["published_json"]),
            )
        )


def downgrade() -> None:
    pass
