from datetime import datetime, timezone
import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.dependencies import get_advisor_service, get_current_user, get_session, require_permissions
from app.models.advisor import ChatMessage, Conversation
from app.models.auth import User
from app.schemas.advisor import AdvisorStatsResponse, AskRequest, AskResponse, ConversationResponse, FeedbackAdminResponse, FeedbackRequest, MessageResponse, RenameConversationRequest
from app.services.advisor import AdvisorService, ConversationNotFoundError, MessageNotFoundError
from app.services.site import feature_enabled
from app.services.plans import scaled_limits

router = APIRouter(prefix="/api/v1", tags=["advisor"])

CHAT_LIMITS = {"normal": 10, "plus": 100, "pro": 1000}


def enforce_chat_limit(session: Session, user: User) -> None:
    month_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    used = session.scalar(
        select(func.count(ChatMessage.id))
        .join(Conversation, Conversation.id == ChatMessage.conversation_id)
        .where(Conversation.user_id == user.id, ChatMessage.role == "user", ChatMessage.created_at >= month_start)
    ) or 0
    limit = scaled_limits(session, user, {tier: {"questions": value} for tier, value in CHAT_LIMITS.items()})["questions"]
    if used >= limit:
        raise HTTPException(status_code=429, detail=f"Monthly question limit ({limit}) reached")


@router.post("/chat/query", response_model=AskResponse)
def ask(payload: AskRequest, user: Annotated[User, Depends(get_current_user)], service: Annotated[AdvisorService, Depends(get_advisor_service)], session: Annotated[Session, Depends(get_session)]) -> AskResponse:
    if not feature_enabled(session, "chatbot_enabled"):
        raise HTTPException(status_code=503, detail="Chatbot is disabled")
    month_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    used = session.scalar(
        select(func.count(ChatMessage.id))
        .join(Conversation, Conversation.id == ChatMessage.conversation_id)
        .where(Conversation.user_id == user.id, ChatMessage.role == "user", ChatMessage.created_at >= month_start)
    ) or 0
    limit = scaled_limits(
        session,
        user,
        {tier: {"questions": value} for tier, value in CHAT_LIMITS.items()},
    )["questions"]
    if used >= limit:
        raise HTTPException(status_code=429, detail=f"سقف {limit} پرسش ماهانه پلن شما تکمیل شده است؛ برای ادامه پلن را ارتقا دهید.")
    try:
        return service.ask(
            payload.question,
            payload.conversation_id,
            user,
            as_of_date=payload.as_of_date,
            topics=payload.topics,
        )
    except ConversationNotFoundError:
        raise HTTPException(status_code=404, detail="Conversation not found") from None


@router.post("/chat/stream")
def ask_stream(payload: AskRequest, user: Annotated[User, Depends(get_current_user)], service: Annotated[AdvisorService, Depends(get_advisor_service)], session: Annotated[Session, Depends(get_session)]) -> StreamingResponse:
    if not feature_enabled(session, "chatbot_enabled"):
        raise HTTPException(status_code=503, detail="Chatbot is disabled")
    enforce_chat_limit(session, user)

    def events():
        yield json.dumps({"type": "status", "message": "در حال بررسی پرسش"}, ensure_ascii=False) + "\n"
        try:
            result = service.ask(payload.question, payload.conversation_id, user, as_of_date=payload.as_of_date, topics=payload.topics)
            yield json.dumps({"type": "result", "data": result.model_dump(mode="json")}, ensure_ascii=False) + "\n"
        except ConversationNotFoundError:
            yield json.dumps({"type": "error", "message": "گفت‌وگو پیدا نشد"}, ensure_ascii=False) + "\n"

    return StreamingResponse(events(), media_type="application/x-ndjson", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@router.get("/conversations", response_model=list[ConversationResponse])
def conversations(user: Annotated[User, Depends(get_current_user)], service: Annotated[AdvisorService, Depends(get_advisor_service)]):
    return service.list_conversations(user)


@router.get("/conversations/{conversation_id}/messages", response_model=list[MessageResponse])
def messages(conversation_id: str, user: Annotated[User, Depends(get_current_user)], service: Annotated[AdvisorService, Depends(get_advisor_service)]):
    try:
        return service.get_messages(conversation_id, user)
    except ConversationNotFoundError:
        raise HTTPException(status_code=404, detail="Conversation not found") from None


@router.patch("/conversations/{conversation_id}", response_model=ConversationResponse)
def rename(conversation_id: str, payload: RenameConversationRequest, user: Annotated[User, Depends(get_current_user)], service: Annotated[AdvisorService, Depends(get_advisor_service)]):
    try:
        return service.rename(conversation_id, payload.title, user)
    except ConversationNotFoundError:
        raise HTTPException(status_code=404, detail="Conversation not found") from None


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete(conversation_id: str, user: Annotated[User, Depends(get_current_user)], service: Annotated[AdvisorService, Depends(get_advisor_service)]) -> Response:
    try:
        service.delete(conversation_id, user)
    except ConversationNotFoundError:
        raise HTTPException(status_code=404, detail="Conversation not found") from None
    return Response(status_code=204)


@router.post("/messages/{message_id}/feedback", status_code=status.HTTP_204_NO_CONTENT)
def feedback(message_id: str, payload: FeedbackRequest, user: Annotated[User, Depends(get_current_user)], service: Annotated[AdvisorService, Depends(get_advisor_service)]) -> Response:
    try:
        service.feedback(message_id, payload.rating, payload.comment, user)
    except MessageNotFoundError:
        raise HTTPException(status_code=404, detail="Message not found") from None
    return Response(status_code=204)


@router.get("/admin/feedback", response_model=list[FeedbackAdminResponse])
def admin_feedback(user: Annotated[User, Depends(require_permissions("feedback:read"))], service: Annotated[AdvisorService, Depends(get_advisor_service)], rating: str | None = None):
    del user
    if rating not in {None, "helpful", "not_helpful"}:
        raise HTTPException(status_code=422, detail="Invalid feedback rating")
    return service.list_feedback(rating)


@router.get("/admin/advisor-stats", response_model=AdvisorStatsResponse)
def advisor_stats(user: Annotated[User, Depends(require_permissions("feedback:read"))], service: Annotated[AdvisorService, Depends(get_advisor_service)]):
    del user
    return service.stats()
