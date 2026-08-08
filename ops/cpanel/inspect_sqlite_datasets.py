from __future__ import annotations

import sqlite3
from pathlib import Path


KEYWORDS = (
    "document",
    "chunk",
    "law",
    "knowledge",
    "source",
)


def main() -> None:
    home = Path.home()
    paths = sorted(home.rglob("*.db"))
    for path in paths:
        if not path.is_file():
            continue
        print(f"DATABASE {path}")
        connection = sqlite3.connect(path)
        try:
            tables = [
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master "
                    "WHERE type='table' ORDER BY name"
                )
            ]
            for table in tables:
                if any(keyword in table.lower() for keyword in KEYWORDS):
                    quoted = table.replace('"', '""')
                    count = connection.execute(
                        f'SELECT COUNT(*) FROM "{quoted}"'
                    ).fetchone()[0]
                    print(f"{table}={count}")
        finally:
            connection.close()


if __name__ == "__main__":
    main()
