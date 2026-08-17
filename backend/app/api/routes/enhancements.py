from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from io import BytesIO

import fitz
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from openpyxl import Workbook
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_session, require_permissions
from app.models.advisor import ChatMessage
from app.models.auth import AuditLog, FailedLoginAttempt, SecurityRiskEvent, User
from app.models.consultations import ConsultationBooking, ConsultantProfile, ConsultantSettlement
from app.models.portal import Payment, ToolUsageEvent, UserNotification, UserSubscription, WalletAccount, WalletTransaction
from app.models.site import SiteConfiguration
from app.schemas.site import SiteConfigPayload

router = APIRouter(prefix="/api/v1", tags=["product completion"])


class BroadcastRequest(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    message: str = Field(min_length=5, max_length=1000)
    action_url: str = Field(default="", max_length=500)
    audience: str = Field(default="all", pattern="^(all|normal|plus|pro)$")


class RefundRequest(BaseModel):
    reason: str = Field(min_length=5, max_length=500)


class SettlementRequest(BaseModel):
    consultant_id: str
    admin_note: str = Field(default="", max_length=1000)


class SettlementReviewRequest(BaseModel):
    status: str = Field(pattern="^(paid|rejected)$")
    reference: str = Field(default="", max_length=100)
    admin_note: str = Field(default="", max_length=1000)


class RiskReviewRequest(BaseModel):
    status: str = Field(pattern=r"^(reviewing|resolved|false_positive)$")


def notification_data(item: UserNotification) -> dict:
    return {
        "id": item.id,
        "title": item.title,
        "message": item.message,
        "type": item.notification_type,
        "action_url": item.action_url,
        "is_read": item.is_read,
        "created_at": item.created_at,
    }


@router.get("/notifications")
def notifications(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    items = session.scalars(
        select(UserNotification)
        .where(UserNotification.user_id == user.id)
        .order_by(UserNotification.created_at.desc())
        .limit(100)
    ).all()
    unread = sum(not item.is_read for item in items)
    return {"unread": unread, "items": [notification_data(item) for item in items]}


@router.patch("/notifications/{notification_id}/read")
def read_notification(
    notification_id: str,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    item = session.scalar(
        select(UserNotification).where(
            UserNotification.id == notification_id,
            UserNotification.user_id == user.id,
        )
    )
    if item is None:
        raise HTTPException(404, "اعلان پیدا نشد")
    item.is_read = True
    session.commit()
    return {"ok": True}


@router.post("/notifications/read-all")
def read_all_notifications(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    session.query(UserNotification).filter(
        UserNotification.user_id == user.id,
        UserNotification.is_read.is_(False),
    ).update({"is_read": True})
    session.commit()
    return {"ok": True}


@router.get("/portal/payments/{payment_id}/invoice.pdf")
def payment_invoice(
    payment_id: str,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    payment = session.scalar(
        select(Payment).where(Payment.id == payment_id, Payment.user_id == user.id)
    )
    if payment is None or payment.status != "paid":
        raise HTTPException(404, "فاکتور پیدا نشد")
    document = fitz.open()
    page = document.new_page(width=595, height=842)
    lines = [
        "CHAKA PAYMENT INVOICE",
        f"Invoice: {payment.id}",
        f"Customer: {user.full_name}",
        f"Email: {user.email}",
        f"Plan: {payment.plan.title}",
        f"Amount: {payment.amount:,} Toman",
        f"Discount: {payment.discount_amount:,} Toman",
        f"Reference: {payment.gateway_reference or '-'}",
        f"Paid at: {payment.paid_at or payment.created_at}",
        "Status: PAID",
    ]
    page.insert_text((72, 90), "\n\n".join(lines), fontsize=12)
    payload = document.tobytes()
    document.close()
    return StreamingResponse(
        BytesIO(payload),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="invoice-{payment.id}.pdf"'},
    )


@router.get("/admin/financial-report")
def financial_report(
    _: User = Depends(require_permissions("payments:manage")),
    session: Session = Depends(get_session),
):
    now = datetime.now(timezone.utc)
    month_start = now - timedelta(days=30)
    paid_total = session.scalar(select(func.sum(Payment.amount)).where(Payment.status == "paid")) or 0
    paid_month = session.scalar(
        select(func.sum(Payment.amount)).where(Payment.status == "paid", Payment.paid_at >= month_start)
    ) or 0
    wallet_charges = session.scalar(
        select(func.sum(WalletTransaction.amount)).where(
            WalletTransaction.transaction_type == "charge",
            WalletTransaction.status == "completed",
        )
    ) or 0
    active_subscriptions = session.scalar(
        select(func.count(UserSubscription.id)).where(UserSubscription.status == "active")
    ) or 0
    return {
        "paid_total": paid_total,
        "paid_last_30_days": paid_month,
        "wallet_charges": wallet_charges,
        "active_subscriptions": active_subscriptions,
    }


@router.get("/admin/consultant-settlements")
def consultant_settlements(
    _: User = Depends(require_permissions("payments:manage")),
    session: Session = Depends(get_session),
):
    rows = session.execute(
        select(ConsultationBooking.consultant_id, User.full_name, func.count(ConsultationBooking.id), func.sum(ConsultationBooking.price))
        .join(User, User.id == ConsultationBooking.consultant_id)
        .where(ConsultationBooking.status == "completed")
        .group_by(ConsultationBooking.consultant_id, User.full_name)
    ).all()
    summaries = [
        {
            "consultant_id": consultant_id,
            "full_name": full_name,
            "completed_sessions": count,
            "gross_amount": gross or 0,
            "platform_fee": (gross or 0) * 15 // 100,
            "payable": (gross or 0) * 85 // 100,
        }
        for consultant_id, full_name, count, gross in rows
    ]
    paid_by_consultant = dict(session.execute(
        select(ConsultantSettlement.consultant_id, func.sum(ConsultantSettlement.gross_amount))
        .where(ConsultantSettlement.status.in_(("pending", "paid")))
        .group_by(ConsultantSettlement.consultant_id)
    ).all())
    for item in summaries:
        item["settled_gross"] = paid_by_consultant.get(item["consultant_id"], 0) or 0
        item["unsettled_gross"] = max(0, item["gross_amount"] - item["settled_gross"])
        item["payable"] = item["unsettled_gross"] * 85 // 100
        profile = session.get(ConsultantProfile, item["consultant_id"])
        item["bank_iban"] = profile.bank_iban if profile else ""
    history = session.scalars(select(ConsultantSettlement).order_by(ConsultantSettlement.created_at.desc()).limit(200)).all()
    return {"summaries": summaries, "history": [{"id": item.id, "consultant_id": item.consultant_id, "gross_amount": item.gross_amount, "platform_fee": item.platform_fee, "payable_amount": item.payable_amount, "status": item.status, "bank_iban": item.bank_iban_snapshot, "reference": item.reference, "admin_note": item.admin_note, "created_at": item.created_at, "paid_at": item.paid_at} for item in history]}


@router.post("/admin/consultant-settlements", status_code=201)
def create_consultant_settlement(
    payload: SettlementRequest,
    actor: User = Depends(require_permissions("payments:manage")),
    session: Session = Depends(get_session),
):
    profile = session.get(ConsultantProfile, payload.consultant_id)
    if profile is None or not profile.bank_iban:
        raise HTTPException(422, "شماره شبای معتبر مشاور ثبت نشده است.")
    gross = session.scalar(select(func.sum(ConsultationBooking.price)).where(ConsultationBooking.consultant_id == payload.consultant_id, ConsultationBooking.status == "completed")) or 0
    settled = session.scalar(select(func.sum(ConsultantSettlement.gross_amount)).where(ConsultantSettlement.consultant_id == payload.consultant_id, ConsultantSettlement.status.in_(("pending", "paid")))) or 0
    unsettled = max(0, gross - settled)
    if not unsettled:
        raise HTTPException(422, "مبلغ تسویه‌نشده‌ای وجود ندارد.")
    item = ConsultantSettlement(consultant_id=payload.consultant_id, gross_amount=unsettled, platform_fee=unsettled * 15 // 100, payable_amount=unsettled * 85 // 100, bank_iban_snapshot=profile.bank_iban, admin_note=payload.admin_note.strip(), created_by=actor.id)
    session.add(item)
    session.add(AuditLog(actor_user_id=actor.id, action="consultant.settlement_created", resource_type="consultant_settlement", resource_id=item.id, metadata_json={"payable": item.payable_amount}))
    session.commit()
    return {"id": item.id, "status": item.status, "payable_amount": item.payable_amount}


@router.patch("/admin/consultant-settlements/{settlement_id}")
def review_consultant_settlement(
    settlement_id: str,
    payload: SettlementReviewRequest,
    actor: User = Depends(require_permissions("payments:manage")),
    session: Session = Depends(get_session),
):
    item = session.get(ConsultantSettlement, settlement_id)
    if item is None or item.status != "pending":
        raise HTTPException(409, "درخواست تسویه قابل تغییر نیست.")
    if payload.status == "paid" and not payload.reference.strip():
        raise HTTPException(422, "شماره پیگیری پرداخت الزامی است.")
    item.status = payload.status
    item.reference = payload.reference.strip()
    item.admin_note = payload.admin_note.strip()
    item.paid_at = datetime.now(timezone.utc) if payload.status == "paid" else None
    session.add(UserNotification(user_id=item.consultant_id, title="وضعیت تسویه به‌روزرسانی شد", message="تسویه شما پرداخت شد." if payload.status == "paid" else item.admin_note, notification_type="settlement", action_url="/consultant"))
    session.add(AuditLog(actor_user_id=actor.id, action=f"consultant.settlement_{payload.status}", resource_type="consultant_settlement", resource_id=item.id, metadata_json={"reference": item.reference}))
    session.commit()
    return {"id": item.id, "status": item.status}


@router.get("/admin/api-usage")
def api_usage(
    _: User = Depends(require_permissions("users:manage")),
    session: Session = Depends(get_session),
):
    since = datetime.now(timezone.utc) - timedelta(days=30)
    chats = session.scalar(select(func.count(ChatMessage.id)).where(ChatMessage.created_at >= since)) or 0
    tools = session.execute(
        select(ToolUsageEvent.tool_type, func.count(ToolUsageEvent.id))
        .where(ToolUsageEvent.created_at >= since)
        .group_by(ToolUsageEvent.tool_type)
    ).all()
    configuration = session.get(SiteConfiguration, 1)
    payload = SiteConfigPayload.model_validate(configuration.published_json if configuration else {})
    estimated_cost = chats * payload.ai_policy.estimated_cost_per_message_toman
    budget = payload.ai_policy.monthly_api_budget_toman
    return {
        "period_days": 30,
        "chat_messages": chats,
        "tool_usage": {name: count for name, count in tools},
        "recommended_monthly_alert": max(1, budget // payload.ai_policy.estimated_cost_per_message_toman),
        "estimated_cost_toman": estimated_cost,
        "monthly_budget_toman": budget,
        "budget_percent": min(100, round(estimated_cost / budget * 100)) if budget else 100,
        "alert_reached": estimated_cost >= budget,
    }


@router.get("/admin/audit-logs")
def audit_logs(
    _: User = Depends(require_permissions("audit:read")),
    session: Session = Depends(get_session),
):
    rows = session.execute(
        select(AuditLog, User.email)
        .outerjoin(User, User.id == AuditLog.actor_user_id)
        .order_by(AuditLog.created_at.desc())
        .limit(250)
    ).all()
    return [
        {
            "id": item.id,
            "actor_email": email or "system",
            "action": item.action,
            "resource_type": item.resource_type,
            "resource_id": item.resource_id,
            "metadata": item.metadata_json,
            "created_at": item.created_at,
        }
        for item, email in rows
    ]


@router.get("/admin/security-risk-events")
def security_risk_events(
    _: User = Depends(require_permissions("audit:read")),
    session: Session = Depends(get_session),
    status: str | None = None,
):
    query = select(SecurityRiskEvent, User.email).outerjoin(User, User.id == SecurityRiskEvent.user_id)
    if status:
        query = query.where(SecurityRiskEvent.status == status)
    rows = session.execute(query.order_by(SecurityRiskEvent.created_at.desc()).limit(500)).all()
    return [{
        "id": item.id, "user_email": email, "category": item.category,
        "severity": item.severity, "risk_score": item.risk_score,
        "ip_address": item.ip_address, "device_name": item.device_name,
        "details": item.details_json, "status": item.status, "created_at": item.created_at,
    } for item, email in rows]


@router.patch("/admin/security-risk-events/{event_id}")
def review_security_risk_event(
    event_id: str,
    payload: RiskReviewRequest,
    user: User = Depends(require_permissions("audit:read")),
    session: Session = Depends(get_session),
):
    item = session.get(SecurityRiskEvent, event_id)
    if item is None:
        raise HTTPException(404, "رخداد امنیتی پیدا نشد.")
    item.status = payload.status
    item.resolved_by_user_id = user.id
    item.resolved_at = datetime.now(timezone.utc) if payload.status in {"resolved", "false_positive"} else None
    session.commit()
    return {"id": item.id, "status": item.status, "resolved_at": item.resolved_at}


@router.post("/admin/notifications/broadcast", status_code=201)
def broadcast_notification(
    payload: BroadcastRequest,
    user: User = Depends(require_permissions("notifications:manage")),
    session: Session = Depends(get_session),
):
    query = select(User.id).where(User.is_active.is_(True))
    if payload.audience != "all":
        query = query.where(User.account_tier == payload.audience)
    user_ids = list(session.scalars(query))
    session.add_all([
        UserNotification(
            user_id=user_id,
            title=payload.title,
            message=payload.message,
            notification_type="announcement",
            action_url=payload.action_url,
        )
        for user_id in user_ids
    ])
    session.add(AuditLog(actor_user_id=user.id, action="notification.broadcast", resource_type="user_notification", metadata_json={"audience": payload.audience, "recipients": len(user_ids)}))
    session.commit()
    return {"recipients": len(user_ids)}


@router.post("/admin/payments/{payment_id}/refund")
def refund_payment(
    payment_id: str,
    payload: RefundRequest,
    user: User = Depends(require_permissions("payments:manage")),
    session: Session = Depends(get_session),
):
    payment = session.scalar(select(Payment).where(Payment.id == payment_id).with_for_update())
    if payment is None:
        raise HTTPException(404, "پرداخت پیدا نشد")
    if payment.status != "paid":
        raise HTTPException(409, "این پرداخت قابل بازپرداخت نیست")
    wallet = session.scalar(select(WalletAccount).where(WalletAccount.user_id == payment.user_id).with_for_update())
    if wallet is None:
        wallet = WalletAccount(user_id=payment.user_id, balance=0)
        session.add(wallet)
        session.flush()
    wallet.balance += payment.amount
    payment.status = "refunded"
    subscription = session.scalar(
        select(UserSubscription)
        .where(UserSubscription.user_id == payment.user_id, UserSubscription.plan_id == payment.plan_id, UserSubscription.status == "active")
        .order_by(UserSubscription.created_at.desc())
    )
    if subscription:
        subscription.status = "refunded"
        account = session.get(User, payment.user_id)
        if account:
            account.account_tier = "normal"
    session.add_all([
        WalletTransaction(user_id=payment.user_id, transaction_type="refund", amount=payment.amount, status="completed", reference=f"REF-{payment.gateway_reference or payment.id}", related_type="payment", related_id=payment.id, otp_hash="", otp_expires_at=datetime.now(timezone.utc), processed_at=datetime.now(timezone.utc)),
        UserNotification(user_id=payment.user_id, title="بازپرداخت انجام شد", message=f"مبلغ {payment.amount:,} تومان به کیف پول شما بازگشت.", notification_type="payment", action_url="/app/wallet"),
        AuditLog(actor_user_id=user.id, action="payment.refunded", resource_type="payment", resource_id=payment.id, metadata_json={"amount": payment.amount, "reason": payload.reason}),
    ])
    session.commit()
    return {"ok": True, "amount": payment.amount}


@router.get("/admin/system-monitor")
def system_monitor(
    _: User = Depends(require_permissions("site:manage")),
    session: Session = Depends(get_session),
):
    since = datetime.now(timezone.utc) - timedelta(hours=24)
    return {
        "status": "healthy",
        "database": "up",
        "failed_logins_24h": session.scalar(
            select(func.count(FailedLoginAttempt.id)).where(FailedLoginAttempt.attempted_at >= since)
        ) or 0,
        "unread_notifications": session.scalar(
            select(func.count(UserNotification.id)).where(UserNotification.is_read.is_(False))
        ) or 0,
        "generated_at": datetime.now(timezone.utc),
    }


def workbook_response(kind: str, rows: list[list[object]], headers: list[str]) -> StreamingResponse:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = kind
    sheet.append(headers)
    for row in rows:
        sheet.append(row)
    stream = BytesIO()
    workbook.save(stream)
    stream.seek(0)
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{kind}.xlsx"'},
    )


@router.get("/admin/export/{kind}.xlsx")
def export_excel(
    kind: str,
    _: User = Depends(require_permissions("users:manage")),
    session: Session = Depends(get_session),
):
    if kind == "users":
        users = session.scalars(select(User).order_by(User.created_at.desc())).all()
        return workbook_response(
            "users",
            [[item.id, item.full_name, item.email, item.account_tier, item.is_active, item.created_at.isoformat()] for item in users],
            ["id", "full_name", "email", "account_tier", "is_active", "created_at"],
        )
    if kind == "payments":
        payments = session.scalars(select(Payment).order_by(Payment.created_at.desc())).all()
        return workbook_response(
            "payments",
            [[item.id, item.user_id, item.plan.title, item.amount, item.discount_amount, item.status, item.gateway_reference, item.created_at.isoformat()] for item in payments],
            ["id", "user_id", "plan", "amount", "discount", "status", "reference", "created_at"],
        )
    if kind == "consultants":
        rows = session.execute(
            select(ConsultantProfile, User.full_name, User.email)
            .join(User, User.id == ConsultantProfile.user_id)
            .order_by(User.full_name)
        ).all()
        return workbook_response(
            "consultants",
            [[profile.user_id, full_name, email, profile.consultant_type, profile.professional_title, profile.rating, profile.consultation_price, profile.contract_status, profile.contract_end.isoformat() if profile.contract_end else "", profile.bank_iban] for profile, full_name, email in rows],
            ["id", "full_name", "email", "type", "title", "rating", "session_price", "contract_status", "contract_end", "iban"],
        )
    raise HTTPException(404, "نوع خروجی پشتیبانی نمی‌شود")


@router.get("/admin/consultants-report.pdf")
def consultants_report_pdf(
    _: User = Depends(require_permissions("payments:manage")),
    session: Session = Depends(get_session),
):
    rows = session.execute(
        select(ConsultantProfile, User.full_name)
        .join(User, User.id == ConsultantProfile.user_id)
        .order_by(User.full_name)
    ).all()
    document = fitz.open()
    page = document.new_page(width=595, height=842)
    y = 60
    page.insert_text((50, y), "CHAKAH - CONSULTANT FINANCIAL REPORT", fontsize=15)
    y += 30
    for profile, full_name in rows:
        gross = session.scalar(select(func.sum(ConsultationBooking.price)).where(ConsultationBooking.consultant_id == profile.user_id, ConsultationBooking.status == "completed")) or 0
        line = f"{full_name[:25]} | Gross: {gross:,} | Payable: {gross * 85 // 100:,} | Contract: {profile.contract_status}"
        if y > 790:
            page = document.new_page(width=595, height=842)
            y = 60
        page.insert_text((50, y), line, fontsize=9)
        y += 18
    payload = document.tobytes()
    document.close()
    return StreamingResponse(BytesIO(payload), media_type="application/pdf", headers={"Content-Disposition": 'attachment; filename="consultants-report.pdf"'})
