"""complete financial workspace details

Revision ID: 0045_financial_workspace_details
Revises: 0043_financial_statements
"""

from alembic import op
import sqlalchemy as sa

revision = "0045_financial_workspace_details"
down_revision = "0043_financial_statements"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    organization_columns = {column["name"] for column in inspector.get_columns("financial_organizations")}
    columns = (
        ("entity_type", sa.String(24), "company"),
        ("economic_code", sa.String(32), ""),
        ("registration_number", sa.String(32), ""),
        ("tax_file_number", sa.String(64), ""),
        ("province", sa.String(80), ""),
        ("city", sa.String(80), ""),
        ("postal_code", sa.String(20), ""),
        ("address", sa.String(500), ""),
    )
    for name, type_, default in columns:
        if name not in organization_columns:
            op.add_column("financial_organizations", sa.Column(name, type_, nullable=False, server_default=default))

    fiscal_year_columns = {column["name"] for column in inspector.get_columns("financial_fiscal_years")}
    if "status" not in fiscal_year_columns:
        op.add_column("financial_fiscal_years", sa.Column("status", sa.String(24), nullable=False, server_default="open"))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    fiscal_year_columns = {column["name"] for column in inspector.get_columns("financial_fiscal_years")}
    if "status" in fiscal_year_columns:
        op.drop_column("financial_fiscal_years", "status")

    organization_columns = {column["name"] for column in inspector.get_columns("financial_organizations")}
    for name in ("address", "postal_code", "city", "province", "tax_file_number", "registration_number", "economic_code", "entity_type"):
        if name in organization_columns:
            op.drop_column("financial_organizations", name)
