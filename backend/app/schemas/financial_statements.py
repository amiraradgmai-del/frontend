from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


class OrganizationCreate(BaseModel):
    name: str = Field(min_length=2, max_length=240)
    national_id: str = Field(default="", max_length=32)
    entity_type: Literal["individual", "company"] = "company"
    economic_code: str = Field(default="", max_length=32)
    registration_number: str = Field(default="", max_length=32)
    tax_file_number: str = Field(default="", max_length=64)
    province: str = Field(default="", max_length=80)
    city: str = Field(default="", max_length=80)
    postal_code: str = Field(default="", max_length=20)
    address: str = Field(default="", max_length=500)


class FiscalYearCreate(BaseModel):
    organization_id: str
    title: str = Field(min_length=2, max_length=80)
    start_date: date | None = None
    end_date: date | None = None
    status: Literal["open", "closed"] = "open"


class MappingUpdate(BaseModel):
    import_row_id: str
    target_field_id: str | None = None
    amount_source: Literal["closing_debit", "closing_credit", "net_closing", "opening_debit", "opening_credit", "net_opening", "period_debit", "period_credit", "net_period"] = "net_closing"
    sign_multiplier: Literal[-1, 1] = 1
    status: Literal["mapped", "needs_review", "unmapped", "ignored"] = "mapped"
    ignore_reason: str = Field(default="", max_length=500)
    save_rule: bool = False
    global_rule: bool = False


class MappingBatch(BaseModel):
    decisions: list[MappingUpdate] = Field(min_length=1, max_length=5000)


class CalculateRequest(BaseModel):
    tolerance: Decimal = Field(default=Decimal(0), ge=0)


class AdjustmentCreate(BaseModel):
    field_id: str
    amount: Decimal
    reason: str = Field(min_length=3, max_length=1000)


class ImportSummary(BaseModel):
    id: str
    organization_id: str
    fiscal_year_id: str
    original_filename: str
    money_unit: str
    status: str
    created_at: datetime
    total_accounts: int = 0
    mapped: int = 0
    needs_review: int = 0
    unmapped: int = 0
    ignored: int = 0
    mapping_coverage: float = 0
