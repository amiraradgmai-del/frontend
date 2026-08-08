from __future__ import annotations

from pathlib import Path


ALLOWED_KEYS = {
    "TAX_AI_AI_PROVIDER",
    "TAX_AI_GEMINI_API_KEY",
    "TAX_AI_GEMINI_BASE_URL",
    "TAX_AI_GEMINI_GENERATION_MODEL",
    "TAX_AI_GEMINI_GENERAL_MODEL",
    "TAX_AI_GEMINI_ADVANCED_MODEL",
    "TAX_AI_GEMINI_EMBEDDING_MODEL",
}


def parse(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def main() -> None:
    backend = Path.home() / "backend"
    destination = backend / ".env"
    release = backend / ".env.ai.release"
    updates = parse(release)
    unexpected = set(updates) - ALLOWED_KEYS
    if unexpected:
        raise ValueError(f"Unexpected environment keys: {sorted(unexpected)}")
    existing_lines = destination.read_text(encoding="utf-8").splitlines()
    output: list[str] = []
    applied: set[str] = set()
    for line in existing_lines:
        key = line.split("=", 1)[0].strip() if "=" in line else ""
        if key in updates:
            output.append(f"{key}={updates[key]}")
            applied.add(key)
        else:
            output.append(line)
    for key, value in updates.items():
        if key not in applied:
            output.append(f"{key}={value}")
    destination.write_text("\n".join(output) + "\n", encoding="utf-8")
    destination.chmod(0o600)
    release.unlink(missing_ok=True)
    print("AI environment merged safely")


if __name__ == "__main__":
    main()
