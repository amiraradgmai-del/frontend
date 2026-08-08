"""separate staff roles and add site configuration

Revision ID: 0012_roles_site_config
Revises: 0011_tool_quotas_laws
"""

from alembic import op
import sqlalchemy as sa


revision = "0012_roles_site_config"
down_revision = "0011_tool_quotas_laws"
branch_labels = None
depends_on = None


DEFAULT_CONFIG = {
    "theme": {
        "primary_color": "#2563eb",
        "accent_color": "#f97316",
        "background_color": "#f4faff",
        "font_family": "Tahoma",
        "border_radius": 14,
    },
    "branding": {
        "site_name": "دستیار هوشمند مالیاتی",
        "short_description": "پاسخ مستند به پرسش‌های مالیاتی ایران",
        "logo_url": "",
        "support_email": "",
        "support_phone": "",
    },
    "seo": {
        "default_title": "دستیار هوشمند مالیاتی",
        "default_description": "پاسخ مستند به پرسش‌های مالیاتی ایران",
        "keywords": "مالیات، قوانین مالیاتی، مشاور مالیاتی",
    },
    "features": {
        "maintenance_mode": False,
        "registration_enabled": True,
        "chatbot_enabled": True,
        "consultations_enabled": True,
    },
}


def upgrade() -> None:
    op.create_table(
        "site_configurations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("draft_json", sa.JSON(), nullable=False),
        sa.Column("published_json", sa.JSON(), nullable=False),
        sa.Column("published_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("updated_by", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_table(
        "site_configuration_versions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("version", sa.Integer(), nullable=False, index=True),
        sa.Column("configuration_json", sa.JSON(), nullable=False),
        sa.Column("created_by", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("note", sa.String(300), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    site_configurations = sa.table(
        "site_configurations",
        sa.column("id", sa.Integer()),
        sa.column("draft_json", sa.JSON()),
        sa.column("published_json", sa.JSON()),
        sa.column("published_version", sa.Integer()),
    )
    op.bulk_insert(site_configurations, [{"id": 1, "draft_json": DEFAULT_CONFIG, "published_json": DEFAULT_CONFIG, "published_version": 1}])

    connection = op.get_bind()
    for code in ("site:manage", "consultations:handle"):
        connection.execute(sa.text("INSERT INTO permissions (code, description) SELECT CAST(:code AS VARCHAR(100)), CAST(:description AS VARCHAR(255)) WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = CAST(:code AS VARCHAR(100)))"), {"code": code, "description": code.replace(":", " ")})
    for name in ("system_admin", "support_admin", "consultant"):
        connection.execute(sa.text("INSERT INTO roles (name, description) SELECT CAST(:name AS VARCHAR(64)), CAST(:description AS VARCHAR(255)) WHERE NOT EXISTS (SELECT 1 FROM roles WHERE name = CAST(:name AS VARCHAR(64)))"), {"name": name, "description": f"Built-in {name} role"})

    connection.execute(sa.text("INSERT INTO role_permissions (role_id, permission_id) SELECT target.id, rp.permission_id FROM roles target JOIN roles legacy ON legacy.name = 'admin' JOIN role_permissions rp ON rp.role_id = legacy.id WHERE target.name = 'system_admin' AND NOT EXISTS (SELECT 1 FROM role_permissions existing WHERE existing.role_id = target.id AND existing.permission_id = rp.permission_id)"))
    connection.execute(sa.text("INSERT INTO role_permissions (role_id, permission_id) SELECT r.id, p.id FROM roles r JOIN permissions p ON p.code = 'site:manage' WHERE r.name = 'system_admin' AND NOT EXISTS (SELECT 1 FROM role_permissions existing WHERE existing.role_id = r.id AND existing.permission_id = p.id)"))

    role_permissions = {
        "support_admin": ("profile:read", "profile:update", "consultations:manage", "tickets:manage", "user_documents:manage"),
        "consultant": ("profile:read", "profile:update", "consultations:handle", "tickets:manage", "documents:review"),
    }
    for role_name, codes in role_permissions.items():
        for code in codes:
            connection.execute(sa.text("INSERT INTO role_permissions (role_id, permission_id) SELECT r.id, p.id FROM roles r JOIN permissions p ON p.code = :code WHERE r.name = :role_name AND NOT EXISTS (SELECT 1 FROM role_permissions existing WHERE existing.role_id = r.id AND existing.permission_id = p.id)"), {"role_name": role_name, "code": code})

    connection.execute(sa.text("INSERT INTO user_roles (user_id, role_id) SELECT ur.user_id, target.id FROM user_roles ur JOIN roles legacy ON legacy.id = ur.role_id AND legacy.name = 'admin' JOIN roles target ON target.name = 'system_admin' WHERE NOT EXISTS (SELECT 1 FROM user_roles existing WHERE existing.user_id = ur.user_id AND existing.role_id = target.id)"))
    connection.execute(sa.text("INSERT INTO user_roles (user_id, role_id) SELECT ur.user_id, target.id FROM user_roles ur JOIN roles legacy ON legacy.id = ur.role_id AND legacy.name = 'tax_expert' JOIN roles target ON target.name = 'consultant' WHERE NOT EXISTS (SELECT 1 FROM user_roles existing WHERE existing.user_id = ur.user_id AND existing.role_id = target.id)"))


def downgrade() -> None:
    connection = op.get_bind()
    connection.execute(sa.text("DELETE FROM user_roles WHERE role_id IN (SELECT id FROM roles WHERE name IN ('system_admin','support_admin','consultant'))"))
    connection.execute(sa.text("DELETE FROM role_permissions WHERE role_id IN (SELECT id FROM roles WHERE name IN ('system_admin','support_admin','consultant'))"))
    connection.execute(sa.text("DELETE FROM roles WHERE name IN ('system_admin','support_admin','consultant')"))
    connection.execute(sa.text("DELETE FROM permissions WHERE code IN ('site:manage','consultations:handle')"))
    op.drop_table("site_configuration_versions")
    op.drop_table("site_configurations")
