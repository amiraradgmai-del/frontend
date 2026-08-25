"""expand financial statement mapping for finalized ledgers

Revision ID: 0048_professional_financial_mapping
Revises: 0047_financial_equity_reconciliation
"""
from alembic import op
import sqlalchemy as sa

revision = "0048_professional_financial_mapping"
down_revision = "0047_financial_equity_reconciliation"
branch_labels = None
depends_on = None

FIELDS = (
    ("BS.OTHER_RECEIVABLES", "BS", "سایر دریافتنی‌ها", 22),
    ("BS.OTHER_CURRENT_ASSETS", "BS", "سایر دارایی‌های جاری", 37),
    ("BS.TRADE_PAYABLES", "BS", "پرداختنی‌های تجاری", 50),
    ("BS.OTHER_PAYABLES", "BS", "سایر پرداختنی‌ها", 51),
    ("BS.TAX_PAYABLE", "BS", "مالیات پرداختنی", 52),
    ("BS.DIVIDEND_PAYABLE", "BS", "سود سهام پرداختنی", 53),
    ("BS.SHORT_TERM_BORROWINGS", "BS", "تسهیلات مالی کوتاه‌مدت", 54),
    ("BS.PROVISIONS", "BS", "ذخایر جاری", 55),
    ("BS.OTHER_CURRENT_LIABILITIES", "BS", "سایر بدهی‌های جاری", 56),
    ("BS.LONG_TERM_PAYABLES", "BS", "پرداختنی‌های بلندمدت", 60),
    ("BS.LONG_TERM_BORROWINGS", "BS", "تسهیلات مالی بلندمدت", 61),
    ("BS.EMPLOYEE_BENEFITS", "BS", "ذخیره مزایای پایان خدمت کارکنان", 62),
    ("BS.OTHER_NON_CURRENT_LIABILITIES", "BS", "سایر بدهی‌های غیرجاری", 63),
)

def upgrade():
    connection = op.get_bind()
    table = sa.table("financial_statement_fields",
        sa.column("id", sa.String()), sa.column("statement", sa.String()),
        sa.column("title", sa.String()), sa.column("field_type", sa.String()),
        sa.column("formula_json", sa.JSON()), sa.column("sort_order", sa.Integer()),
        sa.column("is_active", sa.Boolean()))
    for field_id, statement, title, sort_order in FIELDS:
        exists = connection.execute(sa.text(
            "SELECT 1 FROM financial_statement_fields WHERE id=:id"), {"id": field_id}).first()
        if not exists:
            connection.execute(table.insert().values(id=field_id, statement=statement,
                title=title, field_type="mapped", formula_json={},
                sort_order=sort_order, is_active=True))
    connection.execute(table.update().where(table.c.id == "BS.TOTAL_ASSETS").values(
        formula_json={"sum": ["BS.CASH", "BS.TRADE_RECEIVABLES", "BS.OTHER_RECEIVABLES",
            "BS.SHORT_TERM_INVESTMENTS", "BS.INVENTORY", "BS.PREPAYMENTS",
            "BS.OTHER_CURRENT_ASSETS", "BS.PPE", "BS.INTANGIBLE_ASSETS",
            "BS.LONG_TERM_INVESTMENTS", "BS.LONG_TERM_RECEIVABLES", "BS.OTHER_ASSETS"]}))
    connection.execute(table.update().where(table.c.id == "BS.TOTAL_LIABILITIES").values(
        formula_json={"sum": ["BS.TRADE_PAYABLES", "BS.OTHER_PAYABLES", "BS.TAX_PAYABLE",
            "BS.DIVIDEND_PAYABLE", "BS.SHORT_TERM_BORROWINGS", "BS.PROVISIONS",
            "BS.OTHER_CURRENT_LIABILITIES", "BS.LONG_TERM_PAYABLES",
            "BS.LONG_TERM_BORROWINGS", "BS.EMPLOYEE_BENEFITS",
            "BS.OTHER_NON_CURRENT_LIABILITIES", "BS.CURRENT_LIABILITIES",
            "BS.NON_CURRENT_LIABILITIES"]}))

def downgrade():
    connection = op.get_bind()
    ids = ",".join("'%s'" % item[0] for item in FIELDS)
    connection.execute(sa.text(f"DELETE FROM financial_statement_fields WHERE id IN ({ids})"))
