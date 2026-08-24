from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import JSON, Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def new_uuid() -> str:
    return str(uuid.uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class FinancialOrganization(Base):
    __tablename__ = "financial_organizations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(240), index=True)
    national_id: Mapped[str] = mapped_column(String(32), default="", index=True)
    owner_user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class FinancialFiscalYear(Base):
    __tablename__ = "financial_fiscal_years"
    __table_args__ = (UniqueConstraint("organization_id", "title", name="uq_financial_fiscal_year_title"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    organization_id: Mapped[str] = mapped_column(String(36), ForeignKey("financial_organizations.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(80))
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class FinancialStatementImport(Base):
    __tablename__ = "financial_statement_imports"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    organization_id: Mapped[str] = mapped_column(String(36), ForeignKey("financial_organizations.id", ondelete="RESTRICT"), index=True)
    fiscal_year_id: Mapped[str] = mapped_column(String(36), ForeignKey("financial_fiscal_years.id", ondelete="RESTRICT"), index=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    original_filename: Mapped[str] = mapped_column(String(255))
    storage_key: Mapped[str] = mapped_column(String(500), unique=True)
    mime_type: Mapped[str] = mapped_column(String(120))
    file_size: Mapped[int] = mapped_column(Integer)
    file_hash: Mapped[str] = mapped_column(String(64), index=True)
    money_unit: Mapped[str] = mapped_column(String(24), default="rial")
    status: Mapped[str] = mapped_column(String(32), default="uploaded", index=True)
    company_name_detected: Mapped[str] = mapped_column(String(240), default="")
    from_date: Mapped[date | None] = mapped_column(Date)
    to_date: Mapped[date | None] = mapped_column(Date)
    error_code: Mapped[str | None] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    parsed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rows: Mapped[list[FinancialStatementImportRow]] = relationship(back_populates="import_", cascade="all, delete-orphan")


class FinancialStatementImportRow(Base):
    __tablename__ = "financial_statement_import_rows"
    __table_args__ = (UniqueConstraint("import_id", "source_row_number", name="uq_financial_import_source_row"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    import_id: Mapped[str] = mapped_column(String(36), ForeignKey("financial_statement_imports.id", ondelete="CASCADE"), index=True)
    general_code: Mapped[str] = mapped_column(String(64), default="", index=True)
    general_name: Mapped[str] = mapped_column(String(300), default="")
    subsidiary_code: Mapped[str] = mapped_column(String(64), default="", index=True)
    subsidiary_name: Mapped[str] = mapped_column(String(300), default="")
    detail_code: Mapped[str] = mapped_column(String(64), default="", index=True)
    detail_name: Mapped[str] = mapped_column(String(300), default="")
    normalized_name: Mapped[str] = mapped_column(String(500), default="", index=True)
    opening_debit: Mapped[Decimal] = mapped_column(Numeric(24, 4), default=0)
    opening_credit: Mapped[Decimal] = mapped_column(Numeric(24, 4), default=0)
    period_debit: Mapped[Decimal] = mapped_column(Numeric(24, 4), default=0)
    period_credit: Mapped[Decimal] = mapped_column(Numeric(24, 4), default=0)
    closing_debit: Mapped[Decimal] = mapped_column(Numeric(24, 4), default=0)
    closing_credit: Mapped[Decimal] = mapped_column(Numeric(24, 4), default=0)
    net_closing_balance: Mapped[Decimal] = mapped_column(Numeric(24, 4), default=0)
    source_row_number: Mapped[int] = mapped_column(Integer)
    raw_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    import_: Mapped[FinancialStatementImport] = relationship(back_populates="rows")


class FinancialStatementField(Base):
    __tablename__ = "financial_statement_fields"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    statement: Mapped[str] = mapped_column(String(24), index=True)
    title: Mapped[str] = mapped_column(String(240))
    field_type: Mapped[str] = mapped_column(String(24), default="mapped")
    formula_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class FinancialStatementTemplate(Base):
    __tablename__ = "financial_statement_templates"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(240))
    version: Mapped[int] = mapped_column(Integer, default=1)
    storage_key: Mapped[str] = mapped_column(String(500), default="")
    money_unit: Mapped[str] = mapped_column(String(24), default="million_rial")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_by: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class FinancialStatementTemplateField(Base):
    __tablename__ = "financial_statement_template_fields"
    __table_args__ = (UniqueConstraint("template_id", "field_id", "period_type", name="uq_financial_template_field_period"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    template_id: Mapped[str] = mapped_column(String(36), ForeignKey("financial_statement_templates.id", ondelete="CASCADE"), index=True)
    field_id: Mapped[str] = mapped_column(String(80), ForeignKey("financial_statement_fields.id", ondelete="RESTRICT"), index=True)
    sheet_name: Mapped[str] = mapped_column(String(120))
    cell_address: Mapped[str] = mapped_column(String(20))
    period_type: Mapped[str] = mapped_column(String(24), default="current")


class AccountMappingRule(Base):
    __tablename__ = "account_mapping_rules"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    organization_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("financial_organizations.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(240))
    source_level: Mapped[str] = mapped_column(String(24), default="any")
    source_code: Mapped[str] = mapped_column(String(64), default="", index=True)
    source_code_prefix: Mapped[str] = mapped_column(String(64), default="", index=True)
    source_name: Mapped[str] = mapped_column(String(300), default="")
    normalized_source_name: Mapped[str] = mapped_column(String(300), default="", index=True)
    keywords_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    target_statement: Mapped[str] = mapped_column(String(24), index=True)
    target_field_id: Mapped[str] = mapped_column(String(80), ForeignKey("financial_statement_fields.id", ondelete="RESTRICT"), index=True)
    amount_source: Mapped[str] = mapped_column(String(32), default="net_closing")
    sign_multiplier: Mapped[int] = mapped_column(Integer, default=1)
    priority: Mapped[int] = mapped_column(Integer, default=100)
    confidence: Mapped[int] = mapped_column(Integer, default=100)
    is_global: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_by: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class AccountMappingDecision(Base):
    __tablename__ = "account_mapping_decisions"
    __table_args__ = (UniqueConstraint("import_row_id", name="uq_financial_mapping_row"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    import_row_id: Mapped[str] = mapped_column(String(36), ForeignKey("financial_statement_import_rows.id", ondelete="CASCADE"), index=True)
    rule_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("account_mapping_rules.id", ondelete="SET NULL"))
    target_field_id: Mapped[str | None] = mapped_column(String(80), ForeignKey("financial_statement_fields.id", ondelete="RESTRICT"), index=True)
    amount_source: Mapped[str] = mapped_column(String(32), default="net_closing")
    sign_multiplier: Mapped[int] = mapped_column(Integer, default=1)
    confidence: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(24), default="unmapped", index=True)
    ignore_reason: Mapped[str] = mapped_column(String(500), default="")
    decided_by: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class FinancialStatementRun(Base):
    __tablename__ = "financial_statement_runs"
    __table_args__ = (UniqueConstraint("import_id", "version", name="uq_financial_run_version"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    import_id: Mapped[str] = mapped_column(String(36), ForeignKey("financial_statement_imports.id", ondelete="RESTRICT"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(24), default="calculated", index=True)
    money_unit: Mapped[str] = mapped_column(String(24), default="rial")
    template_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("financial_statement_templates.id", ondelete="SET NULL"))
    created_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="RESTRICT"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class FinancialStatementValue(Base):
    __tablename__ = "financial_statement_values"
    __table_args__ = (UniqueConstraint("run_id", "field_id", name="uq_financial_run_field"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    run_id: Mapped[str] = mapped_column(String(36), ForeignKey("financial_statement_runs.id", ondelete="CASCADE"), index=True)
    field_id: Mapped[str] = mapped_column(String(80), ForeignKey("financial_statement_fields.id", ondelete="RESTRICT"), index=True)
    calculated_value: Mapped[Decimal] = mapped_column(Numeric(24, 4), default=0)
    adjustment_value: Mapped[Decimal] = mapped_column(Numeric(24, 4), default=0)
    final_value: Mapped[Decimal] = mapped_column(Numeric(24, 4), default=0)
    status: Mapped[str] = mapped_column(String(32), default="calculated")


class FinancialStatementValueSource(Base):
    __tablename__ = "financial_statement_value_sources"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    value_id: Mapped[str] = mapped_column(String(36), ForeignKey("financial_statement_values.id", ondelete="CASCADE"), index=True)
    import_row_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("financial_statement_import_rows.id", ondelete="RESTRICT"), index=True)
    mapping_rule_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("account_mapping_rules.id", ondelete="SET NULL"))
    source_amount: Mapped[Decimal] = mapped_column(Numeric(24, 4), default=0)
    contribution_amount: Mapped[Decimal] = mapped_column(Numeric(24, 4), default=0)
    calculation_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class FinancialStatementAdjustment(Base):
    __tablename__ = "financial_statement_adjustments"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    run_id: Mapped[str] = mapped_column(String(36), ForeignKey("financial_statement_runs.id", ondelete="CASCADE"), index=True)
    field_id: Mapped[str] = mapped_column(String(80), ForeignKey("financial_statement_fields.id", ondelete="RESTRICT"), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(24, 4))
    reason: Mapped[str] = mapped_column(String(1000))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="RESTRICT"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class FinancialStatementValidation(Base):
    __tablename__ = "financial_statement_validations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    run_id: Mapped[str] = mapped_column(String(36), ForeignKey("financial_statement_runs.id", ondelete="CASCADE"), index=True)
    code: Mapped[str] = mapped_column(String(80), index=True)
    status: Mapped[str] = mapped_column(String(16), index=True)
    difference: Mapped[Decimal] = mapped_column(Numeric(24, 4), default=0)
    tolerance: Mapped[Decimal] = mapped_column(Numeric(24, 4), default=0)
    message: Mapped[str] = mapped_column(String(1000))


class GeneratedFinancialStatementFile(Base):
    __tablename__ = "generated_financial_statement_files"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    run_id: Mapped[str] = mapped_column(String(36), ForeignKey("financial_statement_runs.id", ondelete="CASCADE"), index=True)
    file_type: Mapped[str] = mapped_column(String(16))
    storage_key: Mapped[str] = mapped_column(String(500), unique=True)
    file_hash: Mapped[str] = mapped_column(String(64))
    created_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="RESTRICT"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
