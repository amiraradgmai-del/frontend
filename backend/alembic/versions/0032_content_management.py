"""add content pages and blog

Revision ID: 0032_content_management
Revises: 0031_consultant_operations
"""

from alembic import op
import sqlalchemy as sa

revision = "0032_content_management"
down_revision = "0031_consultant_operations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "content_pages",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("slug", sa.String(160), nullable=False, unique=True),
        sa.Column("title", sa.String(220), nullable=False),
        sa.Column("excerpt", sa.String(500), server_default="", nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("page_type", sa.String(20), server_default="page", nullable=False),
        sa.Column("seo_title", sa.String(220), server_default="", nullable=False),
        sa.Column("seo_description", sa.String(500), server_default="", nullable=False),
        sa.Column("cover_image_url", sa.String(500), server_default="", nullable=False),
        sa.Column("is_published", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.Column("created_by", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("updated_by", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_content_pages_slug", "content_pages", ["slug"], unique=True)
    op.create_index("ix_content_pages_page_type", "content_pages", ["page_type"])
    op.create_index("ix_content_pages_is_published", "content_pages", ["is_published"])


def downgrade() -> None:
    op.drop_table("content_pages")
