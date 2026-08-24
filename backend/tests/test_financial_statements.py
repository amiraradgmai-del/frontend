from decimal import Decimal
from io import BytesIO

from openpyxl import Workbook
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.financial_statements import *
from app.services.financial_statements import (
    AccountMappingService, ExcelTrialBalanceParser,
    FinancialStatementCalculationService, convert_money, extract_account,
    normalize_persian_financial, normalized_account_name, parse_amount,
)


def excel_bytes() -> bytes:
    workbook = Workbook(); sheet = workbook.active
    sheet.append(["گزارش تراز شش ستونی"])
    sheet.append(["کل", "معین", "تفصیلی", "بدهکار اول دوره", "بستانکار اول دوره", "بدهکار طی دوره", "بستانکار طی دوره", "مانده بدهکار", "مانده بستانکار"])
    sheet.append(["1110 - موجودی نقد و بانک", "111003 - تنخواه گردان", "", 0, 0, 10_000_000, 0, 10_000_000, 0])
    sheet.append(["", "111005 - بانک ریالی", "بانک ملت", 0, 0, 50_000_000, 0, 50_000_000, 0])
    output = BytesIO(); workbook.save(output); return output.getvalue()


def test_persian_normalization_account_and_amount():
    assert normalized_account_name(" موجودي نقد‌ وبانك ") == "موجودی نقد وبانک"
    assert extract_account("۱۱۱۰ — موجودی نقد و بانک") == ("1110", "موجودی نقد و بانک")
    assert parse_amount("(۱٬۲۳۴٬۵۶۷ ریال)") == Decimal("-1234567")


def test_excel_parser_detects_variable_header_position():
    rows = ExcelTrialBalanceParser().parse(excel_bytes())
    assert len(rows) == 2
    assert rows[0].general_code == "1110"
    assert rows[1].subsidiary_code == "111005"
    assert rows[1].closing_debit == Decimal("50000000")


def test_mapping_aggregation_sign_unit_validation_and_versioning(tmp_path):
    engine = create_engine(f"sqlite+pysqlite:///{tmp_path / 'financial.db'}")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(FinancialStatementField(id="BS.CASH", statement="BS", title="موجودی نقد", field_type="mapped"))
        organization = FinancialOrganization(name="شرکت آزمون", owner_user_id="user-1")
        session.add(organization); session.flush()
        year = FinancialFiscalYear(organization_id=organization.id, title="۱۴۰۵")
        session.add(year); session.flush()
        import_ = FinancialStatementImport(organization_id=organization.id, fiscal_year_id=year.id, user_id="user-1", original_filename="sample.xlsx", storage_key="sample", mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", file_size=10, file_hash="a" * 64, money_unit="rial", status="parsed")
        session.add(import_); session.flush()
        for index, amount in enumerate((Decimal("10000000"), Decimal("50000000")), 1):
            session.add(FinancialStatementImportRow(import_id=import_.id, general_code="1110", general_name="موجودی نقد و بانک", subsidiary_code=f"11100{index}", subsidiary_name="بانک", normalized_name="بانک", closing_debit=amount, closing_credit=0, net_closing_balance=amount, source_row_number=index))
        session.add(AccountMappingRule(organization_id=None, name="نقد", source_level="subsidiary", source_code_prefix="1110", target_statement="BS", target_field_id="BS.CASH", amount_source="net_closing", sign_multiplier=1, is_global=True, created_by="user-1"))
        session.flush(); AccountMappingService(session).apply(import_); session.flush()
        decisions = list(session.scalars(select(AccountMappingDecision)))
        assert all(item.status == "mapped" for item in decisions)
        first = FinancialStatementCalculationService(session).calculate(import_, "user-1")
        session.flush()
        value = session.scalar(select(FinancialStatementValue).where(FinancialStatementValue.run_id == first.id, FinancialStatementValue.field_id == "BS.CASH"))
        assert value.final_value == Decimal("60000000")
        second = FinancialStatementCalculationService(session).calculate(import_, "user-1")
        assert (first.version, second.version) == (1, 2)
        assert convert_money(Decimal("1000000"), "rial", "million_rial") == 1
