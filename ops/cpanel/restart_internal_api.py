from __future__ import annotations

import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path


PORT = 18765


def stop_previous(pid_file: Path) -> None:
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


def main() -> None:
    backend = Path.home() / "backend"
    pid_file = backend / "tmp" / "internal-api.pid"
    pid_file.parent.mkdir(parents=True, exist_ok=True)
    stop_previous(pid_file)
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:create_app",
            "--factory",
            "--host",
            "127.0.0.1",
            "--port",
            str(PORT),
            "--no-access-log",
        ],
        cwd=backend,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    pid_file.write_text(str(process.pid), encoding="utf-8")
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        if process.poll() is not None:
            pid_file.unlink(missing_ok=True)
            raise RuntimeError("Internal API process failed to start")
        try:
            with socket.create_connection(("127.0.0.1", PORT), timeout=0.5):
                print("Internal API restarted")
                return
        except OSError:
            time.sleep(0.25)
    raise TimeoutError("Internal API did not become ready")


if __name__ == "__main__":
    main()
