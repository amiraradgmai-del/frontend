from __future__ import annotations

import shutil
from pathlib import Path


def main() -> None:
    root = Path.home() / "backend"
    source = (root / "session.py.release").resolve()
    destination = (root / "app" / "db" / "session.py").resolve()
    if root.resolve() not in source.parents or root.resolve() not in destination.parents:
        raise RuntimeError("Path escapes backend root")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    print(destination)


if __name__ == "__main__":
    main()
