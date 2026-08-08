from __future__ import annotations

import os
import signal
import subprocess
import time
from pathlib import Path


def main() -> None:
    pid_file = Path.home() / "backend" / "tmp" / "internal-api.pid"
    if pid_file.exists():
        try:
            pid = int(pid_file.read_text(encoding="utf-8").strip())
            os.killpg(pid, signal.SIGTERM)
            time.sleep(1)
            os.killpg(pid, signal.SIGKILL)
        except (OSError, ValueError):
            pass
        pid_file.unlink(missing_ok=True)
    subprocess.run(
        ["pkill", "-9", "-f", "uvicorn app.main:create_app"],
        check=False,
    )
    print("Previous internal API process stopped")


if __name__ == "__main__":
    main()
