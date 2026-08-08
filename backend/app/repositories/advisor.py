from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models.advisor import ChatMessage, Conversation, MessageCitation, MessageFeedback, RetrievalLog
from app.models.documents import Document, DocumentChunk, DocumentTopic, DocumentVersion


class AdvisorRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create_conversation(self, user_id: str, title: str) -> Conversation:
        item = Conversation(user_id=user_id, title=title)
        self.session.add(item)
        self.session.flush()
        return item

    def get_conversation(self, conversation_id: str, user_id: str) -> Conversation | None:
        return self.session.scalar(select(Conversation).where(Conversation.id == conversation_id, Conversation.user_id == user_id, Conversation.deleted_at.is_(None)).options(selectinload(Conversation.messages)))

    def list_conversations(self, user_id: str) -> list[Conversation]:
        return list(self.session.scalars(select(Conversation).where(Conversation.user_id == user_id, Conversation.deleted_at.is_(None)).order_by(Conversation.updated_at.desc())))

    def add_message(self, conversation_id: str, role: str, content: str, **values) -> ChatMessage:
        item = ChatMessage(conversation_id=conversation_id, role=role, content=content, **values)
        self.session.add(item)
        self.session.flush()
        return item

    def recent_user_messages(self, user_id: str, *, limit: int = 5) -> list[str]:
        statement = (
            select(ChatMessage.content)
            .join(Conversation)
            .where(
                Conversation.user_id == user_id,
                Conversation.deleted_at.is_(None),
                ChatMessage.role == "user",
            )
            .order_by(ChatMessage.created_at.desc())
            .limit(limit)
        )
        return list(reversed(list(self.session.scalars(statement))))

    def active_chunks(
        self, *, as_of_date: date | None = None, topics: list[str] | None = None
    ) -> list[DocumentChunk]:
        target_date = as_of_date or date.today()
        statement = select(DocumentChunk).join(DocumentVersion).join(Document).where(
            Document.deleted_at.is_(None), DocumentVersion.status == "ready",
            DocumentVersion.review_status == "approved", DocumentVersion.lifecycle_status == "active",
            or_(DocumentVersion.valid_from.is_(None), DocumentVersion.valid_from <= target_date),
            or_(DocumentVersion.valid_to.is_(None), DocumentVersion.valid_to >= target_date),
        ).options(joinedload(DocumentChunk.version).joinedload(DocumentVersion.document))
        if topics:
            statement = statement.where(
                Document.topics.any(DocumentTopic.topic.in_(topics))
            )
        return list(self.session.scalars(statement))

    def add_retrieval(self, message_id: str, chunk: DocumentChunk, score: float, rank: int, selected: bool) -> None:
        self.session.add(RetrievalLog(message_id=message_id, chunk_id=chunk.id, score=score, rank=rank, selected=selected))

    def add_citation(self, message_id: str, chunk: DocumentChunk, quote: str, score: float, rank: int) -> None:
        self.session.add(MessageCitation(message_id=message_id, chunk_id=chunk.id, quote=quote, score=score, rank=rank))

    def get_owned_assistant_message(self, message_id: str, user_id: str) -> ChatMessage | None:
        return self.session.scalar(select(ChatMessage).join(Conversation).where(ChatMessage.id == message_id, ChatMessage.role == "assistant", Conversation.user_id == user_id, Conversation.deleted_at.is_(None)))

    def set_feedback(self, message_id: str, user_id: str, rating: str, comment: str) -> MessageFeedback:
        item = self.session.scalar(select(MessageFeedback).where(MessageFeedback.message_id == message_id, MessageFeedback.user_id == user_id))
        if item is None:
            item = MessageFeedback(message_id=message_id, user_id=user_id, rating=rating, comment=comment)
            self.session.add(item)
        else:
            item.rating, item.comment = rating, comment
        self.session.flush()
        return item

    def list_feedback(self, rating: str | None = None) -> list[dict]:
        statement = (
            select(
                MessageFeedback.id,
                MessageFeedback.message_id,
                ChatMessage.conversation_id,
                MessageFeedback.rating,
                MessageFeedback.comment,
                ChatMessage.content.label("answer"),
                MessageFeedback.created_at,
            )
            .join(ChatMessage, ChatMessage.id == MessageFeedback.message_id)
            .order_by(MessageFeedback.created_at.desc())
        )
        if rating:
            statement = statement.where(MessageFeedback.rating == rating)
        return [dict(row._mapping) for row in self.session.execute(statement)]

    def stats(self) -> dict[str, int]:
        def count(statement) -> int:
            return int(self.session.scalar(statement) or 0)

        return {
            "conversations": count(select(func.count(Conversation.id)).where(Conversation.deleted_at.is_(None))),
            "assistant_messages": count(select(func.count(ChatMessage.id)).where(ChatMessage.role == "assistant")),
            "answers_with_citations": count(select(func.count(func.distinct(MessageCitation.message_id)))),
            "expert_referrals": count(select(func.count(ChatMessage.id)).where(ChatMessage.role == "assistant", ChatMessage.needs_expert.is_(True))),
            "helpful_feedback": count(select(func.count(MessageFeedback.id)).where(MessageFeedback.rating == "helpful")),
            "not_helpful_feedback": count(select(func.count(MessageFeedback.id)).where(MessageFeedback.rating == "not_helpful")),
        }

    def touch(self, conversation: Conversation) -> None:
        conversation.updated_at = datetime.now(timezone.utc)
