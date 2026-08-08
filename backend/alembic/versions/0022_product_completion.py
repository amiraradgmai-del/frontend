"""product completion features

Revision ID: 0022_product_completion
Revises: 0021_legal_source_monitor
"""

from alembic import op
import sqlalchemy as sa

revision = "0022_product_completion"
down_revision = "0021_legal_source_monitor"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "password_reset_tokens",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_password_reset_tokens_user_id", "password_reset_tokens", ["user_id"])
    op.create_index("ix_password_reset_tokens_token_hash", "password_reset_tokens", ["token_hash"], unique=True)
    op.create_index("ix_password_reset_tokens_expires_at", "password_reset_tokens", ["expires_at"])
    op.create_table(
        "user_notifications",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("message", sa.String(1000), nullable=False, server_default=""),
        sa.Column("notification_type", sa.String(40), nullable=False, server_default="general"),
        sa.Column("action_url", sa.String(500), nullable=False, server_default=""),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_user_notifications_user_id", "user_notifications", ["user_id"])
    op.create_index("ix_user_notifications_type", "user_notifications", ["notification_type"])
    op.create_index("ix_user_notifications_read", "user_notifications", ["is_read"])
    op.create_index("ix_user_notifications_created", "user_notifications", ["created_at"])
    op.create_table(
        "consultant_reviews",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("booking_id", sa.String(36), sa.ForeignKey("consultation_bookings.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("consultant_id", sa.String(36), sa.ForeignKey("consultant_profiles.user_id", ondelete="CASCADE"), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("comment", sa.String(1000), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("rating BETWEEN 1 AND 5", name="ck_consultant_review_rating"),
    )
    op.create_index("ix_consultant_reviews_booking", "consultant_reviews", ["booking_id"], unique=True)
    op.create_index("ix_consultant_reviews_user", "consultant_reviews", ["user_id"])
    op.create_index("ix_consultant_reviews_consultant", "consultant_reviews", ["consultant_id"])


def downgrade() -> None:
    op.drop_table("consultant_reviews")
    op.drop_table("user_notifications")
    op.drop_table("password_reset_tokens")
