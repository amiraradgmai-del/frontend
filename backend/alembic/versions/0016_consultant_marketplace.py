"""consultant marketplace and bookings

Revision ID: 0016_consultant_marketplace
Revises: 0015_wallet_profile_reward
"""

from alembic import op
import sqlalchemy as sa

revision = "0016_consultant_marketplace"
down_revision = "0015_wallet_profile_reward"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("consultation_requests", sa.Column("billing_type", sa.String(20), nullable=False, server_default="free"))
    op.add_column("consultation_requests", sa.Column("price", sa.Integer(), nullable=False, server_default="0"))
    op.create_table("consultant_profiles",
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("slug", sa.String(120), nullable=False, unique=True),
        sa.Column("consultant_type", sa.String(20), nullable=False),
        sa.Column("professional_title", sa.String(160), nullable=False),
        sa.Column("bio", sa.Text(), nullable=False),
        sa.Column("specialties", sa.JSON(), nullable=False),
        sa.Column("years_experience", sa.Integer(), nullable=False),
        sa.Column("rating", sa.Float(), nullable=False),
        sa.Column("review_count", sa.Integer(), nullable=False),
        sa.Column("consultation_price", sa.Integer(), nullable=False),
        sa.Column("is_online", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_available", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("consultant_type IN ('independent','company')", name="ck_consultant_profiles_type"),
    )
    op.create_index("ix_consultant_profiles_slug", "consultant_profiles", ["slug"], unique=True)
    op.create_index("ix_consultant_profiles_consultant_type", "consultant_profiles", ["consultant_type"])
    op.create_table("consultation_bookings",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("consultant_id", sa.String(36), sa.ForeignKey("consultant_profiles.user_id", ondelete="CASCADE"), nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("mode", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="reserved"),
        sa.Column("price", sa.Integer(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("consultant_id", "scheduled_at", name="uq_consultation_booking_slot"),
        sa.CheckConstraint("mode IN ('online','phone')", name="ck_consultation_bookings_mode"),
        sa.CheckConstraint("status IN ('reserved','completed','cancelled')", name="ck_consultation_bookings_status"),
    )
    op.create_index("ix_consultation_bookings_user_id", "consultation_bookings", ["user_id"])
    op.create_index("ix_consultation_bookings_consultant_id", "consultation_bookings", ["consultant_id"])
    op.create_index("ix_consultation_bookings_scheduled_at", "consultation_bookings", ["scheduled_at"])


def downgrade() -> None:
    op.drop_table("consultation_bookings")
    op.drop_table("consultant_profiles")
    op.drop_column("consultation_requests", "price")
    op.drop_column("consultation_requests", "billing_type")
