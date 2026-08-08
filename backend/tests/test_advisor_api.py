from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.config import Settings
from app.db.base import Base
from app.main import create_app
from app.models.auth import Role, User
from app.models.portal import LawReferenceRecord
from app.repositories.auth import seed_rbac
from app.services.advisor import AdvisorService, terms
from app.services.documents import DocumentService

PASSWORD = "SecurePassword123"


class GeneralAnswerProvider:
    model_name = None

    def __init__(self):
        self.general_calls = 0

    def generate(self, question, sources):
        return None

    def generate_general(self, question):
        self.general_calls += 1
        return "مالیات مستقیم به‌طور کلی مستقیماً از درآمد یا دارایی دریافت می‌شود."

    def embed_query(self, text):
        return None

    def embed_documents(self, texts):
        return None


@pytest.fixture
def client_with_document(tmp_path):
    settings = Settings(environment="test", database_url=f"sqlite+pysqlite:///{(tmp_path / 'advisor.db').as_posix()}", jwt_secret="test-secret-that-is-at-least-32-characters-long", local_storage_path=str(tmp_path / "storage"), minimum_extracted_chars=10, log_level="CRITICAL")
    app = create_app(settings)
    with TestClient(app) as client:
        Base.metadata.create_all(app.state.database.engine)
        with app.state.database.session() as session:
            seed_rbac(session)
        yield app, client


def auth(client, email):
    client.post("/auth/register", json={"email": email, "password": PASSWORD, "full_name": "کاربر آزمون"})
    token = client.post("/auth/login", json={"email": email, "password": PASSWORD}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def prepare_approved_document(app, client, headers):
    with app.state.database.session() as session:
        user = session.scalar(select(User).where(User.email == "user@example.com"))
        manager = session.scalar(select(Role).where(Role.name == "content_manager"))
        user.roles = [manager]
        session.commit()
    headers = auth_login(client, "user@example.com")
    document = client.post("/api/v1/documents", headers=headers, json={"title": "قانون مالیات بر ارزش افزوده", "document_type": "law", "issuing_authority": "سازمان امور مالیاتی", "source_url": "https://example.test/law", "topics": ["ارزش افزوده"]}).json()
    text = ("ماده ۱- مؤدی باید اظهارنامه مالیات بر ارزش افزوده را در مهلت قانونی ثبت کند. " * 20).encode()
    version = client.post(f"/api/v1/documents/{document['id']}/versions", headers=headers, files={"file": ("law.txt", text, "text/plain")}).json()
    with patch("app.api.routes.documents.process_document_job.delay"):
        job = client.post(f"/api/v1/documents/versions/{version['id']}/process", headers=headers).json()
    with app.state.database.session() as session:
        DocumentService(session, app.state.settings, app.state.storage).process_job(job["id"])
    client.post(f"/api/v1/documents/versions/{version['id']}/review", headers=headers, json={"decision": "approved", "note": "تأیید"})
    return headers


def auth_login(client, email):
    token = client.post("/auth/login", json={"email": email, "password": PASSWORD}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_grounded_answer_history_and_feedback(client_with_document):
    app, client = client_with_document
    headers = auth(client, "user@example.com")
    headers = prepare_approved_document(app, client, headers)
    response = client.post("/api/v1/chat/query", headers=headers, json={"question": "مهلت اظهارنامه مالیات بر ارزش افزوده چیست؟"})
    assert response.status_code == 200, response.text
    answer = response.json()
    assert answer["citations"]
    assert answer["answer_basis"] == "dataset"
    assert answer["citations"][0]["article_number"]
    assert "document_title" not in answer["citations"][0]
    assert "source_url" not in answer["citations"][0]
    conversation_id = answer["conversation_id"]
    messages = client.get(f"/api/v1/conversations/{conversation_id}/messages", headers=headers)
    assert [item["role"] for item in messages.json()] == ["user", "assistant"]
    feedback = client.post(f"/api/v1/messages/{answer['message_id']}/feedback", headers=headers, json={"rating": "helpful", "comment": "مفید بود"})
    assert feedback.status_code == 204


def test_unknown_question_is_limited_and_conversations_are_private(client_with_document):
    _app, client = client_with_document
    first = auth(client, "first@example.com")
    answer = client.post("/api/v1/chat/query", headers=first, json={"question": "حکم موضوع کاملاً ناشناخته چیست؟"}).json()
    assert answer["citations"] == []
    assert answer["confidence"] == 0
    second = auth(client, "second@example.com")
    hidden = client.get(f"/api/v1/conversations/{answer['conversation_id']}/messages", headers=second)
    assert hidden.status_code == 404


def test_curated_question_without_explicit_tax_word_is_answered(client_with_document):
    app, client = client_with_document
    with app.state.database.session() as session:
        session.add(
            LawReferenceRecord(
                id="qa-bank-deposit",
                source_id="curated-tax-qa",
                law_name="راهنمای کاربردی مالیاتی",
                chapter="پرسش‌های کاربردی",
                article_number="",
                official_text=(
                    "پرسش: آیا هر واریزی بانکی درآمد است؟\n"
                    "پاسخ: خیر؛ واریزی بانکی بدون بررسی منشأ آن لزوماً درآمد نیست."
                ),
                source_url="",
                keywords="آیا هر واریزی بانکی درآمد است؟",
                source_info="پرسش آزمون",
                is_active=True,
            )
        )
        session.commit()
    headers = auth(client, "curated@example.com")
    response = client.post(
        "/api/v1/chat/query",
        headers=headers,
        json={"question": "آیا هر واریزی به حساب بانکی درآمد محسوب می‌شود؟"},
    )
    assert response.status_code == 200
    answer = response.json()
    assert answer["answer_basis"] == "dataset"
    assert answer["confidence"] <= 1
    assert "لزوماً درآمد نیست" in answer["answer"]


def test_complex_question_uses_multi_topic_fallback(client_with_document):
    _app, client = client_with_document
    headers = auth(client, "complex@example.com")
    response = client.post(
        "/api/v1/chat/query",
        headers=headers,
        json={
            "question": (
                "اگر اظهارنامه دیر ارسال شود و صورتحساب ناقص باشد، "
                "جریمه و امکان بخشودگی چگونه بررسی می‌شود؟"
            )
        },
    )
    assert response.status_code == 200
    answer = response.json()["answer"]
    assert "ارسال دیرهنگام اظهارنامه" in answer
    assert "صورتحساب" in answer
    assert "بخشودگی" in answer


def test_general_tax_types_has_clear_fallback(client_with_document):
    _app, client = client_with_document
    headers = auth(client, "types@example.com")
    response = client.post(
        "/api/v1/chat/query",
        headers=headers,
        json={"question": "مالیات چند نوع است؟"},
    )
    assert response.status_code == 200
    payload = response.json()
    answer = payload["answer"]
    assert payload["answer_basis"] == "general_knowledge"
    assert "مالیات مستقیم" in answer
    assert "مالیات غیرمستقیم" in answer


def test_bank_deposit_evidence_question_returns_document_checklist(
    client_with_document,
):
    _app, client = client_with_document
    headers = auth(client, "evidence@example.com")
    response = client.post(
        "/api/v1/chat/query",
        headers=headers,
        json={
            "question": (
                "اگر واریزی حساب تجاری مربوط به قرض، انتقال بین حساب‌های شخصی و "
                "برگشت وجه مشتری باشد، برای اثبات درآمد نبودن چه مدارکی لازم است؟"
            )
        },
    )
    assert response.status_code == 200
    answer = response.json()["answer"]
    assert "رسید انتقال" in answer
    assert "قرارداد یا رسید قرض" in answer
    assert "رسید بازپرداخت" in answer


def test_common_typo_for_tax_penalties_is_understood(client_with_document):
    _app, client = client_with_document
    headers = auth(client, "short-question@example.com")
    response = client.post(
        "/api/v1/chat/query",
        headers=headers,
        json={"question": "حریم مالیات"},
    )
    assert response.status_code == 200
    answer = response.json()["answer"]
    assert "جرایم مالیاتی" in answer
    assert "بخشودگی" in answer
    assert "پرداخت قانونی اشخاص" not in answer


def test_known_short_tax_concept_uses_general_fallback(client_with_document):
    _app, client = client_with_document
    headers = auth(client, "economic-code@example.com")
    response = client.post(
        "/api/v1/chat/query",
        headers=headers,
        json={"question": "کد اقتصادی"},
    )
    assert response.status_code == 200
    assert "شناسه فعالیت مالیاتی" in response.json()["answer"]


def test_comparison_question_is_not_misclassified_as_general():
    question = "تفاوت شخص حقیقی و شخص حقوقی در مالیات چیست؟"
    assert AdvisorService._is_broad_general_question(question) is False
    assert "چیست" not in terms(question)


def test_generated_answer_rejects_unsupported_precise_claim():
    assert AdvisorService._answer_is_usable(
        "مهلت ارسال اظهارنامه ۳۰ روز است.",
        ["ارسال اظهارنامه باید در مهلت قانونی انجام شود."],
        "مهلت ارسال اظهارنامه چقدر است؟",
    ) is False


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        ("تفاوت شخص حقیقی و شخص حقوقی در مالیات چیست؟", "شرکت یا مؤسسه ثبت‌شده"),
        ("معافیت مالیاتی شرکت دانش‌بنیان چگونه بررسی می‌شود؟", "همه درآمد شرکت را معاف نمی‌کند"),
        ("مالیات دستگاه پوز چگونه محاسبه می‌شود؟", "مالیات جداگانه ندارد"),
    ],
)
def test_common_questions_use_fast_relevant_answers(question, expected):
    assert expected in (AdvisorService._concept_answer(question) or "")


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        ("اظهارنامه", "گزارش رسمی مؤدی"),
        ("مالیات شرکت‌ها", "درآمد مشمول مالیات"),
        ("مالیات مستقیم", "درآمد یا دارایی"),
        ("مالیات غیرمستقیم", "مصرف‌کننده"),
        ("حریم مالیاتی", "جرایم مالیاتی"),
    ],
)
def test_core_short_concepts_have_stable_answers(question, expected):
    assert expected in (AdvisorService._concept_answer(question) or "")


def test_rule_engine_refuses_evasion_and_requests_missing_deadline_context(client_with_document):
    _app, client = client_with_document
    headers = auth(client, "rules@example.com")
    refused = client.post(
        "/api/v1/chat/query",
        headers=headers,
        json={"question": "چطور برای فرار مالیاتی فاکتور صوری ثبت کنم؟"},
    )
    assert refused.status_code == 200
    assert refused.json()["refusal_reason"]
    assert refused.json()["citations"] == []
    deadline = client.post(
        "/api/v1/chat/query",
        headers=headers,
        json={"question": "مهلت اعتراض به ابلاغ چقدر است؟"},
    ).json()
    assert deadline["needs_expert"] is True
    assert deadline["clarifying_questions"]
    assert "official_notice" in deadline["escalation_reasons"]


def test_casual_chat_and_limited_general_knowledge_fallback(client_with_document):
    app, client = client_with_document
    headers = auth(client, "general@example.com")
    greeting = client.post(
        "/api/v1/chat/query", headers=headers, json={"question": "سلام خوبی؟"}
    ).json()
    assert greeting["answer_basis"] == "casual"
    assert "سلام" in greeting["answer"]
    assert greeting["citations"] == []

    provider = GeneralAnswerProvider()
    app.state.ai_provider = provider
    general = client.post(
        "/api/v1/chat/query",
        headers=headers,
        json={"question": "مالیات مستقیم به زبان ساده چیست؟"},
    ).json()
    assert general["answer_basis"] == "general_knowledge"
    assert general["confidence"] == 0.2
    assert general["source_notice"]
    assert provider.general_calls == 1

    sensitive = client.post(
        "/api/v1/chat/query",
        headers=headers,
        json={"question": "نرخ مالیات مستقیم امسال چند درصد است؟"},
    ).json()
    assert sensitive["answer_basis"] == "general_knowledge"
    assert sensitive["source_notice"]
    assert provider.general_calls == 2
