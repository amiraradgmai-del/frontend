from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path


def copy_if_exists(source: Path, destination: Path) -> None:
    if source.is_file():
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


def main() -> None:
    home = Path.home()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    backup = home / "backups" / f"chakah-{timestamp}"
    backup.mkdir(parents=True, exist_ok=False)

    copy_if_exists(home / "backend" / ".env", backup / "backend.env")
    copy_if_exists(
        home / "backend" / "data" / "chakah.db",
        backup / "chakah.db",
    )
    copy_if_exists(
        home / "chakah-web" / "package.json",
        backup / "frontend-package.json",
    )
    copy_if_exists(
        home / "chakah-web" / "app.js",
        backup / "frontend-app.js",
    )

    print(backup)


if __name__ == "__main__":
    main()
