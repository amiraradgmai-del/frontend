"""add financial statement automation

Revision ID: 0043_financial_statements
Revises: 0044_user_document_workflow
"""

from alembic import op
import sqlalchemy as sa

from app.models.financial_statements import (
    AccountMappingDecision, AccountMappingRule, FinancialFiscalYear,
    FinancialOrganization, FinancialStatementAdjustment,
    FinancialStatementField, FinancialStatementImport,
    FinancialStatementImportRow, FinancialStatementRun,
    FinancialStatementTemplate, FinancialStatementTemplateField,
    FinancialStatementValidation, FinancialStatementValue,
    FinancialStatementValueSource, GeneratedFinancialStatementFile,
)

revision = "0043_financial_statements"
down_revision = "0044_user_document_workflow"
branch_labels = None
depends_on = None

TABLES = (
    FinancialOrganization.__table__, FinancialFiscalYear.__table__,
    FinancialStatementImport.__table__, FinancialStatementImportRow.__table__,
    FinancialStatementField.__table__, FinancialStatementTemplate.__table__,
    FinancialStatementTemplateField.__table__, AccountMappingRule.__table__,
    AccountMappingDecision.__table__, FinancialStatementRun.__table__,
    FinancialStatementValue.__table__, FinancialStatementValueSource.__table__,
    FinancialStatementAdjustment.__table__, FinancialStatementValidation.__table__,
    GeneratedFinancialStatementFile.__table__,
)


def upgrade() -> None:
    bind = op.get_bind()
    for table in TABLES:
        table.create(bind, checkfirst=True)
    fields = sa.table("financial_statement_fields", sa.column("id"), sa.column("statement"), sa.column("title"), sa.column("field_type"), sa.column("formula_json", sa.JSON()), sa.column("sort_order"), sa.column("is_active"))
    op.bulk_insert(fields, [
        {"id": "BS.CASH", "statement": "BS", "title": "موجودی نقد", "field_type": "mapped", "formula_json": {}, "sort_order": 10, "is_active": True},
        {"id": "BS.TRADE_RECEIVABLES", "statement": "BS", "title": "دریافتنی‌های تجاری و سایر دریافتنی‌ها", "field_type": "mapped", "formula_json": {}, "sort_order": 20, "is_active": True},
        {"id": "BS.SHORT_TERM_INVESTMENTS", "statement": "BS", "title": "سرمایه‌گذاری‌های کوتاه‌مدت", "field_type": "mapped", "formula_json": {}, "sort_order": 25, "is_active": True},
        {"id": "BS.INVENTORY", "statement": "BS", "title": "موجودی مواد و کالا", "field_type": "mapped", "formula_json": {}, "sort_order": 30, "is_active": True},
        {"id": "BS.PREPAYMENTS", "statement": "BS", "title": "پیش‌پرداخت‌ها", "field_type": "mapped", "formula_json": {}, "sort_order": 35, "is_active": True},
        {"id": "BS.PPE", "statement": "BS", "title": "دارایی‌های ثابت مشهود", "field_type": "mapped", "formula_json": {}, "sort_order": 40, "is_active": True},
        {"id": "BS.INTANGIBLE_ASSETS", "statement": "BS", "title": "دارایی‌های نامشهود", "field_type": "mapped", "formula_json": {}, "sort_order": 42, "is_active": True},
        {"id": "BS.LONG_TERM_INVESTMENTS", "statement": "BS", "title": "سرمایه‌گذاری‌های بلندمدت", "field_type": "mapped", "formula_json": {}, "sort_order": 44, "is_active": True},
        {"id": "BS.LONG_TERM_RECEIVABLES", "statement": "BS", "title": "دریافتنی‌های بلندمدت", "field_type": "mapped", "formula_json": {}, "sort_order": 46, "is_active": True},
        {"id": "BS.OTHER_ASSETS", "statement": "BS", "title": "سایر دارایی‌ها", "field_type": "mapped", "formula_json": {}, "sort_order": 48, "is_active": True},
        {"id": "BS.CURRENT_LIABILITIES", "statement": "BS", "title": "بدهی‌های جاری", "field_type": "mapped", "formula_json": {}, "sort_order": 50, "is_active": True},
        {"id": "BS.NON_CURRENT_LIABILITIES", "statement": "BS", "title": "بدهی‌های غیرجاری", "field_type": "mapped", "formula_json": {}, "sort_order": 60, "is_active": True},
        {"id": "BS.CAPITAL", "statement": "BS", "title": "سرمایه", "field_type": "mapped", "formula_json": {}, "sort_order": 70, "is_active": True},
        {"id": "BS.RETAINED_EARNINGS", "statement": "BS", "title": "سود و زیان انباشته", "field_type": "mapped", "formula_json": {}, "sort_order": 80, "is_active": True},
        {"id": "BS.TOTAL_ASSETS", "statement": "BS", "title": "جمع دارایی‌ها", "field_type": "derived", "formula_json": {"sum": ["BS.CASH", "BS.TRADE_RECEIVABLES", "BS.SHORT_TERM_INVESTMENTS", "BS.INVENTORY", "BS.PREPAYMENTS", "BS.PPE", "BS.INTANGIBLE_ASSETS", "BS.LONG_TERM_INVESTMENTS", "BS.LONG_TERM_RECEIVABLES", "BS.OTHER_ASSETS"]}, "sort_order": 90, "is_active": True},
        {"id": "BS.TOTAL_LIABILITIES", "statement": "BS", "title": "جمع بدهی‌ها", "field_type": "derived", "formula_json": {"sum": ["BS.CURRENT_LIABILITIES", "BS.NON_CURRENT_LIABILITIES"]}, "sort_order": 91, "is_active": True},
        {"id": "BS.TOTAL_EQUITY", "statement": "BS", "title": "جمع حقوق مالکانه", "field_type": "derived", "formula_json": {"sum": ["BS.CAPITAL", "BS.RETAINED_EARNINGS"]}, "sort_order": 92, "is_active": True},
        {"id": "BS.TOTAL_LIABILITIES_EQUITY", "statement": "BS", "title": "جمع بدهی‌ها و حقوق مالکانه", "field_type": "derived", "formula_json": {"sum": ["BS.TOTAL_LIABILITIES", "BS.TOTAL_EQUITY"]}, "sort_order": 93, "is_active": True},
        {"id": "PL.OPERATING_REVENUE", "statement": "PL", "title": "درآمدهای عملیاتی", "field_type": "mapped", "formula_json": {}, "sort_order": 110, "is_active": True},
        {"id": "PL.COST_OF_REVENUE", "statement": "PL", "title": "بهای تمام‌شده درآمدهای عملیاتی", "field_type": "mapped", "formula_json": {}, "sort_order": 120, "is_active": True},
        {"id": "PL.GROSS_PROFIT", "statement": "PL", "title": "سود ناخالص", "field_type": "derived", "formula_json": {"subtract": ["PL.OPERATING_REVENUE", "PL.COST_OF_REVENUE"]}, "sort_order": 130, "is_active": True},
        {"id": "PL.SELLING_ADMIN_EXPENSE", "statement": "PL", "title": "هزینه‌های فروش، اداری و عمومی", "field_type": "mapped", "formula_json": {}, "sort_order": 140, "is_active": True},
        {"id": "PL.IMPAIRMENT_EXPENSE", "statement": "PL", "title": "هزینه کاهش ارزش", "field_type": "mapped", "formula_json": {}, "sort_order": 145, "is_active": True},
        {"id": "PL.OTHER_INCOME", "statement": "PL", "title": "سایر درآمدها", "field_type": "mapped", "formula_json": {}, "sort_order": 150, "is_active": True},
        {"id": "PL.OTHER_EXPENSE", "statement": "PL", "title": "سایر هزینه‌ها", "field_type": "mapped", "formula_json": {}, "sort_order": 155, "is_active": True},
        {"id": "PL.OPERATING_PROFIT", "statement": "PL", "title": "سود عملیاتی", "field_type": "derived", "formula_json": {"add_subtract": {"add": ["PL.GROSS_PROFIT", "PL.OTHER_INCOME"], "subtract": ["PL.SELLING_ADMIN_EXPENSE", "PL.IMPAIRMENT_EXPENSE", "PL.OTHER_EXPENSE"]}}, "sort_order": 160, "is_active": True},
        {"id": "PL.FINANCE_COST", "statement": "PL", "title": "هزینه‌های مالی", "field_type": "mapped", "formula_json": {}, "sort_order": 165, "is_active": True},
        {"id": "PL.PROFIT_BEFORE_TAX", "statement": "PL", "title": "سود قبل از مالیات", "field_type": "derived", "formula_json": {"subtract": ["PL.OPERATING_PROFIT", "PL.FINANCE_COST"]}, "sort_order": 170, "is_active": True},
        {"id": "PL.INCOME_TAX", "statement": "PL", "title": "مالیات بر درآمد", "field_type": "mapped", "formula_json": {}, "sort_order": 180, "is_active": True},
        {"id": "PL.NET_PROFIT", "statement": "PL", "title": "سود خالص", "field_type": "derived", "formula_json": {"subtract": ["PL.PROFIT_BEFORE_TAX", "PL.INCOME_TAX"]}, "sort_order": 190, "is_active": True},
        {"id": "CI.MANUAL", "statement": "CI", "title": "سود و زیان جامع", "field_type": "manual_required", "formula_json": {}, "sort_order": 210, "is_active": True},
        {"id": "EQ.MANUAL", "statement": "EQ", "title": "تغییرات حقوق مالکانه", "field_type": "manual_required", "formula_json": {}, "sort_order": 310, "is_active": True},
        {"id": "CF.MANUAL", "statement": "CF", "title": "جریان‌های نقدی", "field_type": "manual_required", "formula_json": {}, "sort_order": 410, "is_active": True},
    ])
    rules = sa.table("account_mapping_rules", *[sa.column(name, sa.JSON()) if name == "keywords_json" else sa.column(name) for name in ("id","organization_id","name","source_level","source_code","source_code_prefix","source_name","normalized_source_name","keywords_json","target_statement","target_field_id","amount_source","sign_multiplier","priority","confidence","is_global","is_active","created_by","created_at","updated_at")])
    now = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
    op.bulk_insert(rules, [
        {"id":"seed-cash-1110","organization_id":None,"name":"موجودی نقد و بانک","source_level":"any","source_code":"1110","source_code_prefix":"1110","source_name":"موجودی نقد و بانک","normalized_source_name":"موجودی نقد و بانک","keywords_json":["موجودی","بانک"],"target_statement":"BS","target_field_id":"BS.CASH","amount_source":"net_closing","sign_multiplier":1,"priority":100,"confidence":100,"is_global":True,"is_active":True,"created_by":None,"created_at":now,"updated_at":now},
        {"id":"seed-receivable-1112","organization_id":None,"name":"حساب‌ها و اسناد دریافتنی","source_level":"any","source_code":"1112","source_code_prefix":"1112","source_name":"حساب‌ها و اسناد دریافتنی","normalized_source_name":"حساب ها و اسناد دریافتنی","keywords_json":["دریافتنی"],"target_statement":"BS","target_field_id":"BS.TRADE_RECEIVABLES","amount_source":"net_closing","sign_multiplier":1,"priority":100,"confidence":100,"is_global":True,"is_active":True,"created_by":None,"created_at":now,"updated_at":now},
    ])


def downgrade() -> None:
    bind = op.get_bind()
    for table in reversed(TABLES):
        table.drop(bind, checkfirst=True)
