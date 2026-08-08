from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Annotated, Literal
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_security, get_session, require_permissions
from app.core.security import SecurityManager
from app.models.advisor import ChatMessage, Conversation
from app.models.auth import User
from app.models.consultations import ConsultationRequest
from app.models.portal import Payment, SupportTicket, TaxReminder, ToolUsageEvent, UserDocument, UserProfile
from app.services.plans import active_package, scaled_limits

router = APIRouter(prefix="/api/v1/tools", tags=["tax tools"])
admin_router = APIRouter(prefix="/api/v1/admin", tags=["admin analytics"])

PLAN_LIMITS = {
    "normal": {"questions": 10, "documents": 1, "tickets": 1, "consultations": 1, "law_search": 5, "calculator": 10, "letters": 1},
    "plus": {"questions": 100, "documents": 5, "tickets": 5, "consultations": 2, "law_search": 100, "calculator": 100, "letters": 10},
    "pro": {"questions": 1000, "documents": 20, "tickets": 20, "consultations": 10, "law_search": 1000, "calculator": 1000, "letters": 100},
}


class ReminderCreate(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(default="", max_length=1000)
    due_date: date
    category: str = Field(default="general", max_length=40)
    notify_days_before: int = Field(default=3, ge=0, le=60)


class ReminderUpdate(BaseModel):
    is_done: bool


class CalculatorRequest(BaseModel):
    calculation_type: Literal["percentage", "vat", "penalty"]
    amount: float = Field(ge=0, le=10**15)
    rate: float = Field(ge=0, le=100)
    months: int = Field(default=1, ge=1, le=120)


class LetterRequest(BaseModel):
    letter_type: Literal["objection", "extension", "clarification"]
    recipient: str = Field(min_length=2, max_length=200)
    subject: str = Field(min_length=3, max_length=200)
    taxpayer_name: str = Field(min_length=2, max_length=200)
    case_number: str = Field(default="", max_length=80)
    facts: str = Field(min_length=10, max_length=4000)
    request_text: str = Field(min_length=5, max_length=1000)


class TotpCode(BaseModel):
    code: str = Field(pattern="^[0-9]{6}$")


def reminder_data(item: TaxReminder) -> dict:
    return {"id": item.id, "title": item.title, "description": item.description, "due_date": item.due_date, "category": item.category, "is_done": item.is_done, "notify_days_before": item.notify_days_before}


def consume_tool(session: Session, user: User, tool_type: str) -> None:
    month_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    limit = scaled_limits(session, user, PLAN_LIMITS)[tool_type]
    used = session.scalar(select(func.count(ToolUsageEvent.id)).where(ToolUsageEvent.user_id == user.id, ToolUsageEvent.tool_type == tool_type, ToolUsageEvent.created_at >= month_start)) or 0
    if used >= limit:
        raise HTTPException(429, f"سهمیه این ابزار در پلن شما تکمیل شده است ({limit} بار در ماه).")
    session.add(ToolUsageEvent(user_id=user.id, tool_type=tool_type))


@router.get("/calendar")
def calendar(user: Annotated[User, Depends(get_current_user)], session: Annotated[Session, Depends(get_session)]):
    reminders = session.scalars(select(TaxReminder).where(TaxReminder.user_id == user.id).order_by(TaxReminder.due_date)).all()
    templates = [
        {"title": "ارسال اظهارنامه مالیاتی", "category": "declaration", "description": "تاریخ دقیق را مطابق نوع فعالیت و آخرین بخشنامه ثبت کنید."},
        {"title": "ارسال گزارش ارزش افزوده", "category": "vat", "description": "سررسید دوره ارزش افزوده را پس از بررسی سامانه مؤدیان ثبت کنید."},
        {"title": "پرداخت مالیات حقوق", "category": "payroll", "description": "مهلت پرداخت و ارسال فهرست حقوق ماهانه را ثبت کنید."},
        {"title": "مهلت اعتراض به برگ تشخیص", "category": "appeal", "description": "تاریخ ابلاغ را مبنا قرار دهید و مهلت قانونی را با مشاور کنترل کنید."},
    ]
    return {"reminders": [reminder_data(item) for item in reminders], "templates": templates}


@router.post("/reminders", status_code=201)
def create_reminder(payload: ReminderCreate, user: Annotated[User, Depends(get_current_user)], session: Annotated[Session, Depends(get_session)]):
    item = TaxReminder(user_id=user.id, **payload.model_dump())
    session.add(item); session.commit(); session.refresh(item)
    return reminder_data(item)


@router.patch("/reminders/{reminder_id}")
def update_reminder(reminder_id: str, payload: ReminderUpdate, user: Annotated[User, Depends(get_current_user)], session: Annotated[Session, Depends(get_session)]):
    item = session.scalar(select(TaxReminder).where(TaxReminder.id == reminder_id, TaxReminder.user_id == user.id))
    if item is None: raise HTTPException(404, "یادآور پیدا نشد")
    item.is_done = payload.is_done; session.commit(); return reminder_data(item)


@router.delete("/reminders/{reminder_id}", status_code=204)
def delete_reminder(reminder_id: str, user: Annotated[User, Depends(get_current_user)], session: Annotated[Session, Depends(get_session)]):
    item = session.scalar(select(TaxReminder).where(TaxReminder.id == reminder_id, TaxReminder.user_id == user.id))
    if item is None: raise HTTPException(404, "یادآور پیدا نشد")
    session.delete(item); session.commit()


@router.get("/notifications")
def notifications(user: Annotated[User, Depends(get_current_user)], session: Annotated[Session, Depends(get_session)]):
    today = date.today()
    items = session.scalars(select(TaxReminder).where(TaxReminder.user_id == user.id, TaxReminder.is_done.is_(False)).order_by(TaxReminder.due_date)).all()
    result = []
    for item in items:
        days = (item.due_date - today).days
        if days <= item.notify_days_before:
            result.append({"id": item.id, "title": item.title, "due_date": item.due_date, "days_remaining": days, "severity": "danger" if days < 0 else "warning" if days <= 1 else "info"})
    return result


@router.get("/usage")
def usage(user: Annotated[User, Depends(get_current_user)], session: Annotated[Session, Depends(get_session)]):
    month_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    used = {
        "questions": session.scalar(select(func.count(ChatMessage.id)).join(Conversation).where(Conversation.user_id == user.id, ChatMessage.role == "user", ChatMessage.created_at >= month_start)) or 0,
        "documents": session.scalar(select(func.count(UserDocument.id)).where(UserDocument.user_id == user.id)) or 0,
        "tickets": session.scalar(select(func.count(SupportTicket.id)).where(SupportTicket.user_id == user.id, SupportTicket.status != "closed")) or 0,
        "consultations": session.scalar(select(func.count(ConsultationRequest.id)).where(ConsultationRequest.user_id == user.id, ConsultationRequest.created_at >= month_start)) or 0,
        "law_search": session.scalar(select(func.count(ToolUsageEvent.id)).where(ToolUsageEvent.user_id == user.id, ToolUsageEvent.tool_type == "law_search", ToolUsageEvent.created_at >= month_start)) or 0,
        "calculator": session.scalar(select(func.count(ToolUsageEvent.id)).where(ToolUsageEvent.user_id == user.id, ToolUsageEvent.tool_type == "calculator", ToolUsageEvent.created_at >= month_start)) or 0,
        "letters": session.scalar(select(func.count(ToolUsageEvent.id)).where(ToolUsageEvent.user_id == user.id, ToolUsageEvent.tool_type == "letters", ToolUsageEvent.created_at >= month_start)) or 0,
    }
    return {"tier": user.account_tier, "package": active_package(session, user), "used": used, "limits": scaled_limits(session, user, PLAN_LIMITS)}


@router.post("/calculator")
def calculator(payload: CalculatorRequest, user: Annotated[User, Depends(get_current_user)], session: Annotated[Session, Depends(get_session)]):
    consume_tool(session, user, "calculator")
    multiplier = payload.months if payload.calculation_type == "penalty" else 1
    result = round(payload.amount * payload.rate / 100 * multiplier, 2)
    session.commit()
    return {"result": result, "base_amount": payload.amount, "rate": payload.rate, "months": multiplier, "disclaimer": "این محاسبه برآورد اولیه است و نرخ و مبنای قانونی باید برای پرونده شما بررسی شود."}


@router.post("/letters")
def generate_letter(payload: LetterRequest, user: Annotated[User, Depends(get_current_user)], session: Annotated[Session, Depends(get_session)]):
    consume_tool(session, user, "letters")
    titles = {"objection": "لایحه اعتراض مالیاتی", "extension": "درخواست تمدید مهلت", "clarification": "درخواست رفع ابهام و ارائه توضیحات"}
    body = f"""بسمه‌تعالی
تاریخ: {date.today().isoformat()}
مخاطب: {payload.recipient}
موضوع: {payload.subject}

با سلام و احترام،
اینجانب/این شرکت {payload.taxpayer_name}{f'، مرتبط با پرونده شماره {payload.case_number}' if payload.case_number else ''}، به استحضار می‌رساند:

{payload.facts.strip()}

با توجه به مراتب فوق، تقاضا می‌شود {payload.request_text.strip()}

با تشکر و احترام
نام و امضا: {payload.taxpayer_name}
"""
    session.commit()
    return {"title": titles[payload.letter_type], "content": body, "disclaimer": "پیش از ارسال رسمی، متن و مستندات توسط متخصص مالیاتی بررسی شود."}


@router.get("/comparison/{consultation_id}")
def comparison(consultation_id: str, user: Annotated[User, Depends(get_current_user)], session: Annotated[Session, Depends(get_session)]):
    item = session.scalar(select(ConsultationRequest).where(ConsultationRequest.id == consultation_id, ConsultationRequest.user_id == user.id))
    if item is None: raise HTTPException(404, "درخواست مشاور پیدا نشد")
    message = session.get(ChatMessage, item.source_message_id) if item.source_message_id else None
    return {"ai_answer": message.content if message else "", "expert_answer": item.resolution, "status": item.status, "has_comparison": bool(message and item.resolution)}


@router.get("/wallet")
def wallet(user: Annotated[User, Depends(get_current_user)], session: Annotated[Session, Depends(get_session)]):
    profile = session.get(UserProfile, user.id)
    referrals = session.scalar(select(func.count(UserProfile.user_id)).where(UserProfile.referred_by_user_id == user.id)) or 0
    return {"points": profile.reward_points if profile else 0, "referral_code": profile.referral_code if profile else "", "successful_referrals": referrals, "rewards": [{"points": 500, "title": "تخفیف ۵۰ هزار تومانی"}, {"points": 1500, "title": "یک ماه پلن پلاس"}]}


@router.get("/security/2fa/setup")
def setup_two_factor(user: Annotated[User, Depends(get_current_user)], security: Annotated[SecurityManager, Depends(get_security)]):
    secret = security.two_factor_secret(user.id)
    uri = f"otpauth://totp/{quote('Tax AI')}:{quote(user.email)}?secret={secret}&issuer={quote('Tax AI')}&digits=6&period=30"
    return {"enabled": user.two_factor_enabled, "secret": secret, "otpauth_uri": uri}


@router.post("/security/2fa/enable")
def enable_two_factor(payload: TotpCode, user: Annotated[User, Depends(get_current_user)], security: Annotated[SecurityManager, Depends(get_security)], session: Annotated[Session, Depends(get_session)]):
    if not security.verify_totp(user.id, payload.code): raise HTTPException(422, "کد برنامه احراز هویت صحیح نیست")
    user.two_factor_enabled = True; session.commit(); return {"enabled": True}


@router.delete("/security/2fa")
def disable_two_factor(payload: TotpCode, user: Annotated[User, Depends(get_current_user)], security: Annotated[SecurityManager, Depends(get_security)], session: Annotated[Session, Depends(get_session)]):
    if user.two_factor_enabled and not security.verify_totp(user.id, payload.code): raise HTTPException(422, "کد برنامه احراز هویت صحیح نیست")
    user.two_factor_enabled = False; session.commit(); return {"enabled": False}


@admin_router.get("/analytics")
def admin_analytics(user: Annotated[User, Depends(require_permissions("users:manage"))], session: Annotated[Session, Depends(get_session)]):
    del user
    month_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    tier_rows = session.execute(select(User.account_tier, func.count(User.id)).group_by(User.account_tier))
    return {"tiers": {tier: count for tier, count in tier_rows}, "two_factor_users": session.scalar(select(func.count(User.id)).where(User.two_factor_enabled.is_(True))) or 0, "monthly_questions": session.scalar(select(func.count(ChatMessage.id)).where(ChatMessage.role == "user", ChatMessage.created_at >= month_start)) or 0, "monthly_revenue": session.scalar(select(func.sum(Payment.amount)).where(Payment.status == "paid", Payment.paid_at >= month_start)) or 0, "pending_reminders": session.scalar(select(func.count(TaxReminder.id)).where(TaxReminder.is_done.is_(False))) or 0}
