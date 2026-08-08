from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=2000)
    conversation_id: str | None = None
    as_of_date: date | None = None
    topics: list[str] = Field(default_factory=list, max_length=10)


class CitationResponse(BaseModel):
    chunk_id: str
    article_number: str | None
    score: float


class AskResponse(BaseModel):
    conversation_id: str
    message_id: str
    answer: str
    citations: list[CitationResponse]
    confidence: float
    needs_expert: bool
    disclaimer: str
    clarifying_questions: list[str] = Field(default_factory=list)
    escalation_reasons: list[str] = Field(default_factory=list)
    refusal_reason: str | None = None
    answer_basis: Literal[
        "dataset", "general_knowledge", "casual", "refusal", "out_of_scope", "insufficient_source"
    ]
    source_notice: str | None = None
    agent: str = "tax"
    agent_title: str = "کارشناس مالیاتی"


class ConversationResponse(BaseModel):
    id: str
    title: str
    created_at: datetime
    updated_at: datetime


class MessageCitationResponse(BaseModel):
    chunk_id: str
    quote: str
    score: float
    rank: int


class MessageResponse(BaseModel):
    id: str
    role: str
    content: str
    confidence: float | None
    needs_expert: bool
    disclaimer: str | None
    created_at: datetime
    citations: list[MessageCitationResponse] = Field(default_factory=list)


class RenameConversationRequest(BaseModel):
    title: str = Field(min_length=1, max_length=160)


class FeedbackRequest(BaseModel):
    rating: Literal["helpful", "not_helpful"]
    comment: str = Field(default="", max_length=1000)


class FeedbackAdminResponse(BaseModel):
    id: str
    message_id: str
    conversation_id: str
    rating: str
    comment: str
    answer: str
    created_at: datetime


class AdvisorStatsResponse(BaseModel):
    conversations: int
    assistant_messages: int
    answers_with_citations: int
    expert_referrals: int
    helpful_feedback: int
    not_helpful_feedback: int
