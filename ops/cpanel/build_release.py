from __future__ import annotations

import shutil
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parents[2]
STAGING = ROOT / ".cpanel-release"
ARCHIVE = ROOT / "chakah-cpanel-financial-statements-20260824.zip"


def copy_tree(source: Path, target: Path) -> None:
    shutil.copytree(source, target, dirs_exist_ok=True)


def main() -> None:
    shutil.rmtree(STAGING, ignore_errors=True)
    STAGING.mkdir()

    web = STAGING / "chakah-web-next"
    copy_tree(ROOT / "frontend" / ".next" / "standalone", web)
    copy_tree(ROOT / "frontend" / ".next" / "static", web / ".next" / "static")
    copy_tree(ROOT / "frontend" / "public", web / "public")
    shutil.copy2(ROOT / "ops" / "cpanel" / "app.js", web / "app.js")

    backend = STAGING / "backend-release"
    copy_tree(ROOT / "backend" / "app", backend / "app")
    copy_tree(ROOT / "backend" / "alembic", backend / "alembic")
    for name in ("alembic.ini", "pyproject.toml", "passenger_wsgi.py"):
        source = ROOT / "backend" / name
        if source.exists():
            shutil.copy2(source, backend / name)

    shutil.copy2(ROOT / "ops" / "cpanel" / "deploy_release.py", STAGING / "deploy_release.py")

    ARCHIVE.unlink(missing_ok=True)
    with ZipFile(ARCHIVE, "w", ZIP_DEFLATED, compresslevel=6) as bundle:
        for path in STAGING.rglob("*"):
            if path.is_file():
                bundle.write(path, path.relative_to(STAGING).as_posix())
    print(ARCHIVE)


if __name__ == "__main__":
    main()
