"""make financial summary statements automatic

Revision ID: 0046_automatic_financial_summaries
Revises: 0045_financial_workspace_details
"""
from alembic import op
import sqlalchemy as sa

revision = "0046_automatic_financial_summaries"
down_revision = "0045_financial_workspace_details"
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    updates = {
        "CI.MANUAL": "سود و زیان جامع",
        "EQ.MANUAL": "خالص تغییرات حقوق مالکانه",
        "CF.MANUAL": "خالص افزایش (کاهش) وجه نقد",
    }
    for field_id, title in updates.items():
        connection.execute(
            sa.text("UPDATE financial_statement_fields SET title=:title, field_type='derived' WHERE id=:id"),
            {"id": field_id, "title": title},
        )


def downgrade():
    connection = op.get_bind()
    updates = {
        "CI.MANUAL": "سود و زیان جامع",
        "EQ.MANUAL": "تغییرات حقوق مالکانه",
        "CF.MANUAL": "جریان‌های نقدی",
    }
    for field_id, title in updates.items():
        connection.execute(
            sa.text("UPDATE financial_statement_fields SET title=:title, field_type='manual_required' WHERE id=:id"),
            {"id": field_id, "title": title},
        )
