"""content workflow and consultant contracts

Revision ID: 0033_content_and_contracts
Revises: 0032_content_management
"""

from alembic import op
import sqlalchemy as sa

revision = "0033_content_and_contracts"
down_revision = "0032_content_management"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("content_pages", sa.Column("category", sa.String(100), server_default="", nullable=False))
    op.add_column("content_pages", sa.Column("tags", sa.JSON(), server_default="[]", nullable=False))
    op.add_column("content_pages", sa.Column("scheduled_at", sa.DateTime(timezone=True)))
    op.create_index("ix_content_pages_category", "content_pages", ["category"])
    op.create_index("ix_content_pages_scheduled_at", "content_pages", ["scheduled_at"])
    op.create_table(
        "content_comments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("content_id", sa.String(36), sa.ForeignKey("content_pages.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("status", sa.String(20), server_default="pending", nullable=False),
        sa.Column("admin_note", sa.String(500), server_default="", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_content_comments_content_id", "content_comments", ["content_id"])
    op.create_index("ix_content_comments_user_id", "content_comments", ["user_id"])
    op.create_index("ix_content_comments_status", "content_comments", ["status"])
    op.add_column("consultant_profiles", sa.Column("contract_number", sa.String(100), server_default="", nullable=False))
    op.add_column("consultant_profiles", sa.Column("contract_start", sa.DateTime(timezone=True)))
    op.add_column("consultant_profiles", sa.Column("contract_end", sa.DateTime(timezone=True)))
    op.add_column("consultant_profiles", sa.Column("contract_status", sa.String(20), server_default="not_set", nullable=False))
    op.create_index("ix_consultant_profiles_contract_end", "consultant_profiles", ["contract_end"])
    op.create_index("ix_consultant_profiles_contract_status", "consultant_profiles", ["contract_status"])


def downgrade() -> None:
    for column in ("contract_status", "contract_end", "contract_start", "contract_number"):
        op.drop_column("consultant_profiles", column)
    op.drop_table("content_comments")
    op.drop_index("ix_content_pages_scheduled_at", table_name="content_pages")
    op.drop_index("ix_content_pages_category", table_name="content_pages")
    for column in ("scheduled_at", "tags", "category"):
        op.drop_column("content_pages", column)
