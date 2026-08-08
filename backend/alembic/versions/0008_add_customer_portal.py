"""add customer portal and commerce

Revision ID: 0008_add_customer_portal
Revises: 0007_add_verified_registration
"""
from alembic import op
from datetime import datetime, timezone
import sqlalchemy as sa

revision = "0008_add_customer_portal"
down_revision = "0007_add_verified_registration"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("pending_registrations", sa.Column("referral_code", sa.String(16), server_default="", nullable=False))
    op.create_table("subscription_plans", sa.Column("id", sa.String(36), primary_key=True), sa.Column("code", sa.String(20), nullable=False, unique=True), sa.Column("title", sa.String(80), nullable=False), sa.Column("description", sa.String(500), nullable=False), sa.Column("price", sa.Integer(), nullable=False), sa.Column("duration_days", sa.Integer(), nullable=False), sa.Column("benefits", sa.JSON(), nullable=False), sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False), sa.Column("sort_order", sa.Integer(), nullable=False))
    op.create_index("ix_subscription_plans_code", "subscription_plans", ["code"], unique=True)
    op.create_table("user_profiles", sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True), sa.Column("phone", sa.String(20), nullable=False), sa.Column("province", sa.String(80), nullable=False), sa.Column("city", sa.String(80), nullable=False), sa.Column("company_name", sa.String(160), nullable=False), sa.Column("job_title", sa.String(100), nullable=False), sa.Column("taxpayer_type", sa.String(30), nullable=False), sa.Column("bio", sa.Text(), nullable=False), sa.Column("profile_score", sa.Integer(), server_default="10", nullable=False), sa.Column("reward_points", sa.Integer(), server_default="0", nullable=False), sa.Column("referral_code", sa.String(16), nullable=False, unique=True), sa.Column("referred_by_user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL")), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_user_profiles_referral_code", "user_profiles", ["referral_code"], unique=True)
    op.create_table("payment_methods", sa.Column("id", sa.String(36), primary_key=True), sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False), sa.Column("cardholder_name", sa.String(120), nullable=False), sa.Column("last_four", sa.String(4), nullable=False), sa.Column("issuer", sa.String(80), nullable=False), sa.Column("fingerprint", sa.String(64), nullable=False, unique=True), sa.Column("is_default", sa.Boolean(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_payment_methods_user_id", "payment_methods", ["user_id"])
    op.create_table("discount_codes", sa.Column("id", sa.String(36), primary_key=True), sa.Column("code", sa.String(32), nullable=False, unique=True), sa.Column("percent", sa.Integer(), nullable=False), sa.Column("max_uses", sa.Integer(), nullable=False), sa.Column("used_count", sa.Integer(), server_default="0", nullable=False), sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False), sa.Column("expires_at", sa.DateTime(timezone=True)), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_discount_codes_code", "discount_codes", ["code"], unique=True)
    op.create_table("user_subscriptions", sa.Column("id", sa.String(36), primary_key=True), sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False), sa.Column("plan_id", sa.String(36), sa.ForeignKey("subscription_plans.id"), nullable=False), sa.Column("status", sa.String(20), nullable=False), sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False), sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False), sa.Column("auto_renew", sa.Boolean(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_user_subscriptions_user_id", "user_subscriptions", ["user_id"]); op.create_index("ix_user_subscriptions_status", "user_subscriptions", ["status"])
    op.create_table("payments", sa.Column("id", sa.String(36), primary_key=True), sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False), sa.Column("plan_id", sa.String(36), sa.ForeignKey("subscription_plans.id"), nullable=False), sa.Column("payment_method_id", sa.String(36), sa.ForeignKey("payment_methods.id", ondelete="SET NULL")), sa.Column("discount_code_id", sa.String(36), sa.ForeignKey("discount_codes.id", ondelete="SET NULL")), sa.Column("amount", sa.Integer(), nullable=False), sa.Column("discount_amount", sa.Integer(), nullable=False), sa.Column("status", sa.String(20), nullable=False), sa.Column("gateway_reference", sa.String(100), unique=True), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("paid_at", sa.DateTime(timezone=True)))
    op.create_index("ix_payments_user_id", "payments", ["user_id"]); op.create_index("ix_payments_status", "payments", ["status"])
    op.create_table("user_documents", sa.Column("id", sa.String(36), primary_key=True), sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False), sa.Column("title", sa.String(200), nullable=False), sa.Column("original_filename", sa.String(255), nullable=False), sa.Column("storage_key", sa.String(500), nullable=False, unique=True), sa.Column("mime_type", sa.String(100), nullable=False), sa.Column("file_size", sa.Integer(), nullable=False), sa.Column("status", sa.String(20), nullable=False), sa.Column("admin_note", sa.Text(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_user_documents_user_id", "user_documents", ["user_id"]); op.create_index("ix_user_documents_status", "user_documents", ["status"])
    op.create_table("support_tickets", sa.Column("id", sa.String(36), primary_key=True), sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False), sa.Column("subject", sa.String(200), nullable=False), sa.Column("category", sa.String(40), nullable=False), sa.Column("priority", sa.String(20), nullable=False), sa.Column("status", sa.String(20), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_support_tickets_user_id", "support_tickets", ["user_id"]); op.create_index("ix_support_tickets_status", "support_tickets", ["status"])
    op.create_table("ticket_messages", sa.Column("id", sa.String(36), primary_key=True), sa.Column("ticket_id", sa.String(36), sa.ForeignKey("support_tickets.id", ondelete="CASCADE"), nullable=False), sa.Column("sender_user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False), sa.Column("message", sa.Text(), nullable=False), sa.Column("is_staff", sa.Boolean(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_ticket_messages_ticket_id", "ticket_messages", ["ticket_id"])
    plans = sa.table("subscription_plans", sa.column("id", sa.String), sa.column("code", sa.String), sa.column("title", sa.String), sa.column("description", sa.String), sa.column("price", sa.Integer), sa.column("duration_days", sa.Integer), sa.column("benefits", sa.JSON), sa.column("is_active", sa.Boolean), sa.column("sort_order", sa.Integer))
    op.bulk_insert(plans, [
        {"id":"plan-normal","code":"normal","title":"عادی","description":"برای شروع و استفاده روزمره","price":0,"duration_days":3650,"benefits":["۱۰ پرسش در ماه","تاریخچه گفتگو","۱ تیکت فعال"],"is_active":True,"sort_order":1},
        {"id":"plan-plus","code":"plus","title":"پلاس","description":"برای مؤدیان و کسب‌وکارهای کوچک","price":349000,"duration_days":30,"benefits":["۱۰۰ پرسش در ماه","۵ سند شخصی","اولویت پاسخ تیکت","۲ درخواست مشاور"],"is_active":True,"sort_order":2},
        {"id":"plan-pro","code":"pro","title":"حرفه‌ای","description":"برای شرکت‌ها و متخصصان مالی","price":899000,"duration_days":30,"benefits":["پرسش بیشتر","۲۰ سند شخصی","اولویت مشاور انسانی","گزارش و آرشیو کامل"],"is_active":True,"sort_order":3},
    ])
    discounts = sa.table("discount_codes", sa.column("id", sa.String), sa.column("code", sa.String), sa.column("percent", sa.Integer), sa.column("max_uses", sa.Integer), sa.column("used_count", sa.Integer), sa.column("is_active", sa.Boolean), sa.column("expires_at", sa.DateTime(timezone=True)), sa.column("created_at", sa.DateTime(timezone=True)))
    op.bulk_insert(discounts, [{"id":"discount-welcome20","code":"WELCOME20","percent":20,"max_uses":500,"used_count":0,"is_active":True,"expires_at":None,"created_at":datetime.now(timezone.utc)}])


def downgrade() -> None:
    for table in ["ticket_messages","support_tickets","user_documents","payments","user_subscriptions","discount_codes","payment_methods","user_profiles","subscription_plans"]: op.drop_table(table)
    op.drop_column("pending_registrations", "referral_code")
