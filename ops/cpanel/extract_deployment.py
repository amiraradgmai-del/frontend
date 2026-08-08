from __future__ import annotations

from pathlib import Path
from zipfile import ZipFile


def main() -> None:
    home = Path.home().resolve()
    archives = sorted(
        home.glob("chakah-cpanel-deployment-*.zip"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not archives:
        raise FileNotFoundError("No Chakah deployment archive was found")
    archive = archives[0]

    with ZipFile(archive) as bundle:
        for member in bundle.infolist():
            relative_path = Path(member.filename)
            if relative_path.is_absolute() or ".." in relative_path.parts:
                raise ValueError(f"Unsafe archive path: {member.filename}")

            destination = (home / relative_path).resolve()
            if home not in destination.parents and destination != home:
                raise ValueError(f"Archive path escapes home: {member.filename}")

            if member.is_dir():
                destination.mkdir(parents=True, exist_ok=True)
                continue

            destination.parent.mkdir(parents=True, exist_ok=True)
            with bundle.open(member) as source, destination.open("wb") as target:
                target.write(source.read())


if __name__ == "__main__":
    main()
