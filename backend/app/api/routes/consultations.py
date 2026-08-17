from typing import Annotated, Literal
import re

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import StreamingResponse
from io import BytesIO
from openpyxl import Workbook, load_workbook
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import get_consultation_service, get_current_user, get_security, get_session, require_permissions
from app.core.security import SecurityManager
from app.models.auth import AuditLog, Role, User
from app.models.consultations import ConsultationBooking, ConsultantProfile, ConsultantReview, ConsultantSettlement, ConsultantVerificationRequest, ConsultationRequest
from app.models.portal import UserDocument, UserNotification, UserProfile, WalletAccount, WalletTransaction
from app.schemas.consultations import BookingCreateRequest, ConsultantAdminUpdate, ConsultationCreateRequest, ConsultationHandleRequest, ConsultationManagerResponse, ConsultationResponse, ConsultationUpdateRequest, VerificationRequestCreate, VerificationReviewRequest
from app.services.plans import scaled_limits
from app.services.consultations import ConsultationNotFoundError, ConsultationService, InvalidConsultationError
from app.services.site import feature_enabled
from app.services.email import EmailDeliveryError, EmailSender

router = APIRouter(prefix="/api/v1/consultations", tags=["consultations"])
REQUIRED_VERIFICATION_DOCUMENTS = {
    "independent": {"national_card", "education_certificate", "resume"},
    "company": {"company_registration", "company_national_id", "representative_card"},
}


class BookingStatusUpdate(BaseModel):
    status: str = Field(pattern="^(completed|cancelled)$")
    session_report: str = Field(default="", max_length=5000)


class BookingRescheduleRequest(BaseModel):
    scheduled_at: datetime


class BookingCancelRequest(BaseModel):
    reason: str = Field(default="", max_length=1000)


class ConsultantReviewRequest(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: str = Field(default="", max_length=1000)


class ConsultantBlockRequest(BaseModel):
    days: int = Field(ge=1, le=365)
    reason: str = Field(min_length=5, max_length=1000)


class ReviewModerationRequest(BaseModel):
    status: str = Field(pattern="^(published|hidden)$")


class CompanyConsultantCreate(BaseModel):
    consultant_type: Literal["company", "independent"] = "company"
    full_name: str = Field(min_length=3, max_length=120)
    email: EmailStr
    initial_password: str = Field(min_length=8, max_length=128)
    phone: str = Field(default="", max_length=20)
    professional_title: str = Field(min_length=3, max_length=160)
    bio: str = Field(min_length=20, max_length=3000)
    specialties: list[str] = Field(min_length=1, max_length=20)
    skills: list[str] = Field(default_factory=list, max_length=20)
    qualifications: str = Field(default="", max_length=2000)
    years_experience: int = Field(default=0, ge=0, le=70)
    consultation_price: int = Field(default=0, ge=0, le=1_000_000_000)
    city: str = Field(default="", max_length=80)
    office_address: str = Field(default="", max_length=300)
    profile_image_url: str = Field(default="", max_length=500)
    is_online: bool = True
    offers_in_person: bool = False
    is_available: bool = True


@router.post("", response_model=ConsultationResponse, status_code=status.HTTP_201_CREATED)
def create(payload: ConsultationCreateRequest, user: Annotated[User, Depends(get_current_user)], service: Annotated[ConsultationService, Depends(get_consultation_service)], session: Annotated[Session, Depends(get_session)]):
    if not feature_enabled(session, "consultations_enabled"):
        raise HTTPException(status_code=503, detail="Consultations are disabled")
    try:
        return service.create(subject=payload.subject, description=payload.description, source_message_id=payload.source_message_id, use_wallet_if_needed=payload.use_wallet_if_needed, user=user)
    except InvalidConsultationError as error:
        raise HTTPException(status_code=422, detail=str(error)) from None


@router.get("", response_model=list[ConsultationResponse])
def mine(user: Annotated[User, Depends(get_current_user)], service: Annotated[ConsultationService, Depends(get_consultation_service)]):
    return service.list_for_user(user)


def profile_data(profile: ConsultantProfile, user: User) -> dict:
    return {"id": profile.user_id, "slug": profile.slug, "full_name": user.full_name, "email": user.email or "", "consultant_type": profile.consultant_type, "professional_title": profile.professional_title, "bio": profile.bio, "specialties": profile.specialties, "skills": profile.skills, "qualifications": profile.qualifications, "education": profile.education, "certifications": profile.certifications, "work_history": profile.work_history, "weekly_schedule": profile.weekly_schedule, "profile_image_url": profile.profile_image_url, "years_experience": profile.years_experience, "rating": profile.rating, "review_count": profile.review_count, "consultation_price": profile.consultation_price, "city": profile.city, "office_address": profile.office_address, "is_online": profile.is_online, "offers_in_person": profile.offers_in_person, "is_verified": profile.is_verified, "is_available": profile.is_available, "boosted_until": profile.boosted_until, "account_active": user.is_active, "created_at": profile.created_at}


def consultant_slug(user: User) -> str:
    source = user.email or getattr(user, "phone", None) or user.full_name or "consultant"
    safe = re.sub(r"[^a-zA-Z0-9-]+", "-", source.split("@", 1)[0]).strip("-").lower()
    return f"{(safe or 'consultant')[:40]}-{user.id[:8]}"


def verification_data(item: ConsultantVerificationRequest, account: User) -> dict:
    return {
        "id": item.id,
        "user_id": item.user_id,
        "full_name": account.full_name,
        "email": account.email,
        "consultant_type": item.consultant_type,
        "professional_title": item.professional_title,
        "national_id": item.national_id,
        "license_number": item.license_number,
        "specialties": item.specialties,
        "years_experience": item.years_experience,
        "qualifications": item.qualifications,
        "document_ids": item.document_ids,
        "profile_payload": item.profile_payload,
        "status": item.status,
        "applicant_note": item.applicant_note,
        "admin_note": item.admin_note,
        "reviewed_by": item.reviewed_by,
        "reviewed_at": item.reviewed_at,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
    }


@router.get("/verification/mine")
def my_verification_requests(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
):
    items = session.scalars(
        select(ConsultantVerificationRequest)
        .where(ConsultantVerificationRequest.user_id == user.id)
        .order_by(ConsultantVerificationRequest.created_at.desc())
    ).all()
    return [verification_data(item, user) for item in items]


@router.post("/verification", status_code=201)
def request_verification(
    payload: VerificationRequestCreate,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
):
    active = session.scalar(
        select(ConsultantVerificationRequest).where(
            ConsultantVerificationRequest.user_id == user.id,
            ConsultantVerificationRequest.status == "pending",
        )
    )
    if active is not None:
        raise HTTPException(
            409,
            "یک درخواست فعال یا تأییدشده برای این حساب وجود دارد.",
        )
    effective_document_ids = list(payload.document_ids)
    existing_profile = session.get(ConsultantProfile, user.id)
    if existing_profile is not None and not effective_document_ids:
        previous_approved = session.scalar(select(ConsultantVerificationRequest).where(ConsultantVerificationRequest.user_id == user.id, ConsultantVerificationRequest.status == "approved").order_by(ConsultantVerificationRequest.updated_at.desc()))
        effective_document_ids = list(previous_approved.document_ids) if previous_approved else []
    owned_documents = list(session.scalars(select(UserDocument).where(UserDocument.user_id == user.id, UserDocument.id.in_(effective_document_ids))).all()) if effective_document_ids else []
    if {document.id for document in owned_documents} != set(effective_document_ids):
        raise HTTPException(422, "یک یا چند مدرک انتخاب‌شده معتبر نیست.")
    required_types = REQUIRED_VERIFICATION_DOCUMENTS[payload.consultant_type]
    uploaded_types = {document.document_type for document in owned_documents if document.purpose == "consultant_verification"}
    missing_types = sorted(required_types - uploaded_types)
    if missing_types:
        labels = {
            "national_card": "کارت ملی",
            "education_certificate": "مدرک تحصیلی مرتبط",
            "resume": "رزومه حرفه‌ای",
            "company_registration": "آگهی ثبت یا آخرین تغییرات شرکت",
            "company_national_id": "شناسه ملی شرکت",
            "representative_card": "کارت ملی نماینده شرکت",
        }
        raise HTTPException(422, "مدارک الزامی ناقص است: " + "، ".join(labels[item] for item in missing_types))
    item = ConsultantVerificationRequest(
        user_id=user.id,
        consultant_type=payload.consultant_type,
        professional_title=payload.professional_title.strip(),
        national_id=payload.national_id,
        license_number=payload.license_number.strip(),
        specialties=sorted(set(value.strip() for value in payload.specialties if value.strip())),
        years_experience=payload.years_experience,
        qualifications=payload.qualifications.strip(),
        document_ids=effective_document_ids,
        applicant_note=payload.applicant_note.strip(),
        profile_payload={
            "bio": payload.bio.strip(),
            "skills": payload.skills,
            "education": payload.education,
            "certifications": payload.certifications,
            "work_history": payload.work_history,
            "weekly_schedule": payload.weekly_schedule,
            "profile_image_url": payload.profile_image_url.strip(),
            "consultation_price": payload.consultation_price,
            "city": payload.city.strip(),
            "office_address": payload.office_address.strip(),
            "is_online": payload.is_online,
            "offers_in_person": payload.offers_in_person,
        },
    )
    session.add(item)
    session.add(
        AuditLog(
            actor_user_id=user.id,
            action="consultant.verification_requested",
            resource_type="consultant_verification",
            resource_id=item.id,
            metadata_json={"consultant_type": item.consultant_type},
        )
    )
    session.commit()
    session.refresh(item)
    return verification_data(item, user)


@router.get("/manage/verifications")
def manage_verifications(
    user: Annotated[User, Depends(require_permissions("consultations:manage"))],
    session: Annotated[Session, Depends(get_session)],
    request_status: Annotated[str | None, Query(alias="status")] = None,
):
    del user
    statement = (
        select(ConsultantVerificationRequest, User)
        .join(User, User.id == ConsultantVerificationRequest.user_id)
        .order_by(ConsultantVerificationRequest.created_at.desc())
    )
    if request_status:
        statement = statement.where(
            ConsultantVerificationRequest.status == request_status
        )
    result = []
    for item, account in session.execute(statement):
        data = verification_data(item, account)
        documents = list(session.scalars(select(UserDocument).where(UserDocument.id.in_(item.document_ids))).all()) if item.document_ids else []
        data["documents"] = [{"id": document.id, "title": document.title, "document_type": document.document_type, "description": document.description, "status": document.status, "download_url": f"/api/backend/api/v1/admin/user-documents/{document.id}/download"} for document in documents]
        result.append(data)
    return result


@router.patch("/manage/verifications/{request_id}")
def review_verification(
    request_id: str,
    payload: VerificationReviewRequest,
    request: Request,
    actor: Annotated[User, Depends(require_permissions("consultations:manage"))],
    session: Annotated[Session, Depends(get_session)],
):
    item = session.get(ConsultantVerificationRequest, request_id)
    if item is None:
        raise HTTPException(404, "درخواست احراز صلاحیت پیدا نشد.")
    if item.status == "approved":
        raise HTTPException(409, "درخواست تأییدشده قابل بررسی مجدد نیست.")
    if payload.status in ("rejected", "correction_required") and not payload.admin_note.strip():
        raise HTTPException(422, "برای رد یا درخواست اصلاح، توضیح مدیر الزامی است.")
    account = session.get(User, item.user_id)
    if account is None:
        raise HTTPException(404, "حساب متقاضی پیدا نشد.")

    item.status = payload.status
    item.admin_note = payload.admin_note.strip()
    item.reviewed_by = actor.id
    item.reviewed_at = datetime.now(timezone.utc)
    if payload.status == "approved":
        role_name = "tax_expert" if item.consultant_type == "independent" else "company_expert"
        role = session.scalar(select(Role).where(Role.name == role_name))
        if role is None:
            raise HTTPException(500, "نقش مشاور در سامانه پیکربندی نشده است.")
        account.roles = [role]
        profile = session.get(ConsultantProfile, account.id)
        if profile is None:
            profile = ConsultantProfile(
                user_id=account.id,
                slug=f"{account.email.split('@', 1)[0][:40]}-{account.id[:8]}",
                consultant_type=item.consultant_type,
                professional_title=item.professional_title,
                bio=item.qualifications,
            )
            session.add(profile)
        profile.consultant_type = item.consultant_type
        profile.professional_title = item.professional_title
        profile.specialties = item.specialties
        profile.qualifications = item.qualifications
        profile.years_experience = item.years_experience
        for field, value in (item.profile_payload or {}).items():
            if hasattr(profile, field):
                setattr(profile, field, value)
        profile.is_verified = True
        profile.is_available = True
    session.add(
        AuditLog(
            actor_user_id=actor.id,
            action=f"consultant.verification_{payload.status}",
            resource_type="consultant_verification",
            resource_id=item.id,
            metadata_json={"user_id": item.user_id},
        )
    )
    session.add(
        UserNotification(
            user_id=item.user_id,
            title="نتیجه بررسی پروفایل مشاور",
            message=(
                "پروفایل حرفه‌ای شما تأیید شد."
                if payload.status == "approved"
                else payload.admin_note.strip()
            ),
            notification_type="consultant_profile",
            action_url="/consultant/profile",
        )
    )
    session.commit()
    try:
        EmailSender(request.app.state.settings).send_notification(
            account.email,
            "نتیجه بررسی صلاحیت مشاور",
            "پروفایل حرفه‌ای شما تأیید شد." if payload.status == "approved" else payload.admin_note.strip(),
        )
    except EmailDeliveryError:
        pass
    return verification_data(item, account)


@router.get("/manage/dashboard")
def consultant_dashboard(
    user: Annotated[User, Depends(require_permissions("consultations:manage"))],
    session: Annotated[Session, Depends(get_session)],
):
    del user
    counts = dict(
        session.execute(
            select(
                ConsultantProfile.consultant_type,
                func.count(ConsultantProfile.user_id),
            ).group_by(ConsultantProfile.consultant_type)
        ).all()
    )
    statuses = dict(
        session.execute(
            select(
                ConsultantVerificationRequest.status,
                func.count(ConsultantVerificationRequest.id),
            ).group_by(ConsultantVerificationRequest.status)
        ).all()
    )
    active = session.scalar(
        select(func.count(ConsultantProfile.user_id))
        .join(User, User.id == ConsultantProfile.user_id)
        .where(
            User.is_active.is_(True),
            ConsultantProfile.is_available.is_(True),
        )
    ) or 0
    return {
        "independent": counts.get("independent", 0),
        "company": counts.get("company", 0),
        "pending": statuses.get("pending", 0),
        "approved": statuses.get("approved", 0),
        "rejected": statuses.get("rejected", 0),
        "correction_required": statuses.get("correction_required", 0),
        "active": active,
        "inactive": sum(counts.values()) - active,
    }


@router.get("/manage/profiles")
def manage_profiles(
    user: Annotated[User, Depends(require_permissions("consultations:manage"))],
    session: Annotated[Session, Depends(get_session)],
    consultant_type: Annotated[str | None, Query(alias="type")] = None,
):
    del user
    statement = (
        select(ConsultantProfile, User)
        .join(User, User.id == ConsultantProfile.user_id)
        .where(ConsultantProfile.deleted_at.is_(None))
        .order_by(User.full_name)
    )
    if consultant_type:
        statement = statement.where(
            ConsultantProfile.consultant_type == consultant_type
        )
    return [
        profile_data(profile, account)
        for profile, account in session.execute(statement)
    ]


@router.get("/profile/mine")
def my_consultant_profile(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
):
    profile = session.get(ConsultantProfile, user.id)
    if profile is None:
        role_names = {role.name for role in user.roles}
        consultant_type = "company" if "company_expert" in role_names else "independent"
        if not role_names.intersection({"company_expert", "tax_expert"}):
            raise HTTPException(403, "این حساب نقش مشاور ندارد.")
        approved = session.scalar(
            select(ConsultantVerificationRequest)
            .where(
                ConsultantVerificationRequest.user_id == user.id,
                ConsultantVerificationRequest.status == "approved",
            )
            .order_by(ConsultantVerificationRequest.updated_at.desc())
        )
        profile = ConsultantProfile(
            user_id=user.id,
            slug=consultant_slug(user),
            consultant_type=consultant_type,
            professional_title=approved.professional_title if approved else "مشاور مالیاتی",
            bio=approved.qualifications if approved else "",
            specialties=approved.specialties if approved else [],
            qualifications=approved.qualifications if approved else "",
            years_experience=approved.years_experience if approved else 0,
            is_verified=approved is not None,
            is_available=approved is not None,
        )
        session.add(profile)
        session.commit()
        session.refresh(profile)
    requests = session.scalars(
        select(ConsultantVerificationRequest)
        .where(ConsultantVerificationRequest.user_id == user.id)
        .order_by(ConsultantVerificationRequest.created_at.desc())
    ).all()
    result = profile_data(profile, user)
    result["verification_requests"] = [verification_data(item, user) for item in requests]
    return result


@router.get("/manage/deleted-profiles")
def deleted_consultant_profiles(
    actor: Annotated[User, Depends(require_permissions("consultations:manage"))],
    session: Annotated[Session, Depends(get_session)],
):
    del actor
    rows = session.execute(
        select(ConsultantProfile, User)
        .join(User, User.id == ConsultantProfile.user_id)
        .where(ConsultantProfile.deleted_at.is_not(None))
        .order_by(ConsultantProfile.deleted_at.desc())
    )
    return [profile_data(profile, account) | {"deleted_at": profile.deleted_at} for profile, account in rows]


@router.post("/profile/boost")
def boost_my_profile(
    user: Annotated[User, Depends(require_permissions("consultations:handle"))],
    session: Annotated[Session, Depends(get_session)],
):
    profile = session.get(ConsultantProfile, user.id)
    if profile is None or not profile.is_verified or not profile.is_available:
        raise HTTPException(422, "فقط پروفایل فعال و تأییدشده قابل ارتقا است.")
    price = 99_000
    wallet = session.get(WalletAccount, user.id)
    if wallet is None or wallet.balance < price:
        raise HTTPException(422, "موجودی کیف پول برای ارتقای هفت‌روزه کافی نیست.")
    now = datetime.now(timezone.utc)
    start = profile.boosted_until if profile.boosted_until and profile.boosted_until > now else now
    profile.boosted_until = start + timedelta(days=7)
    wallet.balance -= price
    session.add(WalletTransaction(user_id=user.id, transaction_type="purchase", amount=price, status="completed", reference=f"BOOST-{uuid.uuid4().hex[:12].upper()}", related_type="consultant_boost", related_id=user.id, otp_hash="", otp_expires_at=now, processed_at=now))
    session.add(AuditLog(actor_user_id=user.id, action="consultant.profile_boosted", resource_type="consultant_profile", resource_id=user.id, metadata_json={"price": price, "boosted_until": profile.boosted_until.isoformat()}))
    session.commit()
    return {"ok": True, "price": price, "boosted_until": profile.boosted_until, "wallet_balance": wallet.balance}


@router.get("/manage/bookings")
def manage_bookings(
    actor: Annotated[User, Depends(require_permissions("consultations:manage"))],
    session: Annotated[Session, Depends(get_session)],
    booking_status: Annotated[str | None, Query(alias="status")] = None,
):
    del actor
    statement = select(ConsultationBooking, User, ConsultantProfile).join(User, User.id == ConsultationBooking.user_id).join(ConsultantProfile, ConsultantProfile.user_id == ConsultationBooking.consultant_id).order_by(ConsultationBooking.scheduled_at.desc())
    if booking_status:
        statement = statement.where(ConsultationBooking.status == booking_status)
    consultants = {item.user_id: session.get(User, item.user_id) for item in session.scalars(select(ConsultantProfile)).all()}
    return [{"id": booking.id, "scheduled_at": booking.scheduled_at, "status": booking.status, "mode": booking.mode, "price": booking.price, "refund_amount": booking.refund_amount, "cancelled_by": booking.cancelled_by, "cancellation_reason": booking.cancellation_reason, "client": {"id": client.id, "full_name": client.full_name, "email": client.email}, "consultant": {"id": profile.user_id, "full_name": consultants[profile.user_id].full_name if consultants.get(profile.user_id) else profile.slug}} for booking, client, profile in session.execute(statement)]


@router.patch("/manage/profiles/{consultant_id}")
def update_consultant_profile(
    consultant_id: str,
    payload: ConsultantAdminUpdate,
    actor: Annotated[User, Depends(require_permissions("consultations:manage"))],
    session: Annotated[Session, Depends(get_session)],
):
    profile = session.get(ConsultantProfile, consultant_id)
    account = session.get(User, consultant_id)
    if profile is None or account is None:
        raise HTTPException(404, "پروفایل مشاور پیدا نشد.")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(profile, field, value)
    session.add(
        AuditLog(
            actor_user_id=actor.id,
            action="consultant.profile_updated",
            resource_type="consultant_profile",
            resource_id=profile.user_id,
            metadata_json={"fields": sorted(payload.model_fields_set)},
        )
    )
    session.commit()
    return profile_data(profile, account)


@router.get("/manage/profiles/{consultant_id}/details")
def consultant_details(
    consultant_id: str,
    actor: Annotated[User, Depends(require_permissions("consultations:manage"))],
    session: Annotated[Session, Depends(get_session)],
):
    del actor
    profile = session.get(ConsultantProfile, consultant_id)
    account = session.get(User, consultant_id)
    if profile is None or account is None:
        raise HTTPException(404, "پروفایل مشاور پیدا نشد.")
    documents = session.scalars(select(UserDocument).where(UserDocument.user_id == consultant_id).order_by(UserDocument.created_at.desc())).all()
    requests = session.scalars(select(ConsultantVerificationRequest).where(ConsultantVerificationRequest.user_id == consultant_id).order_by(ConsultantVerificationRequest.created_at.desc())).all()
    reviews = session.scalars(select(ConsultantReview).where(ConsultantReview.consultant_id == consultant_id).order_by(ConsultantReview.created_at.desc())).all()
    completed = session.scalar(select(func.count(ConsultationBooking.id)).where(ConsultationBooking.consultant_id == consultant_id, ConsultationBooking.status == "completed")) or 0
    cancelled = session.scalar(select(func.count(ConsultationBooking.id)).where(ConsultationBooking.consultant_id == consultant_id, ConsultationBooking.status == "cancelled")) or 0
    revenue = session.scalar(select(func.sum(ConsultationBooking.price)).where(ConsultationBooking.consultant_id == consultant_id, ConsultationBooking.status == "completed")) or 0
    return {
        "profile": profile_data(profile, account) | {"bank_account_holder": profile.bank_account_holder, "bank_iban": profile.bank_iban, "blocked_until": profile.blocked_until, "blocked_reason": profile.blocked_reason, "contract_number": profile.contract_number, "contract_start": profile.contract_start, "contract_end": profile.contract_end, "contract_status": profile.contract_status},
        "documents": [{"id": item.id, "title": item.title, "filename": item.original_filename, "status": item.status, "created_at": item.created_at} for item in documents],
        "verification_history": [verification_data(item, account) for item in requests],
        "reviews": [{"id": item.id, "rating": item.rating, "comment": item.comment, "status": item.moderation_status, "created_at": item.created_at} for item in reviews],
        "stats": {"completed_sessions": completed, "cancelled_sessions": cancelled, "gross_revenue": revenue},
    }


@router.delete("/manage/profiles/{consultant_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_consultant_profile(
    consultant_id: str,
    actor: Annotated[User, Depends(require_permissions("consultations:manage"))],
    session: Annotated[Session, Depends(get_session)],
):
    profile = session.get(ConsultantProfile, consultant_id)
    account = session.get(User, consultant_id)
    if profile is None or account is None:
        raise HTTPException(404, "پروفایل مشاور پیدا نشد.")
    if actor.id == consultant_id:
        raise HTTPException(422, "امکان حذف پروفایل مدیریتی خودتان وجود ندارد.")
    profile.deleted_at = datetime.now(timezone.utc)
    profile.is_available = False
    profile.is_verified = False
    account.is_active = False
    session.add(AuditLog(
        actor_user_id=actor.id,
        action="consultant.profile_deleted",
        resource_type="consultant_profile",
        resource_id=consultant_id,
        metadata_json={"email": account.email, "consultant_type": profile.consultant_type},
    ))
    session.commit()
    return None


@router.post("/manage/profiles/{consultant_id}/restore")
def restore_consultant_profile(
    consultant_id: str,
    actor: Annotated[User, Depends(require_permissions("consultations:manage"))],
    session: Annotated[Session, Depends(get_session)],
):
    profile = session.get(ConsultantProfile, consultant_id)
    account = session.get(User, consultant_id)
    if profile is None or account is None or profile.deleted_at is None:
        raise HTTPException(404, "مشاور حذف‌شده پیدا نشد.")
    profile.deleted_at = None
    profile.is_available = True
    account.is_active = True
    session.add(AuditLog(actor_user_id=actor.id, action="consultant.profile_restored", resource_type="consultant_profile", resource_id=consultant_id, metadata_json={}))
    session.commit()
    return profile_data(profile, account)


@router.post("/manage/profiles/{consultant_id}/block")
def block_consultant(
    consultant_id: str,
    payload: ConsultantBlockRequest,
    actor: Annotated[User, Depends(require_permissions("consultations:manage"))],
    session: Annotated[Session, Depends(get_session)],
):
    profile = session.get(ConsultantProfile, consultant_id)
    if profile is None:
        raise HTTPException(404, "مشاور پیدا نشد.")
    profile.blocked_until = datetime.now(timezone.utc) + timedelta(days=payload.days)
    profile.blocked_reason = payload.reason.strip()
    profile.is_available = False
    session.add(UserNotification(user_id=consultant_id, title="دسترسی مشاور موقتاً تعلیق شد", message=payload.reason.strip(), notification_type="consultant_profile", action_url="/consultant/profile"))
    session.add(AuditLog(actor_user_id=actor.id, action="consultant.blocked", resource_type="consultant_profile", resource_id=consultant_id, metadata_json={"days": payload.days, "reason": payload.reason}))
    session.commit()
    return {"blocked_until": profile.blocked_until}


@router.patch("/manage/reviews/{review_id}")
def moderate_consultant_review(
    review_id: str,
    payload: ReviewModerationRequest,
    actor: Annotated[User, Depends(require_permissions("consultations:manage"))],
    session: Annotated[Session, Depends(get_session)],
):
    review = session.get(ConsultantReview, review_id)
    if review is None:
        raise HTTPException(404, "نظر پیدا نشد.")
    review.moderation_status = payload.status
    session.add(AuditLog(actor_user_id=actor.id, action="consultant.review_moderated", resource_type="consultant_review", resource_id=review_id, metadata_json={"status": payload.status}))
    session.commit()
    return {"id": review.id, "status": review.moderation_status}


@router.get("/advisors")
def advisors(session: Annotated[Session, Depends(get_session)], user: Annotated[User, Depends(get_current_user)], consultant_type: Annotated[str, Query(alias="type")] = "independent"):
    del user
    now = datetime.now(timezone.utc)
    rows = session.execute(select(ConsultantProfile, User).join(User, User.id == ConsultantProfile.user_id).where(ConsultantProfile.consultant_type == consultant_type, ConsultantProfile.is_verified.is_(True), ConsultantProfile.is_available.is_(True), ConsultantProfile.deleted_at.is_(None), (ConsultantProfile.blocked_until.is_(None) | (ConsultantProfile.blocked_until < now))).order_by((ConsultantProfile.boosted_until.is_not(None) & (ConsultantProfile.boosted_until > now)).desc(), ConsultantProfile.rating.desc(), User.full_name))
    return [profile_data(profile, account) for profile, account in rows]


@router.get("/public/advisors")
def public_advisors(
    session: Annotated[Session, Depends(get_session)],
    city: str | None = None,
    limit: int = Query(default=6, ge=1, le=24),
):
    statement = (
        select(ConsultantProfile, User)
        .join(User, User.id == ConsultantProfile.user_id)
        .where(
            ConsultantProfile.consultant_type == "independent",
            ConsultantProfile.is_verified.is_(True),
            ConsultantProfile.is_available.is_(True),
            ConsultantProfile.deleted_at.is_(None),
            (
                ConsultantProfile.blocked_until.is_(None)
                | (ConsultantProfile.blocked_until < datetime.now(timezone.utc))
            ),
            User.is_active.is_(True),
        )
        .order_by((ConsultantProfile.boosted_until.is_not(None) & (ConsultantProfile.boosted_until > datetime.now(timezone.utc))).desc(), ConsultantProfile.rating.desc(), ConsultantProfile.review_count.desc())
        .limit(limit)
    )
    if city:
        statement = statement.where(func.lower(ConsultantProfile.city) == city.strip().lower())
    return [profile_data(profile, account) for profile, account in session.execute(statement)]


@router.get("/public/advisors/{slug}")
def public_advisor(slug: str, session: Annotated[Session, Depends(get_session)]):
    row = session.execute(
        select(ConsultantProfile, User)
        .join(User, User.id == ConsultantProfile.user_id)
        .where(
            ConsultantProfile.slug == slug,
            ConsultantProfile.consultant_type == "independent",
            ConsultantProfile.is_verified.is_(True),
            ConsultantProfile.is_available.is_(True),
            ConsultantProfile.deleted_at.is_(None),
            (
                ConsultantProfile.blocked_until.is_(None)
                | (ConsultantProfile.blocked_until < datetime.now(timezone.utc))
            ),
            User.is_active.is_(True),
        )
    ).first()
    if row is None:
        raise HTTPException(404, "مشاور پیدا نشد")
    result = profile_data(row[0], row[1])
    booked = set(
        session.scalars(
            select(ConsultationBooking.scheduled_at).where(
                ConsultationBooking.consultant_id == row[0].user_id,
                ConsultationBooking.status == "reserved",
                ConsultationBooking.scheduled_at >= datetime.now(timezone.utc),
            )
        ).all()
    )
    slots = []
    for day in range(1, 8):
        current = (datetime.now(timezone.utc) + timedelta(days=day)).replace(
            minute=0, second=0, microsecond=0
        )
        for hour in (9, 11, 14, 16):
            slot = current.replace(hour=hour)
            if slot not in booked:
                slots.append(slot)
    result["available_slots"] = slots
    return result


@router.get("/advisors/{slug}")
def advisor(slug: str, session: Annotated[Session, Depends(get_session)], user: Annotated[User, Depends(get_current_user)]):
    del user
    row = session.execute(select(ConsultantProfile, User).join(User, User.id == ConsultantProfile.user_id).where(ConsultantProfile.slug == slug, ConsultantProfile.is_verified.is_(True))).first()
    if row is None: raise HTTPException(404, "مشاور پیدا نشد")
    result = profile_data(row[0], row[1])
    booked = set(session.scalars(select(ConsultationBooking.scheduled_at).where(ConsultationBooking.consultant_id == row[0].user_id, ConsultationBooking.status == "reserved", ConsultationBooking.scheduled_at >= datetime.now(timezone.utc))).all())
    slots = []
    for day in range(1, 8):
        date = (datetime.now(timezone.utc) + timedelta(days=day)).replace(minute=0, second=0, microsecond=0)
        for hour in (9, 11, 14, 16):
            slot = date.replace(hour=hour)
            if slot not in booked: slots.append(slot)
    result["available_slots"] = slots
    return result


@router.get("/company/quota")
def company_quota(user: Annotated[User, Depends(get_current_user)], session: Annotated[Session, Depends(get_session)]):
    month_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    limits = {"normal": {"consultations": 1}, "plus": {"consultations": 2}, "pro": {"consultations": 10}}
    limit = scaled_limits(session, user, limits)["consultations"]
    used = session.scalar(select(func.count(ConsultationRequest.id)).where(ConsultationRequest.user_id == user.id, ConsultationRequest.created_at >= month_start)) or 0
    wallet = session.get(WalletAccount, user.id)
    return {"free_limit": limit, "used": min(used, limit), "remaining": max(0, limit - used), "next_price": 149000, "wallet_balance": wallet.balance if wallet else 0}


@router.get("/bookings/mine")
def my_bookings(user: Annotated[User, Depends(get_current_user)], session: Annotated[Session, Depends(get_session)]):
    rows = session.execute(select(ConsultationBooking, ConsultantProfile, User).join(ConsultantProfile, ConsultantProfile.user_id == ConsultationBooking.consultant_id).join(User, User.id == ConsultantProfile.user_id).where(ConsultationBooking.user_id == user.id).order_by(ConsultationBooking.scheduled_at.desc()))
    reviewed = set(session.scalars(select(ConsultantReview.booking_id).where(ConsultantReview.user_id == user.id)).all())
    return [{"id": booking.id, "consultant_name": account.full_name, "slug": profile.slug, "scheduled_at": booking.scheduled_at, "mode": booking.mode, "status": booking.status, "price": booking.price, "reviewed": booking.id in reviewed} for booking, profile, account in rows]


@router.patch("/bookings/{booking_id}/reschedule")
def reschedule_booking(booking_id: str, payload: BookingRescheduleRequest, user: Annotated[User, Depends(get_current_user)], session: Annotated[Session, Depends(get_session)]):
    booking = session.scalar(select(ConsultationBooking).where(ConsultationBooking.id == booking_id, ConsultationBooking.user_id == user.id))
    if booking is None or booking.status != "reserved":
        raise HTTPException(404, "رزرو فعال پیدا نشد")
    current = booking.scheduled_at if booking.scheduled_at.tzinfo else booking.scheduled_at.replace(tzinfo=timezone.utc)
    if current - datetime.now(timezone.utc) < timedelta(hours=12):
        raise HTTPException(422, "تغییر زمان فقط تا ۱۲ ساعت قبل از جلسه ممکن است")
    target = payload.scheduled_at if payload.scheduled_at.tzinfo else payload.scheduled_at.replace(tzinfo=timezone.utc)
    if target <= datetime.now(timezone.utc):
        raise HTTPException(422, "زمان جدید معتبر نیست")
    booking.scheduled_at = target
    session.add(UserNotification(user_id=booking.consultant_id, title="زمان رزرو تغییر کرد", message=f"زمان جلسه به {target.isoformat()} تغییر کرد.", notification_type="booking", action_url="/consultant"))
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(409, "زمان انتخابی قبلاً رزرو شده است") from None
    return {"id": booking.id, "scheduled_at": booking.scheduled_at}


@router.post("/bookings/{booking_id}/cancel")
def cancel_booking(booking_id: str, user: Annotated[User, Depends(get_current_user)], session: Annotated[Session, Depends(get_session)], payload: BookingCancelRequest = BookingCancelRequest()):
    booking = session.scalar(select(ConsultationBooking).where(ConsultationBooking.id == booking_id, ConsultationBooking.user_id == user.id))
    if booking is None or booking.status != "reserved":
        raise HTTPException(404, "رزرو فعال پیدا نشد")
    scheduled = booking.scheduled_at if booking.scheduled_at.tzinfo else booking.scheduled_at.replace(tzinfo=timezone.utc)
    if scheduled <= datetime.now(timezone.utc):
        raise HTTPException(422, "جلسه شروع شده و قابل لغو نیست")
    refund = booking.price if scheduled - datetime.now(timezone.utc) >= timedelta(hours=24) else booking.price // 2
    wallet = session.get(WalletAccount, user.id)
    if wallet is None:
        wallet = WalletAccount(user_id=user.id)
        session.add(wallet)
    wallet.balance += refund
    booking.status = "cancelled"
    booking.cancelled_by = "user"
    booking.cancellation_reason = payload.reason.strip()
    booking.refund_amount = refund
    reference = f"REFUND-{booking.id[:12].upper()}"
    session.add(WalletTransaction(user_id=user.id, transaction_type="refund", amount=refund, status="completed", reference=reference, related_type="consultation_booking", related_id=booking.id, otp_hash="", otp_expires_at=datetime.now(timezone.utc), processed_at=datetime.now(timezone.utc)))
    session.add(UserNotification(user_id=booking.consultant_id, title="رزرو لغو شد", message="کاربر جلسه رزروشده را لغو کرد.", notification_type="booking", action_url="/consultant"))
    session.commit()
    return {"ok": True, "refund": refund}


@router.post("/bookings/{booking_id}/review", status_code=201)
def review_booking(booking_id: str, payload: ConsultantReviewRequest, user: Annotated[User, Depends(get_current_user)], session: Annotated[Session, Depends(get_session)]):
    booking = session.scalar(select(ConsultationBooking).where(ConsultationBooking.id == booking_id, ConsultationBooking.user_id == user.id))
    if booking is None or booking.status != "completed":
        raise HTTPException(422, "فقط جلسه انجام‌شده قابل امتیازدهی است")
    if session.scalar(select(ConsultantReview.id).where(ConsultantReview.booking_id == booking.id)):
        raise HTTPException(409, "برای این جلسه قبلاً امتیاز ثبت شده است")
    session.add(ConsultantReview(booking_id=booking.id, user_id=user.id, consultant_id=booking.consultant_id, rating=payload.rating, comment=payload.comment.strip()))
    profile = session.get(ConsultantProfile, booking.consultant_id)
    total = profile.rating * profile.review_count + payload.rating
    profile.review_count += 1
    profile.rating = round(total / profile.review_count, 2)
    session.commit()
    return {"ok": True, "rating": profile.rating, "review_count": profile.review_count}


@router.get("/bookings/consultant/me")
def consultant_bookings(user: Annotated[User, Depends(require_permissions("consultations:handle"))], session: Annotated[Session, Depends(get_session)]):
    rows = session.execute(
        select(ConsultationBooking, User, UserProfile)
        .join(User, User.id == ConsultationBooking.user_id)
        .outerjoin(UserProfile, UserProfile.user_id == User.id)
        .where(ConsultationBooking.consultant_id == user.id)
        .order_by(ConsultationBooking.scheduled_at)
    )
    return [
        {
            "id": booking.id,
            "scheduled_at": booking.scheduled_at,
            "duration_minutes": booking.duration_minutes,
            "mode": booking.mode,
            "status": booking.status,
            "price": booking.price,
            "notes": booking.notes,
            "session_report": booking.session_report,
            "client": {
                "full_name": account.full_name,
                "phone": profile.phone if profile else "",
                "city": profile.city if profile else "",
                "company_name": profile.company_name if profile else "",
                "job_title": profile.job_title if profile else "",
                "taxpayer_type": profile.taxpayer_type if profile else "individual",
            },
        }
        for booking, account, profile in rows
    ]


@router.patch("/bookings/consultant/{booking_id}")
def update_consultant_booking(booking_id: str, payload: BookingStatusUpdate, user: Annotated[User, Depends(require_permissions("consultations:handle"))], session: Annotated[Session, Depends(get_session)]):
    booking = session.scalar(select(ConsultationBooking).where(ConsultationBooking.id == booking_id, ConsultationBooking.consultant_id == user.id))
    if booking is None:
        raise HTTPException(404, "رزرو پیدا نشد")
    if booking.status != "reserved":
        raise HTTPException(422, "این رزرو قبلاً تعیین تکلیف شده است")
    booking.status = payload.status
    booking.session_report = payload.session_report.strip()
    if payload.status == "cancelled":
        booking.cancelled_by = "consultant"
        booking.cancellation_reason = payload.session_report.strip()
        booking.refund_amount = booking.price
        wallet = session.get(WalletAccount, booking.user_id)
        if wallet is None:
            wallet = WalletAccount(user_id=booking.user_id)
            session.add(wallet)
        wallet.balance += booking.price
        now = datetime.now(timezone.utc)
        session.add(WalletTransaction(user_id=booking.user_id, transaction_type="refund", amount=booking.price, status="completed", reference=f"REFUND-{booking.id[:12].upper()}", related_type="consultation_booking", related_id=booking.id, otp_hash="", otp_expires_at=now, processed_at=now))
    session.add(UserNotification(user_id=booking.user_id, title="وضعیت جلسه به‌روزرسانی شد", message="وضعیت رزرو شما توسط مشاور تغییر کرد.", notification_type="booking", action_url="/app/consultations/independent"))
    session.commit()
    return {"id": booking.id, "status": booking.status}


@router.post("/bookings", status_code=201)
def create_booking(payload: BookingCreateRequest, user: Annotated[User, Depends(get_current_user)], session: Annotated[Session, Depends(get_session)]):
    if user.account_tier == "normal":
        raise HTTPException(403, "رزرو مشاور مستقل فقط برای کاربران دارای اشتراک پلاس یا حرفه‌ای فعال است.")
    profile = session.get(ConsultantProfile, payload.consultant_id)
    if profile is not None and payload.mode == "online" and not profile.is_online:
        raise HTTPException(422, "این مشاور، مشاوره آنلاین ارائه نمی‌دهد.")
    if profile is not None and payload.mode == "in_person" and not profile.offers_in_person:
        raise HTTPException(422, "این مشاور، مشاوره حضوری ارائه نمی‌دهد.")
    if profile is None or profile.consultant_type != "independent" or not profile.is_available: raise HTTPException(404, "مشاور در دسترس نیست")
    scheduled_at = payload.scheduled_at if payload.scheduled_at.tzinfo else payload.scheduled_at.replace(tzinfo=timezone.utc)
    if scheduled_at <= datetime.now(timezone.utc): raise HTTPException(422, "زمان رزرو معتبر نیست")
    wallet = session.get(WalletAccount, user.id)
    if wallet is None or wallet.balance < profile.consultation_price: raise HTTPException(422, "موجودی کیف پول برای رزرو کافی نیست")
    wallet.balance -= profile.consultation_price
    booking_id = str(uuid.uuid4())
    booking = ConsultationBooking(id=booking_id, user_id=user.id, consultant_id=profile.user_id, scheduled_at=scheduled_at, duration_minutes=30, mode=payload.mode, price=profile.consultation_price, notes=payload.notes.strip())
    session.add(booking)
    session.add(UserNotification(user_id=user.id, title="رزرو مشاور ثبت شد", message=f"جلسه شما برای {scheduled_at.isoformat()} ثبت شد.", notification_type="booking", action_url="/app/consultations/independent"))
    session.add(UserNotification(user_id=profile.user_id, title="رزرو جدید", message="یک جلسه جدید برای شما ثبت شد.", notification_type="booking", action_url="/consultant"))
    session.add(WalletTransaction(user_id=user.id, transaction_type="consultation", amount=profile.consultation_price, status="completed", reference=f"BOOK-{booking_id[:12].upper()}", related_type="consultation_booking", related_id=booking_id, otp_hash="", otp_expires_at=datetime.now(timezone.utc), processed_at=datetime.now(timezone.utc)))
    try: session.commit()
    except IntegrityError: session.rollback(); raise HTTPException(409, "این زمان قبلاً رزرو شده است") from None
    return {"id": booking.id, "status": booking.status, "scheduled_at": booking.scheduled_at, "price": booking.price}


@router.get("/manage/all", response_model=list[ConsultationManagerResponse])
def manage_all(user: Annotated[User, Depends(require_permissions("consultations:manage"))], service: Annotated[ConsultationService, Depends(get_consultation_service)], request_status: Annotated[str | None, Query(alias="status")] = None):
    del user
    return service.list_all(request_status)


@router.get("/manage/consultants")
def consultants(
    user: Annotated[User, Depends(require_permissions("consultations:manage"))],
    session: Annotated[Session, Depends(get_session)],
):
    del user
    rows = session.execute(
        select(User.id, User.full_name, User.email).distinct()
        .join(User.roles)
        .where(Role.name.in_(("company_expert", "tax_expert", "consultant")), User.is_active.is_(True))
        .order_by(User.full_name)
    )
    return [{"id": user_id, "full_name": full_name, "email": email} for user_id, full_name, email in rows]


@router.post("/manage/company-consultants", status_code=status.HTTP_201_CREATED)
def create_company_consultant(
    payload: CompanyConsultantCreate,
    actor: Annotated[User, Depends(require_permissions("consultations:manage"))],
    session: Annotated[Session, Depends(get_session)],
    security: Annotated[SecurityManager, Depends(get_security)],
):
    email = str(payload.email).strip().lower()
    if session.scalar(select(User.id).where(func.lower(User.email) == email)):
        raise HTTPException(409, "این ایمیل قبلاً ثبت شده است.")

    role_name = "company_expert" if payload.consultant_type == "company" else "tax_expert"
    role = session.scalar(select(Role).where(Role.name == role_name))
    if role is None:
        raise HTTPException(503, "نقش کارشناس شرکت در سامانه فعال نیست.")

    user_id = str(uuid.uuid4())
    slug = f"{payload.consultant_type}-{uuid.uuid4().hex[:12]}"
    account = User(
        id=user_id,
        email=email,
        email_verified_at=datetime.now(timezone.utc),
        password_hash=security.hash_password(payload.initial_password),
        full_name=payload.full_name.strip(),
        account_tier="normal",
        is_active=True,
        must_change_password=True,
        roles=[role],
    )
    profile = ConsultantProfile(
        user_id=user_id,
        slug=slug,
        consultant_type=payload.consultant_type,
        professional_title=payload.professional_title.strip(),
        bio=payload.bio.strip(),
        specialties=[item.strip() for item in payload.specialties if item.strip()],
        skills=[item.strip() for item in payload.skills if item.strip()],
        qualifications=payload.qualifications.strip(),
        years_experience=payload.years_experience,
        consultation_price=payload.consultation_price,
        city=payload.city.strip(),
        office_address=payload.office_address.strip(),
        profile_image_url=payload.profile_image_url.strip(),
        is_online=payload.is_online,
        offers_in_person=payload.offers_in_person,
        is_verified=True,
        is_available=payload.is_available,
    )
    user_profile = UserProfile(
        user_id=user_id,
        phone=payload.phone.strip(),
        city=payload.city.strip(),
        job_title=payload.professional_title.strip(),
        taxpayer_type="legal",
        bio=payload.bio.strip(),
        referral_code=uuid.uuid4().hex[:10].upper(),
    )
    session.add_all([account, profile, user_profile])
    session.add(
        AuditLog(
            actor_user_id=actor.id,
            action="company_consultant.create",
            resource_type="consultant_profile",
            resource_id=user_id,
            metadata_json={"email": email, "professional_title": profile.professional_title},
        )
    )
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(409, "ایمیل یا شناسه این مشاور قبلاً استفاده شده است.") from None
    return {
        "id": user_id,
        "full_name": account.full_name,
        "email": account.email,
        "role": role_name,
        "slug": slug,
        "is_verified": True,
    }


@router.get("/manage/consultants-import-template.xlsx")
def consultant_import_template(
    _: Annotated[User, Depends(require_permissions("consultations:manage"))],
):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "consultants"
    sheet.append(["consultant_type", "full_name", "email", "initial_password", "phone", "professional_title", "bio", "specialties", "skills", "qualifications", "years_experience", "consultation_price", "city", "office_address", "is_online", "offers_in_person", "is_available"])
    sheet.append(["independent", "نمونه مشاور", "advisor@example.com", "ChangeMe123!", "09120000000", "مشاور ارشد مالیاتی", "معرفی کوتاه و سوابق مشاور", "ارزش افزوده، مالیات عملکرد", "تنظیم لایحه، حسابرسی", "کارشناسی ارشد و گواهی‌های حرفه‌ای", 8, 500000, "شیراز", "آدرس دفتر", True, True, True])
    sheet.freeze_panes = "A2"
    stream = BytesIO()
    workbook.save(stream)
    stream.seek(0)
    return StreamingResponse(stream, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": 'attachment; filename="consultants-import-template.xlsx"'})


@router.post("/manage/consultants-import")
async def import_consultants(
    file: Annotated[UploadFile, File(...)],
    actor: Annotated[User, Depends(require_permissions("consultations:manage"))],
    session: Annotated[Session, Depends(get_session)],
    security: Annotated[SecurityManager, Depends(get_security)],
):
    if not (file.filename or "").lower().endswith(".xlsx"):
        raise HTTPException(422, "فقط فایل Excel با پسوند xlsx قابل قبول است.")
    try:
        workbook = load_workbook(BytesIO(await file.read()), read_only=True, data_only=True)
        sheet = workbook.active
        rows = list(sheet.iter_rows(values_only=True))
    except Exception as error:
        raise HTTPException(422, "فایل Excel قابل خواندن نیست.") from error
    if not rows:
        raise HTTPException(422, "فایل Excel خالی است.")
    headers = [str(value or "").strip() for value in rows[0]]
    required = {"consultant_type", "full_name", "email", "initial_password", "professional_title", "bio", "specialties"}
    if not required.issubset(headers):
        raise HTTPException(422, "ستون‌های فایل با قالب راهنما مطابقت ندارند.")
    created, errors = 0, []
    for number, values in enumerate(rows[1:], start=2):
        data = dict(zip(headers, values))
        if not any(value not in (None, "") for value in values):
            continue
        try:
            with session.begin_nested():
                email = str(data.get("email") or "").strip().lower()
                if session.scalar(select(User.id).where(func.lower(User.email) == email)):
                    raise ValueError("ایمیل قبلاً ثبت شده است")
                consultant_type = str(data.get("consultant_type") or "independent").strip().lower()
                role = session.scalar(select(Role).where(Role.name == ("company_expert" if consultant_type == "company" else "tax_expert")))
                if role is None:
                    raise ValueError("نقش مشاور در سامانه فعال نیست")
                user_id = str(uuid.uuid4())
                list_value = lambda key: [item.strip() for item in str(data.get(key) or "").replace(",", "،").split("،") if item.strip()]
                boolean = lambda key, default=True: str(data.get(key) if data.get(key) is not None else default).strip().lower() in {"true", "1", "yes", "بله"}
                account = User(id=user_id, email=email, email_verified_at=datetime.now(timezone.utc), password_hash=security.hash_password(str(data.get("initial_password") or "")), full_name=str(data.get("full_name") or "").strip(), account_tier="normal", is_active=True, must_change_password=True, roles=[role])
                profile = ConsultantProfile(user_id=user_id, slug=f"{consultant_type}-{uuid.uuid4().hex[:12]}", consultant_type=consultant_type, professional_title=str(data.get("professional_title") or "").strip(), bio=str(data.get("bio") or "").strip(), specialties=list_value("specialties"), skills=list_value("skills"), qualifications=str(data.get("qualifications") or "").strip(), years_experience=int(data.get("years_experience") or 0), consultation_price=int(data.get("consultation_price") or 0), city=str(data.get("city") or "").strip(), office_address=str(data.get("office_address") or "").strip(), is_online=boolean("is_online"), offers_in_person=boolean("offers_in_person", False), is_verified=True, is_available=boolean("is_available"))
                user_profile = UserProfile(user_id=user_id, phone=str(data.get("phone") or "").strip(), city=profile.city, job_title=profile.professional_title, taxpayer_type="legal", bio=profile.bio, referral_code=uuid.uuid4().hex[:10].upper())
                session.add_all([account, profile, user_profile])
                session.flush()
            created += 1
        except Exception as error:
            errors.append({"row": number, "error": str(error)})
    session.add(AuditLog(actor_user_id=actor.id, action="consultant.excel_import", resource_type="consultant_profile", resource_id="bulk", metadata_json={"created": created, "errors": len(errors)}))
    session.commit()
    return {"created": created, "failed": len(errors), "errors": errors[:50]}


@router.patch("/manage/{consultation_id}", response_model=ConsultationManagerResponse)
def manage_update(consultation_id: str, payload: ConsultationUpdateRequest, user: Annotated[User, Depends(require_permissions("consultations:manage"))], service: Annotated[ConsultationService, Depends(get_consultation_service)]):
    try:
        return service.update(consultation_id, status=payload.status, priority=payload.priority, assigned_to=payload.assigned_to, internal_note=payload.internal_note, resolution=payload.resolution, note=payload.note, user=user)
    except ConsultationNotFoundError:
        raise HTTPException(status_code=404, detail="Consultation not found") from None
    except InvalidConsultationError as error:
        raise HTTPException(status_code=422, detail=str(error)) from None


@router.get("/assigned/me", response_model=list[ConsultationManagerResponse])
def assigned_to_me(
    user: Annotated[User, Depends(require_permissions("consultations:handle"))],
    service: Annotated[ConsultationService, Depends(get_consultation_service)],
):
    return service.list_assigned(user)


@router.patch("/assigned/{consultation_id}", response_model=ConsultationManagerResponse)
def handle_assigned(
    consultation_id: str,
    payload: ConsultationHandleRequest,
    user: Annotated[User, Depends(require_permissions("consultations:handle"))],
    service: Annotated[ConsultationService, Depends(get_consultation_service)],
):
    try:
        return service.handle_assigned(
            consultation_id,
            status=payload.status,
            internal_note=payload.internal_note,
            resolution=payload.resolution,
            note=payload.note,
            user=user,
        )
    except ConsultationNotFoundError:
        raise HTTPException(status_code=404, detail="Consultation not found") from None
    except InvalidConsultationError as error:
        raise HTTPException(status_code=422, detail=str(error)) from None


@router.get("/{consultation_id}", response_model=ConsultationResponse)
def get_one(consultation_id: str, user: Annotated[User, Depends(get_current_user)], service: Annotated[ConsultationService, Depends(get_consultation_service)]):
    try:
        return service.get_for_user(consultation_id, user)
    except ConsultationNotFoundError:
        raise HTTPException(status_code=404, detail="Consultation not found") from None
