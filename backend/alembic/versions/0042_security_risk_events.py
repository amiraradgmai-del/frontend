"""add security risk events

Revision ID: 0042_security_risk_events
Revises: 0041_account_sessions
"""

from alembic import op
import sqlalchemy as sa

revision = "0042_security_risk_events"
down_revision = "0041_account_sessions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "security_risk_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("category", sa.String(64), nullable=False),
        sa.Column("severity", sa.String(16), nullable=False),
        sa.Column("risk_score", sa.Integer(), nullable=False),
        sa.Column("ip_address", sa.String(64), nullable=False, server_default=""),
        sa.Column("device_name", sa.String(160), nullable=False, server_default=""),
        sa.Column("details_json", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("status", sa.String(20), nullable=False, server_default="open"),
        sa.Column("resolved_by_user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("severity IN ('low','medium','high','critical')", name="ck_security_risk_severity"),
        sa.CheckConstraint("status IN ('open','reviewing','resolved','false_positive')", name="ck_security_risk_status"),
    )
    op.create_index("ix_security_risk_events_user_id", "security_risk_events", ["user_id"])
    op.create_index("ix_security_risk_events_category", "security_risk_events", ["category"])
    op.create_index("ix_security_risk_events_status", "security_risk_events", ["status"])
    op.create_index("ix_security_risk_status_time", "security_risk_events", ["status", "created_at"])


def downgrade() -> None:
    op.drop_table("security_risk_events")
