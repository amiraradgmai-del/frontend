from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> None:
    backend = Path.home() / "backend"
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=backend,
        check=False,
        capture_output=True,
        text=True,
        timeout=180,
    )
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    if result.returncode:
        raise SystemExit(result.returncode)
    print("Database migrations completed")


if __name__ == "__main__":
    main()
