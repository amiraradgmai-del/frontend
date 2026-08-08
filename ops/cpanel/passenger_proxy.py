from __future__ import annotations

import http.client
import os
import socket
import subprocess
import sys
import threading
import time
from http import HTTPStatus

HOST = "127.0.0.1"
PORT = int(os.getenv("CHAKAH_INTERNAL_API_PORT", "18765"))
_startup_lock = threading.Lock()
_process: subprocess.Popen[bytes] | None = None


def _is_ready() -> bool:
    try:
        with socket.create_connection((HOST, PORT), timeout=0.25):
            return True
    except OSError:
        return False


def _ensure_server() -> None:
    global _process
    if _is_ready():
        return
    with _startup_lock:
        if _is_ready():
            return
        _process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "app.main:create_app",
                "--factory",
                "--host",
                HOST,
                "--port",
                str(PORT),
                "--no-access-log",
            ],
            cwd=os.path.dirname(__file__),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            if _is_ready():
                return
            if _process.poll() is not None:
                raise RuntimeError("The internal API process failed to start")
            time.sleep(0.2)
        raise TimeoutError("The internal API process did not become ready")


def application(environ, start_response):
    _ensure_server()
    query = environ.get("QUERY_STRING", "")
    path = environ.get("PATH_INFO", "/")
    target = f"{path}?{query}" if query else path
    content_length = int(environ.get("CONTENT_LENGTH") or 0)
    body = environ["wsgi.input"].read(content_length) if content_length else None
    headers = {}
    for key, value in environ.items():
        if key.startswith("HTTP_"):
            header = key[5:].replace("_", "-").title()
            if header.lower() not in {"connection", "host"}:
                headers[header] = value
    if environ.get("CONTENT_TYPE"):
        headers["Content-Type"] = environ["CONTENT_TYPE"]
    if content_length:
        headers["Content-Length"] = str(content_length)

    connection = http.client.HTTPConnection(HOST, PORT, timeout=120)
    connection.request(environ["REQUEST_METHOD"], target, body=body, headers=headers)
    response = connection.getresponse()
    payload = response.read()
    status_text = HTTPStatus(response.status).phrase
    response_headers = [
        (key, value)
        for key, value in response.getheaders()
        if key.lower() not in {"connection", "content-length", "transfer-encoding"}
    ]
    response_headers.append(("Content-Length", str(len(payload))))
    start_response(f"{response.status} {status_text}", response_headers)
    connection.close()
    return [payload]
