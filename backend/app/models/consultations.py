from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, CheckConstraint, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def new_uuid() -> str:
    return str(uuid.uuid4())


class ConsultationRequest(Base):
    __tablename__ = "consultation_requests"
    __table_args__ = (
        CheckConstraint(
            "status IN ('submitted','in_review','waiting_for_user','resolved','closed')",
            name="ck_consultation_requests_status",
        ),
        CheckConstraint(
            "priority IN ('normal','high')",
            name="ck_consultation_requests_priority",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    source_message_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("chat_messages.id", ondelete="SET NULL")
    )
    assigned_to: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    subject: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        String(30), default="submitted", server_default="submitted"
    )
    priority: Mapped[str] = mapped_column(
        String(10), default="normal", server_default="normal"
    )
    internal_note: Mapped[str] = mapped_column(Text, default="")
    resolution: Mapped[str] = mapped_column(Text, default="")
    billing_type: Mapped[str] = mapped_column(String(20), default="free", server_default="free")
    price: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    history: Mapped[list[ConsultationStatusHistory]] = relationship(
        back_populates="consultation",
        cascade="all, delete-orphan",
        order_by="ConsultationStatusHistory.created_at",
    )


class ConsultationStatusHistory(Base):
    __tablename__ = "consultation_status_history"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    consultation_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("consultation_requests.id", ondelete="CASCADE"),
        index=True,
    )
    changed_by: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="RESTRICT")
    )
    from_status: Mapped[str | None] = mapped_column(String(30))
    to_status: Mapped[str] = mapped_column(String(30))
    note: Mapped[str] = mapped_column(String(1000), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    consultation: Mapped[ConsultationRequest] = relationship(back_populates="history")


class ConsultantProfile(Base):
    __tablename__ = "consultant_profiles"
    __table_args__ = (
        CheckConstraint("consultant_type IN ('independent','company')", name="ck_consultant_profiles_type"),
    )

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    consultant_type: Mapped[str] = mapped_column(String(20), index=True)
    professional_title: Mapped[str] = mapped_column(String(160))
    bio: Mapped[str] = mapped_column(Text)
    specialties: Mapped[list[str]] = mapped_column(JSON, default=list)
    skills: Mapped[list[str]] = mapped_column(JSON, default=list)
    qualifications: Mapped[str] = mapped_column(Text, default="", server_default="")
    education: Mapped[list[dict]] = mapped_column(JSON, default=list)
    certifications: Mapped[list[dict]] = mapped_column(JSON, default=list)
    work_history: Mapped[list[dict]] = mapped_column(JSON, default=list)
    weekly_schedule: Mapped[dict] = mapped_column(JSON, default=dict)
    profile_image_url: Mapped[str] = mapped_column(
        String(500), default="", server_default=""
    )
    years_experience: Mapped[int] = mapped_column(Integer, default=0)
    rating: Mapped[float] = mapped_column(Float, default=5.0)
    review_count: Mapped[int] = mapped_column(Integer, default=0)
    consultation_price: Mapped[int] = mapped_column(Integer, default=0)
    city: Mapped[str] = mapped_column(String(80), default="", server_default="")
    office_address: Mapped[str] = mapped_column(String(300), default="", server_default="")
    is_online: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    offers_in_person: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    is_available: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    bank_account_holder: Mapped[str] = mapped_column(String(120), default="", server_default="")
    bank_iban: Mapped[str] = mapped_column(String(34), default="", server_default="")
    blocked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    blocked_reason: Mapped[str] = mapped_column(Text, default="", server_default="")
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    contract_number: Mapped[str] = mapped_column(String(100), default="", server_default="")
    contract_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    contract_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    contract_status: Mapped[str] = mapped_column(String(20), default="not_set", server_default="not_set", index=True)
    boosted_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ConsultantVerificationRequest(Base):
    __tablename__ = "consultant_verification_requests"
    __table_args__ = (
        CheckConstraint(
            "consultant_type IN ('independent','company')",
            name="ck_consultant_verification_type",
        ),
        CheckConstraint(
            "status IN ('pending','approved','rejected','correction_required')",
            name="ck_consultant_verification_status",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    consultant_type: Mapped[str] = mapped_column(String(20), index=True)
    professional_title: Mapped[str] = mapped_column(String(160))
    national_id: Mapped[str] = mapped_column(String(20), default="")
    license_number: Mapped[str] = mapped_column(String(80), default="")
    specialties: Mapped[list[str]] = mapped_column(JSON, default=list)
    years_experience: Mapped[int] = mapped_column(Integer, default=0)
    qualifications: Mapped[str] = mapped_column(Text, default="")
    document_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    profile_payload: Mapped[dict] = mapped_column(JSON, default=dict, server_default="{}")
    status: Mapped[str] = mapped_column(
        String(30), default="pending", server_default="pending", index=True
    )
    applicant_note: Mapped[str] = mapped_column(Text, default="")
    admin_note: Mapped[str] = mapped_column(Text, default="")
    reviewed_by: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL")
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class ConsultationBooking(Base):
    __tablename__ = "consultation_bookings"
    __table_args__ = (
        UniqueConstraint("consultant_id", "scheduled_at", name="uq_consultation_booking_slot"),
        CheckConstraint("mode IN ('online','in_person','phone')", name="ck_consultation_bookings_mode"),
        CheckConstraint("status IN ('reserved','completed','cancelled')", name="ck_consultation_bookings_status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    consultant_id: Mapped[str] = mapped_column(String(36), ForeignKey("consultant_profiles.user_id", ondelete="CASCADE"), index=True)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=30)
    mode: Mapped[str] = mapped_column(String(20), default="online")
    status: Mapped[str] = mapped_column(String(20), default="reserved", server_default="reserved")
    price: Mapped[int] = mapped_column(Integer, default=0)
    notes: Mapped[str] = mapped_column(Text, default="")
    session_report: Mapped[str] = mapped_column(Text, default="", server_default="")
    cancelled_by: Mapped[str] = mapped_column(String(20), default="", server_default="")
    cancellation_reason: Mapped[str] = mapped_column(Text, default="", server_default="")
    refund_amount: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ConsultantReview(Base):
    __tablename__ = "consultant_reviews"
    __table_args__ = (
        UniqueConstraint("booking_id", name="uq_consultant_review_booking"),
        CheckConstraint("rating BETWEEN 1 AND 5", name="ck_consultant_review_rating"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    booking_id: Mapped[str] = mapped_column(String(36), ForeignKey("consultation_bookings.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    consultant_id: Mapped[str] = mapped_column(String(36), ForeignKey("consultant_profiles.user_id", ondelete="CASCADE"), index=True)
    rating: Mapped[int] = mapped_column(Integer)
    comment: Mapped[str] = mapped_column(String(1000), default="")
    moderation_status: Mapped[str] = mapped_column(
        String(20), default="published", server_default="published", index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ConsultantSettlement(Base):
    __tablename__ = "consultant_settlements"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending','paid','rejected')",
            name="ck_consultant_settlements_status",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    consultant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("consultant_profiles.user_id", ondelete="CASCADE"), index=True
    )
    gross_amount: Mapped[int] = mapped_column(Integer)
    platform_fee: Mapped[int] = mapped_column(Integer)
    payable_amount: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="pending", server_default="pending", index=True)
    bank_iban_snapshot: Mapped[str] = mapped_column(String(34), default="")
    reference: Mapped[str] = mapped_column(String(100), default="")
    admin_note: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="RESTRICT"))
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
