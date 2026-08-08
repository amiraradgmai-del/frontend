"""add consultant verification and professional profile fields"""

from alembic import op
import sqlalchemy as sa

revision = "0018_consultant_verification"
down_revision = "0017_consultant_filters"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "consultant_profiles",
        sa.Column("skills", sa.JSON(), nullable=False, server_default="[]"),
    )
    op.add_column(
        "consultant_profiles",
        sa.Column("qualifications", sa.Text(), nullable=False, server_default=""),
    )
    op.add_column(
        "consultant_profiles",
        sa.Column("education", sa.JSON(), nullable=False, server_default="[]"),
    )
    op.add_column(
        "consultant_profiles",
        sa.Column("certifications", sa.JSON(), nullable=False, server_default="[]"),
    )
    op.add_column(
        "consultant_profiles",
        sa.Column("work_history", sa.JSON(), nullable=False, server_default="[]"),
    )
    op.add_column(
        "consultant_profiles",
        sa.Column("weekly_schedule", sa.JSON(), nullable=False, server_default="{}"),
    )
    op.add_column(
        "consultant_profiles",
        sa.Column("profile_image_url", sa.String(500), nullable=False, server_default=""),
    )
    op.create_table(
        "consultant_verification_requests",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("consultant_type", sa.String(20), nullable=False),
        sa.Column("professional_title", sa.String(160), nullable=False),
        sa.Column("national_id", sa.String(20), nullable=False),
        sa.Column("license_number", sa.String(80), nullable=False),
        sa.Column("specialties", sa.JSON(), nullable=False),
        sa.Column("years_experience", sa.Integer(), nullable=False),
        sa.Column("qualifications", sa.Text(), nullable=False),
        sa.Column("document_ids", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="pending"),
        sa.Column("applicant_note", sa.Text(), nullable=False),
        sa.Column("admin_note", sa.Text(), nullable=False),
        sa.Column(
            "reviewed_by",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
        ),
        sa.Column("reviewed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "consultant_type IN ('independent','company')",
            name="ck_consultant_verification_type",
        ),
        sa.CheckConstraint(
            "status IN ('pending','approved','rejected','correction_required')",
            name="ck_consultant_verification_status",
        ),
    )
    op.create_index(
        "ix_consultant_verification_requests_user_id",
        "consultant_verification_requests",
        ["user_id"],
    )
    op.create_index(
        "ix_consultant_verification_requests_status",
        "consultant_verification_requests",
        ["status"],
    )


def downgrade() -> None:
    op.drop_table("consultant_verification_requests")
    op.drop_column("consultant_profiles", "profile_image_url")
    op.drop_column("consultant_profiles", "weekly_schedule")
    op.drop_column("consultant_profiles", "work_history")
    op.drop_column("consultant_profiles", "certifications")
    op.drop_column("consultant_profiles", "education")
    op.drop_column("consultant_profiles", "qualifications")
    op.drop_column("consultant_profiles", "skills")
