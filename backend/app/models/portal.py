from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.auth import new_uuid


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class UserProfile(Base):
    __tablename__ = "user_profiles"

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    phone: Mapped[str] = mapped_column(String(20), default="")
    alternate_phone: Mapped[str] = mapped_column(String(20), default="", server_default="")
    alternate_email: Mapped[str] = mapped_column(String(320), default="", server_default="")
    phone_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
    )
    phone_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    province: Mapped[str] = mapped_column(String(80), default="")
    city: Mapped[str] = mapped_column(String(80), default="")
    postal_code: Mapped[str] = mapped_column(String(10), default="", server_default="")
    address: Mapped[str] = mapped_column(String(500), default="", server_default="")
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    company_name: Mapped[str] = mapped_column(String(160), default="")
    job_title: Mapped[str] = mapped_column(String(100), default="")
    business_type: Mapped[str] = mapped_column(String(80), default="", server_default="")
    economic_code: Mapped[str] = mapped_column(String(20), default="", server_default="")
    website: Mapped[str] = mapped_column(String(300), default="", server_default="")
    taxpayer_type: Mapped[str] = mapped_column(String(30), default="individual")
    preferred_contact_method: Mapped[str] = mapped_column(String(20), default="phone", server_default="phone")
    marketing_notifications: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    service_notifications: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    bio: Mapped[str] = mapped_column(Text, default="")
    profile_score: Mapped[int] = mapped_column(Integer, default=10, server_default="10")
    reward_points: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    completion_rewarded: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    referral_code: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    referred_by_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class PhoneVerificationChallenge(Base):
    __tablename__ = "phone_verification_challenges"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=new_uuid,
    )
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    phone: Mapped[str] = mapped_column(
        String(20),
        index=True,
    )
    code_hash: Mapped[str] = mapped_column(
        String(64),
    )
    attempts: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0",
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
    )
    last_sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
    )
    used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        index=True,
    )


class WalletAccount(Base):
    __tablename__ = "wallet_accounts"

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    balance: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class WalletTransaction(Base):
    __tablename__ = "wallet_transactions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    transaction_type: Mapped[str] = mapped_column(String(20), index=True)
    amount: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="otp_pending", index=True)
    reference: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    related_type: Mapped[str] = mapped_column(String(40), default="", server_default="")
    related_id: Mapped[str | None] = mapped_column(String(64), index=True)
    failure_reason: Mapped[str] = mapped_column(Text, default="", server_default="")
    otp_hash: Mapped[str] = mapped_column(String(64))
    otp_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)


class SubscriptionPlan(Base):
    __tablename__ = "subscription_plans"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    code: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(80))
    description: Mapped[str] = mapped_column(String(500), default="")
    price: Mapped[int] = mapped_column(Integer)
    duration_days: Mapped[int] = mapped_column(Integer, default=30)
    benefits: Mapped[list[str]] = mapped_column(JSON, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class UserSubscription(Base):
    __tablename__ = "user_subscriptions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    plan_id: Mapped[str] = mapped_column(String(36), ForeignKey("subscription_plans.id"))
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)
    package_code: Mapped[str] = mapped_column(String(20), default="silver", server_default="silver")
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    auto_renew: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    plan: Mapped[SubscriptionPlan] = relationship(lazy="joined")


class PaymentMethod(Base):
    __tablename__ = "payment_methods"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    cardholder_name: Mapped[str] = mapped_column(String(120))
    last_four: Mapped[str] = mapped_column(String(4))
    issuer: Mapped[str] = mapped_column(String(80), default="کارت بانکی")
    fingerprint: Mapped[str] = mapped_column(String(64), unique=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class PaymentOtpChallenge(Base):
    __tablename__ = "payment_otp_challenges"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    plan_code: Mapped[str] = mapped_column(String(20))
    payment_method_id: Mapped[str] = mapped_column(String(36), ForeignKey("payment_methods.id", ondelete="CASCADE"))
    discount_code: Mapped[str] = mapped_column(String(32), default="")
    otp_hash: Mapped[str] = mapped_column(String(64))
    attempts: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class DiscountCode(Base):
    __tablename__ = "discount_codes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    percent: Mapped[int] = mapped_column(Integer)
    max_uses: Mapped[int] = mapped_column(Integer, default=100)
    used_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    plan_id: Mapped[str] = mapped_column(String(36), ForeignKey("subscription_plans.id"))
    payment_method_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("payment_methods.id", ondelete="SET NULL"))
    discount_code_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("discount_codes.id", ondelete="SET NULL"))
    amount: Mapped[int] = mapped_column(Integer)
    discount_amount: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    gateway_name: Mapped[str] = mapped_column(String(30), default="internal", server_default="internal")
    gateway_authority: Mapped[str | None] = mapped_column(String(100), unique=True, index=True)
    gateway_reference: Mapped[str | None] = mapped_column(String(100), unique=True)
    package_code: Mapped[str] = mapped_column(String(20), default="silver", server_default="silver")
    card_pan: Mapped[str | None] = mapped_column(String(40))
    card_hash: Mapped[str | None] = mapped_column(String(128))
    failure_reason: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    plan: Mapped[SubscriptionPlan] = relationship(lazy="joined")


class UserDocument(Base):
    __tablename__ = "user_documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    document_type: Mapped[str] = mapped_column(String(60), default="other", server_default="other", index=True)
    description: Mapped[str] = mapped_column(Text, default="", server_default="")
    purpose: Mapped[str] = mapped_column(String(80), default="general_review", server_default="general_review", index=True)
    intended_reviewer: Mapped[str] = mapped_column(String(40), default="support", server_default="support", index=True)
    original_filename: Mapped[str] = mapped_column(String(255))
    storage_key: Mapped[str] = mapped_column(String(500), unique=True)
    mime_type: Mapped[str] = mapped_column(String(100))
    file_size: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="uploaded", index=True)
    admin_note: Mapped[str] = mapped_column(Text, default="")
    reviewed_by: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), index=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class SupportTicket(Base):
    __tablename__ = "support_tickets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    assigned_staff_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), index=True)
    subject: Mapped[str] = mapped_column(String(200))
    category: Mapped[str] = mapped_column(String(40), default="general")
    priority: Mapped[str] = mapped_column(String(20), default="normal")
    status: Mapped[str] = mapped_column(String(20), default="open", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
    messages: Mapped[list[TicketMessage]] = relationship(back_populates="ticket", cascade="all, delete-orphan", lazy="selectin", order_by="TicketMessage.created_at")


class TicketMessage(Base):
    __tablename__ = "ticket_messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    ticket_id: Mapped[str] = mapped_column(String(36), ForeignKey("support_tickets.id", ondelete="CASCADE"), index=True)
    sender_user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"))
    message: Mapped[str] = mapped_column(Text)
    attachment_name: Mapped[str] = mapped_column(String(255), default="", server_default="")
    attachment_key: Mapped[str] = mapped_column(String(500), default="", server_default="")
    attachment_mime: Mapped[str] = mapped_column(String(100), default="", server_default="")
    is_staff: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    ticket: Mapped[SupportTicket] = relationship(back_populates="messages")


class TaxReminder(Base):
    __tablename__ = "tax_reminders"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(String(1000), default="")
    due_date: Mapped[date] = mapped_column(Date, index=True)
    category: Mapped[str] = mapped_column(String(40), default="general")
    is_done: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    notify_days_before: Mapped[int] = mapped_column(Integer, default=3)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ToolUsageEvent(Base):
    __tablename__ = "tool_usage_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    tool_type: Mapped[str] = mapped_column(String(30), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)


class UserNotification(Base):
    __tablename__ = "user_notifications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    message: Mapped[str] = mapped_column(String(1000), default="")
    notification_type: Mapped[str] = mapped_column(String(40), default="general", index=True)
    action_url: Mapped[str] = mapped_column(String(500), default="")
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)


class LawReferenceRecord(Base):
    __tablename__ = "law_reference_records"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    source_id: Mapped[str] = mapped_column(String(40), index=True)
    law_name: Mapped[str] = mapped_column(String(300), index=True)
    chapter: Mapped[str] = mapped_column(String(300), default="")
    article_number: Mapped[str] = mapped_column(String(50), index=True)
    official_text: Mapped[str] = mapped_column(Text)
    source_url: Mapped[str] = mapped_column(String(1000))
    keywords: Mapped[str] = mapped_column(String(500), default="")
    clause: Mapped[str] = mapped_column(String(80), default="", server_default="")
    source_type: Mapped[str] = mapped_column(String(24), default="official", server_default="official", index=True)
    legal_status: Mapped[str] = mapped_column(String(24), default="valid", server_default="valid", index=True)
    fiscal_year: Mapped[int | None] = mapped_column(Integer, index=True)
    approval_date: Mapped[date | None] = mapped_column(Date)
    expiry_date: Mapped[date | None] = mapped_column(Date)
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    verified_by_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), index=True)
    supersedes_record_id: Mapped[str | None] = mapped_column(String(80), ForeignKey("law_reference_records.id", ondelete="SET NULL"), index=True)
    category_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("legal_categories.id", ondelete="SET NULL"), index=True)
    publication_date: Mapped[date | None] = mapped_column(Date)
    effective_date: Mapped[date | None] = mapped_column(Date)
    source_info: Mapped[str] = mapped_column(String(500), default="", server_default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", index=True)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class LegalCategory(Base):
    __tablename__ = "legal_categories"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(String(500), default="")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class LegalExternalSource(Base):
    __tablename__ = "legal_external_sources"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    title: Mapped[str] = mapped_column(String(200))
    base_url: Mapped[str] = mapped_column(String(1000))
    source_type: Mapped[str] = mapped_column(String(40), default="website")
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", index=True)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_status: Mapped[str] = mapped_column(String(30), default="not_checked", server_default="not_checked")
    last_error: Mapped[str] = mapped_column(Text, default="", server_default="")
    content_hash: Mapped[str] = mapped_column(String(64), default="", server_default="")
    last_title: Mapped[str] = mapped_column(String(300), default="", server_default="")
    last_content_length: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class LegalUpdateCandidate(Base):
    __tablename__ = "legal_update_candidates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    source_id: Mapped[str] = mapped_column(String(36), ForeignKey("legal_external_sources.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(300))
    article_number: Mapped[str] = mapped_column(String(50), default="")
    proposed_text: Mapped[str] = mapped_column(Text)
    source_url: Mapped[str] = mapped_column(String(1000), default="")
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    status: Mapped[str] = mapped_column(String(30), default="pending", server_default="pending", index=True)
    reviewer_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"))
    review_note: Mapped[str] = mapped_column(Text, default="", server_default="")
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
