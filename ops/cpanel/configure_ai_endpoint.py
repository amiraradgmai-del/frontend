from __future__ import annotations

from pathlib import Path


def main() -> None:
    path = Path.home() / "backend" / ".env"
    values = {
        "TAX_AI_GEMINI_BASE_URL": "https://api.avalai.ir/v1beta",
        "TAX_AI_GEMINI_TIMEOUT_SECONDS": "8",
    }
    lines = path.read_text(encoding="utf-8").splitlines()
    output: list[str] = []
    found: set[str] = set()
    for line in lines:
        key = line.split("=", 1)[0].strip() if "=" in line else ""
        if key in values:
            output.append(f"{key}={values[key]}")
            found.add(key)
        else:
            output.append(line)
    for key, value in values.items():
        if key not in found:
            output.append(f"{key}={value}")
    path.write_text("\n".join(output) + "\n", encoding="utf-8")
    print("AI endpoint configured")


if __name__ == "__main__":
    main()
