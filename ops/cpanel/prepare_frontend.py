from __future__ import annotations

import json
import shutil
from pathlib import Path


def main() -> None:
    home = Path.home()
    source = home / "frontend" / ".next" / "standalone"
    target = home / "chakah-web"
    shutil.copytree(
        source,
        target,
        dirs_exist_ok=True,
        ignore=shutil.ignore_patterns("node_modules"),
    )
    shutil.copytree(
        home / "frontend" / ".next" / "static",
        target / ".next" / "static",
        dirs_exist_ok=True,
    )
    shutil.copytree(
        home / "frontend" / "public",
        target / "public",
        dirs_exist_ok=True,
    )

    package_path = target / "package.json"
    package = json.loads(package_path.read_text(encoding="utf-8"))
    package["scripts"] = {
        "start": "node app.js",
        "setup": "npm install --omit=dev --include=optional",
    }
    package_path.write_text(
        json.dumps(package, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (target / "app.js").write_text(
        "\n".join(
            (
                'process.env.NODE_ENV = "production";',
                'process.env.UV_THREADPOOL_SIZE = "2";',
                'process.env.NEXT_TELEMETRY_DISABLED = "1";',
                'process.env.BACKEND_URL = "http://127.0.0.1:18765";',
                'process.env.AUTH_COOKIE_SECURE = "true";',
                'process.env.NEXT_PUBLIC_SITE_URL = "https://chekahtax.com";',
                'require("./server.js");',
                "",
            )
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
