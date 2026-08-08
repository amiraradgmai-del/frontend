from typing import Annotated

from datetime import datetime, timezone
import uuid
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_session, require_permissions
from app.models.auth import AuditLog, User
from app.models.documents import Document, DocumentChunk, DocumentVersion
from app.models.portal import LawReferenceRecord
from app.models.site import ContentComment, ContentPage, SiteConfiguration, SiteConfigurationVersion
from app.schemas.site import SiteConfigPayload, SiteDraftUpdate, SitePublishRequest, SiteRollbackRequest

router = APIRouter(prefix="/api/v1/site", tags=["site configuration"])


class ContentPagePayload(BaseModel):
    slug: str = Field(min_length=2, max_length=160, pattern=r"^[a-z0-9-]+$")
    title: str = Field(min_length=3, max_length=220)
    excerpt: str = Field(default="", max_length=500)
    content: str = Field(min_length=10, max_length=100_000)
    page_type: str = Field(default="page", pattern="^(page|post)$")
    seo_title: str = Field(default="", max_length=220)
    seo_description: str = Field(default="", max_length=500)
    cover_image_url: str = Field(default="", max_length=500)
    category: str = Field(default="", max_length=100)
    tags: list[str] = Field(default_factory=list, max_length=20)
    is_published: bool = False
    scheduled_at: datetime | None = None


class CommentCreate(BaseModel):
    message: str = Field(min_length=3, max_length=2000)


class CommentReview(BaseModel):
    status: str = Field(pattern="^(approved|rejected)$")
    admin_note: str = Field(default="", max_length=500)


def content_data(item: ContentPage) -> dict:
    return {"id": item.id, "slug": item.slug, "title": item.title, "excerpt": item.excerpt, "content": item.content, "page_type": item.page_type, "seo_title": item.seo_title, "seo_description": item.seo_description, "cover_image_url": item.cover_image_url, "category": item.category, "tags": item.tags, "is_published": item.is_published, "published_at": item.published_at, "scheduled_at": item.scheduled_at, "created_at": item.created_at, "updated_at": item.updated_at}


@router.get("/content")
def public_content(
    session: Annotated[Session, Depends(get_session)],
    page_type: str | None = None,
):
    now = datetime.now(timezone.utc)
    statement = select(ContentPage).where(ContentPage.is_published.is_(True), (ContentPage.scheduled_at.is_(None) | (ContentPage.scheduled_at <= now))).order_by(ContentPage.published_at.desc())
    if page_type:
        statement = statement.where(ContentPage.page_type == page_type)
    return [content_data(item) for item in session.scalars(statement)]


@router.get("/content/{slug}")
def public_content_item(slug: str, session: Annotated[Session, Depends(get_session)]):
    now = datetime.now(timezone.utc)
    item = session.scalar(select(ContentPage).where(ContentPage.slug == slug, ContentPage.is_published.is_(True), (ContentPage.scheduled_at.is_(None) | (ContentPage.scheduled_at <= now))))
    if item is None:
        raise HTTPException(404, "صفحه پیدا نشد.")
    return content_data(item)


@router.get("/content/{slug}/comments")
def public_comments(slug: str, session: Annotated[Session, Depends(get_session)]):
    page = session.scalar(select(ContentPage).where(ContentPage.slug == slug))
    if page is None:
        raise HTTPException(404, "مطلب پیدا نشد.")
    rows = session.execute(select(ContentComment, User.full_name).join(User, User.id == ContentComment.user_id).where(ContentComment.content_id == page.id, ContentComment.status == "approved").order_by(ContentComment.created_at.desc()))
    return [{"id": item.id, "full_name": full_name, "message": item.message, "created_at": item.created_at} for item, full_name in rows]


@router.post("/content/{slug}/comments", status_code=201)
def create_comment(slug: str, payload: CommentCreate, user: Annotated[User, Depends(get_current_user)], session: Annotated[Session, Depends(get_session)]):
    page = session.scalar(select(ContentPage).where(ContentPage.slug == slug, ContentPage.page_type == "post"))
    if page is None:
        raise HTTPException(404, "مطلب پیدا نشد.")
    item = ContentComment(content_id=page.id, user_id=user.id, message=payload.message.strip())
    session.add(item)
    session.commit()
    return {"id": item.id, "status": item.status}


@router.get("/manage/comments")
def manage_comments(user: Annotated[User, Depends(require_permissions("site:manage"))], session: Annotated[Session, Depends(get_session)]):
    del user
    rows = session.execute(select(ContentComment, ContentPage.title, User.full_name).join(ContentPage, ContentPage.id == ContentComment.content_id).join(User, User.id == ContentComment.user_id).order_by(ContentComment.created_at.desc()))
    return [{"id": item.id, "page_title": page_title, "full_name": full_name, "message": item.message, "status": item.status, "admin_note": item.admin_note, "created_at": item.created_at} for item, page_title, full_name in rows]


@router.patch("/manage/comments/{comment_id}")
def review_comment(comment_id: str, payload: CommentReview, user: Annotated[User, Depends(require_permissions("site:manage"))], session: Annotated[Session, Depends(get_session)]):
    item = session.get(ContentComment, comment_id)
    if item is None:
        raise HTTPException(404, "نظر پیدا نشد.")
    item.status = payload.status
    item.admin_note = payload.admin_note.strip()
    session.add(AuditLog(actor_user_id=user.id, action=f"content.comment_{payload.status}", resource_type="content_comment", resource_id=item.id, metadata_json={}))
    session.commit()
    return {"id": item.id, "status": item.status}


@router.post("/manage/content-media", status_code=201)
async def upload_content_media(
    request: Request,
    user: Annotated[User, Depends(require_permissions("site:manage"))],
    file: UploadFile = File(...),
):
    del user
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(422, "فقط فایل تصویری مجاز است.")
    data = await file.read()
    if len(data) > 5 * 1024 * 1024:
        raise HTTPException(422, "حجم تصویر بیشتر از ۵ مگابایت است.")
    extension = (file.filename or "image.jpg").rsplit(".", 1)[-1].lower()
    key = f"content/{uuid.uuid4().hex}.{extension}"
    request.app.state.storage.put(key, data, file.content_type)
    return {"url": f"/api/backend/api/v1/site/content-media/{key.split('/', 1)[1]}"}


@router.get("/content-media/{filename}")
def content_media(filename: str, request: Request):
    key = f"content/{filename}"
    try:
        data = request.app.state.storage.get(key)
    except Exception:
        raise HTTPException(404, "تصویر پیدا نشد.") from None
    return Response(content=data, media_type="image/jpeg", headers={"Cache-Control": "public, max-age=86400"})


@router.get("/manage/content")
def manage_content(
    user: Annotated[User, Depends(require_permissions("site:manage"))],
    session: Annotated[Session, Depends(get_session)],
):
    del user
    return [content_data(item) for item in session.scalars(select(ContentPage).order_by(ContentPage.updated_at.desc()))]


@router.post("/manage/content", status_code=201)
def create_content(
    payload: ContentPagePayload,
    user: Annotated[User, Depends(require_permissions("site:manage"))],
    session: Annotated[Session, Depends(get_session)],
):
    if session.scalar(select(ContentPage.id).where(ContentPage.slug == payload.slug)):
        raise HTTPException(409, "این آدرس قبلاً استفاده شده است.")
    now = datetime.now(timezone.utc)
    item = ContentPage(**payload.model_dump(), created_by=user.id, updated_by=user.id, published_at=now if payload.is_published else None)
    session.add(item)
    session.add(AuditLog(actor_user_id=user.id, action="content.created", resource_type="content_page", resource_id=item.id, metadata_json={"slug": item.slug}))
    session.commit()
    return content_data(item)


@router.patch("/manage/content/{content_id}")
def update_content(
    content_id: str,
    payload: ContentPagePayload,
    user: Annotated[User, Depends(require_permissions("site:manage"))],
    session: Annotated[Session, Depends(get_session)],
):
    item = session.get(ContentPage, content_id)
    if item is None:
        raise HTTPException(404, "محتوا پیدا نشد.")
    duplicate = session.scalar(select(ContentPage.id).where(ContentPage.slug == payload.slug, ContentPage.id != content_id))
    if duplicate:
        raise HTTPException(409, "این آدرس قبلاً استفاده شده است.")
    was_published = item.is_published
    for field, value in payload.model_dump().items():
        setattr(item, field, value)
    item.updated_by = user.id
    if item.is_published and not was_published:
        item.published_at = datetime.now(timezone.utc)
    session.add(AuditLog(actor_user_id=user.id, action="content.updated", resource_type="content_page", resource_id=item.id, metadata_json={"published": item.is_published}))
    session.commit()
    return content_data(item)


@router.delete("/manage/content/{content_id}", status_code=204)
def delete_content(
    content_id: str,
    user: Annotated[User, Depends(require_permissions("site:manage"))],
    session: Annotated[Session, Depends(get_session)],
):
    item = session.get(ContentPage, content_id)
    if item is None:
        raise HTTPException(404, "محتوا پیدا نشد.")
    session.add(AuditLog(actor_user_id=user.id, action="content.deleted", resource_type="content_page", resource_id=item.id, metadata_json={"slug": item.slug}))
    session.delete(item)
    session.commit()
    return None


def default_config() -> dict:
    return SiteConfigPayload().model_dump()


def get_configuration(session: Session) -> SiteConfiguration:
    item = session.get(SiteConfiguration, 1)
    if item is None:
        configuration = default_config()
        item = SiteConfiguration(id=1, draft_json=configuration, published_json=configuration)
        session.add(item)
        if session.scalar(select(SiteConfigurationVersion.id).where(SiteConfigurationVersion.version == 1)) is None:
            session.add(SiteConfigurationVersion(version=1, configuration_json=configuration, note="نسخه اولیه سامانه"))
        session.commit()
        session.refresh(item)
    return item


@router.get("/config")
def public_configuration(session: Annotated[Session, Depends(get_session)]):
    item = get_configuration(session)
    return {"version": item.published_version, "configuration": SiteConfigPayload.model_validate(item.published_json)}


@router.get("/manage")
def manage_configuration(
    request: Request,
    user: Annotated[User, Depends(require_permissions("site:manage"))],
    session: Annotated[Session, Depends(get_session)],
):
    del user
    item = get_configuration(session)
    settings = request.app.state.settings
    return {
        "published_version": item.published_version,
        "draft": SiteConfigPayload.model_validate(item.draft_json),
        "published": SiteConfigPayload.model_validate(item.published_json),
        "updated_at": item.updated_at,
        "services": {
            "environment": settings.environment,
            "ai_provider": "chaka_ai" if settings.gemini_api_key else "disabled",
            "ai_configured": bool(settings.gemini_api_key),
            "generation_model": "پاسخ هوشمند چکاه",
            "embedding_model": "جست‌وجوی معنایی چکاه",
            "email_mode": settings.email_delivery_mode,
            "storage_backend": settings.storage_backend,
        },
        "dataset": {
            "documents": session.scalar(select(func.count(Document.id))) or 0,
            "versions": session.scalar(select(func.count(DocumentVersion.id))) or 0,
            "chunks": session.scalar(select(func.count(DocumentChunk.id))) or 0,
            "starter_records": session.scalar(select(func.count(LawReferenceRecord.id))) or 0,
        },
    }


@router.patch("/manage/draft")
def update_draft(
    payload: SiteDraftUpdate,
    user: Annotated[User, Depends(require_permissions("site:manage"))],
    session: Annotated[Session, Depends(get_session)],
):
    item = get_configuration(session)
    item.draft_json = payload.configuration.model_dump()
    item.updated_by = user.id
    session.add(AuditLog(actor_user_id=user.id, action="site.draft_updated", resource_type="site_configuration", resource_id="1"))
    session.commit()
    return {"ok": True}


@router.post("/manage/publish")
def publish_configuration(
    payload: SitePublishRequest,
    user: Annotated[User, Depends(require_permissions("site:manage"))],
    session: Annotated[Session, Depends(get_session)],
):
    item = get_configuration(session)
    next_version = item.published_version + 1
    item.published_json = item.draft_json
    item.published_version = next_version
    item.updated_by = user.id
    session.add(SiteConfigurationVersion(version=next_version, configuration_json=item.published_json, created_by=user.id, note=payload.note))
    session.add(AuditLog(actor_user_id=user.id, action="site.published", resource_type="site_configuration", resource_id="1", metadata_json={"version": next_version}))
    session.commit()
    return {"ok": True, "version": next_version}


@router.get("/manage/versions")
def configuration_versions(
    user: Annotated[User, Depends(require_permissions("site:manage"))],
    session: Annotated[Session, Depends(get_session)],
):
    del user
    return [{"version": item.version, "note": item.note, "created_at": item.created_at} for item in session.scalars(select(SiteConfigurationVersion).order_by(SiteConfigurationVersion.version.desc()).limit(30))]


@router.post("/manage/rollback")
def rollback_configuration(
    payload: SiteRollbackRequest,
    user: Annotated[User, Depends(require_permissions("site:manage"))],
    session: Annotated[Session, Depends(get_session)],
):
    previous = session.scalar(select(SiteConfigurationVersion).where(SiteConfigurationVersion.version == payload.version))
    if previous is None:
        raise HTTPException(404, "Configuration version not found")
    item = get_configuration(session)
    next_version = item.published_version + 1
    item.draft_json = previous.configuration_json
    item.published_json = previous.configuration_json
    item.published_version = next_version
    item.updated_by = user.id
    session.add(SiteConfigurationVersion(version=next_version, configuration_json=previous.configuration_json, created_by=user.id, note=payload.note))
    session.add(AuditLog(actor_user_id=user.id, action="site.rolled_back", resource_type="site_configuration", resource_id="1", metadata_json={"source_version": payload.version, "version": next_version}))
    session.commit()
    return {"ok": True, "version": next_version}
