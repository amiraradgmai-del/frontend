from __future__ import annotations

import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


TABLES = (
    "legal_external_sources",
    "law_reference_records",
)


def columns(connection: sqlite3.Connection, schema: str, table: str) -> list[str]:
    return [
        row[1]
        for row in connection.execute(
            f'PRAGMA {schema}.table_info("{table}")'
        )
    ]


def main() -> None:
    home = Path.home()
    target = home / "backend" / "data" / "chakah.db"
    source = home / "data" / "chakah.db"
    if not target.is_file() or not source.is_file():
        raise FileNotFoundError("Source or target database is missing")

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    backup = target.with_name(f"chakah-before-dataset-restore-{timestamp}.db")
    shutil.copy2(target, backup)

    connection = sqlite3.connect(target)
    try:
        connection.execute("PRAGMA foreign_keys=OFF")
        connection.execute("ATTACH DATABASE ? AS source_db", (str(source),))
        connection.execute("BEGIN IMMEDIATE")
        for table in TABLES:
            target_columns = columns(connection, "main", table)
            source_columns = columns(connection, "source_db", table)
            shared = [name for name in target_columns if name in source_columns]
            if not shared:
                raise RuntimeError(f"No shared columns for {table}")
            quoted = ", ".join(f'"{name}"' for name in shared)
            connection.execute(f'DELETE FROM "{table}"')
            connection.execute(
                f'INSERT INTO "{table}" ({quoted}) '
                f'SELECT {quoted} FROM source_db."{table}"'
            )
        connection.commit()
        for table in TABLES:
            count = connection.execute(
                f'SELECT COUNT(*) FROM "{table}"'
            ).fetchone()[0]
            print(f"{table}={count}")
        print(f"backup={backup}")
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


if __name__ == "__main__":
    main()
