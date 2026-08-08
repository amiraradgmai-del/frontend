"""add tool quotas and starter law records

Revision ID: 0011_tool_quotas_laws
Revises: 0010_tools_security
"""
from alembic import op
import sqlalchemy as sa

revision = "0011_tool_quotas_laws"
down_revision = "0010_tools_security"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("tool_usage_events", sa.Column("id", sa.String(36), primary_key=True), sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False), sa.Column("tool_type", sa.String(30), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_tool_usage_events_user_id", "tool_usage_events", ["user_id"])
    op.create_index("ix_tool_usage_events_tool_type", "tool_usage_events", ["tool_type"])
    op.create_index("ix_tool_usage_events_created_at", "tool_usage_events", ["created_at"])
    op.create_table("law_reference_records", sa.Column("id", sa.String(80), primary_key=True), sa.Column("source_id", sa.String(40), nullable=False), sa.Column("law_name", sa.String(300), nullable=False), sa.Column("chapter", sa.String(300), nullable=False), sa.Column("article_number", sa.String(50), nullable=False), sa.Column("official_text", sa.Text(), nullable=False), sa.Column("source_url", sa.String(1000), nullable=False), sa.Column("keywords", sa.String(500), nullable=False))
    op.create_index("ix_law_reference_records_source_id", "law_reference_records", ["source_id"])
    op.create_index("ix_law_reference_records_law_name", "law_reference_records", ["law_name"])
    op.create_index("ix_law_reference_records_article_number", "law_reference_records", ["article_number"])
    records = sa.table("law_reference_records", sa.column("id", sa.String), sa.column("source_id", sa.String), sa.column("law_name", sa.String), sa.column("chapter", sa.String), sa.column("article_number", sa.String), sa.column("official_text", sa.Text), sa.column("source_url", sa.String), sa.column("keywords", sa.String))
    op.bulk_insert(records, [
        {"id":"LAW-VAT-A1","source_id":"LAW-VAT","law_name":"قانون مالیات بر ارزش افزوده","chapter":"فصل اول ـ تعاریف و کلیات","article_number":"1","official_text":"مفاهیم و اصطلاحات زیر، در این قانون، دارای تعاریف مشروحه ذیل می‌باشند.","source_url":"https://qavanin.ir/Law/TreeText/?IDS=17874811672232780652","keywords":"تعاریف، مالیات بر ارزش افزوده"},
        {"id":"LAW-VAT-A2","source_id":"LAW-VAT","law_name":"قانون مالیات بر ارزش افزوده","chapter":"فصل اول ـ تعاریف و کلیات","article_number":"2","official_text":"عرضه کالاها و ارائه خدمات در ایران و واردات و صادرات آنها، از لحاظ مالیات و عوارض مشمول مقررات این قانون است.","source_url":"https://qavanin.ir/Law/TreeText/?IDS=17874811672232780652","keywords":"عرضه، خدمات، واردات، صادرات"},
        {"id":"LAW-TERMINAL-A1","source_id":"LAW-TERMINAL","law_name":"قانون پایانه‌های فروشگاهی و سامانه مؤدیان","chapter":"فصل اول ـ تعاریف","article_number":"1","official_text":"در این قانون، اصطلاحات زیر در معانی مشروحه مربوط به‌کار می‌روند.","source_url":"https://qavanin.ir/Law/TreeText/?IDS=12936955486234542481","keywords":"سامانه مؤدیان، پایانه فروشگاهی، تعاریف"},
        {"id":"LAW-EASE-A2","source_id":"LAW-EASE","law_name":"قانون تسهیل تکالیف مؤدیان جهت اجرای قانون پایانه‌های فروشگاهی و سامانه مؤدیان","chapter":"","article_number":"2","official_text":"سازمان امور مالیاتی کشور می‌تواند تا پایان سال 1403 تا صد درصد جرایم موضوع ماده (22) قانون پایانه‌های فروشگاهی و سامانه مؤدیان را مورد بخشودگی قرار دهد.","source_url":"https://qavanin.ir/Law/TreeText/?IDS=4822349448318190655","keywords":"بخشودگی جرایم، ماده 22"},
    ])
    plans = sa.table("subscription_plans", sa.column("code", sa.String), sa.column("benefits", sa.JSON))
    bind = op.get_bind()
    bind.execute(plans.update().where(plans.c.code == "normal").values(benefits=["۱۰ پرسش در ماه", "۵ جست‌وجوی قانون", "۱۰ محاسبه", "۱ نامه", "تقویم نامحدود"]))
    bind.execute(plans.update().where(plans.c.code == "plus").values(benefits=["۱۰۰ پرسش در ماه", "۱۰۰ جست‌وجوی قانون", "۱۰۰ محاسبه", "۱۰ نامه", "تقویم نامحدود", "۲ مشاور انسانی"]))
    bind.execute(plans.update().where(plans.c.code == "pro").values(benefits=["۱۰۰۰ پرسش در ماه", "۱۰۰۰ جست‌وجوی قانون", "۱۰۰۰ محاسبه", "۱۰۰ نامه", "تقویم نامحدود", "۱۰ مشاور انسانی"]))


def downgrade() -> None:
    op.drop_table("law_reference_records")
    op.drop_table("tool_usage_events")
