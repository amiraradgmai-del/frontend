from __future__ import annotations

import shutil
from pathlib import Path


def main() -> None:
    modules = Path.home() / "chakah-web" / "node_modules"
    if modules.is_symlink() or modules.is_file():
        modules.unlink()
    elif modules.exists():
        shutil.rmtree(modules)


if __name__ == "__main__":
    main()
