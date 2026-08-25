"""separate equity components and current result

Revision ID: 0047_financial_equity_reconciliation
Revises: 0046_automatic_financial_summaries
"""
from alembic import op
import sqlalchemy as sa

revision = "0047_financial_equity_reconciliation"
down_revision = "0046_automatic_financial_summaries"
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    field_table = sa.table(
        "financial_statement_fields",
        sa.column("id", sa.String()), sa.column("statement", sa.String()),
        sa.column("title", sa.String()), sa.column("field_type", sa.String()),
        sa.column("formula_json", sa.JSON()), sa.column("sort_order", sa.Integer()),
        sa.column("is_active", sa.Boolean()),
    )
    fields = (
        ("BS.CAPITAL_IN_PROGRESS", "سرمایه در جریان", 71),
        ("BS.LEGAL_RESERVE", "اندوخته قانونی", 72),
        ("BS.OTHER_RESERVES", "سایر اندوخته‌ها", 73),
        ("BS.CURRENT_YEAR_PROFIT_LOSS", "سود (زیان) سال جاری", 81),
    )
    for field_id, title, sort_order in fields:
        exists = connection.execute(
            sa.text("SELECT 1 FROM financial_statement_fields WHERE id=:id"), {"id": field_id}
        ).first()
        if not exists:
            connection.execute(field_table.insert().values(
                id=field_id, statement="BS", title=title, field_type="mapped",
                formula_json={}, sort_order=sort_order, is_active=True,
            ))
    connection.execute(
        field_table.update().where(field_table.c.id == "BS.TOTAL_EQUITY").values(
            formula_json={"sum": [
                "BS.CAPITAL", "BS.CAPITAL_IN_PROGRESS", "BS.LEGAL_RESERVE",
                "BS.OTHER_RESERVES", "BS.RETAINED_EARNINGS",
                "BS.CURRENT_YEAR_PROFIT_LOSS",
            ]}
        )
    )


def downgrade():
    connection = op.get_bind()
    field_table = sa.table(
        "financial_statement_fields", sa.column("id", sa.String()),
        sa.column("formula_json", sa.JSON()),
    )
    connection.execute(
        field_table.update().where(field_table.c.id == "BS.TOTAL_EQUITY").values(
            formula_json={"sum": ["BS.CAPITAL", "BS.RETAINED_EARNINGS"]}
        )
    )
    connection.execute(sa.text("DELETE FROM financial_statement_fields WHERE id IN ('BS.CAPITAL_IN_PROGRESS','BS.LEGAL_RESERVE','BS.OTHER_RESERVES','BS.CURRENT_YEAR_PROFIT_LOSS')"))
