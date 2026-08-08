from sqlalchemy import select

from app.bootstrap import bootstrap_admin
from app.core.config import Settings
from app.db.base import Base
from app.db.session import Database
from app.models.auth import User


def test_bootstrap_admin_is_idempotent(tmp_path):
    settings = Settings(
        environment="test",
        database_url=f"sqlite+pysqlite:///{(tmp_path / 'bootstrap.db').as_posix()}",
        jwt_secret="test-secret-that-is-at-least-32-characters-long",
        bootstrap_admin_email="admin@example.com",
        bootstrap_admin_password="StrongAdmin123",
    )
    database = Database(settings.database_url)
    Base.metadata.create_all(database.engine)
    try:
        with database.session() as session:
            assert bootstrap_admin(session, settings) is True
            assert bootstrap_admin(session, settings) is True
            users = list(session.scalars(select(User)))
            assert len(users) == 1
            assert {role.name for role in users[0].roles} == {"system_admin"}
    finally:
        database.dispose()
