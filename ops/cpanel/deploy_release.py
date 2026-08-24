from __future__ import annotations

import shutil
import socket
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZipFile


HOME = Path("/home/magnbxua")
ARCHIVE = HOME / "chakah-cpanel-financial-statements-20260824.zip"
PYTHON = HOME / "backend" / ".venv" / "bin" / "python"


def safe_extract(target: Path) -> None:
    with ZipFile(ARCHIVE) as bundle:
        for member in bundle.infolist():
            relative = Path(member.filename)
            destination = (target / relative).resolve()
            if relative.is_absolute() or ".." in relative.parts or target.resolve() not in destination.parents:
                raise ValueError(f"Unsafe archive path: {member.filename}")
        bundle.extractall(target)


def wait_for_port(port: int, timeout: int = 25) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                return
        except OSError:
            time.sleep(0.25)
    raise TimeoutError(f"Port {port} did not become ready")


def main() -> None:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
    work = HOME / f".release-{stamp}"
    work.mkdir()
    safe_extract(work)

    active_web = HOME / "chakah-web"
    previous_web = work / "chakah-web-previous"
    # Passenger can leave orphaned Next workers after repeated releases. Stop
    # only this account's stale web workers before swapping the application.
    subprocess.run(["pkill", "-u", "magnbxua", "-f", "next-server"], check=False)
    time.sleep(2)
    active_web.rename(previous_web)
    try:
        (work / "chakah-web-next").rename(active_web)
    except Exception:
        previous_web.rename(active_web)
        raise

    htaccess = HOME / "public_html" / ".htaccess"
    if htaccess.exists():
        content = htaccess.read_text(encoding="utf-8")
        content = content.replace(
            f'PassengerNodejs "{HOME}/nodevenv/chakah-web/22/bin/node"',
            'PassengerNodejs "/opt/alt/alt-nodejs22/root/usr/bin/node"',
        )
        htaccess.write_text(content, encoding="utf-8")

    backend_release = work / "backend-release"
    shutil.copytree(backend_release / "app", HOME / "backend" / "app", dirs_exist_ok=True)
    shutil.copytree(backend_release / "alembic", HOME / "backend" / "alembic", dirs_exist_ok=True)
    for name in ("alembic.ini", "pyproject.toml", "passenger_wsgi.py"):
        source = backend_release / name
        if source.exists():
            shutil.copy2(source, HOME / "backend" / name)

    migration = subprocess.run(
        [str(PYTHON), "-m", "alembic", "upgrade", "head"],
        cwd=HOME / "backend",
        capture_output=True,
        text=True,
        timeout=180,
    )
    if migration.returncode:
        raise RuntimeError(migration.stderr or migration.stdout)

    permissions = subprocess.run(
        [str(PYTHON), "-c", "from app.core.config import get_settings; from app.db.session import Database; from app.repositories.auth import seed_rbac; d=Database(get_settings().database_url); s=d.session_factory(); seed_rbac(s); s.close(); d.dispose()"],
        cwd=HOME / "backend",
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
        cwd=HOME / "backend",
        stdout=(HOME / "backend" / "uvicorn.log").open("ab"),
        stderr=(HOME / "backend" / "uvicorn-error.log").open("ab"),
        start_new_session=True,
    )
    (HOME / "backend" / "tmp" / "internal-api.pid").write_text(str(process.pid), encoding="utf-8")
    wait_for_port(18765)

    restart = active_web / "tmp" / "restart.txt"
    restart.parent.mkdir(parents=True, exist_ok=True)
    restart.touch()

    shutil.rmtree(work, ignore_errors=True)
    shutil.rmtree(HOME / "chakah-web-next", ignore_errors=True)
    shutil.rmtree(HOME / "backend-release", ignore_errors=True)
    ARCHIVE.unlink(missing_ok=True)
    (HOME / ".deploy-20260810-final.done").write_text(stamp, encoding="utf-8")
    print("Deployment completed", stamp)


if __name__ == "__main__":
    main()
