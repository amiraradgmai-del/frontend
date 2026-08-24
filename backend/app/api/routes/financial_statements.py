from __future__ import annotations

import re
from datetime import datetime, timezone
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_session, permission_codes, require_permissions
from app.models.auth import AuditLog, User
from app.models.financial_statements import *
from app.schemas.financial_statements import *
from app.services.financial_statements import (
    AccountMappingService, ExcelTrialBalanceParser, LegacyExcelTrialBalanceParser, FinancialStatementCalculationService,
    PdfTrialBalanceParser, normalize_persian_financial, pdf_export, sha256, workbook_export,
)

router = APIRouter(prefix="/api/v1/financial-statements", tags=["financial statements"])
ALLOWED = {
    ".xlsx": {"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "application/octet-stream"},
    ".xls": {"application/vnd.ms-excel", "application/octet-stream"},
    ".pdf": {"application/pdf", "application/octet-stream"},
}
MAX_FILE_SIZE = 25 * 1024 * 1024


def _owns(session: Session, user: User, organization_id: str) -> FinancialOrganization:
    item = session.get(FinancialOrganization, organization_id)
    if item is None or (item.owner_user_id != user.id and "users:manage" not in permission_codes(user)):
        raise HTTPException(404, "شرکت پیدا نشد")
    return item


def _import(session: Session, user: User, import_id: str) -> FinancialStatementImport:
    item = session.get(FinancialStatementImport, import_id)
    if item is None: raise HTTPException(404, "پردازش پیدا نشد")
    _owns(session, user, item.organization_id); return item


def _run(session: Session, user: User, run_id: str) -> FinancialStatementRun:
    run = session.get(FinancialStatementRun, run_id)
    if run is None: raise HTTPException(404, "نسخه صورت مالی پیدا نشد")
    _import(session, user, run.import_id); return run


def _audit(session: Session, user: User, action: str, resource: str, resource_id: str, metadata: dict | None = None):
    session.add(AuditLog(actor_user_id=user.id, action=action, resource_type=resource, resource_id=resource_id, metadata_json=metadata or {}))


@router.get("/organizations")
def organizations(user: Annotated[User, Depends(require_permissions("financial_statements:view"))], session: Annotated[Session, Depends(get_session)]):
    query = select(FinancialOrganization).order_by(FinancialOrganization.created_at.desc())
    if "users:manage" not in permission_codes(user): query = query.where(FinancialOrganization.owner_user_id == user.id)
    items = list(session.scalars(query))
    if not items:
        item = FinancialOrganization(name=f"پرونده مالی {user.full_name}", national_id="", owner_user_id=user.id)
        session.add(item); session.flush()
        current_year = datetime.now(timezone.utc).year - 621
        for year in range(current_year, current_year - 3, -1):
            session.add(FinancialFiscalYear(organization_id=item.id, title=f"سال مالی {year}"))
        _audit(session, user, "financial.defaults_created", "financial_organization", item.id)
        session.commit(); items = [item]
    return [{"id": x.id, "name": x.name, "national_id": x.national_id, "entity_type": x.entity_type, "economic_code": x.economic_code, "registration_number": x.registration_number, "tax_file_number": x.tax_file_number, "province": x.province, "city": x.city, "postal_code": x.postal_code, "address": x.address} for x in items]


@router.post("/organizations", status_code=201)
def create_organization(payload: OrganizationCreate, user: Annotated[User, Depends(require_permissions("financial_statements:upload"))], session: Annotated[Session, Depends(get_session)]):
    values = payload.model_dump()
    values["name"] = normalize_persian_financial(values["name"])
    for key in ("national_id", "economic_code", "registration_number", "tax_file_number", "postal_code"):
        values[key] = re.sub(r"\D", "", values[key].translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")))
    if values["entity_type"] == "company" and values["national_id"] and len(values["national_id"]) != 11:
        raise HTTPException(422, "شناسه ملی شرکت باید ۱۱ رقم باشد")
    if values["postal_code"] and len(values["postal_code"]) != 10:
        raise HTTPException(422, "کد پستی باید ۱۰ رقم باشد")
    item = FinancialOrganization(**values, owner_user_id=user.id)
    session.add(item); session.flush(); _audit(session, user, "financial.organization_created", "financial_organization", item.id); session.commit()
    return {"id": item.id, **payload.model_dump()}


@router.get("/fiscal-years")
def fiscal_years(organization_id: str, user: Annotated[User, Depends(require_permissions("financial_statements:view"))], session: Annotated[Session, Depends(get_session)]):
    _owns(session, user, organization_id)
    return [{"id": x.id, "title": x.title, "start_date": x.start_date, "end_date": x.end_date, "status": x.status} for x in session.scalars(select(FinancialFiscalYear).where(FinancialFiscalYear.organization_id == organization_id).order_by(FinancialFiscalYear.end_date.desc()))]


@router.post("/fiscal-years", status_code=201)
def create_fiscal_year(payload: FiscalYearCreate, user: Annotated[User, Depends(require_permissions("financial_statements:upload"))], session: Annotated[Session, Depends(get_session)]):
    _owns(session, user, payload.organization_id)
    if payload.start_date and payload.end_date and payload.end_date < payload.start_date: raise HTTPException(422, "تاریخ پایان نمی‌تواند قبل از تاریخ شروع باشد")
    item = FinancialFiscalYear(**payload.model_dump()); session.add(item); session.flush(); _audit(session, user, "financial.fiscal_year_created", "financial_fiscal_year", item.id); session.commit()
    return {"id": item.id, "title": item.title, "start_date": item.start_date, "end_date": item.end_date, "status": item.status}


@router.get("/fields")
def fields(_: Annotated[User, Depends(require_permissions("financial_statements:view"))], session: Annotated[Session, Depends(get_session)]):
    return [{"id": x.id, "statement": x.statement, "title": x.title, "field_type": x.field_type} for x in session.scalars(select(FinancialStatementField).where(FinancialStatementField.is_active.is_(True)).order_by(FinancialStatementField.sort_order))]


@router.get("/imports")
def imports(user: Annotated[User, Depends(require_permissions("financial_statements:view"))], session: Annotated[Session, Depends(get_session)]):
    query = select(FinancialStatementImport).join(FinancialOrganization).order_by(FinancialStatementImport.created_at.desc())
    if "users:manage" not in permission_codes(user): query = query.where(FinancialOrganization.owner_user_id == user.id)
    return [_summary(session, item) for item in session.scalars(query)]


@router.post("/imports", status_code=201)
async def upload_import(request: Request, user: Annotated[User, Depends(require_permissions("financial_statements:upload"))], session: Annotated[Session, Depends(get_session)], organization_id: Annotated[str, Form()], fiscal_year_id: Annotated[str, Form()], money_unit: Annotated[str, Form()], allow_duplicate: Annotated[bool, Form()] = False, file: UploadFile = File(...)):
    _owns(session, user, organization_id); year = session.get(FinancialFiscalYear, fiscal_year_id)
    if year is None or year.organization_id != organization_id: raise HTTPException(422, "سال مالی معتبر نیست")
    extension = "." + file.filename.rsplit(".", 1)[-1].lower() if file.filename and "." in file.filename else ""
    if extension not in ALLOWED or file.content_type not in ALLOWED[extension]: raise HTTPException(415, "فقط فایل Excel یا PDF معتبر قابل پذیرش است")
    if money_unit not in {"rial", "toman"}: raise HTTPException(422, "واحد پول باید ریال یا تومان باشد")
    data = await file.read(MAX_FILE_SIZE + 1)
    if not data: raise HTTPException(422, "فایل خالی است")
    if len(data) > MAX_FILE_SIZE: raise HTTPException(413, "حجم فایل بیشتر از حد مجاز است")
    digest = sha256(data)
    duplicate = session.scalar(select(FinancialStatementImport).where(FinancialStatementImport.organization_id == organization_id, FinancialStatementImport.fiscal_year_id == fiscal_year_id, FinancialStatementImport.file_hash == digest))
    if duplicate and not allow_duplicate: raise HTTPException(409, detail={"code": "duplicate_file", "import_id": duplicate.id, "message": "این فایل قبلاً برای همین شرکت و سال مالی بارگذاری شده است."})
    item = FinancialStatementImport(organization_id=organization_id, fiscal_year_id=fiscal_year_id, user_id=user.id, original_filename=(file.filename or "trial-balance")[:255], storage_key=f"financial-statements/{organization_id}/{new_uuid()}{extension}", mime_type=file.content_type or "application/octet-stream", file_size=len(data), file_hash=digest, money_unit=money_unit)
    request.app.state.storage.put(item.storage_key, data, item.mime_type); session.add(item); session.flush(); _audit(session, user, "financial.import_uploaded", "financial_statement_import", item.id, {"organization_id": organization_id, "fiscal_year_id": fiscal_year_id, "file_hash": digest}); session.commit()
    return _summary(session, item)


@router.get("/imports/{import_id}")
def get_import(import_id: str, user: Annotated[User, Depends(require_permissions("financial_statements:view"))], session: Annotated[Session, Depends(get_session)]): return _summary(session, _import(session, user, import_id))


@router.post("/imports/{import_id}/parse")
def parse_import(import_id: str, request: Request, user: Annotated[User, Depends(require_permissions("financial_statements:upload"))], session: Annotated[Session, Depends(get_session)]):
    item = _import(session, user, import_id)
    if item.status == "parsing": raise HTTPException(409, "پردازش این فایل هم‌اکنون در حال انجام است")
    item.status = "parsing"; session.commit()
    try:
        data = request.app.state.storage.get(item.storage_key)
        extension = "." + item.original_filename.rsplit(".", 1)[-1].lower()
        parser = PdfTrialBalanceParser() if extension == ".pdf" else LegacyExcelTrialBalanceParser() if extension == ".xls" else ExcelTrialBalanceParser()
        parsed = parser.parse(data)
        session.query(FinancialStatementImportRow).filter(FinancialStatementImportRow.import_id == item.id).delete(synchronize_session=False)
        for row in parsed:
            name = row.detail_name or row.subsidiary_name or row.general_name
            raw = {key: str(value) if isinstance(value, Decimal) else value for key, value in row.__dict__.items()}
            session.add(FinancialStatementImportRow(import_id=item.id, normalized_name=normalize_persian_financial(name), net_closing_balance=row.closing_debit-row.closing_credit, raw_json=raw, **row.__dict__))
        session.flush(); item.status = "parsed"; item.parsed_at = datetime.now(timezone.utc)
        counts = AccountMappingService(session).apply(item); _audit(session, user, "financial.import_parsed", "financial_statement_import", item.id, {"rows": len(parsed), **counts}); session.commit()
        return _summary(session, item)
    except ValueError as exc:
        session.rollback(); item = session.get(FinancialStatementImport, import_id); item.status = "failed"; item.error_code = str(exc); session.commit()
        raise HTTPException(422, "ساختار فایل قابل تشخیص نیست یا نیاز به بررسی دستی دارد") from exc


@router.get("/imports/{import_id}/rows")
def import_rows(import_id: str, user: Annotated[User, Depends(require_permissions("financial_statements:view"))], session: Annotated[Session, Depends(get_session)], status: str | None = None, search: str = "", offset: int = 0, limit: int = 50):
    _import(session, user, import_id); query = select(FinancialStatementImportRow, AccountMappingDecision).outerjoin(AccountMappingDecision, AccountMappingDecision.import_row_id == FinancialStatementImportRow.id).where(FinancialStatementImportRow.import_id == import_id)
    if status: query = query.where(AccountMappingDecision.status == status)
    if search.strip(): query = query.where((FinancialStatementImportRow.normalized_name.contains(normalize_persian_financial(search))) | (FinancialStatementImportRow.general_code.contains(search)) | (FinancialStatementImportRow.subsidiary_code.contains(search)) | (FinancialStatementImportRow.detail_code.contains(search)))
    rows = session.execute(query.order_by(FinancialStatementImportRow.source_row_number).offset(max(offset, 0)).limit(min(max(limit, 1), 200))).all()
    return [_row_data(row, decision) for row, decision in rows]


@router.get("/imports/{import_id}/unmapped")
def unmapped(import_id: str, user: Annotated[User, Depends(require_permissions("financial_statements:view"))], session: Annotated[Session, Depends(get_session)]): return import_rows(import_id, user, session, status="unmapped", limit=200)


@router.post("/imports/{import_id}/mapping")
def mapping(import_id: str, payload: MappingBatch, user: Annotated[User, Depends(require_permissions("financial_statements:map"))], session: Annotated[Session, Depends(get_session)]):
    item = _import(session, user, import_id)
    for update in payload.decisions:
        row = session.get(FinancialStatementImportRow, update.import_row_id)
        if row is None or row.import_id != item.id: raise HTTPException(422, "ردیف نگاشت معتبر نیست")
        decision = session.scalar(select(AccountMappingDecision).where(AccountMappingDecision.import_row_id == row.id)) or AccountMappingDecision(import_row_id=row.id)
        old = {"target": decision.target_field_id, "status": decision.status}
        decision.target_field_id = update.target_field_id; decision.amount_source = update.amount_source; decision.sign_multiplier = update.sign_multiplier; decision.status = update.status; decision.confidence = 100 if update.status == "mapped" else decision.confidence; decision.ignore_reason = update.ignore_reason; decision.decided_by = user.id; decision.decided_at = datetime.now(timezone.utc); session.add(decision)
        if update.save_rule and update.target_field_id:
            if update.global_rule and "financial_statements:manage_mapping" not in permission_codes(user): raise HTTPException(403, "مجوز ساخت نگاشت عمومی را ندارید")
            level, code, name = AccountMappingService._identity(row)
            rule = AccountMappingRule(organization_id=None if update.global_rule else item.organization_id, name=f"نگاشت {code or name}", source_level=level, source_code=code, source_name=name, normalized_source_name=normalize_persian_financial(name), target_statement=update.target_field_id.split(".",1)[0], target_field_id=update.target_field_id, amount_source=update.amount_source, sign_multiplier=update.sign_multiplier, priority=200, confidence=100, is_global=update.global_rule, created_by=user.id)
            session.add(rule); session.flush(); decision.rule_id = rule.id
        _audit(session, user, "financial.mapping_changed", "account_mapping_decision", decision.id, {"old": old, "new": {"target": decision.target_field_id, "status": decision.status}})
    session.flush(); counts = _mapping_counts(session, item.id); item.status = "ready_to_calculate" if counts["unmapped"] == 0 and counts["needs_review"] == 0 else "mapping_required"; session.commit(); return _summary(session, item)


@router.post("/imports/{import_id}/calculate", status_code=201)
def calculate(import_id: str, payload: CalculateRequest, user: Annotated[User, Depends(require_permissions("financial_statements:calculate"))], session: Annotated[Session, Depends(get_session)]):
    item = _import(session, user, import_id); counts = _mapping_counts(session, item.id)
    if counts["unmapped"] or counts["needs_review"]: raise HTTPException(409, "ابتدا حساب‌های نامشخص و نیازمند بررسی را تعیین تکلیف کنید")
    run = FinancialStatementCalculationService(session).calculate(item, user.id, payload.tolerance); _audit(session, user, "financial.run_calculated", "financial_statement_run", run.id, {"version": run.version}); session.commit(); return _run_data(session, run)


@router.get("/runs/{run_id}")
def get_run(run_id: str, user: Annotated[User, Depends(require_permissions("financial_statements:view"))], session: Annotated[Session, Depends(get_session)]): return _run_data(session, _run(session, user, run_id))


@router.get("/runs/{run_id}/values")
def values(run_id: str, user: Annotated[User, Depends(require_permissions("financial_statements:view"))], session: Annotated[Session, Depends(get_session)]):
    _run(session, user, run_id); rows = session.execute(select(FinancialStatementValue, FinancialStatementField).join(FinancialStatementField, FinancialStatementField.id == FinancialStatementValue.field_id).where(FinancialStatementValue.run_id == run_id).order_by(FinancialStatementField.sort_order)).all()
    result=[]
    for value, field in rows:
        sources=session.execute(select(FinancialStatementValueSource, FinancialStatementImportRow).join(FinancialStatementImportRow, FinancialStatementImportRow.id == FinancialStatementValueSource.import_row_id).where(FinancialStatementValueSource.value_id == value.id)).all()
        result.append({"field_id":field.id,"statement":field.statement,"title":field.title,"calculated_value":value.calculated_value,"adjustment_value":value.adjustment_value,"final_value":value.final_value,"status":value.status,"sources":[{"row_id":row.id,"code":row.detail_code or row.subsidiary_code or row.general_code,"name":row.detail_name or row.subsidiary_name or row.general_name,"amount":source.contribution_amount} for source,row in sources]})
    return result


@router.get("/runs/{run_id}/validations")
def validations(run_id: str, user: Annotated[User, Depends(require_permissions("financial_statements:view"))], session: Annotated[Session, Depends(get_session)]): _run(session,user,run_id); return [{"code":x.code,"status":x.status,"difference":x.difference,"tolerance":x.tolerance,"message":x.message} for x in session.scalars(select(FinancialStatementValidation).where(FinancialStatementValidation.run_id==run_id))]


@router.post("/runs/{run_id}/adjustments", status_code=201)
def add_adjustment(run_id: str, payload: AdjustmentCreate, user: Annotated[User, Depends(require_permissions("financial_statements:adjust"))], session: Annotated[Session, Depends(get_session)]):
    source_run = _run(session, user, run_id)
    run = _clone_run(session, source_run, user.id) if source_run.finalized_at else source_run
    value = session.scalar(select(FinancialStatementValue).where(FinancialStatementValue.run_id == run.id, FinancialStatementValue.field_id == payload.field_id))
    if value is None: raise HTTPException(422, "فیلد صورت مالی معتبر نیست")
    adjustment = FinancialStatementAdjustment(run_id=run.id, field_id=payload.field_id, amount=payload.amount, reason=payload.reason, user_id=user.id)
    session.add(adjustment); session.flush(); value.adjustment_value += payload.amount; value.final_value = value.calculated_value + value.adjustment_value; value.status = "adjusted"
    _audit(session,user,"financial.adjustment_created","financial_statement_adjustment",adjustment.id,{"run_id":run.id,"field_id":payload.field_id,"amount":str(payload.amount),"reason":payload.reason}); session.commit()
    return {"run_id":run.id,"field_id":value.field_id,"calculated_value":value.calculated_value,"adjustment_value":value.adjustment_value,"final_value":value.final_value}


@router.post("/runs/{run_id}/finalize")
def finalize(run_id: str, user: Annotated[User, Depends(require_permissions("financial_statements:finalize"))], session: Annotated[Session, Depends(get_session)]):
    run=_run(session,user,run_id)
    if run.finalized_at: raise HTTPException(409,"این نسخه قبلاً نهایی شده است")
    if session.scalar(select(func.count()).select_from(FinancialStatementValidation).where(FinancialStatementValidation.run_id==run.id,FinancialStatementValidation.status=="failed")): raise HTTPException(409,"نسخه دارای کنترل ناموفق است")
    run.status="finalized"; run.finalized_at=datetime.now(timezone.utc); _audit(session,user,"financial.run_finalized","financial_statement_run",run.id,{"version":run.version}); session.commit(); return _run_data(session,run)


@router.get("/runs/{run_id}/export/excel")
def export_excel(run_id: str, user: Annotated[User, Depends(require_permissions("financial_statements:export"))], session: Annotated[Session, Depends(get_session)]):
    run=_run(session,user,run_id); item=session.get(FinancialStatementImport,run.import_id); org=session.get(FinancialOrganization,item.organization_id); year=session.get(FinancialFiscalYear,item.fiscal_year_id)
    rows=session.execute(select(FinancialStatementField,FinancialStatementValue).join(FinancialStatementValue,FinancialStatementValue.field_id==FinancialStatementField.id).where(FinancialStatementValue.run_id==run.id).order_by(FinancialStatementField.sort_order)).all(); data=workbook_export(rows,org.name,year.title); _audit(session,user,"financial.export_excel","financial_statement_run",run.id); session.commit()
    safe=re.sub(r"[^\w-]+","-",org.name); return Response(data,media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",headers={"Content-Disposition":f'attachment; filename="Financial-Statements-{safe}-{year.title}.xlsx"'})


@router.get("/runs/{run_id}/export/pdf")
def export_pdf(run_id: str, user: Annotated[User, Depends(require_permissions("financial_statements:export"))], session: Annotated[Session, Depends(get_session)]):
    run=_run(session,user,run_id); item=session.get(FinancialStatementImport,run.import_id); org=session.get(FinancialOrganization,item.organization_id); year=session.get(FinancialFiscalYear,item.fiscal_year_id)
    rows=session.execute(select(FinancialStatementField,FinancialStatementValue).join(FinancialStatementValue,FinancialStatementValue.field_id==FinancialStatementField.id).where(FinancialStatementValue.run_id==run.id).order_by(FinancialStatementField.sort_order)).all(); data=pdf_export(rows,org.name,year.title); _audit(session,user,"financial.export_pdf","financial_statement_run",run.id); session.commit()
    safe=re.sub(r"[^\w-]+","-",org.name); return Response(data,media_type="application/pdf",headers={"Content-Disposition":f'attachment; filename="Financial-Statements-{safe}-{year.title}.pdf"'})


def _mapping_counts(session: Session, import_id: str):
    rows=session.execute(select(AccountMappingDecision.status,func.count()).join(FinancialStatementImportRow,FinancialStatementImportRow.id==AccountMappingDecision.import_row_id).where(FinancialStatementImportRow.import_id==import_id).group_by(AccountMappingDecision.status)).all(); counts={"mapped":0,"needs_review":0,"unmapped":0,"ignored":0}; counts.update(dict(rows)); return counts


def _summary(session,item):
    counts=_mapping_counts(session,item.id); total=session.scalar(select(func.count()).select_from(FinancialStatementImportRow).where(FinancialStatementImportRow.import_id==item.id)) or 0; return {"id":item.id,"organization_id":item.organization_id,"fiscal_year_id":item.fiscal_year_id,"original_filename":item.original_filename,"money_unit":item.money_unit,"status":item.status,"created_at":item.created_at,"total_accounts":total,**counts,"mapping_coverage":round((counts["mapped"]+counts["ignored"])*100/total,1) if total else 0}


def _row_data(row,decision): return {"id":row.id,"general_code":row.general_code,"general_name":row.general_name,"subsidiary_code":row.subsidiary_code,"subsidiary_name":row.subsidiary_name,"detail_code":row.detail_code,"detail_name":row.detail_name,"opening_debit":row.opening_debit,"opening_credit":row.opening_credit,"period_debit":row.period_debit,"period_credit":row.period_credit,"closing_debit":row.closing_debit,"closing_credit":row.closing_credit,"net_closing_balance":row.net_closing_balance,"source_row_number":row.source_row_number,"target_field_id":decision.target_field_id if decision else None,"confidence":decision.confidence if decision else 0,"status":decision.status if decision else "unmapped"}


def _run_data(session,run): return {"id":run.id,"import_id":run.import_id,"version":run.version,"status":run.status,"money_unit":run.money_unit,"created_at":run.created_at,"finalized_at":run.finalized_at}


def _clone_run(session: Session, source: FinancialStatementRun, user_id: str) -> FinancialStatementRun:
    version=(session.scalar(select(func.max(FinancialStatementRun.version)).where(FinancialStatementRun.import_id==source.import_id)) or 0)+1
    target=FinancialStatementRun(import_id=source.import_id,version=version,status="calculated",money_unit=source.money_unit,template_id=source.template_id,created_by=user_id); session.add(target); session.flush()
    value_map={}
    for value in session.scalars(select(FinancialStatementValue).where(FinancialStatementValue.run_id==source.id)):
        cloned=FinancialStatementValue(run_id=target.id,field_id=value.field_id,calculated_value=value.calculated_value,adjustment_value=value.adjustment_value,final_value=value.final_value,status=value.status); session.add(cloned); session.flush(); value_map[value.id]=cloned.id
    for source_item in session.scalars(select(FinancialStatementValueSource).join(FinancialStatementValue,FinancialStatementValue.id==FinancialStatementValueSource.value_id).where(FinancialStatementValue.run_id==source.id)):
        session.add(FinancialStatementValueSource(value_id=value_map[source_item.value_id],import_row_id=source_item.import_row_id,mapping_rule_id=source_item.mapping_rule_id,source_amount=source_item.source_amount,contribution_amount=source_item.contribution_amount,calculation_json=source_item.calculation_json))
    for validation in session.scalars(select(FinancialStatementValidation).where(FinancialStatementValidation.run_id==source.id)):
        session.add(FinancialStatementValidation(run_id=target.id,code=validation.code,status=validation.status,difference=validation.difference,tolerance=validation.tolerance,message=validation.message))
    return target
