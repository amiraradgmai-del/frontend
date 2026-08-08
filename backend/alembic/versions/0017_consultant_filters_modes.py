"""add consultant filters and in-person mode"""

from alembic import op
import sqlalchemy as sa

revision = "0017_consultant_filters"
down_revision = "0016_consultant_marketplace"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("consultant_profiles", sa.Column("city", sa.String(80), nullable=False, server_default=""))
    op.add_column("consultant_profiles", sa.Column("office_address", sa.String(300), nullable=False, server_default=""))
    op.add_column("consultant_profiles", sa.Column("offers_in_person", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.drop_constraint("ck_consultation_bookings_mode", "consultation_bookings", type_="check")
    op.create_check_constraint("ck_consultation_bookings_mode", "consultation_bookings", "mode IN ('online','in_person','phone')")

    profiles = sa.table("consultant_profiles", sa.column("slug", sa.String), sa.column("city", sa.String), sa.column("office_address", sa.String), sa.column("offers_in_person", sa.Boolean))
    bind = op.get_bind()
    locations = {
        "arman-nik": ("تهران", "تهران، میدان ونک"),
        "maryam-rahimi": ("تهران", "تهران، بلوار کشاورز"),
        "mohammad-karimi": ("شیراز", "شیراز، بلوار چمران"),
    }
    for slug, (city, address) in locations.items():
        bind.execute(profiles.update().where(profiles.c.slug == slug).values(city=city, office_address=address, offers_in_person=True))

    plans = sa.table("subscription_plans", sa.column("code", sa.String), sa.column("benefits", sa.JSON))
    benefit = "امکان رزرو مشاور مستقل حضوری یا آنلاین"
    for code in ("plus", "pro"):
        benefits = bind.execute(sa.select(plans.c.benefits).where(plans.c.code == code)).scalar_one_or_none() or []
        if benefit not in benefits:
            bind.execute(plans.update().where(plans.c.code == code).values(benefits=[*benefits, benefit]))


def downgrade() -> None:
    op.drop_constraint("ck_consultation_bookings_mode", "consultation_bookings", type_="check")
    op.create_check_constraint("ck_consultation_bookings_mode", "consultation_bookings", "mode IN ('online','phone')")
    op.drop_column("consultant_profiles", "offers_in_person")
    op.drop_column("consultant_profiles", "office_address")
    op.drop_column("consultant_profiles", "city")
