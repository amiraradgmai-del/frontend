from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ConsultationCreateRequest(BaseModel):
    subject: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=10, max_length=5000)
    source_message_id: str | None = None
    use_wallet_if_needed: bool = False


class ConsultationUpdateRequest(BaseModel):
    status: Literal[
        "submitted", "in_review", "waiting_for_user", "resolved", "closed"
    ]
    priority: Literal["normal", "high"] | None = None
    assigned_to: str | None = None
    internal_note: str = Field(default="", max_length=5000)
    resolution: str = Field(default="", max_length=5000)
    note: str = Field(default="", max_length=1000)


class ConsultationHandleRequest(BaseModel):
    status: Literal["in_review", "waiting_for_user", "resolved", "closed"]
    internal_note: str = Field(default="", max_length=5000)
    resolution: str = Field(default="", max_length=5000)
    note: str = Field(default="", max_length=1000)


class ConsultationHistoryResponse(BaseModel):
    from_status: str | None
    to_status: str
    note: str
    created_at: datetime


class ConsultationResponse(BaseModel):
    id: str
    user_id: str
    source_message_id: str | None
    assigned_to: str | None
    subject: str
    description: str
    status: str
    priority: str
    resolution: str
    billing_type: str
    price: int
    created_at: datetime
    updated_at: datetime
    history: list[ConsultationHistoryResponse]


class ConsultationManagerResponse(ConsultationResponse):
    internal_note: str


class BookingCreateRequest(BaseModel):
    consultant_id: str
    scheduled_at: datetime
    mode: Literal["online", "in_person"] = "online"
    notes: str = Field(default="", max_length=1000)


class VerificationRequestCreate(BaseModel):
    consultant_type: Literal["independent", "company"]
    professional_title: str = Field(min_length=3, max_length=160)
    national_id: str = Field(default="", max_length=20, pattern=r"^$|^[0-9]{10,12}$")
    license_number: str = Field(default="", max_length=80)
    specialties: list[str] = Field(min_length=1, max_length=12)
    years_experience: int = Field(ge=0, le=70)
    qualifications: str = Field(min_length=10, max_length=5000)
    document_ids: list[str] = Field(default_factory=list, max_length=12)
    applicant_note: str = Field(default="", max_length=2000)
    bio: str = Field(default="", max_length=5000)
    skills: list[str] = Field(default_factory=list, max_length=20)
    education: list[dict] = Field(default_factory=list, max_length=10)
    certifications: list[dict] = Field(default_factory=list, max_length=20)
    work_history: list[dict] = Field(default_factory=list, max_length=20)
    weekly_schedule: dict = Field(default_factory=dict)
    profile_image_url: str = Field(default="", max_length=500)
    consultation_price: int = Field(default=0, ge=0, le=100_000_000)
    city: str = Field(default="", max_length=80)
    office_address: str = Field(default="", max_length=300)
    is_online: bool = True
    offers_in_person: bool = True


class VerificationReviewRequest(BaseModel):
    status: Literal["approved", "rejected", "correction_required"]
    admin_note: str = Field(default="", max_length=3000)


class ConsultantAdminUpdate(BaseModel):
    professional_title: str | None = Field(default=None, min_length=3, max_length=160)
    bio: str | None = Field(default=None, max_length=5000)
    specialties: list[str] | None = Field(default=None, max_length=12)
    skills: list[str] | None = Field(default=None, max_length=20)
    qualifications: str | None = Field(default=None, max_length=5000)
    consultation_price: int | None = Field(default=None, ge=0, le=100_000_000)
    is_verified: bool | None = None
    is_available: bool | None = None
    is_online: bool | None = None
    offers_in_person: bool | None = None
    city: str | None = Field(default=None, max_length=80)
    office_address: str | None = Field(default=None, max_length=300)
    years_experience: int | None = Field(default=None, ge=0, le=70)
    bank_account_holder: str | None = Field(default=None, max_length=120)
    bank_iban: str | None = Field(default=None, pattern=r"^$|^IR[0-9]{24}$")
    contract_number: str | None = Field(default=None, max_length=100)
    contract_start: datetime | None = None
    contract_end: datetime | None = None
    contract_status: Literal["not_set", "draft", "active", "expired", "terminated"] | None = None
