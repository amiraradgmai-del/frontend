from __future__ import annotations

from pathlib import Path


def main() -> None:
    root = Path.home() / "backend"
    source = root / ".env.release"
    destination = root / ".env"
    if not source.is_file():
        raise FileNotFoundError(source)
    source.replace(destination)
    destination.chmod(0o600)
    print("Production environment updated")


if __name__ == "__main__":
    main()
