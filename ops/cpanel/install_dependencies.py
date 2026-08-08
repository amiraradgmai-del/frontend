from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> None:
    app_root = Path(__file__).resolve().parent
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "--disable-pip-version-check", "."],
        cwd=app_root,
        check=True,
    )


if __name__ == "__main__":
    main()
