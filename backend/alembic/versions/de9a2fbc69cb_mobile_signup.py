"""mobile signup

Revision ID: de9a2fbc69cb
Revises: e4e9f204a138
Create Date: 2026-07-29
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "de9a2fbc69cb"
down_revision: str | Sequence[str] | None = "e4e9f204a138"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ایمیل کاربر اختیاری می‌شود.
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column(
            "email",
            existing_type=sa.String(length=320),
            nullable=True,
        )

    # درخواست‌های ثبت‌نام قبلی موقتی هستند و با ساختار جدید
    # شماره موبایل سازگار نیستند؛ بنابراین پاک می‌شوند.
    op.execute("DELETE FROM pending_registrations")

    # شماره موبایل به ثبت‌نام موقت اضافه می‌شود.
    with op.batch_alter_table("pending_registrations") as batch_op:
        batch_op.add_column(
            sa.Column("phone", sa.String(length=20), nullable=False)
        )
        # ایمیل در ثبت‌نام اختیاری می‌شود.
        batch_op.alter_column(
            "email",
            existing_type=sa.String(length=320),
            nullable=True,
        )

    # هر شماره موبایل فقط یک ثبت‌نام در حال انتظار داشته باشد.
    op.create_index(
        "ix_pending_registrations_phone",
        "pending_registrations",
        ["phone"],
        unique=True,
    )

    # جلوگیری از استفاده یک شماره موبایل برای چند حساب.
    # شماره‌های خالی کاربران قدیمی در این محدودیت حساب نمی‌شوند.
    op.create_index(
        "uq_user_profiles_phone_not_empty",
        "user_profiles",
        ["phone"],
        unique=True,
        postgresql_where=sa.text("phone <> ''"),
        sqlite_where=sa.text("phone <> ''"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_user_profiles_phone_not_empty",
        table_name="user_profiles",
    )

    op.drop_index(
        "ix_pending_registrations_phone",
        table_name="pending_registrations",
    )

    # ثبت‌نام‌هایی که ایمیل ندارند در ساختار قدیمی قابل نگهداری نیستند.
    op.execute(
        "DELETE FROM pending_registrations WHERE email IS NULL"
    )

    with op.batch_alter_table("pending_registrations") as batch_op:
        batch_op.alter_column(
            "email",
            existing_type=sa.String(length=320),
            nullable=False,
        )
        batch_op.drop_column("phone")

    # برای کاربران موبایلی بدون ایمیل، هنگام بازگشت یک ایمیل داخلی می‌سازیم.
    op.execute(
        """
        UPDATE users
        SET email =
            'mobile-'
            || REPLACE(id, '-', '')
            || '@local.invalid'
        WHERE email IS NULL
        """
    )

    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column(
            "email",
            existing_type=sa.String(length=320),
            nullable=False,
        )
