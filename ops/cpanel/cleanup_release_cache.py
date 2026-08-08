from __future__ import annotations

import shutil
from pathlib import Path


def main() -> None:
    home = Path.home()
    cache = home / ".npm" / "_cacache"
    if cache.exists():
        shutil.rmtree(cache)

    for archive in home.glob("chakah-cpanel-deployment-*.zip"):
        if archive.name != "chakah-cpanel-deployment-20260729-final.zip":
            archive.unlink()

    print("Release cache cleaned")


if __name__ == "__main__":
    main()
