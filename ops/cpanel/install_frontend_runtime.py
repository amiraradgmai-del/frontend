from __future__ import annotations

from pathlib import Path
from zipfile import ZipFile


def main() -> None:
    home = Path.home().resolve()
    archives = sorted(
        home.glob("frontend-runtime-modules-*.zip"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not archives:
        raise FileNotFoundError("Frontend runtime archive was not found")

    modules = home / "chakah-web" / "node_modules"
    target = modules.resolve()
    if home not in target.parents:
        raise RuntimeError(f"Unsafe Node modules path: {target}")
    target.mkdir(parents=True, exist_ok=True)

    with ZipFile(archives[0]) as bundle:
        for member in bundle.infolist():
            relative = Path(member.filename)
            if relative.is_absolute() or ".." in relative.parts:
                raise ValueError(f"Unsafe archive path: {member.filename}")
            destination = (target / relative).resolve()
            if target not in destination.parents and destination != target:
                raise ValueError(f"Archive escapes Node modules: {member.filename}")
            if member.is_dir():
                destination.mkdir(parents=True, exist_ok=True)
                continue
            destination.parent.mkdir(parents=True, exist_ok=True)
            with bundle.open(member) as source, destination.open("wb") as output:
                output.write(source.read())

    print(f"Frontend runtime installed in {target}")


if __name__ == "__main__":
    main()
