from __future__ import annotations

import socket
import subprocess
import sys
import time
from pathlib import Path


PORT = 18765


def is_ready() -> bool:
    try:
        with socket.create_connection(("127.0.0.1", PORT), timeout=0.5):
            return True
    except OSError:
        return False


def main() -> None:
    if is_ready():
        print("Internal API is already ready on 127.0.0.1:18765")
        return
    backend = Path.home() / "backend"
    pid_file = backend / "tmp" / "internal-api.pid"
    pid_file.parent.mkdir(parents=True, exist_ok=True)
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
        if is_ready():
            break
        time.sleep(0.25)
    else:
        raise TimeoutError("Internal API did not become ready")
    print("Internal API is ready on 127.0.0.1:18765")


if __name__ == "__main__":
    main()
