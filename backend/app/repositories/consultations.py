from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.consultations import ConsultationRequest, ConsultationStatusHistory


class ConsultationRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(
        self,
        *,
        user_id: str,
        subject: str,
        description: str,
        source_message_id: str | None,
    ) -> ConsultationRequest:
        item = ConsultationRequest(
            user_id=user_id,
            subject=subject,
            description=description,
            source_message_id=source_message_id,
        )
        self.session.add(item)
        self.session.flush()
        return item

    def add_history(
        self,
        item: ConsultationRequest,
        *,
        changed_by: str,
        from_status: str | None,
        to_status: str,
        note: str,
    ) -> None:
        self.session.add(
            ConsultationStatusHistory(
                consultation_id=item.id,
                changed_by=changed_by,
                from_status=from_status,
                to_status=to_status,
                note=note,
            )
        )

    def get(self, consultation_id: str) -> ConsultationRequest | None:
        return self.session.scalar(
            select(ConsultationRequest)
            .where(ConsultationRequest.id == consultation_id)
            .options(selectinload(ConsultationRequest.history))
        )

    def list_for_user(self, user_id: str) -> list[ConsultationRequest]:
        return list(
            self.session.scalars(
                select(ConsultationRequest)
                .where(ConsultationRequest.user_id == user_id)
                .options(selectinload(ConsultationRequest.history))
                .order_by(ConsultationRequest.updated_at.desc())
            )
        )

    def list_all(self, status: str | None = None) -> list[ConsultationRequest]:
        statement = select(ConsultationRequest).options(
            selectinload(ConsultationRequest.history)
        )
        if status:
            statement = statement.where(ConsultationRequest.status == status)
        return list(
            self.session.scalars(statement.order_by(ConsultationRequest.updated_at.desc()))
        )

    def list_assigned(self, user_id: str) -> list[ConsultationRequest]:
        return list(
            self.session.scalars(
                select(ConsultationRequest)
                .where(ConsultationRequest.assigned_to == user_id)
                .options(selectinload(ConsultationRequest.history))
                .order_by(ConsultationRequest.updated_at.desc())
            )
        )
