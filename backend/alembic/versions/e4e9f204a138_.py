"""empty message

Revision ID: e4e9f204a138
Revises: 0036_phone_verification_schema, 0036_zarinpal_gateway
Create Date: 2026-07-28 14:17:17.847539
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e4e9f204a138'
down_revision: Union[str, None] = ('0036_phone_verification_schema', '0036_zarinpal_gateway')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

