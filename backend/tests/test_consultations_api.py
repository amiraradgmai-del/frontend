import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.config import Settings
from app.db.base import Base
from app.main import create_app
from app.models.auth import Role, User
from app.models.consultations import ConsultantProfile, ConsultantVerificationRequest
from app.repositories.auth import seed_rbac

PASSWORD = "SecurePassword123"


@pytest.fixture
def consultation_client(tmp_path):
    settings = Settings(
        environment="test",
        database_url=f"sqlite+pysqlite:///{(tmp_path / 'consultations.db').as_posix()}",
        jwt_secret="test-secret-that-is-at-least-32-characters-long",
        local_storage_path=str(tmp_path / "storage"),
        log_level="CRITICAL",
    )
    app = create_app(settings)
    with TestClient(app) as client:
        Base.metadata.create_all(app.state.database.engine)
        with app.state.database.session() as session:
            seed_rbac(session)
        yield app, client


def register(client, email):
    client.post(
        "/auth/register",
        json={"email": email, "password": PASSWORD, "full_name": "کاربر آزمون"},
    )
    token = client.post(
        "/auth/login", json={"email": email, "password": PASSWORD}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def login(client, email):
    token = client.post(
        "/auth/login", json={"email": email, "password": PASSWORD}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_consultation_owner_and_manager_workflow(consultation_client):
    app, client = consultation_client
    owner_headers = register(client, "owner@example.com")
    manager_headers = register(client, "expert@example.com")
    with app.state.database.session() as session:
        manager = session.scalar(select(User).where(User.email == "expert@example.com"))
        role = session.scalar(select(Role).where(Role.name == "admin"))
        manager.roles = [role]
        manager_id = manager.id
        session.commit()
    manager_headers = login(client, "expert@example.com")
    created = client.post(
        "/api/v1/consultations",
        headers=owner_headers,
        json={
            "subject": "بررسی مهلت اعتراض",
            "description": "برای یک ابلاغ مالیاتی نیاز به بررسی تخصصی دارم.",
        },
    )
    assert created.status_code == 201, created.text
    consultation = created.json()
    assert consultation["status"] == "submitted"
    queue = client.get(
        "/api/v1/consultations/manage/all", headers=manager_headers
    )
    assert queue.status_code == 200
    updated = client.patch(
        f"/api/v1/consultations/manage/{consultation['id']}",
        headers=manager_headers,
        json={
            "status": "resolved",
            "priority": "high",
            "assigned_to": manager_id,
            "internal_note": "یادداشت داخلی",
            "resolution": "نتیجه بررسی تخصصی ثبت شد.",
            "note": "پرونده بسته شد",
        },
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["internal_note"] == "یادداشت داخلی"
    owner_view = client.get(
        f"/api/v1/consultations/{consultation['id']}", headers=owner_headers
    )
    assert owner_view.status_code == 200
    assert owner_view.json()["resolution"]
    assert "internal_note" not in owner_view.json()


def test_user_cannot_access_another_users_consultation(consultation_client):
    _app, client = consultation_client
    first = register(client, "first-consult@example.com")
    second = register(client, "second-consult@example.com")
    item = client.post(
        "/api/v1/consultations",
        headers=first,
        json={"subject": "موضوع مالیاتی", "description": "شرح کافی برای درخواست مشاور مالیاتی"},
    ).json()
    response = client.get(f"/api/v1/consultations/{item['id']}", headers=second)
    assert response.status_code == 404


def test_consultant_only_sees_assigned_cases(consultation_client):
    app, client = consultation_client
    owner = register(client, "assigned-owner@example.com")
    consultant_headers = register(client, "assigned-consultant@example.com")
    support_headers = register(client, "assigned-support@example.com")
    with app.state.database.session() as session:
        consultant = session.scalar(select(User).where(User.email == "assigned-consultant@example.com"))
        consultant.roles = [session.scalar(select(Role).where(Role.name == "consultant"))]
        support = session.scalar(select(User).where(User.email == "assigned-support@example.com"))
        support.roles = [session.scalar(select(Role).where(Role.name == "support_admin"))]
        consultant_id = consultant.id
        session.commit()
    consultant_headers = login(client, "assigned-consultant@example.com")
    support_headers = login(client, "assigned-support@example.com")
    first = client.post("/api/v1/consultations", headers=owner, json={"subject": "پرونده اول", "description": "شرح کامل پرونده مالیاتی اول برای بررسی مشاور"}).json()
    client.post("/api/v1/consultations", headers=owner, json={"subject": "پرونده دوم", "description": "شرح کامل پرونده مالیاتی دوم برای بررسی مشاور"})
    assigned = client.patch(f"/api/v1/consultations/manage/{first['id']}", headers=support_headers, json={"status": "in_review", "priority": "normal", "assigned_to": consultant_id, "internal_note": "", "resolution": "", "note": "ارجاع"})
    assert assigned.status_code == 200, assigned.text
    queue = client.get("/api/v1/consultations/assigned/me", headers=consultant_headers)
    assert queue.status_code == 200
    assert [item["id"] for item in queue.json()] == [first["id"]]


def test_finance_expert_cannot_manage_unassigned_cases(consultation_client):
    app, client = consultation_client
    owner_headers = register(client, "restricted-owner@example.com")
    expert_headers = register(client, "restricted-expert@example.com")
    with app.state.database.session() as session:
        expert = session.scalar(
            select(User).where(User.email == "restricted-expert@example.com")
        )
        expert.roles = [
            session.scalar(select(Role).where(Role.name == "tax_expert"))
        ]
        session.commit()
    expert_headers = login(client, "restricted-expert@example.com")
    consultation = client.post(
        "/api/v1/consultations",
        headers=owner_headers,
        json={
            "subject": "پرونده محرمانه",
            "description": "شرح پرونده‌ای که هنوز به این کارشناس ارجاع نشده است.",
        },
    ).json()

    assert (
        client.get(
            "/api/v1/consultations/manage/all", headers=expert_headers
        ).status_code
        == 403
    )
    assert (
        client.patch(
            f"/api/v1/consultations/manage/{consultation['id']}",
            headers=expert_headers,
            json={
                "status": "in_review",
                "priority": "normal",
                "assigned_to": None,
                "internal_note": "",
                "resolution": "",
                "note": "",
            },
        ).status_code
        == 403
    )
    assigned = client.get(
        "/api/v1/consultations/assigned/me", headers=expert_headers
    )
    assert assigned.status_code == 200
    assert assigned.json() == []


def test_consultant_verification_approval_creates_profile_and_role(
    consultation_client,
):
    app, client = consultation_client
    applicant_headers = register(client, "verification-applicant@example.com")
    manager_headers = register(client, "verification-manager@example.com")
    with app.state.database.session() as session:
        manager = session.scalar(
            select(User).where(User.email == "verification-manager@example.com")
        )
        manager.roles = [
            session.scalar(select(Role).where(Role.name == "system_admin"))
        ]
        session.commit()
    manager_headers = login(client, "verification-manager@example.com")

    document_ids = []
    for document_type, title in (("national_card", "کارت ملی"), ("education_certificate", "مدرک تحصیلی"), ("resume", "رزومه")):
        uploaded = client.post(
            "/api/v1/portal/documents",
            headers=applicant_headers,
            data={"title": title, "document_type": document_type, "description": "مدرک آزمون احراز صلاحیت", "purpose": "consultant_verification", "intended_reviewer": "consultant_management"},
            files={"file": (f"{document_type}.txt", b"verified document", "text/plain")},
        )
        assert uploaded.status_code == 201, uploaded.text
        document_ids.append(uploaded.json()["id"])

    created = client.post(
        "/api/v1/consultations/verification",
        headers=applicant_headers,
        json={
            "consultant_type": "independent",
            "professional_title": "مشاور ارشد مالیاتی",
            "national_id": "0012345678",
            "license_number": "TAX-1405-1",
            "specialties": ["مالیات مستقیم", "ارزش افزوده"],
            "years_experience": 8,
            "qualifications": "دارای سابقه حرفه‌ای در رسیدگی و دادرسی مالیاتی.",
            "document_ids": document_ids,
            "applicant_note": "درخواست بررسی صلاحیت",
        },
    )
    assert created.status_code == 201, created.text
    request_id = created.json()["id"]
    assert created.json()["status"] == "pending"

    approved = client.patch(
        f"/api/v1/consultations/manage/verifications/{request_id}",
        headers=manager_headers,
        json={"status": "approved", "admin_note": "مدارک بررسی و تأیید شد."},
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "approved"

    with app.state.database.session() as session:
        request = session.get(ConsultantVerificationRequest, request_id)
        applicant = session.scalar(
            select(User).where(User.email == "verification-applicant@example.com")
        )
        profile = session.get(ConsultantProfile, applicant.id)
        assert request is not None and request.reviewed_at is not None
        assert {role.name for role in applicant.roles} == {"tax_expert"}
        assert profile is not None
        assert profile.is_verified is True
        assert profile.specialties == ["ارزش افزوده", "مالیات مستقیم"]


def test_verification_rejection_requires_admin_explanation(consultation_client):
    app, client = consultation_client
    applicant_headers = register(client, "correction-applicant@example.com")
    manager_headers = register(client, "correction-manager@example.com")
    with app.state.database.session() as session:
        manager = session.scalar(
            select(User).where(User.email == "correction-manager@example.com")
        )
        manager.roles = [
            session.scalar(select(Role).where(Role.name == "system_admin"))
        ]
        session.commit()
    manager_headers = login(client, "correction-manager@example.com")
    document_ids = []
    for document_type, title in (("company_registration", "آگهی ثبت"), ("company_national_id", "شناسه ملی"), ("representative_card", "کارت نماینده")):
        uploaded = client.post(
            "/api/v1/portal/documents",
            headers=applicant_headers,
            data={"title": title, "document_type": document_type, "description": "مدرک شرکت", "purpose": "consultant_verification", "intended_reviewer": "consultant_management"},
            files={"file": (f"{document_type}.txt", b"company document", "text/plain")},
        )
        document_ids.append(uploaded.json()["id"])
    created = client.post(
        "/api/v1/consultations/verification",
        headers=applicant_headers,
        json={
            "consultant_type": "company",
            "professional_title": "کارشناس مالی شرکت",
            "specialties": ["مالیات شرکت‌ها"],
            "years_experience": 3,
            "qualifications": "سابقه فعالیت مالی و مالیاتی در شرکت‌های بازرگانی.",
            "document_ids": document_ids,
        },
    ).json()

    response = client.patch(
        f"/api/v1/consultations/manage/verifications/{created['id']}",
        headers=manager_headers,
        json={"status": "correction_required", "admin_note": ""},
    )
    assert response.status_code == 422


def test_public_advisor_directory_only_exposes_active_verified_profiles(
    consultation_client,
):
    app, client = consultation_client
    register(client, "public-advisor@example.com")
    register(client, "hidden-advisor@example.com")
    with app.state.database.session() as session:
        public_user = session.scalar(
            select(User).where(User.email == "public-advisor@example.com")
        )
        hidden_user = session.scalar(
            select(User).where(User.email == "hidden-advisor@example.com")
        )
        session.add_all(
            [
                ConsultantProfile(
                    user_id=public_user.id,
                    slug="public-advisor",
                    consultant_type="independent",
                    professional_title="مشاور مالیاتی",
                    bio="مشاور تأییدشده برای آزمون فهرست عمومی سامانه.",
                    city="شیراز",
                    is_verified=True,
                    is_available=True,
                ),
                ConsultantProfile(
                    user_id=hidden_user.id,
                    slug="hidden-advisor",
                    consultant_type="independent",
                    professional_title="مشاور غیرفعال",
                    bio="این پروفایل نباید در فهرست عمومی نمایش داده شود.",
                    city="تهران",
                    is_verified=False,
                    is_available=True,
                ),
            ]
        )
        session.commit()

    listing = client.get("/api/v1/consultations/public/advisors?city=شیراز")
    assert listing.status_code == 200
    assert [item["slug"] for item in listing.json()] == ["public-advisor"]

    details = client.get("/api/v1/consultations/public/advisors/public-advisor")
    assert details.status_code == 200
    assert details.json()["available_slots"]
    assert (
        client.get("/api/v1/consultations/public/advisors/hidden-advisor").status_code
        == 404
    )


def test_email_less_consultant_profile_is_created_without_server_error(
    consultation_client,
):
    app, client = consultation_client
    headers = register(client, "phone-consultant@example.com")
    with app.state.database.session() as session:
        consultant = session.scalar(
            select(User).where(User.email == "phone-consultant@example.com")
        )
        consultant.roles = [
            session.scalar(select(Role).where(Role.name == "tax_expert"))
        ]
        consultant.phone = "09121234567"
        consultant.email = None
        session.commit()

    response = client.get("/api/v1/consultations/profile/mine", headers=headers)
    assert response.status_code == 200, response.text
    assert response.json()["email"] == ""
    assert response.json()["slug"].startswith("consultant-")
