from __future__ import annotations

import re
import sqlite3
from pathlib import Path

import app.models  # noqa: F401
from app.core.config import get_settings
from app.db.base import Base
from app.db.session import Database


def database_path(database_url: str) -> Path:
    prefix = "sqlite:////"
    if not database_url.startswith(prefix):
        raise RuntimeError("This updater only supports an absolute SQLite URL")
    return Path("/" + database_url.removeprefix(prefix))


def columns(connection: sqlite3.Connection, table: str) -> dict[str, sqlite3.Row]:
    return {
        row["name"]: row
        for row in connection.execute(f'PRAGMA table_info("{table}")')
    }


def make_user_email_nullable(connection: sqlite3.Connection) -> None:
    user_columns = columns(connection, "users")
    if not user_columns or not user_columns["email"]["notnull"]:
        return

    create_sql = connection.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='users'"
    ).fetchone()[0]
    index_sql = [
        row[0]
        for row in connection.execute(
            """
            SELECT sql
            FROM sqlite_master
            WHERE type='index' AND tbl_name='users' AND sql IS NOT NULL
            """
        )
    ]
    column_names = list(user_columns)
    quoted_columns = ", ".join(f'"{name}"' for name in column_names)

    replacement = re.sub(
        r"(?i)\bemail\s+VARCHAR\(320\)\s+NOT\s+NULL",
        "email VARCHAR(320)",
        create_sql,
        count=1,
    )
    replacement = re.sub(
        r"(?i)^CREATE TABLE\s+[\"`']?users[\"`']?",
        "CREATE TABLE users_new",
        replacement,
        count=1,
    )
    if replacement == create_sql:
        raise RuntimeError("Could not prepare nullable users.email migration")

    connection.execute(replacement)
    connection.execute(
        f"INSERT INTO users_new ({quoted_columns}) "
        f"SELECT {quoted_columns} FROM users"
    )
    connection.execute("DROP TABLE users")
    connection.execute("ALTER TABLE users_new RENAME TO users")
    for statement in index_sql:
        connection.execute(statement)


def main() -> None:
    settings = get_settings()
    path = database_path(settings.database_url)
    path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute("PRAGMA foreign_keys=OFF")
        connection.execute("BEGIN IMMEDIATE")
        make_user_email_nullable(connection)

        profile_columns = columns(connection, "user_profiles")
        if profile_columns and "phone_verified" not in profile_columns:
            connection.execute(
                "ALTER TABLE user_profiles "
                "ADD COLUMN phone_verified BOOLEAN NOT NULL DEFAULT 0"
            )
        if profile_columns and "phone_verified_at" not in profile_columns:
            connection.execute(
                "ALTER TABLE user_profiles ADD COLUMN phone_verified_at DATETIME"
            )

        if columns(connection, "pending_registrations"):
            connection.execute("DROP TABLE pending_registrations")

        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()

    database = Database(settings.database_url)
    Base.metadata.create_all(database.engine)
    with database.engine.begin() as sqlalchemy_connection:
        sqlalchemy_connection.exec_driver_sql(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS uq_user_profiles_phone_not_empty
            ON user_profiles (phone)
            WHERE phone <> ''
            """
        )
    database.dispose()
    print(f"SQLite schema upgraded: {path}")


if __name__ == "__main__":
    main()
