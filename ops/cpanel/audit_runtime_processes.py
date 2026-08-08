from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path


OWNED_MARKERS = ("uvicorn", "next-server", "node", "passenger", "python")


def main() -> None:
    result = subprocess.run(
        ["ps", "-u", str(os.getuid()), "-o", "pid=,ppid=,stat=,etimes=,comm=,args="],
        check=True,
        capture_output=True,
        text=True,
    )
    processes = []
    for line in result.stdout.splitlines():
        stripped = line.strip()
        if stripped and any(marker in stripped.lower() for marker in OWNED_MARKERS):
            processes.append(stripped)

    pid_file = Path.home() / "backend" / "tmp" / "internal-api.pid"
    payload = {
        "matched_processes": processes,
        "matched_count": len(processes),
        "internal_api_pid": pid_file.read_text(encoding="utf-8").strip() if pid_file.exists() else None,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
