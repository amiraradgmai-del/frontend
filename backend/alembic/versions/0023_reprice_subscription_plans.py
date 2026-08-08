"""reprice subscription plans for gemini flash usage

Revision ID: 0023_plan_pricing
Revises: 0022_product_completion
"""

from alembic import op
import sqlalchemy as sa


revision = "0023_plan_pricing"
down_revision = "0022_product_completion"
branch_labels = None
depends_on = None


def upgrade() -> None:
    plans = sa.table(
        "subscription_plans",
        sa.column("code", sa.String),
        sa.column("price", sa.Integer),
    )
    bind = op.get_bind()
    bind.execute(plans.update().where(plans.c.code == "plus").values(price=149_000))
    bind.execute(plans.update().where(plans.c.code == "pro").values(price=549_000))


def downgrade() -> None:
    plans = sa.table(
        "subscription_plans",
        sa.column("code", sa.String),
        sa.column("price", sa.Integer),
    )
    bind = op.get_bind()
    bind.execute(plans.update().where(plans.c.code == "plus").values(price=349_000))
    bind.execute(plans.update().where(plans.c.code == "pro").values(price=899_000))
