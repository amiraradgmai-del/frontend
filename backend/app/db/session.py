from __future__ import annotations

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker


class Database:
    def __init__(
        self, database_url: str, *, connect_timeout_seconds: float = 2.0
    ) -> None:
        options = {"pool_pre_ping": True}
        if database_url.startswith("sqlite"):
            options["connect_args"] = {
                "check_same_thread": False,
                "timeout": 30,
            }
        elif database_url.startswith("postgresql"):
            options["connect_args"] = {
                "connect_timeout": max(1, round(connect_timeout_seconds))
            }
        self.engine: Engine = create_engine(database_url, **options)
        if database_url.startswith("sqlite"):
            event.listen(
                self.engine,
                "connect",
                self._configure_sqlite,
            )
        self.session_factory = sessionmaker(
            bind=self.engine, class_=Session, autoflush=False, expire_on_commit=False
        )

    def ping(self) -> None:
        with self.engine.connect() as connection:
            connection.execute(text("SELECT 1"))

    def dispose(self) -> None:
        self.engine.dispose()

    def session(self) -> Session:
        return self.session_factory()

    @staticmethod
    def _configure_sqlite(
        connection,
        _connection_record,
    ) -> None:
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA busy_timeout=30000")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()
