from __future__ import annotations

import os
import signal
import subprocess
import time


def next_server_pids() -> list[int]:
    result = subprocess.run(
        ["ps", "-u", str(os.getuid()), "-o", "pid=,comm=,args="],
        check=True,
        capture_output=True,
        text=True,
    )
    pids: list[int] = []
    for line in result.stdout.splitlines():
        parts = line.strip().split(maxsplit=2)
        if len(parts) == 3 and "next-server" in f"{parts[1]} {parts[2]}".lower():
            pids.append(int(parts[0]))
    return pids


def main() -> None:
    pids = next_server_pids()
    for pid in pids:
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    time.sleep(2)
    for pid in pids:
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    print(f"Stopped {len(pids)} stale Next.js process(es)")


if __name__ == "__main__":
    main()
