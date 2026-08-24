from __future__ import annotations

import socket
import subprocess
import time
from pathlib import Path


HOME = Path("/home/magnbxua")
BACKEND = HOME / "backend"
PYTHON = BACKEND / ".venv" / "bin" / "python"


def wait_for_port(port: int, timeout: int = 30) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                return
        except OSError:
            time.sleep(0.25)
    raise TimeoutError(f"Port {port} did not become ready")


def main() -> None:
    migration = subprocess.run(
        [str(PYTHON), "-m", "alembic", "upgrade", "head"],
        cwd=BACKEND,
        capture_output=True,
        text=True,
        timeout=180,
    )
    if migration.returncode:
        raise RuntimeError(migration.stderr or migration.stdout)

    permissions = subprocess.run(
        [str(PYTHON), "-c", "from app.core.config import get_settings; from app.db.session import Database; from app.repositories.auth import seed_rbac; d=Database(get_settings().database_url); s=d.session_factory(); seed_rbac(s); s.close(); d.dispose()"],
        cwd=BACKEND,
        capture_output=True,
        text=True,
        timeout=120,
    )
    if permissions.returncode:
        raise RuntimeError(permissions.stderr or permissions.stdout)

    subprocess.run(["pkill", "-f", "uvicorn app.main:create_app"], check=False)
    time.sleep(1)
    process = subprocess.Popen(
        [str(PYTHON), "-m", "uvicorn", "app.main:create_app", "--factory", "--host", "127.0.0.1", "--port", "18765", "--no-access-log"],
        cwd=BACKEND,
        stdout=(BACKEND / "uvicorn.log").open("ab"),
        stderr=(BACKEND / "uvicorn-error.log").open("ab"),
        start_new_session=True,
    )
    (BACKEND / "tmp" / "internal-api.pid").write_text(str(process.pid), encoding="utf-8")
    wait_for_port(18765)
    restart = HOME / "chakah-web" / "tmp" / "restart.txt"
    restart.parent.mkdir(parents=True, exist_ok=True)
    restart.touch()
    (HOME / ".financial-statements-release.done").write_text("ok", encoding="utf-8")
    print("Financial statements release completed")


if __name__ == "__main__":
    main()
