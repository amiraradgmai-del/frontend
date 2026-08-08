from __future__ import annotations

import json
import re
import shutil
import sys
import zipfile
from pathlib import Path


def safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]+", "_", value).strip("_")


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python scripts/import-font-collection.py <font-archive.zip>")

    archive = Path(sys.argv[1]).resolve()
    frontend = Path(__file__).resolve().parents[1]
    output = frontend / "public" / "fonts" / "collection"
    output.mkdir(parents=True, exist_ok=True)

    for old_file in output.glob("*"):
        if old_file.is_file():
            old_file.unlink()

    fonts: list[dict[str, str]] = []
    with zipfile.ZipFile(archive) as source:
        for entry in source.infolist():
            suffix = Path(entry.filename).suffix.lower()
            if entry.is_dir() or suffix not in {".ttf", ".otf", ".woff", ".woff2"}:
                continue
            stem = safe_name(Path(entry.filename).stem)
            filename = f"{stem}{suffix}"
            family = f"Chakah_{stem}"
            with source.open(entry) as input_stream, (output / filename).open("wb") as output_stream:
                shutil.copyfileobj(input_stream, output_stream)
            fonts.append({"family": family, "label": Path(entry.filename).stem, "file": filename})

    fonts.sort(key=lambda item: item["label"].lower())
    css = [
        f'@font-face {{ font-family: "{item["family"]}"; src: url("/fonts/collection/{item["file"]}") format("truetype"); font-display: swap; }}'
        for item in fonts
    ]
    (frontend / "src" / "app" / "font-collection.css").write_text("\n".join(css) + "\n", encoding="utf-8")
    payload = "export const fontOptions = " + json.dumps(fonts, ensure_ascii=False, indent=2) + " as const;\n"
    (frontend / "src" / "lib" / "font-catalog.ts").write_text(payload, encoding="utf-8")
    print(f"Imported {len(fonts)} fonts")


if __name__ == "__main__":
    main()
