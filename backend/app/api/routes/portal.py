import hashlib
import hmac
import json
import re
import secrets
import uuid
from io import BytesIO
from datetime import date, datetime, timedelta, timezone
from typing import Annotated, Literal
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import RedirectResponse, StreamingResponse
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.api.dependencies import get_current_user, get_session, require_permissions
from app.documents.storage import ObjectStorage
from app.documents.validation import FileValidationError, validate_upload
from app.models.advisor import ChatMessage, Conversation
from app.models.auth import Role, User
from app.models.portal import (
    DiscountCode,
    Payment,
    PaymentMethod,
    PaymentOtpChallenge,
    PhoneVerificationChallenge,
    SubscriptionPlan,
    SupportTicket,
    TicketMessage,
    UserDocument,
    UserNotification,
    UserProfile,
    UserSubscription,
    WalletAccount,
    WalletTransaction,
)
from app.services.email import EmailDeliveryError, EmailSender
from app.services.plans import package_price, scaled_limits
from app.services.sms import MelipayamakSender, SmsDeliveryError
from app.services.zarinpal import ZarinpalError, ZarinpalGateway

PROFILE_COMPLETION_THRESHOLD = 85

PROFILE_REQUIRED_FIELDS = {
    "phone": "شماره موبایل تأییدشده",
    "province": "استان",
    "city": "شهر",
    "taxpayer_type": "نوع مؤدی",
}


router = APIRouter(prefix="/api/v1/portal", tags=["customer portal"])
admin_router = APIRouter(prefix="/api/v1/admin", tags=["admin portal"])


class ProfileUpdate(BaseModel):
    email: EmailStr | None = None
    phone: str = Field(default="", max_length=20)
    alternate_phone: str = Field(default="", max_length=20)
    alternate_email: EmailStr | None = None
    province: str = Field(default="", max_length=80)
    city: str = Field(default="", max_length=80)
    postal_code: str = Field(default="", max_length=10, pattern=r"^$|^[0-9]{10}$")
    address: str = Field(default="", max_length=500)
    birth_date: date | None = None
    company_name: str = Field(default="", max_length=160)
    job_title: str = Field(default="", max_length=100)
    business_type: str = Field(default="", max_length=80)
    economic_code: str = Field(default="", max_length=20, pattern=r"^$|^[0-9]{8,20}$")
    website: str = Field(default="", max_length=300)
    taxpayer_type: str = Field(default="individual", max_length=30)
    preferred_contact_method: Literal["phone", "sms", "email", "both"] = "phone"
    marketing_notifications: bool = False
    service_notifications: bool = True
    bio: str = Field(default="", max_length=1000)


class AdminProfileUpdate(ProfileUpdate):
    reward_points: int | None = Field(default=None, ge=0, le=10_000_000)


class PhoneCodeRequest(BaseModel):
    phone: str = Field(min_length=10, max_length=20)


class PhoneCodeVerify(BaseModel):
    request_id: str = Field(min_length=1, max_length=36)
    code: str = Field(pattern=r"^[0-9]{6}$")


class CardCreate(BaseModel):
    card_number: str = Field(min_length=16, max_length=25)
    cardholder_name: str = Field(min_length=2, max_length=120)


class CheckoutRequest(BaseModel):
    plan_code: str
    package: Literal["silver", "gold", "diamond"] = "silver"
    payment_method_id: str | None = None
    discount_code: str = Field(default="", max_length=32)
    otp_request_id: str | None = None
    otp_code: str = Field(default="", max_length=6, pattern="^$|^[0-9]{6}$")


class WalletRequest(BaseModel):
    transaction_type: Literal["charge", "withdraw"]
    amount: int = Field(ge=10_000, le=100_000_000)


class WalletAmountRequest(BaseModel):
    amount: int = Field(ge=10_000, le=100_000_000)


class WalletConfirm(BaseModel):
    transaction_id: str
    code: str = Field(pattern="^[0-9]{6}$")


class WalletCheckoutRequest(BaseModel):
    plan_code: str
    package: Literal["silver", "gold", "diamond"] = "silver"
    discount_code: str = Field(default="", max_length=32)


class ZarinpalCheckoutRequest(BaseModel):
    plan_code: str
    package: Literal["silver", "gold", "diamond"] = "silver"
    discount_code: str = Field(default="", max_length=32)


class TicketCreate(BaseModel):
    subject: str = Field(min_length=3, max_length=200)
    category: str = Field(default="general", max_length=40)
    message: str = Field(min_length=5, max_length=5000)


class MessageCreate(BaseModel):
    message: str = Field(min_length=1, max_length=5000)


class DocumentAdminUpdate(BaseModel):
    status: str = Field(pattern="^(uploaded|reviewing|accepted|rejected)$")
    admin_note: str = Field(default="", max_length=2000)


class DiscountCreate(BaseModel):
    code: str = Field(min_length=3, max_length=32, pattern="^[A-Za-z0-9_-]+$")
    percent: int = Field(ge=1, le=100)
    max_uses: int = Field(default=100, ge=1, le=100000)
    is_active: bool = True


class DiscountUpdate(BaseModel):
    percent: int | None = Field(default=None, ge=1, le=100)
    max_uses: int | None = Field(default=None, ge=1, le=100000)
    is_active: bool | None = None


class SubscriptionAdminUpdate(BaseModel):
    status: str = Field(pattern="^(active|cancelled)$")


class PlanAdminUpdate(BaseModel):
    price: int = Field(ge=0, le=100_000_000)
    duration_days: int = Field(ge=1, le=3650)
    is_active: bool


class TicketAdminUpdate(BaseModel):
    status: str = Field(pattern="^(open|answered|closed)$")


PLAN_LIMITS = {
    "normal": {"documents": 1, "tickets": 1},
    "plus": {"documents": 5, "tickets": 5},
    "pro": {"documents": 20, "tickets": 20},
}

SUPPORT_FAQ = (
    (
        ("اشتراک", "پلن", "بسته"),
        "برای تهیه اشتراک وارد بخش «اشتراک و پرداخت» شوید، بسته مناسب را انتخاب کنید و پرداخت را انجام دهید. اشتراک بعد از پرداخت موفق خودکار فعال می‌شود.",
    ),
    (
        ("پرداخت ناموفق", "پرداخت نشد", "پول کم شد"),
        "اگر مبلغ کسر شده ولی پرداخت ناموفق است، شماره پیگیری و زمان پرداخت را در همین گفتگو بفرستید. بازگشت وجه بانکی معمولاً تا ۷۲ ساعت کاری انجام می‌شود.",
    ),
    (
        ("ارسال فایل", "فایل مالیاتی", "آپلود فایل", "مدرک", "سند", "پیوست"),
        "از بخش «اسناد من» فایل را بارگذاری کنید. برای ارسال مستقیم به پشتیبانی نیز می‌توانید از دکمه پیوست داخل همین گفتگو استفاده کنید.",
    ),
    (
        ("رزرو", "نوبت", "مشاور"),
        "از «لیست مشاوران» مشاور و زمان آزاد را انتخاب کنید. برای نهایی‌شدن رزرو باید یکی از اشتراک‌های فعال را داشته باشید.",
    ),
)


def profile_for(session: Session, user: User) -> UserProfile:
    profile = session.get(UserProfile, user.id)
    if profile is None:
        profile = UserProfile(user_id=user.id, referral_code=user.id.replace("-", "")[:10].upper())
        session.add(profile); session.commit(); session.refresh(profile)
    return profile


def profile_data(profile: UserProfile, user: User | None = None) -> dict:
    missing_required_fields = profile_missing_required_fields(profile)
    return {
        "email": user.email if user else "",
        "phone": profile.phone,
        "alternate_phone": profile.alternate_phone,
        "alternate_email": profile.alternate_email,
        "phone_verified": profile.phone_verified,
        "phone_verified_at": profile.phone_verified_at,
        "province": profile.province,
        "city": profile.city,
        "postal_code": profile.postal_code,
        "address": profile.address,
        "birth_date": profile.birth_date,
        "company_name": profile.company_name,
        "job_title": profile.job_title,
        "business_type": profile.business_type,
        "economic_code": profile.economic_code,
        "website": profile.website,
        "taxpayer_type": profile.taxpayer_type,
        "preferred_contact_method": profile.preferred_contact_method,
        "marketing_notifications": profile.marketing_notifications,
        "service_notifications": profile.service_notifications,
        "bio": profile.bio,
        "profile_score": profile.profile_score,
        "reward_points": profile.reward_points,
        "referral_code": profile.referral_code,
        "profile_complete": not missing_required_fields,
        "missing_required_fields": missing_required_fields,
    }


def normalize_iranian_phone(value: str) -> str:
    translated = value.strip().translate(
        str.maketrans(
            "۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩",
            "01234567890123456789",
        )
    )
    compact = re.sub(r"[\s\-()]", "", translated)

    if compact.startswith("+98"):
        compact = "0" + compact[3:]
    elif compact.startswith("0098"):
        compact = "0" + compact[4:]
    elif compact.startswith("98") and len(compact) == 12:
        compact = "0" + compact[2:]

    if not re.fullmatch(r"09[0-9]{9}", compact):
        raise HTTPException(422, "شماره موبایل معتبر نیست؛ مانند 09123456789 وارد کنید.")

    return compact


def optional_iranian_phone(value: str) -> str:
    return normalize_iranian_phone(value) if value.strip() else ""


def refresh_profile_score(profile: UserProfile) -> None:
    profile.profile_score = min(
        100,
        10
        + (25 if profile.phone and profile.phone_verified else 0)
        + (25 if profile.province.strip() else 0)
        + (20 if profile.city.strip() else 0)
        + (20 if profile.taxpayer_type.strip() else 0),
    )


def profile_missing_required_fields(profile: UserProfile) -> list[str]:
    missing: list[str] = []
    if not profile.phone or not profile.phone_verified:
        missing.append(PROFILE_REQUIRED_FIELDS["phone"])
    if not profile.province.strip():
        missing.append(PROFILE_REQUIRED_FIELDS["province"])
    if not profile.city.strip():
        missing.append(PROFILE_REQUIRED_FIELDS["city"])
    if not profile.taxpayer_type.strip():
        missing.append(PROFILE_REQUIRED_FIELDS["taxpayer_type"])
    return missing


def aware_datetime(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def masked_phone(phone: str) -> str:
    return f"{phone[:4]}***{phone[-4:]}"


def plan_data(plan: SubscriptionPlan) -> dict:
    return {"id":plan.id,"code":plan.code,"title":plan.title,"description":plan.description,"price":plan.price,"duration_days":plan.duration_days,"benefits":plan.benefits,"is_active":plan.is_active}


def ticket_data(ticket: SupportTicket, session: Session) -> dict:
    staff = session.get(User, ticket.assigned_staff_id) if ticket.assigned_staff_id else None
    online_cutoff = datetime.now(timezone.utc) - timedelta(minutes=5)
    return {"id":ticket.id,"user_id":ticket.user_id,"subject":ticket.subject,"category":ticket.category,"priority":ticket.priority,"status":ticket.status,"assigned_staff_id":ticket.assigned_staff_id,"assigned_staff_name":staff.full_name if staff else "تیم پشتیبانی","staff_online":bool(staff and staff.last_seen_at and aware_datetime(staff.last_seen_at) >= online_cutoff),"staff_last_seen_at":staff.last_seen_at if staff else None,"created_at":ticket.created_at,"updated_at":ticket.updated_at,"messages":[{"id":m.id,"message":m.message,"is_staff":m.is_staff,"attachment_name":m.attachment_name,"attachment_mime":m.attachment_mime,"attachment_url":f"/api/backend/api/v1/portal/tickets/attachments/{m.id}" if m.attachment_key else "","created_at":m.created_at} for m in ticket.messages]}


def best_available_staff(session: Session) -> User | None:
    return session.scalar(select(User).join(User.roles).where(Role.name.in_(("admin", "support_admin", "system_admin")), User.is_active.is_(True)).order_by(User.last_seen_at.desc().nullslast(), User.updated_at.desc()))


def support_faq_answer(subject: str, message: str) -> str | None:
    normalized = f"{subject} {message}".replace("ي", "ی").replace("ك", "ک").lower()
    best_answer: str | None = None
    best_score = 0
    for keywords, answer in SUPPORT_FAQ:
        score = sum(keyword in normalized for keyword in keywords)
        if score > best_score:
            best_score = score
            best_answer = answer
    return best_answer if best_score else None


@router.get("/overview")
def overview(user: Annotated[User, Depends(get_current_user)], session: Annotated[Session, Depends(get_session)]):
    profile = profile_for(session, user)
    subscription = session.scalar(select(UserSubscription).where(UserSubscription.user_id == user.id, UserSubscription.status == "active").order_by(UserSubscription.ends_at.desc()))
    remaining_percent = None
    if subscription:
        starts_at = subscription.starts_at.replace(tzinfo=timezone.utc) if subscription.starts_at.tzinfo is None else subscription.starts_at
        ends_at = subscription.ends_at.replace(tzinfo=timezone.utc) if subscription.ends_at.tzinfo is None else subscription.ends_at
        total_seconds = max(1, (ends_at - starts_at).total_seconds())
        remaining_percent = max(0, min(100, round((ends_at - datetime.now(timezone.utc)).total_seconds() / total_seconds * 100)))
    return {"profile":profile_data(profile, user),"subscription":({"plan":plan_data(subscription.plan),"package":subscription.package_code,"starts_at":subscription.starts_at,"ends_at":subscription.ends_at,"remaining_percent":remaining_percent,"auto_renew":subscription.auto_renew} if subscription else None),"documents":session.scalar(select(func.count(UserDocument.id)).where(UserDocument.user_id==user.id)) or 0,"tickets":session.scalar(select(func.count(SupportTicket.id)).where(SupportTicket.user_id==user.id,SupportTicket.status!="closed")) or 0,"chats":session.scalar(select(func.count(Conversation.id)).where(Conversation.user_id==user.id,Conversation.deleted_at.is_(None))) or 0}


@router.get("/profile")
def get_profile(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
):
    return profile_data(profile_for(session, user), user)


@router.get("/account/export")
def export_my_account(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
):
    profile = profile_for(session, user)
    payments = session.scalars(select(Payment).where(Payment.user_id == user.id).order_by(Payment.created_at.desc())).all()
    transactions = session.scalars(select(WalletTransaction).where(WalletTransaction.user_id == user.id).order_by(WalletTransaction.created_at.desc())).all()
    payload = {
        "account": {"id": user.id, "full_name": user.full_name, "email": user.email, "tier": user.account_tier, "created_at": user.created_at.isoformat()},
        "profile": profile_data(profile, user),
        "payments": [{"amount": item.amount, "status": item.status, "reference": item.gateway_reference, "created_at": item.created_at.isoformat()} for item in payments],
        "wallet_transactions": [{"type": item.transaction_type, "amount": item.amount, "status": item.status, "reference": item.reference, "created_at": item.created_at.isoformat()} for item in transactions],
    }
    content = json.dumps(payload, ensure_ascii=False, default=str, indent=2).encode("utf-8")
    return StreamingResponse(BytesIO(content), media_type="application/json; charset=utf-8", headers={"Content-Disposition": 'attachment; filename="my-account-data.json"'})


@router.post("/account/delete-request", status_code=201)
def request_account_deletion(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
):
    existing = session.scalar(select(SupportTicket).where(SupportTicket.user_id == user.id, SupportTicket.category == "account_deletion", SupportTicket.status != "closed"))
    if existing:
        return {"ok": True, "ticket_id": existing.id, "already_requested": True}
    staff = best_available_staff(session)
    ticket = SupportTicket(user_id=user.id, assigned_staff_id=staff.id if staff else None, subject="درخواست حذف حساب کاربری", category="account_deletion", priority="high")
    session.add(ticket)
    session.flush()
    session.add(TicketMessage(ticket_id=ticket.id, sender_user_id=user.id, message="کاربر درخواست بررسی و حذف حساب و اطلاعات مرتبط را ثبت کرده است.", is_staff=False))
    session.commit()
    return {"ok": True, "ticket_id": ticket.id, "already_requested": False}


@router.patch("/profile")
def update_profile(
    payload: ProfileUpdate,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
):
    profile = profile_for(session, user)
    values = payload.model_dump(exclude_unset=True)

    if "email" in values:
        new_email = values.pop("email")
        normalized_email = str(new_email).strip().lower() if new_email else None
        if normalized_email != user.email:
            duplicate = session.scalar(select(User.id).where(func.lower(User.email) == normalized_email, User.id != user.id)) if normalized_email else None
            if duplicate:
                raise HTTPException(409, "این ایمیل قبلاً برای حساب دیگری ثبت شده است.")
            user.email = normalized_email
            user.email_verified_at = None

    if "phone" in values:
        new_phone = values.pop("phone").strip()
        if new_phone:
            new_phone = normalize_iranian_phone(new_phone)
        if new_phone != profile.phone:
            profile.phone = new_phone
            profile.phone_verified = False
            profile.phone_verified_at = None

    if "alternate_phone" in values:
        values["alternate_phone"] = optional_iranian_phone(values["alternate_phone"])
    if "alternate_email" in values:
        values["alternate_email"] = str(values["alternate_email"] or "").strip().lower()
    for key, value in values.items():
        setattr(profile, key, value.strip() if isinstance(value, str) else value)
    refresh_profile_score(profile)

    if (
        profile.profile_score >= PROFILE_COMPLETION_THRESHOLD
        and not profile.completion_rewarded
    ):
        profile.reward_points += 500
        profile.completion_rewarded = True

    session.commit()
    return profile_data(profile, user)


@router.post("/profile/phone/send-code", status_code=201)
def send_phone_verification_code(
    payload: PhoneCodeRequest,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
):
    settings = request.app.state.settings
    if (
        not settings.melipayamak_username
        or not settings.melipayamak_api_key
        or settings.melipayamak_body_id is None
    ):
        raise HTTPException(503, "سرویس پیامک هنوز به‌درستی تنظیم نشده است.")

    phone = normalize_iranian_phone(payload.phone)
    now = datetime.now(timezone.utc)

    latest = session.scalar(
        select(PhoneVerificationChallenge)
        .where(PhoneVerificationChallenge.user_id == user.id)
        .order_by(PhoneVerificationChallenge.last_sent_at.desc())
        .limit(1)
    )
    if latest is not None:
        elapsed = (now - aware_datetime(latest.last_sent_at)).total_seconds()
        if elapsed < settings.verification_resend_seconds:
            retry_after = max(1, int(settings.verification_resend_seconds - elapsed))
            raise HTTPException(
                429,
                f"برای ارسال دوباره کد، {retry_after} ثانیه صبر کنید.",
                headers={"Retry-After": str(retry_after)},
            )

    code = f"{secrets.randbelow(900000) + 100000}"
    phone = ""
    if transaction_type == "withdraw":
        profile = session.get(UserProfile, user.id)
        phone = profile.phone.strip() if profile else ""
        if not profile or not phone or not profile.phone_verified:
            raise HTTPException(422, "برای برداشت وجه، ابتدا شماره موبایل خود را در پروفایل تأیید کنید.")
    challenge = PhoneVerificationChallenge(
        user_id=user.id,
        phone=phone,
        code_hash="",
        expires_at=now + timedelta(minutes=settings.verification_code_minutes),
        last_sent_at=now,
    )
    session.add(challenge)
    session.flush()
    challenge.code_hash = hashlib.sha256(
        f"{challenge.id}:{code}".encode("utf-8")
    ).hexdigest()

    try:
        MelipayamakSender(settings).send_verification_code(phone, code)
    except SmsDeliveryError:
        session.rollback()
        raise HTTPException(
            503,
            "ارسال پیامک ممکن نشد؛ چند دقیقه دیگر دوباره تلاش کنید.",
        ) from None

    session.commit()
    return {
        "request_id": challenge.id,
        "phone": masked_phone(phone),
        "expires_in": settings.verification_code_minutes * 60,
        "resend_after": settings.verification_resend_seconds,
    }


@router.post("/profile/phone/verify")
def verify_phone_code(
    payload: PhoneCodeVerify,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
):
    challenge = session.scalar(
        select(PhoneVerificationChallenge).where(
            PhoneVerificationChallenge.id == payload.request_id,
            PhoneVerificationChallenge.user_id == user.id,
        )
    )

    if challenge is None or challenge.used_at is not None:
        raise HTTPException(422, "درخواست تأیید شماره موبایل معتبر نیست.")

    now = datetime.now(timezone.utc)
    if aware_datetime(challenge.expires_at) < now:
        raise HTTPException(422, "کد تأیید منقضی شده است؛ کد جدید بگیرید.")

    settings_max_attempts = 5
    if challenge.attempts >= settings_max_attempts:
        raise HTTPException(429, "تعداد تلاش مجاز تمام شده است؛ کد جدید بگیرید.")

    expected = hashlib.sha256(
        f"{challenge.id}:{payload.code}".encode("utf-8")
    ).hexdigest()
    if not hmac.compare_digest(challenge.code_hash, expected):
        challenge.attempts += 1
        session.commit()
        raise HTTPException(422, "کد تأیید صحیح نیست.")

    profile = profile_for(session, user)
    profile.phone = challenge.phone
    profile.phone_verified = True
    profile.phone_verified_at = now
    challenge.used_at = now

    refresh_profile_score(profile)

    if (
        profile.profile_score >= PROFILE_COMPLETION_THRESHOLD
        and not profile.completion_rewarded
    ):
        profile.reward_points += 500
        profile.completion_rewarded = True

    session.commit()
    return {
        "ok": True,
        "message": "شماره موبایل با موفقیت تأیید شد.",
        "profile": profile_data(profile, user),
    }


@router.get("/plans")
def plans(session: Annotated[Session, Depends(get_session)], user: Annotated[User, Depends(get_current_user)]):
    del user; return [plan_data(item) for item in session.scalars(select(SubscriptionPlan).where(SubscriptionPlan.is_active.is_(True)).order_by(SubscriptionPlan.sort_order))]


def luhn(number: str) -> bool:
    total=0
    for index,digit in enumerate(reversed(number)):
        value=int(digit)*(2 if index%2 else 1); total += value-9 if value>9 else value
    return total%10==0


@router.get("/payment-methods")
def payment_methods(user: Annotated[User, Depends(get_current_user)], session: Annotated[Session, Depends(get_session)]):
    return [{"id":m.id,"cardholder_name":m.cardholder_name,"last_four":m.last_four,"issuer":m.issuer,"is_default":m.is_default} for m in session.scalars(select(PaymentMethod).where(PaymentMethod.user_id==user.id).order_by(PaymentMethod.created_at.desc()))]


@router.patch("/payment-methods/{method_id}/default")
def set_default_card(method_id: str, user: Annotated[User, Depends(get_current_user)], session: Annotated[Session, Depends(get_session)]):
    method = session.scalar(select(PaymentMethod).where(PaymentMethod.id == method_id, PaymentMethod.user_id == user.id))
    if method is None: raise HTTPException(404, "کارت پیدا نشد")
    session.query(PaymentMethod).filter(PaymentMethod.user_id == user.id).update({"is_default": False})
    method.is_default = True; session.commit(); return {"ok": True}


@router.delete("/payment-methods/{method_id}", status_code=204)
def delete_card(method_id: str, user: Annotated[User, Depends(get_current_user)], session: Annotated[Session, Depends(get_session)]):
    method = session.scalar(select(PaymentMethod).where(PaymentMethod.id == method_id, PaymentMethod.user_id == user.id))
    if method is None: raise HTTPException(404, "کارت پیدا نشد")
    if session.scalar(select(Payment.id).where(Payment.payment_method_id == method.id)):
        raise HTTPException(409, "کارت دارای سابقه پرداخت است و قابل حذف نیست")
    session.delete(method); session.commit()


@router.post("/checkout/preview")
def checkout_preview(payload: CheckoutRequest, user: Annotated[User, Depends(get_current_user)], session: Annotated[Session, Depends(get_session)]):
    del user
    plan = session.scalar(select(SubscriptionPlan).where(SubscriptionPlan.code == payload.plan_code, SubscriptionPlan.is_active.is_(True)))
    if plan is None: raise HTTPException(404, "پلن پیدا نشد")
    amount = package_price(plan.price, payload.package)
    discount_amount = 0
    if payload.discount_code.strip():
        discount = session.scalar(select(DiscountCode).where(DiscountCode.code == payload.discount_code.strip().upper(), DiscountCode.is_active.is_(True)))
        if discount is None or discount.used_count >= discount.max_uses: raise HTTPException(422, "کد تخفیف معتبر نیست")
        discount_amount = amount * discount.percent // 100
    return {"amount": amount, "discount_amount": discount_amount, "payable": amount - discount_amount}


def wallet_for(session: Session, user: User) -> WalletAccount:
    wallet = session.get(WalletAccount, user.id)
    if wallet is None:
        wallet = WalletAccount(user_id=user.id)
        session.add(wallet); session.commit(); session.refresh(wallet)
    return wallet


def withdrawal_day_start_utc() -> datetime:
    local_now = datetime.now(ZoneInfo("Asia/Tehran"))
    local_start = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
    return local_start.astimezone(timezone.utc)


def withdrawn_today(session: Session, user_id: str) -> int:
    return session.scalar(
        select(func.sum(WalletTransaction.amount)).where(
            WalletTransaction.user_id == user_id,
            WalletTransaction.transaction_type == "withdraw",
            WalletTransaction.status.in_(["pending", "completed"]),
            WalletTransaction.created_at >= withdrawal_day_start_utc(),
        )
    ) or 0


@router.get("/wallet")
def wallet(request: Request, user: Annotated[User, Depends(get_current_user)], session: Annotated[Session, Depends(get_session)]):
    account = wallet_for(session, user)
    profile = profile_for(session, user)
    items = session.scalars(select(WalletTransaction).where(WalletTransaction.user_id == user.id).order_by(WalletTransaction.created_at.desc()).limit(50)).all()
    daily_limit = request.app.state.settings.wallet_daily_withdrawal_limit
    today = withdrawn_today(session, user.id)
    return {"balance": account.balance, "points": profile.reward_points, "referral_code": profile.referral_code, "daily_withdrawal_limit": daily_limit, "withdrawn_today": today, "withdrawal_remaining": max(0, daily_limit - today), "transactions": [{"id": item.id, "type": item.transaction_type, "amount": item.amount, "status": item.status, "reference": item.reference, "related_type": item.related_type, "related_id": item.related_id, "failure_reason": item.failure_reason, "processed_at": item.processed_at, "created_at": item.created_at} for item in items]}


def create_wallet_otp(
    transaction_type: Literal["charge", "withdraw"],
    amount: int,
    request: Request,
    user: User,
    session: Session,
):
    account = wallet_for(session, user)
    limit = request.app.state.settings.wallet_daily_withdrawal_limit
    if transaction_type == "withdraw":
        if amount > account.balance:
            raise HTTPException(422, "موجودی کیف پول کافی نیست")
        if withdrawn_today(session, user.id) + amount > limit:
            raise HTTPException(
                422,
                f"سقف برداشت روزانه {limit:,} تومان است.",
            )
    code = f"{secrets.randbelow(900000) + 100000}"
    item = WalletTransaction(user_id=user.id, transaction_type=transaction_type, amount=amount, status="otp_pending", reference=f"WALLET-{uuid.uuid4().hex[:12].upper()}", related_type="wallet", otp_hash="", otp_expires_at=datetime.now(timezone.utc) + timedelta(minutes=2))
    session.add(item)
    session.flush()
    item.otp_hash = hashlib.sha256(f"{item.id}:{code}".encode()).hexdigest()
    try:
        if transaction_type == "withdraw":
            if request.app.state.settings.environment != "test":
                MelipayamakSender(request.app.state.settings).send_verification_code(phone, code)
        else:
            EmailSender(request.app.state.settings).send_security_code(user.email, user.full_name, code, "شارژ کیف پول")
    except (EmailDeliveryError, SmsDeliveryError):
        session.rollback()
        raise HTTPException(503, "ارسال کد تأیید ممکن نیست؛ دوباره تلاش کنید.") from None
    session.commit()
    response = {"transaction_id": item.id, "expires_in": 120, "delivery": "sms" if transaction_type == "withdraw" else "email"}
    if request.app.state.settings.environment == "test":
        response["test_otp"] = code
    return response


@router.post("/wallet/deposits/otp", status_code=201)
def deposit_otp(payload: WalletAmountRequest, request: Request, user: Annotated[User, Depends(get_current_user)], session: Annotated[Session, Depends(get_session)]):
    return create_wallet_otp("charge", payload.amount, request, user, session)


@router.post("/wallet/deposits", status_code=201)
def create_deposit(payload: WalletAmountRequest, user: Annotated[User, Depends(get_current_user)], session: Annotated[Session, Depends(get_session)]):
    account = wallet_for(session, user)
    now = datetime.now(timezone.utc)
    item = WalletTransaction(
        user_id=user.id,
        transaction_type="charge",
        amount=payload.amount,
        status="completed",
        reference=f"WALLET-{uuid.uuid4().hex[:12].upper()}",
        related_type="wallet",
        otp_hash="",
        otp_expires_at=now,
        processed_at=now,
    )
    account.balance += payload.amount
    session.add(item)
    session.commit()
    return {"transaction_id": item.id, "status": "completed", "balance": account.balance}


@router.post("/wallet/withdrawals/otp", status_code=201)
def withdrawal_otp(payload: WalletAmountRequest, request: Request, user: Annotated[User, Depends(get_current_user)], session: Annotated[Session, Depends(get_session)]):
    return create_wallet_otp("withdraw", payload.amount, request, user, session)


@router.post("/wallet/otp", status_code=201)
def wallet_otp(payload: WalletRequest, request: Request, user: Annotated[User, Depends(get_current_user)], session: Annotated[Session, Depends(get_session)]):
    return create_wallet_otp(payload.transaction_type, payload.amount, request, user, session)


def confirm_wallet_transaction(
    payload: WalletConfirm,
    expected_type: Literal["charge", "withdraw"] | None,
    request: Request,
    user: User,
    session: Session,
):
    item = session.scalar(select(WalletTransaction).where(WalletTransaction.id == payload.transaction_id, WalletTransaction.user_id == user.id))
    if item is None or item.status != "otp_pending": raise HTTPException(422, "درخواست کیف پول معتبر نیست")
    if expected_type is not None and item.transaction_type != expected_type:
        raise HTTPException(422, "نوع تراکنش با درخواست مطابقت ندارد.")
    expires_at = item.otp_expires_at if item.otp_expires_at.tzinfo else item.otp_expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        item.status = "failed"
        item.failure_reason = "otp_expired"
        item.processed_at = datetime.now(timezone.utc)
        session.commit()
        raise HTTPException(422, "کد تأیید منقضی شده است")
    expected = hashlib.sha256(f"{item.id}:{payload.code}".encode()).hexdigest()
    if not hmac.compare_digest(item.otp_hash, expected): raise HTTPException(422, "کد تأیید صحیح نیست")
    account = session.scalar(
        select(WalletAccount)
        .where(WalletAccount.user_id == user.id)
        .with_for_update()
    )
    if account is None:
        raise HTTPException(422, "کیف پول معتبر نیست.")
    if item.transaction_type == "charge":
        account.balance += item.amount
        item.status = "completed"
    else:
        limit = request.app.state.settings.wallet_daily_withdrawal_limit
        if withdrawn_today(session, user.id) + item.amount > limit:
            item.status = "failed"
            item.failure_reason = "daily_limit_exceeded"
            item.processed_at = datetime.now(timezone.utc)
            session.commit()
            raise HTTPException(422, f"سقف برداشت روزانه {limit:,} تومان است.")
        if item.amount > account.balance:
            item.status = "failed"
            item.failure_reason = "insufficient_balance"
            item.processed_at = datetime.now(timezone.utc)
            session.commit()
            raise HTTPException(422, "موجودی کیف پول کافی نیست")
        account.balance -= item.amount
        item.status = "pending"
    item.processed_at = datetime.now(timezone.utc)
    session.commit()
    return {"balance": account.balance, "status": item.status}


@router.post("/wallet/deposits/confirm")
def confirm_deposit(payload: WalletConfirm, request: Request, user: Annotated[User, Depends(get_current_user)], session: Annotated[Session, Depends(get_session)]):
    return confirm_wallet_transaction(payload, "charge", request, user, session)


@router.post("/wallet/withdrawals/confirm")
def confirm_withdrawal(payload: WalletConfirm, request: Request, user: Annotated[User, Depends(get_current_user)], session: Annotated[Session, Depends(get_session)]):
    return confirm_wallet_transaction(payload, "withdraw", request, user, session)


@router.post("/wallet/confirm")
def wallet_confirm(payload: WalletConfirm, request: Request, user: Annotated[User, Depends(get_current_user)], session: Annotated[Session, Depends(get_session)]):
    return confirm_wallet_transaction(payload, None, request, user, session)


@router.post("/payment-methods", status_code=201)
def add_card(payload: CardCreate, request: Request, user: Annotated[User, Depends(get_current_user)], session: Annotated[Session, Depends(get_session)]):
    if request.app.state.settings.payment_provider == "zarinpal":
        raise HTTPException(410, "ثبت کارت در پرداخت امن زرین‌پال استفاده نمی‌شود")
    number=re.sub(r"\D","",payload.card_number)
    if len(number)!=16 or not luhn(number): raise HTTPException(422,"شماره کارت معتبر نیست")
    fingerprint=hashlib.sha256(f"{user.id}:{number}".encode()).hexdigest()
    existing=session.scalar(select(PaymentMethod).where(PaymentMethod.fingerprint==fingerprint))
    if existing: return {"id":existing.id,"last_four":existing.last_four,"issuer":existing.issuer}
    session.query(PaymentMethod).filter(PaymentMethod.user_id==user.id).update({"is_default":False})
    item=PaymentMethod(user_id=user.id,cardholder_name=payload.cardholder_name,last_four=number[-4:],fingerprint=fingerprint,is_default=True)
    session.add(item); session.commit(); return {"id":item.id,"last_four":item.last_four,"issuer":item.issuer}


def _valid_discount(session: Session, code: str, now: datetime) -> DiscountCode | None:
    normalized = code.strip().upper()
    if not normalized:
        return None
    discount = session.scalar(
        select(DiscountCode).where(
            DiscountCode.code == normalized,
            DiscountCode.is_active.is_(True),
        )
    )
    if (
        discount is None
        or discount.used_count >= discount.max_uses
        or (discount.expires_at and discount.expires_at < now)
    ):
        raise HTTPException(422, "کد تخفیف معتبر نیست")
    return discount


def _activate_gateway_payment(session: Session, payment: Payment, reference: str) -> None:
    if payment.status == "paid":
        return
    now = datetime.now(timezone.utc)
    if payment.discount_code_id:
        discount = session.scalar(
            select(DiscountCode)
            .where(DiscountCode.id == payment.discount_code_id)
            .with_for_update()
        )
        if discount is not None:
            discount.used_count += 1
    session.query(UserSubscription).filter(
        UserSubscription.user_id == payment.user_id,
        UserSubscription.status == "active",
    ).update({"status": "replaced"})
    subscription = UserSubscription(
        user_id=payment.user_id,
        plan_id=payment.plan_id,
        status="active",
        package_code=payment.package_code,
        starts_at=now,
        ends_at=now + timedelta(days=payment.plan.duration_days),
    )
    account = session.get(User, payment.user_id)
    if account is not None:
        account.account_tier = payment.plan.code
    payment.status = "paid"
    payment.gateway_reference = reference
    payment.paid_at = now
    session.add_all(
        [
            subscription,
            UserNotification(
                user_id=payment.user_id,
                title="پرداخت موفق",
                message=f"اشتراک {payment.plan.title} با موفقیت فعال شد.",
                notification_type="payment",
                action_url="/app/plans",
            ),
        ]
    )


@router.post("/checkout/zarinpal", status_code=201)
def start_zarinpal_checkout(
    payload: ZarinpalCheckoutRequest,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
):
    settings = request.app.state.settings
    if settings.payment_provider != "zarinpal":
        raise HTTPException(503, "درگاه پرداخت واقعی هنوز فعال نشده است")
    plan = session.scalar(
        select(SubscriptionPlan).where(
            SubscriptionPlan.code == payload.plan_code,
            SubscriptionPlan.is_active.is_(True),
        )
    )
    if plan is None or plan.price <= 0:
        raise HTTPException(422, "پلن پولی معتبر پیدا نشد")
    now = datetime.now(timezone.utc)
    amount = package_price(plan.price, payload.package)
    discount = _valid_discount(session, payload.discount_code, now)
    discount_amount = amount * discount.percent // 100 if discount else 0
    payable = amount - discount_amount
    payment = Payment(
        user_id=user.id,
        plan_id=plan.id,
        payment_method_id=None,
        discount_code_id=discount.id if discount else None,
        amount=payable,
        discount_amount=discount_amount,
        status="pending",
        gateway_name="zarinpal",
        package_code=payload.package,
    )
    session.add(payment)
    session.flush()
    if payable <= 0:
        _activate_gateway_payment(session, payment, f"DISCOUNT-{payment.id[:12].upper()}")
        session.commit()
        return {
            "payment_id": payment.id,
            "status": "paid",
            "payment_url": f"{settings.public_site_url}/plans/payment-result?status=success&payment_id={payment.id}",
        }
    profile = session.scalar(select(UserProfile).where(UserProfile.user_id == user.id))
    try:
        authority, payment_url = ZarinpalGateway(settings).create_payment(
            amount_toman=payable,
            description=f"خرید اشتراک {plan.title} - بسته {payload.package}",
            email=user.email,
            mobile=profile.phone if profile else None,
            order_id=payment.id,
        )
    except ZarinpalError as error:
        payment.status = "failed"
        payment.failure_reason = str(error)
        session.commit()
        raise HTTPException(502, str(error)) from None
    payment.gateway_authority = authority
    session.commit()
    return {
        "payment_id": payment.id,
        "status": "pending",
        "authority": authority,
        "payment_url": payment_url,
    }


@router.get("/payments/zarinpal/callback", include_in_schema=False)
def zarinpal_callback(
    request: Request,
    authority: Annotated[str, Query(alias="Authority", min_length=10, max_length=100)],
    gateway_status: Annotated[str, Query(alias="Status", pattern="^(OK|NOK)$")],
    session: Annotated[Session, Depends(get_session)],
):
    settings = request.app.state.settings
    result_url = f"{settings.public_site_url}/plans/payment-result"
    payment = session.scalar(
        select(Payment)
        .where(
            Payment.gateway_name == "zarinpal",
            Payment.gateway_authority == authority,
        )
        .with_for_update()
    )
    if payment is None:
        return RedirectResponse(f"{result_url}?status=not_found", status_code=303)
    if payment.status == "paid":
        return RedirectResponse(
            f"{result_url}?status=success&payment_id={payment.id}",
            status_code=303,
        )
    if gateway_status != "OK":
        payment.status = "cancelled"
        payment.failure_reason = "لغو پرداخت توسط کاربر"
        session.commit()
        return RedirectResponse(
            f"{result_url}?status=cancelled&payment_id={payment.id}",
            status_code=303,
        )
    try:
        verified = ZarinpalGateway(settings).verify_payment(
            amount_toman=payment.amount,
            authority=authority,
        )
    except ZarinpalError as error:
        payment.status = "failed"
        payment.failure_reason = str(error)
        session.commit()
        return RedirectResponse(
            f"{result_url}?status=failed&payment_id={payment.id}",
            status_code=303,
        )
    payment.card_pan = verified.card_pan
    payment.card_hash = verified.card_hash
    _activate_gateway_payment(session, payment, verified.reference_id)
    session.commit()
    return RedirectResponse(
        f"{result_url}?status=success&payment_id={payment.id}",
        status_code=303,
    )


@router.post("/checkout", status_code=201)
def checkout(payload: CheckoutRequest, request: Request, user: Annotated[User, Depends(get_current_user)], session: Annotated[Session, Depends(get_session)]):
    if request.app.state.settings.payment_provider == "zarinpal":
        raise HTTPException(410, "پرداخت آزمایشی غیرفعال است؛ از درگاه زرین‌پال استفاده کنید")
    plan=session.scalar(select(SubscriptionPlan).where(SubscriptionPlan.code==payload.plan_code,SubscriptionPlan.is_active.is_(True)))
    if plan is None: raise HTTPException(404,"پلن پیدا نشد")
    method=None
    if plan.price>0:
        method=session.scalar(select(PaymentMethod).where(PaymentMethod.id==payload.payment_method_id,PaymentMethod.user_id==user.id))
        if method is None: raise HTTPException(422,"ابتدا یک کارت بانکی معتبر ثبت کنید")
        challenge=session.scalar(select(PaymentOtpChallenge).where(PaymentOtpChallenge.id==payload.otp_request_id,PaymentOtpChallenge.user_id==user.id))
        if challenge is None or challenge.used_at is not None: raise HTTPException(422,"درخواست رمز پویا معتبر نیست")
        expires_at=challenge.expires_at if challenge.expires_at.tzinfo else challenge.expires_at.replace(tzinfo=timezone.utc)
        if expires_at<datetime.now(timezone.utc): raise HTTPException(422,"رمز پویا منقضی شده است؛ رمز جدید بگیرید")
        if challenge.attempts>=5: raise HTTPException(429,"تعداد تلاش مجاز تمام شده است؛ رمز جدید بگیرید")
        if challenge.plan_code!=f"{payload.plan_code}:{payload.package}" or challenge.payment_method_id!=payload.payment_method_id or challenge.discount_code!=payload.discount_code.strip().upper(): raise HTTPException(422,"اطلاعات پرداخت پس از دریافت رمز تغییر کرده است")
        expected=hashlib.sha256(f"{challenge.id}:{payload.otp_code}".encode()).hexdigest()
        if not hmac.compare_digest(challenge.otp_hash,expected):
            challenge.attempts+=1; session.commit(); raise HTTPException(422,"رمز پویا صحیح نیست")
        challenge.used_at=datetime.now(timezone.utc)
    amount = package_price(plan.price, payload.package)
    discount=None; discount_amount=0; now=datetime.now(timezone.utc)
    if payload.discount_code.strip():
        discount=session.scalar(select(DiscountCode).where(DiscountCode.code==payload.discount_code.strip().upper(),DiscountCode.is_active.is_(True)))
        if discount is None or discount.used_count>=discount.max_uses or (discount.expires_at and discount.expires_at<now): raise HTTPException(422,"کد تخفیف معتبر نیست")
        discount_amount=amount*discount.percent//100; discount.used_count+=1
    payment=Payment(user_id=user.id,plan_id=plan.id,payment_method_id=method.id if method else None,discount_code_id=discount.id if discount else None,amount=amount-discount_amount,discount_amount=discount_amount,status="paid",gateway_reference=f"PAY-{uuid.uuid4().hex[:16].upper()}",paid_at=now)
    session.query(UserSubscription).filter(UserSubscription.user_id==user.id,UserSubscription.status=="active").update({"status":"replaced"})
    subscription=UserSubscription(user_id=user.id,plan_id=plan.id,status="active",package_code=payload.package,starts_at=now,ends_at=now+timedelta(days=plan.duration_days))
    user.account_tier=plan.code; session.add_all([payment,subscription,UserNotification(user_id=user.id,title="پرداخت موفق",message=f"اشتراک {plan.title} با موفقیت فعال شد.",notification_type="payment",action_url="/app/plans")]); session.commit()
    return {"payment_id":payment.id,"status":payment.status,"amount":payment.amount,"discount_amount":discount_amount,"reference":payment.gateway_reference,"package":payload.package,"plan":plan_data(plan)}


@router.post("/checkout/wallet", status_code=201)
def checkout_with_wallet(payload: WalletCheckoutRequest, user: Annotated[User, Depends(get_current_user)], session: Annotated[Session, Depends(get_session)]):
    plan = session.scalar(select(SubscriptionPlan).where(SubscriptionPlan.code == payload.plan_code, SubscriptionPlan.is_active.is_(True)))
    if plan is None or plan.price <= 0:
        raise HTTPException(422, "پلن پولی معتبر پیدا نشد")
    amount = package_price(plan.price, payload.package)
    discount = None
    discount_amount = 0
    now = datetime.now(timezone.utc)
    if payload.discount_code.strip():
        discount = session.scalar(select(DiscountCode).where(DiscountCode.code == payload.discount_code.strip().upper(), DiscountCode.is_active.is_(True)))
        if discount is None or discount.used_count >= discount.max_uses or (discount.expires_at and discount.expires_at < now):
            raise HTTPException(422, "کد تخفیف معتبر نیست")
        discount_amount = amount * discount.percent // 100
    payable = amount - discount_amount
    wallet = session.scalar(select(WalletAccount).where(WalletAccount.user_id == user.id).with_for_update())
    if wallet is None or wallet.balance < payable:
        raise HTTPException(422, "موجودی کیف پول برای خرید این بسته کافی نیست")
    wallet.balance -= payable
    if discount is not None:
        discount.used_count += 1
    payment = Payment(user_id=user.id, plan_id=plan.id, payment_method_id=None, discount_code_id=discount.id if discount else None, amount=payable, discount_amount=discount_amount, status="paid", gateway_reference=f"WALLET-{uuid.uuid4().hex[:12].upper()}", paid_at=now)
    session.query(UserSubscription).filter(UserSubscription.user_id == user.id, UserSubscription.status == "active").update({"status": "replaced"})
    subscription = UserSubscription(user_id=user.id, plan_id=plan.id, status="active", package_code=payload.package, starts_at=now, ends_at=now + timedelta(days=plan.duration_days))
    session.add(subscription)
    session.flush()
    transaction = WalletTransaction(user_id=user.id, transaction_type="subscription", amount=payable, status="completed", reference=payment.gateway_reference, related_type="subscription", related_id=subscription.id, otp_hash="", otp_expires_at=now, processed_at=now)
    user.account_tier = plan.code
    session.add_all([payment, transaction, UserNotification(user_id=user.id, title="خرید با کیف پول انجام شد", message=f"اشتراک {plan.title} با موفقیت فعال شد.", notification_type="payment", action_url="/app/plans")])
    session.commit()
    return {"payment_id": payment.id, "status": payment.status, "amount": payment.amount, "discount_amount": discount_amount, "reference": payment.gateway_reference, "package": payload.package, "plan": plan_data(plan), "wallet_balance": wallet.balance}


@router.post("/payment-otp", status_code=201)
def request_payment_otp(payload: CheckoutRequest, request: Request, user: Annotated[User, Depends(get_current_user)], session: Annotated[Session, Depends(get_session)]):
    if request.app.state.settings.payment_provider == "zarinpal":
        raise HTTPException(410, "رمز آزمایشی غیرفعال است؛ از درگاه زرین‌پال استفاده کنید")
    plan=session.scalar(select(SubscriptionPlan).where(SubscriptionPlan.code==payload.plan_code,SubscriptionPlan.is_active.is_(True)))
    if plan is None or plan.price<=0: raise HTTPException(422,"این پلن به رمز پویا نیاز ندارد")
    method=session.scalar(select(PaymentMethod).where(PaymentMethod.id==payload.payment_method_id,PaymentMethod.user_id==user.id))
    if method is None: raise HTTPException(422,"ابتدا یک کارت بانکی معتبر ثبت کنید")
    code=f"{secrets.randbelow(900000)+100000}"
    challenge=PaymentOtpChallenge(user_id=user.id,plan_code=f"{plan.code}:{payload.package}",payment_method_id=method.id,discount_code=payload.discount_code.strip().upper(),otp_hash="",expires_at=datetime.now(timezone.utc)+timedelta(minutes=2))
    session.add(challenge); session.flush()
    challenge.otp_hash=hashlib.sha256(f"{challenge.id}:{code}".encode()).hexdigest()
    try:
        EmailSender(request.app.state.settings).send_security_code(
            user.email, user.full_name, code, "پرداخت اشتراک"
        )
    except EmailDeliveryError:
        session.rollback()
        raise HTTPException(503, "ارسال رمز پویا ممکن نیست؛ دوباره تلاش کنید.") from None
    session.commit()
    response={"request_id":challenge.id,"expires_in":120,"card_last_four":method.last_four}
    if request.app.state.settings.environment == "test":
        response["test_otp"] = code
    return response


@router.get("/payments")
def my_payments(user: Annotated[User, Depends(get_current_user)], session: Annotated[Session, Depends(get_session)]):
    return [{"id":p.id,"plan":p.plan.title,"amount":p.amount,"discount_amount":p.discount_amount,"status":p.status,"reference":p.gateway_reference,"created_at":p.created_at} for p in session.scalars(select(Payment).where(Payment.user_id==user.id).order_by(Payment.created_at.desc()))]


@router.get("/documents")
def my_documents(user: Annotated[User, Depends(get_current_user)], session: Annotated[Session, Depends(get_session)]): return [{"id":d.id,"title":d.title,"filename":d.original_filename,"file_size":d.file_size,"status":d.status,"admin_note":d.admin_note,"created_at":d.created_at} for d in session.scalars(select(UserDocument).where(UserDocument.user_id==user.id).order_by(UserDocument.created_at.desc()))]


@router.post("/documents", status_code=201)
async def upload_document(request: Request, user: Annotated[User, Depends(get_current_user)], session: Annotated[Session, Depends(get_session)], title: Annotated[str, Form()], file: Annotated[UploadFile, File()]):
    limit = scaled_limits(session, user, PLAN_LIMITS)["documents"]
    used = session.scalar(select(func.count(UserDocument.id)).where(UserDocument.user_id == user.id)) or 0
    if used >= limit:
        raise HTTPException(429, f"سقف {limit} سند در پلن شما تکمیل شده است؛ برای افزایش ظرفیت پلن را ارتقا دهید.")
    data=await file.read(20*1024*1024+1)
    try: validated=validate_upload(file.filename or "",file.content_type,data,20*1024*1024)
    except FileValidationError as error: raise HTTPException(422,str(error)) from None
    storage: ObjectStorage = request.app.state.storage
    key=f"user-documents/{user.id}/{uuid.uuid4().hex}{validated.extension}"
    storage.put(key,validated.data,validated.mime_type)
    item=UserDocument(user_id=user.id,title=title.strip(),original_filename=validated.filename,storage_key=key,mime_type=validated.mime_type,file_size=len(validated.data))
    session.add(item); session.commit()
    return {"id":item.id,"title":item.title,"filename":item.original_filename,"file_size":item.file_size,"status":item.status,"created_at":item.created_at}


@router.get("/tickets")
def my_tickets(user: Annotated[User, Depends(get_current_user)], session: Annotated[Session, Depends(get_session)]): return [ticket_data(t, session) for t in session.scalars(select(SupportTicket).where(SupportTicket.user_id==user.id).options(selectinload(SupportTicket.messages)).order_by(SupportTicket.updated_at.desc()))]


@router.post("/tickets", status_code=201)
def create_ticket(payload: TicketCreate,user: Annotated[User, Depends(get_current_user)],session: Annotated[Session, Depends(get_session)]):
    unanswered = session.scalar(select(SupportTicket).where(SupportTicket.user_id == user.id, SupportTicket.status == "open").order_by(SupportTicket.updated_at.desc()))
    if unanswered is not None:
        raise HTTPException(409, "تا زمانی که پشتیبانی به درخواست باز شما پاسخ نداده است، پیام خود را در همان گفتگو ادامه دهید.")
    staff = best_available_staff(session)
    automatic_answer = support_faq_answer(payload.subject, payload.message)
    ticket=SupportTicket(user_id=user.id,assigned_staff_id=staff.id if staff else None,subject=payload.subject,category=payload.category,status="answered" if automatic_answer else "open")
    session.add(ticket)
    session.flush()
    session.add(TicketMessage(ticket_id=ticket.id,sender_user_id=user.id,message=payload.message,is_staff=False))
    if automatic_answer:
        session.add(TicketMessage(ticket_id=ticket.id,sender_user_id=staff.id if staff else user.id,message=automatic_answer,is_staff=True))
    session.commit()
    return ticket_data(session.scalar(select(SupportTicket).where(SupportTicket.id==ticket.id).options(selectinload(SupportTicket.messages))), session)


@router.post("/tickets/{ticket_id}/messages")
def reply_ticket(ticket_id:str,payload:MessageCreate,user:Annotated[User,Depends(get_current_user)],session:Annotated[Session,Depends(get_session)]):
    ticket=session.scalar(select(SupportTicket).where(SupportTicket.id==ticket_id,SupportTicket.user_id==user.id));
    if ticket is None: raise HTTPException(404,"تیکت پیدا نشد")
    if ticket.status=="closed": raise HTTPException(409,"تیکت بسته شده است")
    automatic_answer = support_faq_answer(ticket.subject, payload.message)
    session.add(TicketMessage(ticket_id=ticket.id,sender_user_id=user.id,message=payload.message,is_staff=False))
    if automatic_answer:
        session.add(TicketMessage(ticket_id=ticket.id,sender_user_id=ticket.assigned_staff_id or user.id,message=automatic_answer,is_staff=True))
        ticket.status="answered"
    else:
        ticket.status="open"
    session.commit()
    return {"ok":True,"automatic_answer":bool(automatic_answer)}


@router.post("/tickets/{ticket_id}/attachments")
async def upload_ticket_attachment(ticket_id: str, request: Request, file: Annotated[UploadFile, File()], user: Annotated[User, Depends(get_current_user)], session: Annotated[Session, Depends(get_session)]):
    ticket = session.scalar(select(SupportTicket).where(SupportTicket.id == ticket_id, SupportTicket.user_id == user.id))
    if ticket is None: raise HTTPException(404, "گفتگو پیدا نشد")
    data = await file.read(10 * 1024 * 1024 + 1)
    try: validated = validate_upload(file.filename or "", file.content_type, data, 10 * 1024 * 1024)
    except FileValidationError as error: raise HTTPException(422, str(error)) from None
    key = f"ticket-attachments/{ticket.id}/{uuid.uuid4().hex}{validated.extension}"
    storage: ObjectStorage = request.app.state.storage
    storage.put(key, validated.data, validated.mime_type)
    message = TicketMessage(ticket_id=ticket.id, sender_user_id=user.id, message="فایل پیوست شد.", is_staff=False, attachment_name=validated.filename, attachment_key=key, attachment_mime=validated.mime_type)
    session.add(message); ticket.status = "open"; session.commit()
    return {"ok": True}


@router.get("/tickets/attachments/{message_id}")
def download_ticket_attachment(message_id: str, request: Request, user: Annotated[User, Depends(get_current_user)], session: Annotated[Session, Depends(get_session)]):
    message = session.get(TicketMessage, message_id)
    ticket = session.get(SupportTicket, message.ticket_id) if message else None
    permissions = {permission.code for role in user.roles for permission in role.permissions}
    if message is None or ticket is None or (ticket.user_id != user.id and "tickets:manage" not in permissions): raise HTTPException(404, "فایل پیدا نشد")
    storage: ObjectStorage = request.app.state.storage
    return StreamingResponse(BytesIO(storage.get(message.attachment_key)), media_type=message.attachment_mime, headers={"Content-Disposition": f'inline; filename="{message.attachment_name}"'})


@admin_router.get("/summary")
def admin_summary(user:Annotated[User,Depends(require_permissions("users:manage"))],session:Annotated[Session,Depends(get_session)]):
    del user; return {"users":session.scalar(select(func.count(User.id))) or 0,"payments":session.scalar(select(func.count(Payment.id))) or 0,"revenue":session.scalar(select(func.sum(Payment.amount)).where(Payment.status=="paid")) or 0,"active_subscriptions":session.scalar(select(func.count(UserSubscription.id)).where(UserSubscription.status=="active")) or 0,"open_tickets":session.scalar(select(func.count(SupportTicket.id)).where(SupportTicket.status!="closed")) or 0,"user_documents":session.scalar(select(func.count(UserDocument.id))) or 0,"conversations":session.scalar(select(func.count(Conversation.id)).where(Conversation.deleted_at.is_(None))) or 0}


@admin_router.get("/payments")
def admin_payments(user:Annotated[User,Depends(require_permissions("payments:manage"))],session:Annotated[Session,Depends(get_session)]):
    del user; rows=session.execute(select(Payment,User.email).join(User,User.id==Payment.user_id).order_by(Payment.created_at.desc())); return [{"id":p.id,"email":email,"plan":p.plan.title,"amount":p.amount,"discount_amount":p.discount_amount,"status":p.status,"reference":p.gateway_reference,"created_at":p.created_at} for p,email in rows]


@admin_router.get("/wallets")
def admin_wallets(
    user: Annotated[User, Depends(require_permissions("payments:manage"))],
    session: Annotated[Session, Depends(get_session)],
    query: Annotated[str, Query(alias="q", max_length=120)] = "",
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
):
    del user
    statement = (
        select(User, WalletAccount)
        .outerjoin(WalletAccount, WalletAccount.user_id == User.id)
        .order_by(User.created_at.desc())
    )
    if query.strip():
        value = f"%{query.strip().lower()}%"
        statement = statement.where(
            func.lower(User.email).like(value)
            | func.lower(User.full_name).like(value)
        )
    rows = session.execute(statement.offset(offset).limit(limit))
    result = []
    for account, wallet_account in rows:
        totals = dict(
            session.execute(
                select(
                    WalletTransaction.transaction_type,
                    func.sum(WalletTransaction.amount),
                )
                .where(
                    WalletTransaction.user_id == account.id,
                    WalletTransaction.status.in_(("completed", "pending")),
                )
                .group_by(WalletTransaction.transaction_type)
            ).all()
        )
        result.append(
            {
                "user_id": account.id,
                "full_name": account.full_name,
                "email": account.email,
                "balance": wallet_account.balance if wallet_account else 0,
                "total_deposited": totals.get("charge", 0),
                "total_withdrawn": totals.get("withdraw", 0),
                "total_spent": sum(
                    amount
                    for transaction_type, amount in totals.items()
                    if transaction_type not in ("charge", "withdraw")
                ),
            }
        )
    return result


@admin_router.get("/wallets/{user_id}")
def admin_wallet_details(
    user_id: str,
    user: Annotated[User, Depends(require_permissions("payments:manage"))],
    session: Annotated[Session, Depends(get_session)],
):
    del user
    account = session.get(User, user_id)
    if account is None:
        raise HTTPException(404, "کاربر پیدا نشد.")
    wallet_account = session.get(WalletAccount, user_id)
    items = session.scalars(
        select(WalletTransaction)
        .where(WalletTransaction.user_id == user_id)
        .order_by(WalletTransaction.created_at.desc())
        .limit(500)
    ).all()
    return {
        "user_id": account.id,
        "full_name": account.full_name,
        "email": account.email,
        "balance": wallet_account.balance if wallet_account else 0,
        "transactions": [
            {
                "id": item.id,
                "type": item.transaction_type,
                "amount": item.amount,
                "status": item.status,
                "reference": item.reference,
                "related_type": item.related_type,
                "related_id": item.related_id,
                "failure_reason": item.failure_reason,
                "processed_at": item.processed_at,
                "created_at": item.created_at,
            }
            for item in items
        ],
    }


@admin_router.get("/subscriptions")
def admin_subscriptions(user:Annotated[User,Depends(require_permissions("subscriptions:manage"))],session:Annotated[Session,Depends(get_session)]):
    del user; rows=session.execute(select(UserSubscription,User.email).join(User,User.id==UserSubscription.user_id).order_by(UserSubscription.created_at.desc())); return [{"id":s.id,"email":email,"plan":s.plan.title,"package":s.package_code,"status":s.status,"starts_at":s.starts_at,"ends_at":s.ends_at} for s,email in rows]


@admin_router.get("/plans")
def admin_plans(user: Annotated[User, Depends(require_permissions("subscriptions:manage"))], session: Annotated[Session, Depends(get_session)]):
    del user
    return [plan_data(item) for item in session.scalars(select(SubscriptionPlan).order_by(SubscriptionPlan.sort_order))]


@admin_router.patch("/plans/{plan_id}")
def update_plan(plan_id: str, payload: PlanAdminUpdate, user: Annotated[User, Depends(require_permissions("subscriptions:manage"))], session: Annotated[Session, Depends(get_session)]):
    del user
    item = session.get(SubscriptionPlan, plan_id)
    if item is None:
        raise HTTPException(404, "پلن پیدا نشد")
    if item.code == "normal" and not payload.is_active:
        raise HTTPException(400, "پلن رایگان را نمی‌توان غیرفعال کرد")
    item.price = payload.price
    item.duration_days = payload.duration_days
    item.is_active = payload.is_active
    session.commit()
    return plan_data(item)


@admin_router.patch("/subscriptions/{subscription_id}")
def update_subscription(subscription_id: str, payload: SubscriptionAdminUpdate, user: Annotated[User, Depends(require_permissions("subscriptions:manage"))], session: Annotated[Session, Depends(get_session)]):
    del user
    item = session.get(UserSubscription, subscription_id)
    if item is None:
        raise HTTPException(404, "اشتراک پیدا نشد")
    if payload.status == "active":
        session.query(UserSubscription).filter(UserSubscription.user_id == item.user_id, UserSubscription.id != item.id, UserSubscription.status == "active").update({"status": "replaced"})
        item.status = "active"
        item.ends_at = datetime.now(timezone.utc) + timedelta(days=30)
        session.get(User, item.user_id).account_tier = item.plan.code
    else:
        item.status = "cancelled"
        session.get(User, item.user_id).account_tier = "normal"
    session.commit()
    return {"ok": True}


@admin_router.get("/user-documents")
def admin_documents(user:Annotated[User,Depends(require_permissions("user_documents:manage"))],session:Annotated[Session,Depends(get_session)]):
    del user; rows=session.execute(select(UserDocument,User.email).join(User,User.id==UserDocument.user_id).order_by(UserDocument.created_at.desc())); return [{"id":d.id,"email":email,"title":d.title,"filename":d.original_filename,"file_size":d.file_size,"status":d.status,"admin_note":d.admin_note,"created_at":d.created_at} for d,email in rows]


@admin_router.patch("/user-documents/{document_id}")
def review_user_document(document_id:str,payload:DocumentAdminUpdate,user:Annotated[User,Depends(require_permissions("user_documents:manage"))],session:Annotated[Session,Depends(get_session)]):
    del user; item=session.get(UserDocument,document_id)
    if item is None: raise HTTPException(404,"سند پیدا نشد")
    item.status=payload.status; item.admin_note=payload.admin_note; session.commit(); return {"ok":True}


@admin_router.get("/tickets")
def admin_tickets(user:Annotated[User,Depends(require_permissions("tickets:manage"))],session:Annotated[Session,Depends(get_session)]):
    statement = select(SupportTicket).options(selectinload(SupportTicket.messages)).order_by((SupportTicket.assigned_staff_id == user.id).desc(), SupportTicket.updated_at.desc())
    if "system_admin" not in {role.name for role in user.roles}:
        statement = statement.where((SupportTicket.assigned_staff_id == user.id) | (SupportTicket.assigned_staff_id.is_(None)))
    return [ticket_data(t, session) for t in session.scalars(statement)]


@admin_router.post("/tickets/{ticket_id}/reply")
def admin_ticket_reply(ticket_id:str,payload:MessageCreate,user:Annotated[User,Depends(require_permissions("tickets:manage"))],session:Annotated[Session,Depends(get_session)]):
    ticket=session.get(SupportTicket,ticket_id)
    if ticket is None: raise HTTPException(404,"تیکت پیدا نشد")
    if ticket.assigned_staff_id is None:
        ticket.assigned_staff_id = user.id
    session.add(TicketMessage(ticket_id=ticket.id,sender_user_id=user.id,message=payload.message,is_staff=True)); ticket.status="answered"; session.add(UserNotification(user_id=ticket.user_id,title="پاسخ جدید تیکت",message=f"برای تیکت «{ticket.subject}» پاسخ جدید ثبت شد.",notification_type="ticket",action_url="/app/tickets")); session.commit(); return {"ok":True}


@admin_router.patch("/tickets/{ticket_id}")
def update_ticket(ticket_id: str, payload: TicketAdminUpdate, user: Annotated[User, Depends(require_permissions("tickets:manage"))], session: Annotated[Session, Depends(get_session)]):
    del user
    ticket = session.get(SupportTicket, ticket_id)
    if ticket is None:
        raise HTTPException(404, "تیکت پیدا نشد")
    ticket.status = payload.status; session.commit()
    return {"ok": True}


@admin_router.get("/chats")
def admin_chats(user:Annotated[User,Depends(require_permissions("chats:manage"))],session:Annotated[Session,Depends(get_session)]):
    del user; rows=session.execute(select(Conversation,User.email).join(User,User.id==Conversation.user_id).where(Conversation.deleted_at.is_(None)).order_by(Conversation.updated_at.desc()).limit(200)); return [{"id":c.id,"email":email,"title":c.title,"created_at":c.created_at,"updated_at":c.updated_at,"message_count":session.scalar(select(func.count(ChatMessage.id)).where(ChatMessage.conversation_id==c.id)) or 0} for c,email in rows]


@admin_router.get("/chats/{conversation_id}")
def admin_chat_messages(conversation_id: str, user: Annotated[User, Depends(require_permissions("chats:manage"))], session: Annotated[Session, Depends(get_session)]):
    del user
    conversation = session.get(Conversation, conversation_id)
    if conversation is None or conversation.deleted_at is not None:
        raise HTTPException(404, "گفتگو پیدا نشد")
    return [{"id": message.id, "role": message.role, "content": message.content, "created_at": message.created_at} for message in session.scalars(select(ChatMessage).where(ChatMessage.conversation_id == conversation_id).order_by(ChatMessage.created_at))]


@admin_router.delete("/chats/{conversation_id}", status_code=204)
def admin_delete_chat(conversation_id: str, user: Annotated[User, Depends(require_permissions("chats:manage"))], session: Annotated[Session, Depends(get_session)]):
    del user
    conversation = session.get(Conversation, conversation_id)
    if conversation is None:
        raise HTTPException(404, "گفتگو پیدا نشد")
    conversation.deleted_at = datetime.now(timezone.utc); session.commit()


@admin_router.get("/profiles")
def admin_profiles(user: Annotated[User, Depends(require_permissions("users:manage"))], session: Annotated[Session, Depends(get_session)]):
    del user
    rows = session.execute(select(User, UserProfile).outerjoin(UserProfile, UserProfile.user_id == User.id).order_by(User.created_at.desc()))
    return [({"id": account.id, "full_name": account.full_name, "email": account.email, "tier": account.account_tier, "is_active": account.is_active} | (profile_data(profile, account) if profile else {"profile_score": 10, "reward_points": 0})) for account, profile in rows]


@admin_router.patch("/profiles/{user_id}")
def admin_update_profile(user_id: str, payload: AdminProfileUpdate, user: Annotated[User, Depends(require_permissions("users:manage"))], session: Annotated[Session, Depends(get_session)]):
    account = session.get(User, user_id)
    if account is None:
        raise HTTPException(404, "کاربر پیدا نشد.")
    profile = profile_for(session, account)
    values = payload.model_dump()
    reward_points = values.pop("reward_points")
    phone = values.pop("phone").strip()
    if phone:
        phone = normalize_iranian_phone(phone)
    if phone != profile.phone:
        profile.phone = phone
        profile.phone_verified = False
        profile.phone_verified_at = None
    values["alternate_phone"] = optional_iranian_phone(values["alternate_phone"])
    values["alternate_email"] = str(values["alternate_email"] or "").strip().lower()
    for key, value in values.items():
        setattr(profile, key, value.strip() if isinstance(value, str) else value)
    if reward_points is not None:
        profile.reward_points = reward_points
    refresh_profile_score(profile)
    session.commit()
    return {"id": account.id, "full_name": account.full_name, "tier": account.account_tier, "is_active": account.is_active} | profile_data(profile, account)


@admin_router.get("/users/{user_id}/overview")
def admin_user_overview(
    user_id: str,
    user: Annotated[User, Depends(require_permissions("users:manage"))],
    session: Annotated[Session, Depends(get_session)],
):
    del user
    account = session.scalar(select(User).options(selectinload(User.roles)).where(User.id == user_id))
    if account is None:
        raise HTTPException(404, "کاربر پیدا نشد.")
    profile = profile_for(session, account)
    wallet = session.get(WalletAccount, user_id)
    transactions = session.scalars(select(WalletTransaction).where(WalletTransaction.user_id == user_id).order_by(WalletTransaction.created_at.desc()).limit(100)).all()
    subscriptions = session.scalars(select(UserSubscription).options(selectinload(UserSubscription.plan)).where(UserSubscription.user_id == user_id).order_by(UserSubscription.created_at.desc()).limit(20)).all()
    payments = session.scalars(select(Payment).where(Payment.user_id == user_id).order_by(Payment.created_at.desc()).limit(50)).all()
    return {
        "account": {
            "id": account.id,
            "full_name": account.full_name,
            "email": account.email,
            "tier": account.account_tier,
            "is_active": account.is_active,
            "two_factor_enabled": account.two_factor_enabled,
            "roles": [role.name for role in account.roles],
            "created_at": account.created_at,
            "last_seen_at": account.last_seen_at,
        },
        "profile": profile_data(profile, account),
        "wallet": {
            "balance": wallet.balance if wallet else 0,
            "transactions": [{"id": item.id, "type": item.transaction_type, "amount": item.amount, "status": item.status, "reference": item.reference, "created_at": item.created_at} for item in transactions],
        },
        "subscriptions": [{"id": item.id, "title": item.plan.title, "package": item.package_code, "status": item.status, "starts_at": item.starts_at, "ends_at": item.ends_at} for item in subscriptions],
        "payments": [{"id": item.id, "amount": item.amount, "status": item.status, "reference": item.gateway_reference, "created_at": item.created_at} for item in payments],
        "activity": {
            "documents": session.scalar(select(func.count(UserDocument.id)).where(UserDocument.user_id == user_id)) or 0,
            "tickets": session.scalar(select(func.count(SupportTicket.id)).where(SupportTicket.user_id == user_id)) or 0,
            "conversations": session.scalar(select(func.count(Conversation.id)).where(Conversation.user_id == user_id, Conversation.deleted_at.is_(None))) or 0,
            "consultations": 0,
        },
    }


@admin_router.get("/discounts")
def admin_discounts(user: Annotated[User, Depends(require_permissions("payments:manage"))], session: Annotated[Session, Depends(get_session)]):
    del user
    return [{"id": item.id, "code": item.code, "percent": item.percent, "max_uses": item.max_uses, "used_count": item.used_count, "is_active": item.is_active, "expires_at": item.expires_at} for item in session.scalars(select(DiscountCode).order_by(DiscountCode.created_at.desc()))]


@admin_router.post("/discounts", status_code=201)
def create_discount(payload: DiscountCreate, user: Annotated[User, Depends(require_permissions("payments:manage"))], session: Annotated[Session, Depends(get_session)]):
    del user
    code = payload.code.strip().upper()
    if session.scalar(select(DiscountCode).where(DiscountCode.code == code)):
        raise HTTPException(409, "این کد تخفیف قبلاً ساخته شده است")
    item = DiscountCode(code=code, percent=payload.percent, max_uses=payload.max_uses, is_active=payload.is_active)
    session.add(item); session.commit(); session.refresh(item)
    return {"id": item.id, "code": item.code}


@admin_router.patch("/discounts/{discount_id}")
def update_discount(discount_id: str, payload: DiscountUpdate, user: Annotated[User, Depends(require_permissions("payments:manage"))], session: Annotated[Session, Depends(get_session)]):
    del user
    item = session.get(DiscountCode, discount_id)
    if item is None:
        raise HTTPException(404, "کد تخفیف پیدا نشد")
    for key, value in payload.model_dump(exclude_none=True).items():
        setattr(item, key, value)
    session.commit()
    return {"ok": True}
