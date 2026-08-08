

from datetime import date, datetime, timezone
import re
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_session, require_permissions
from app.models.auth import User, new_uuid
from app.models.portal import LawReferenceRecord, LegalCategory, LegalExternalSource, LegalUpdateCandidate

router = APIRouter(prefix="/api/v1/legal", tags=["legal center"])
manage_router = APIRouter(prefix="/api/v1/legal/manage", tags=["legal management"])


class CategoryPayload(BaseModel):
    code: str = Field(min_length=2, max_length=50, pattern=r"^[a-z0-9-]+$")
    title: str = Field(min_length=2, max_length=120)
    description: str = Field(default="", max_length=500)
    sort_order: int = Field(default=0, ge=0, le=10000)
    is_active: bool = True


class LawPayload(BaseModel):
    law_name: str = Field(min_length=2, max_length=300)
    chapter: str = Field(default="", max_length=300)
    article_number: str = Field(min_length=1, max_length=50)
    official_text: str = Field(min_length=3)
    keywords: str = Field(default="", max_length=500)
    category_id: str | None = None
    publication_date: date | None = None
    effective_date: date | None = None
    source_info: str = Field(default="", max_length=500)
    source_url: str = Field(default="", max_length=1000)


class SourcePayload(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    base_url: str = Field(min_length=5, max_length=1000)
    source_type: str = Field(default="website", max_length=40)
    is_enabled: bool = True


class CandidatePayload(BaseModel):
    source_id: str
    title: str = Field(min_length=2, max_length=300)
    article_number: str = Field(default="", max_length=50)
    proposed_text: str = Field(min_length=3)
    source_url: str = Field(default="", max_length=1000)


class ReviewPayload(BaseModel):
    decision: str = Field(pattern=r"^(approved|rejected)$")
    note: str = Field(default="", max_length=2000)
    category_id: str | None = None
    law_name: str | None = Field(default=None, max_length=300)


def category_data(item: LegalCategory) -> dict:
    return {"id": item.id, "code": item.code, "title": item.title, "description": item.description, "sort_order": item.sort_order, "is_active": item.is_active}


def law_data(item: LawReferenceRecord, category_title: str | None = None, include_source: bool = False) -> dict:
    result = {
        "id": item.id, "law_name": item.law_name, "chapter": item.chapter,
        "article_number": item.article_number, "official_text": item.official_text,
        "keywords": item.keywords, "category_id": item.category_id,
        "category_title": category_title, "publication_date": item.publication_date,
        "effective_date": item.effective_date, "is_active": item.is_active,
        "updated_at": item.updated_at,
    }
    if include_source:
        result.update({"source_id": item.source_id, "source_info": item.source_info, "source_url": item.source_url, "archived_at": item.archived_at})
    return result


@router.get("/categories")
def categories(_: Annotated[User, Depends(get_current_user)], session: Annotated[Session, Depends(get_session)]):
    items = session.scalars(select(LegalCategory).where(LegalCategory.is_active.is_(True)).order_by(LegalCategory.sort_order, LegalCategory.title)).all()
    return [category_data(item) for item in items]


@router.get("/search")
def search_laws(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
    q: str = Query(default="", max_length=200),
    category_id: str | None = None,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
):
    del user
    query = select(LawReferenceRecord, LegalCategory.title).outerjoin(LegalCategory, LegalCategory.id == LawReferenceRecord.category_id).where(LawReferenceRecord.is_active.is_(True))
    term = q.strip()
    if term:
        conditions = [
            LawReferenceRecord.law_name.ilike(f"%{term}%"),
            LawReferenceRecord.chapter.ilike(f"%{term}%"),
            LawReferenceRecord.official_text.ilike(f"%{term}%"),
            LawReferenceRecord.keywords.ilike(f"%{term}%"),
        ]
        number_match = re.search(r"\d+", term)
        if number_match:
            conditions.append(LawReferenceRecord.article_number == number_match.group())
        query = query.where(or_(*conditions))
    if category_id:
        query = query.where(LawReferenceRecord.category_id == category_id)
    rows = session.execute(query.order_by(LawReferenceRecord.law_name, LawReferenceRecord.article_number).offset(offset).limit(limit)).all()
    return [law_data(item, category_title) for item, category_title in rows]


@router.get("/records/{record_id}")
def law_detail(record_id: str, _: Annotated[User, Depends(get_current_user)], session: Annotated[Session, Depends(get_session)]):
    row = session.execute(
        select(LawReferenceRecord, LegalCategory.title)
        .outerjoin(LegalCategory, LegalCategory.id == LawReferenceRecord.category_id)
        .where(LawReferenceRecord.id == record_id, LawReferenceRecord.is_active.is_(True))
    ).first()
    if row is None:
        raise HTTPException(404, "ماده قانونی پیدا نشد.")
    return law_data(row[0], row[1])


@manage_router.get("/dashboard")
def dashboard(_: Annotated[User, Depends(require_permissions("documents:manage"))], session: Annotated[Session, Depends(get_session)]):
    return {
        "active_laws": session.scalar(select(func.count(LawReferenceRecord.id)).where(LawReferenceRecord.is_active.is_(True))) or 0,
        "archived_laws": session.scalar(select(func.count(LawReferenceRecord.id)).where(LawReferenceRecord.is_active.is_(False))) or 0,
        "sources": session.scalar(select(func.count(LegalExternalSource.id))) or 0,
        "pending_updates": session.scalar(select(func.count(LegalUpdateCandidate.id)).where(LegalUpdateCandidate.status == "pending")) or 0,
    }


@manage_router.get("/categories")
def manage_categories(_: Annotated[User, Depends(require_permissions("documents:manage"))], session: Annotated[Session, Depends(get_session)]):
    return [category_data(item) for item in session.scalars(select(LegalCategory).order_by(LegalCategory.sort_order, LegalCategory.title)).all()]


@manage_router.post("/categories", status_code=201)
def create_category(payload: CategoryPayload, _: Annotated[User, Depends(require_permissions("documents:manage"))], session: Annotated[Session, Depends(get_session)]):
    if session.scalar(select(LegalCategory).where(LegalCategory.code == payload.code)):
        raise HTTPException(409, "این کد دسته‌بندی قبلاً ثبت شده است.")
    item = LegalCategory(**payload.model_dump())
    session.add(item); session.commit(); session.refresh(item)
    return category_data(item)


@manage_router.patch("/categories/{category_id}")
def update_category(category_id: str, payload: CategoryPayload, _: Annotated[User, Depends(require_permissions("documents:manage"))], session: Annotated[Session, Depends(get_session)]):
    item = session.get(LegalCategory, category_id)
    if item is None:
        raise HTTPException(404, "دسته‌بندی پیدا نشد.")
    duplicate = session.scalar(select(LegalCategory).where(LegalCategory.code == payload.code, LegalCategory.id != category_id))
    if duplicate:
        raise HTTPException(409, "این کد دسته‌بندی قبلاً ثبت شده است.")
    for key, value in payload.model_dump().items():
        setattr(item, key, value)
    session.commit()
    return category_data(item)


@manage_router.get("/laws")
def manage_laws(
    _: Annotated[User, Depends(require_permissions("documents:manage"))],
    session: Annotated[Session, Depends(get_session)],
    q: str = Query(default="", max_length=200),
    include_archived: bool = False,
    limit: int = Query(default=100, ge=1, le=500),
):
    query = select(LawReferenceRecord, LegalCategory.title).outerjoin(LegalCategory, LegalCategory.id == LawReferenceRecord.category_id)
    if not include_archived:
        query = query.where(LawReferenceRecord.is_active.is_(True))
    if q.strip():
        term = q.strip()
        query = query.where(or_(LawReferenceRecord.law_name.ilike(f"%{term}%"), LawReferenceRecord.article_number.ilike(f"%{term}%"), LawReferenceRecord.official_text.ilike(f"%{term}%")))
    rows = session.execute(query.order_by(LawReferenceRecord.updated_at.desc()).limit(limit)).all()
    return [law_data(item, title, include_source=True) for item, title in rows]


@manage_router.post("/laws", status_code=201)
def create_law(payload: LawPayload, _: Annotated[User, Depends(require_permissions("documents:manage"))], session: Annotated[Session, Depends(get_session)]):
    item = LawReferenceRecord(id=new_uuid(), source_id="manual", **payload.model_dump())
    session.add(item); session.commit(); session.refresh(item)
    return law_data(item, include_source=True)


@manage_router.patch("/laws/{record_id}")
def update_law(record_id: str, payload: LawPayload, _: Annotated[User, Depends(require_permissions("documents:manage"))], session: Annotated[Session, Depends(get_session)]):
    item = session.get(LawReferenceRecord, record_id)
    if item is None:
        raise HTTPException(404, "ماده قانونی پیدا نشد.")
    for key, value in payload.model_dump().items():
        setattr(item, key, value)
    item.updated_at = datetime.now(timezone.utc)
    session.commit()
    return law_data(item, include_source=True)


@manage_router.delete("/laws/{record_id}", status_code=204)
def archive_law(record_id: str, _: Annotated[User, Depends(require_permissions("documents:manage"))], session: Annotated[Session, Depends(get_session)]):
    item = session.get(LawReferenceRecord, record_id)
    if item is None:
        raise HTTPException(404, "ماده قانونی پیدا نشد.")
    item.is_active = False
    item.archived_at = datetime.now(timezone.utc)
    session.commit()


@manage_router.get("/sources")
def sources(_: Annotated[User, Depends(require_permissions("documents:manage"))], session: Annotated[Session, Depends(get_session)]):
    return [{"id": item.id, "title": item.title, "base_url": item.base_url, "source_type": item.source_type, "is_enabled": item.is_enabled, "last_checked_at": item.last_checked_at, "last_status": item.last_status, "last_error": item.last_error, "last_title": item.last_title, "last_content_length": item.last_content_length} for item in session.scalars(select(LegalExternalSource).order_by(LegalExternalSource.created_at.desc())).all()]


@manage_router.post("/sources/check", status_code=202)
def check_sources_now(request: Request, _: Annotated[User, Depends(require_permissions("documents:manage"))]):
    from app.workers.tasks import check_legal_sources_job

    if request.app.state.settings.task_execution_mode == "inline":
        result = check_legal_sources_job()
        return {"status": "completed", **result}
    task = check_legal_sources_job.delay()
    return {"task_id": task.id, "status": "queued"}


@manage_router.post("/sources", status_code=201)
def create_source(payload: SourcePayload, _: Annotated[User, Depends(require_permissions("documents:manage"))], session: Annotated[Session, Depends(get_session)]):
    item = LegalExternalSource(**payload.model_dump())
    session.add(item); session.commit(); session.refresh(item)
    return {"id": item.id, **payload.model_dump(), "last_status": item.last_status}


@manage_router.patch("/sources/{source_id}")
def update_source(source_id: str, payload: SourcePayload, _: Annotated[User, Depends(require_permissions("documents:manage"))], session: Annotated[Session, Depends(get_session)]):
    item = session.get(LegalExternalSource, source_id)
    if item is None:
        raise HTTPException(404, "منبع پیدا نشد.")
    for key, value in payload.model_dump().items():
        setattr(item, key, value)
    session.commit()
    return {"id": item.id, **payload.model_dump(), "last_status": item.last_status}


@manage_router.post("/candidates", status_code=201)
def create_candidate(payload: CandidatePayload, _: Annotated[User, Depends(require_permissions("documents:manage"))], session: Annotated[Session, Depends(get_session)]):
    if session.get(LegalExternalSource, payload.source_id) is None:
        raise HTTPException(404, "منبع پیدا نشد.")
    item = LegalUpdateCandidate(**payload.model_dump())
    session.add(item); session.commit(); session.refresh(item)
    return {"id": item.id, "status": item.status}


@manage_router.get("/candidates")
def candidates(_: Annotated[User, Depends(require_permissions("documents:manage"))], session: Annotated[Session, Depends(get_session)], status: str | None = None):
    query = select(LegalUpdateCandidate).order_by(LegalUpdateCandidate.detected_at.desc())
    if status:
        query = query.where(LegalUpdateCandidate.status == status)
    return [{"id": item.id, "source_id": item.source_id, "title": item.title, "article_number": item.article_number, "proposed_text": item.proposed_text, "source_url": item.source_url, "detected_at": item.detected_at, "status": item.status, "review_note": item.review_note} for item in session.scalars(query).all()]


@manage_router.post("/candidates/{candidate_id}/review")
def review_candidate(candidate_id: str, payload: ReviewPayload, user: Annotated[User, Depends(require_permissions("documents:manage"))], session: Annotated[Session, Depends(get_session)]):
    item = session.get(LegalUpdateCandidate, candidate_id)
    if item is None:
        raise HTTPException(404, "به‌روزرسانی پیدا نشد.")
    if item.status != "pending":
        raise HTTPException(409, "این به‌روزرسانی قبلاً بررسی شده است.")
    item.status = payload.decision
    item.review_note = payload.note
    item.reviewer_user_id = user.id
    item.reviewed_at = datetime.now(timezone.utc)
    record_id = None
    if payload.decision == "approved":
        law = LawReferenceRecord(
            id=new_uuid(), source_id=item.source_id, law_name=payload.law_name or item.title,
            chapter="", article_number=item.article_number or "بدون شماره",
            official_text=item.proposed_text, source_url=item.source_url, keywords="",
            category_id=payload.category_id, source_info="به‌روزرسانی تأییدشده",
        )
        session.add(law)
        record_id = law.id
    session.commit()
    return {"status": item.status, "record_id": record_id}
