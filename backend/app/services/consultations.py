from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.auth import User
import uuid

from app.models.consultations import ConsultationRequest
from app.models.portal import WalletAccount, WalletTransaction
from app.repositories.advisor import AdvisorRepository
from app.repositories.auth import AuthRepository
from app.repositories.consultations import ConsultationRepository
from app.services.plans import scaled_limits


class ConsultationNotFoundError(Exception):
    pass


class InvalidConsultationError(Exception):
    pass


class ConsultationService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = ConsultationRepository(session)
        self.audit = AuthRepository(session)

    def create(
        self,
        *,
        subject: str,
        description: str,
        source_message_id: str | None,
        use_wallet_if_needed: bool = False,
        user: User,
    ) -> ConsultationRequest:
        month_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        limits = {"normal": {"consultations": 1}, "plus": {"consultations": 2}, "pro": {"consultations": 10}}
        used = self.session.scalar(select(func.count(ConsultationRequest.id)).where(ConsultationRequest.user_id == user.id, ConsultationRequest.created_at >= month_start)) or 0
        free_limit = scaled_limits(self.session, user, limits)["consultations"]
        billing_type = "free"
        price = 0
        if used >= free_limit:
            price = 149_000
            if not use_wallet_if_needed:
                raise InvalidConsultationError("سهمیه رایگان تمام شده است؛ ادامه مشاوره ۱۴۹٬۰۰۰ تومان هزینه دارد")
            wallet = self.session.get(WalletAccount, user.id)
            if wallet is None or wallet.balance < price:
                raise InvalidConsultationError("موجودی کیف پول برای ادامه مشاوره کافی نیست")
            wallet.balance -= price
            billing_type = "wallet"
            self.session.add(WalletTransaction(user_id=user.id, transaction_type="consultation", amount=price, status="completed", reference=f"CONSULT-{uuid.uuid4().hex[:12].upper()}", otp_hash="", otp_expires_at=datetime.now(timezone.utc)))
        if source_message_id and AdvisorRepository(
            self.session
        ).get_owned_assistant_message(source_message_id, user.id) is None:
            raise InvalidConsultationError("Source message does not belong to user")
        item = self.repository.create(
            user_id=user.id,
            subject=subject.strip(),
            description=description.strip(),
            source_message_id=source_message_id,
        )
        item.billing_type = billing_type
        item.price = price
        self.repository.add_history(
            item,
            changed_by=user.id,
            from_status=None,
            to_status="submitted",
            note="",
        )
        self.audit.add_audit(
            "consultation.created",
            "consultation",
            actor_user_id=user.id,
            resource_id=item.id,
        )
        self.session.commit()
        return self.repository.get(item.id) or item

    def list_for_user(self, user: User) -> list[ConsultationRequest]:
        return self.repository.list_for_user(user.id)

    def get_for_user(self, consultation_id: str, user: User) -> ConsultationRequest:
        item = self.repository.get(consultation_id)
        if item is None or item.user_id != user.id:
            raise ConsultationNotFoundError
        return item

    def list_all(self, status: str | None) -> list[ConsultationRequest]:
        return self.repository.list_all(status)

    def list_assigned(self, user: User) -> list[ConsultationRequest]:
        return self.repository.list_assigned(user.id)

    def handle_assigned(
        self,
        consultation_id: str,
        *,
        status: str,
        internal_note: str,
        resolution: str,
        note: str,
        user: User,
    ) -> ConsultationRequest:
        item = self.repository.get(consultation_id)
        if item is None or item.assigned_to != user.id:
            raise ConsultationNotFoundError
        if status == "resolved" and not resolution.strip():
            raise InvalidConsultationError("Resolution is required")
        previous_status = item.status
        item.status = status
        item.internal_note = internal_note
        item.resolution = resolution
        self.repository.add_history(
            item,
            changed_by=user.id,
            from_status=previous_status,
            to_status=status,
            note=note,
        )
        self.audit.add_audit(
            "consultation.handled",
            "consultation",
            actor_user_id=user.id,
            resource_id=item.id,
            metadata={"from_status": previous_status, "to_status": status},
        )
        self.session.commit()
        return self.repository.get(item.id) or item

    def update(
        self,
        consultation_id: str,
        *,
        status: str,
        priority: str | None,
        assigned_to: str | None,
        internal_note: str,
        resolution: str,
        note: str,
        user: User,
    ) -> ConsultationRequest:
        item = self.repository.get(consultation_id)
        if item is None:
            raise ConsultationNotFoundError
        previous_status = item.status
        item.status = status
        if priority is not None:
            item.priority = priority
        item.assigned_to = assigned_to
        item.internal_note = internal_note
        item.resolution = resolution
        if status == "resolved" and not resolution.strip():
            raise InvalidConsultationError("Resolution is required")
        self.repository.add_history(
            item,
            changed_by=user.id,
            from_status=previous_status,
            to_status=status,
            note=note,
        )
        self.audit.add_audit(
            "consultation.updated",
            "consultation",
            actor_user_id=user.id,
            resource_id=item.id,
            metadata={"from_status": previous_status, "to_status": status},
        )
        self.session.commit()
        return self.repository.get(item.id) or item
