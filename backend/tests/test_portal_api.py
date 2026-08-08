import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.config import Settings
from app.db.base import Base
from app.main import create_app
from app.models.auth import Role, User
from app.models.portal import DiscountCode, LawReferenceRecord, Payment, SubscriptionPlan, UserSubscription, WalletAccount
from app.repositories.auth import seed_rbac

PASSWORD = "SecurePassword123"


@pytest.fixture
def portal_client(tmp_path):
    settings = Settings(
        environment="test",
        database_url=f"sqlite+pysqlite:///{(tmp_path / 'portal.db').as_posix()}",
        jwt_secret="test-secret-that-is-at-least-32-characters-long",
        local_storage_path=str(tmp_path / "storage"),
        log_level="CRITICAL",
    )
    app = create_app(settings)
    with TestClient(app) as client:
        Base.metadata.create_all(app.state.database.engine)
        with app.state.database.session() as session:
            seed_rbac(session)
            session.add_all([
                SubscriptionPlan(id="normal", code="normal", title="عادی", price=0, duration_days=3650, benefits=["۱۰ پرسش"], sort_order=1),
                SubscriptionPlan(id="plus", code="plus", title="پلاس", price=349000, duration_days=30, benefits=["۱۰۰ پرسش"], sort_order=2),
                DiscountCode(id="welcome", code="WELCOME20", percent=20, max_uses=10),
                LawReferenceRecord(id="LAW-TEST-A2", source_id="LAW-TEST", law_name="قانون مالیات آزمایشی", chapter="فصل اول", article_number="2", official_text="متن آزمایشی ماده دوم درباره مالیات است.", source_url="https://example.com/law", keywords="مالیات، ماده دو"),
            ])
            session.commit()
        yield app, client


def register(client: TestClient, email: str) -> dict[str, str]:
    response = client.post("/auth/register", json={"email": email, "password": PASSWORD, "full_name": "کاربر آزمون"})
    assert response.status_code == 201, response.text
    token = client.post("/auth/login", json={"email": email, "password": PASSWORD}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_customer_profile_checkout_documents_and_tickets(portal_client):
    app, client = portal_client
    headers = register(client, "portal@example.com")

    profile = client.patch("/api/v1/portal/profile", headers=headers, json={"phone": "09120000000", "province": "تهران", "city": "تهران", "company_name": "نمونه", "job_title": "مدیر", "taxpayer_type": "company", "bio": "پروفایل آزمایشی"})
    assert profile.status_code == 200, profile.text
    assert profile.json()["profile_score"] == 85
    assert profile.json()["reward_points"] == 500
    repeated_profile = client.patch("/api/v1/portal/profile", headers=headers, json={"phone": "09120000000", "province": "تهران", "city": "تهران", "company_name": "نمونه", "job_title": "مدیر", "taxpayer_type": "company", "bio": "پروفایل آزمایشی"})
    assert repeated_profile.json()["reward_points"] == 500

    wallet_otp = client.post("/api/v1/portal/wallet/otp", headers=headers, json={"transaction_type": "charge", "amount": 250000})
    assert wallet_otp.status_code == 201, wallet_otp.text
    wallet_confirm = client.post("/api/v1/portal/wallet/confirm", headers=headers, json={"transaction_id": wallet_otp.json()["transaction_id"], "code": wallet_otp.json()["test_otp"]})
    assert wallet_confirm.status_code == 200, wallet_confirm.text
    assert wallet_confirm.json()["balance"] == 250000
    withdraw_otp = client.post("/api/v1/portal/wallet/otp", headers=headers, json={"transaction_type": "withdraw", "amount": 50000})
    withdraw_confirm = client.post("/api/v1/portal/wallet/confirm", headers=headers, json={"transaction_id": withdraw_otp.json()["transaction_id"], "code": withdraw_otp.json()["test_otp"]})
    assert withdraw_confirm.json() == {"balance": 200000, "status": "pending"}

    card = client.post("/api/v1/portal/payment-methods", headers=headers, json={"card_number": "4242424242424242", "cardholder_name": "کاربر آزمون"})
    assert card.status_code == 201, card.text
    assert card.json()["last_four"] == "4242"

    otp = client.post("/api/v1/portal/payment-otp", headers=headers, json={"plan_code": "plus", "package": "gold", "payment_method_id": card.json()["id"], "discount_code": "WELCOME20"})
    assert otp.status_code == 201, otp.text
    assert len(otp.json()["test_otp"]) == 6
    checkout = client.post("/api/v1/portal/checkout", headers=headers, json={"plan_code": "plus", "package": "gold", "payment_method_id": card.json()["id"], "discount_code": "WELCOME20", "otp_request_id": otp.json()["request_id"], "otp_code": otp.json()["test_otp"]})
    assert checkout.status_code == 201, checkout.text
    assert checkout.json()["amount"] == 488800
    with app.state.database.session() as session:
        assert session.scalar(select(UserSubscription)).package_code == "gold"
    assert client.get("/users/me", headers=headers).json()["account_tier"] == "plus"

    document = client.post("/api/v1/portal/documents", headers=headers, data={"title": "اظهارنامه"}, files={"file": ("tax.txt", "متن سند".encode(), "text/plain")})
    assert document.status_code == 201, document.text
    ticket = client.post("/api/v1/portal/tickets", headers=headers, json={"subject": "پیگیری پرداخت", "category": "billing", "message": "لطفاً پرداخت من را بررسی کنید."})
    assert ticket.status_code == 201, ticket.text
    assert ticket.json()["messages"][0]["is_staff"] is False
    blocked_reply = client.post(f"/api/v1/portal/tickets/{ticket.json()['id']}/messages", headers=headers, json={"message": "پیام دوم پیش از پاسخ مدیر"})
    assert blocked_reply.status_code == 409

    reminder = client.post("/api/v1/tools/reminders", headers=headers, json={"title": "مهلت اظهارنامه", "description": "یادآوری آزمون", "due_date": "2027-01-01", "category": "declaration", "notify_days_before": 7})
    assert reminder.status_code == 201, reminder.text
    assert client.get("/api/v1/tools/calendar", headers=headers).json()["reminders"][0]["title"] == "مهلت اظهارنامه"
    calculation = client.post("/api/v1/tools/calculator", headers=headers, json={"calculation_type": "vat", "amount": 1000000, "rate": 10, "months": 1})
    assert calculation.json()["result"] == 100000
    letter = client.post("/api/v1/tools/letters", headers=headers, json={"letter_type": "objection", "recipient": "اداره امور مالیاتی", "subject": "اعتراض", "taxpayer_name": "شرکت آزمون", "case_number": "123", "facts": "شرح کامل رویداد مالیاتی و مستندات پرونده", "request_text": "درخواست رسیدگی مجدد دارم"})
    assert letter.status_code == 200
    assert "شرکت آزمون" in letter.json()["content"]
    assert client.get("/api/v1/tools/security/2fa/setup", headers=headers).status_code == 200
    search = client.get("/api/v1/legal/search?q=ماده 2", headers=headers)
    assert search.status_code == 200
    assert search.json()[0]["article_number"] == "2"


def test_system_admin_can_manage_commerce_and_customer_data(portal_client):
    app, client = portal_client
    headers = register(client, "admin-portal@example.com")
    with app.state.database.session() as session:
        account = session.scalar(select(User).where(User.email == "admin-portal@example.com"))
        account.roles = [session.scalar(select(Role).where(Role.name == "system_admin"))]
        session.commit()
    token = client.post("/auth/login", json={"email": "admin-portal@example.com", "password": PASSWORD}).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    assert client.get("/api/v1/admin/summary", headers=headers).status_code == 200
    assert client.get("/api/v1/admin/profiles", headers=headers).status_code == 200
    assert client.get("/api/v1/admin/analytics", headers=headers).status_code == 200
    plans = client.get("/api/v1/admin/plans", headers=headers)
    assert plans.status_code == 200
    plus = next(item for item in plans.json() if item["code"] == "plus")
    updated_plan = client.patch(
        f"/api/v1/admin/plans/{plus['id']}",
        headers=headers,
        json={"price": 159000, "duration_days": 45, "is_active": True},
    )
    assert updated_plan.status_code == 200
    assert updated_plan.json()["price"] == 159000
    assert updated_plan.json()["duration_days"] == 45
    broadcast = client.post("/api/v1/admin/notifications/broadcast", headers=headers, json={"title": "اطلاعیه آزمون", "message": "این یک پیام مدیریتی آزمایشی است.", "audience": "all"})
    assert broadcast.status_code == 201
    assert broadcast.json()["recipients"] >= 1
    assert client.get("/api/v1/admin/audit-logs", headers=headers).status_code == 200
    with app.state.database.session() as session:
        account = session.scalar(select(User).where(User.email == "admin-portal@example.com"))
        plan = session.scalar(select(SubscriptionPlan).where(SubscriptionPlan.code == "plus"))
        payment = Payment(user_id=account.id, plan_id=plan.id, amount=159000, discount_amount=0, status="paid", gateway_reference="REFUND-TEST", paid_at=datetime.now(timezone.utc))
        session.add(payment)
        session.commit()
        payment_id = payment.id
        wallet = session.get(WalletAccount, account.id)
        previous_balance = wallet.balance if wallet else 0
    refunded = client.post(f"/api/v1/admin/payments/{payment_id}/refund", headers=headers, json={"reason": "بازپرداخت آزمایشی معتبر"})
    assert refunded.status_code == 200
    repeated_refund = client.post(f"/api/v1/admin/payments/{payment_id}/refund", headers=headers, json={"reason": "تلاش مجدد بازپرداخت"})
    assert repeated_refund.status_code == 409
    with app.state.database.session() as session:
        assert session.get(WalletAccount, account.id).balance == previous_balance + 159000
    created = client.post("/api/v1/admin/discounts", headers=headers, json={"code": "TEST25", "percent": 25, "max_uses": 5})
    assert created.status_code == 201, created.text
    toggled = client.patch(f"/api/v1/admin/discounts/{created.json()['id']}", headers=headers, json={"is_active": False})
    assert toggled.status_code == 200


def test_wallet_daily_withdrawal_limit_is_enforced_on_backend(portal_client):
    _app, client = portal_client
    headers = register(client, "wallet-limit@example.com")
    charge = client.post(
        "/api/v1/portal/wallet/deposits/otp",
        headers=headers,
        json={"amount": 20_000_000},
    )
    assert charge.status_code == 201, charge.text
    confirmed_charge = client.post(
        "/api/v1/portal/wallet/deposits/confirm",
        headers=headers,
        json={
            "transaction_id": charge.json()["transaction_id"],
            "code": charge.json()["test_otp"],
        },
    )
    assert confirmed_charge.json()["balance"] == 20_000_000

    withdrawal = client.post(
        "/api/v1/portal/wallet/withdrawals/otp",
        headers=headers,
        json={"amount": 15_000_000},
    )
    assert withdrawal.status_code == 201, withdrawal.text
    confirmed_withdrawal = client.post(
        "/api/v1/portal/wallet/withdrawals/confirm",
        headers=headers,
        json={
            "transaction_id": withdrawal.json()["transaction_id"],
            "code": withdrawal.json()["test_otp"],
        },
    )
    assert confirmed_withdrawal.json() == {"balance": 5_000_000, "status": "pending"}

    exceeded = client.post(
        "/api/v1/portal/wallet/withdrawals/otp",
        headers=headers,
        json={"amount": 10_000},
    )
    assert exceeded.status_code == 422
    assert "15,000,000" in exceeded.json()["detail"]

    wallet = client.get("/api/v1/portal/wallet", headers=headers).json()
    assert wallet["daily_withdrawal_limit"] == 15_000_000
    assert wallet["withdrawn_today"] == 15_000_000
    assert wallet["withdrawal_remaining"] == 0


def test_system_admin_can_version_site_configuration(portal_client):
    app, client = portal_client
    headers = register(client, "system-settings@example.com")
    with app.state.database.session() as session:
        account = session.scalar(select(User).where(User.email == "system-settings@example.com"))
        account.roles = [session.scalar(select(Role).where(Role.name == "system_admin"))]
        session.commit()
    headers = register_login(client, "system-settings@example.com")

    current = client.get("/api/v1/site/manage", headers=headers)
    assert current.status_code == 200, current.text
    configuration = current.json()["draft"]
    configuration["theme"]["primary_color"] = "#0284c7"
    saved = client.patch("/api/v1/site/manage/draft", headers=headers, json={"configuration": configuration})
    assert saved.status_code == 200, saved.text
    published = client.post("/api/v1/site/manage/publish", headers=headers, json={"note": "test publish"})
    assert published.status_code == 200, published.text
    assert client.get("/api/v1/site/config").json()["configuration"]["theme"]["primary_color"] == "#0284c7"


def register_login(client: TestClient, email: str) -> dict[str, str]:
    token = client.post("/auth/login", json={"email": email, "password": PASSWORD}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
