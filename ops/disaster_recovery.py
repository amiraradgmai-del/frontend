from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import shutil
import subprocess
import tarfile
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

MAGIC = b"CHKDR01"
NONCE_SIZE = 12
TAG_SIZE = 16


def decode_key(encoded: str) -> bytes:
    try:
        key = base64.b64decode(encoded.strip(), validate=True)
    except (ValueError, TypeError):
        raise ValueError("DR encryption key must be valid base64") from None
    if len(key) != 32:
        raise ValueError("DR encryption key must decode to 32 bytes")
    return key


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class EncryptedWriter:
    def __init__(self, target: Path, key: bytes) -> None:
        self.stream = target.open("wb")
        nonce = os.urandom(NONCE_SIZE)
        self.stream.write(MAGIC + nonce)
        self.encryptor = Cipher(algorithms.AES(key), modes.GCM(nonce)).encryptor()
        self.encryptor.authenticate_additional_data(MAGIC)

    def write(self, data: bytes) -> int:
        self.stream.write(self.encryptor.update(data))
        return len(data)

    def flush(self) -> None:
        self.stream.flush()

    def tell(self) -> int:
        return self.stream.tell()

    def close(self) -> None:
        if self.stream.closed:
            return
        self.stream.write(self.encryptor.finalize())
        self.stream.write(self.encryptor.tag)
        self.stream.flush()
        os.fsync(self.stream.fileno())
        self.stream.close()


def safe_archive_name(name: str) -> bool:
    path = PurePosixPath(name)
    return bool(name) and not path.is_absolute() and ".." not in path.parts


def build_manifest(database_dump: Path, storage_root: Path) -> dict:
    files = [{
        "path": "database/database.dump",
        "size": database_dump.stat().st_size,
        "sha256": file_hash(database_dump),
    }]
    if storage_root.exists():
        for path in sorted(item for item in storage_root.rglob("*") if item.is_file()):
            relative = path.relative_to(storage_root).as_posix()
            files.append({
                "path": f"storage/{relative}",
                "size": path.stat().st_size,
                "sha256": file_hash(path),
            })
    return {
        "format": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "files": files,
    }


def create_bundle(database_dump: Path, storage_root: Path, target: Path, encoded_key: str) -> Path:
    database_dump, storage_root, target = database_dump.resolve(), storage_root.resolve(), target.resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    manifest = build_manifest(database_dump, storage_root)
    temporary = target.with_suffix(target.suffix + ".tmp")
    temporary.unlink(missing_ok=True)
    writer = EncryptedWriter(temporary, decode_key(encoded_key))
    try:
        with tarfile.open(fileobj=writer, mode="w|gz") as archive:
            data = json.dumps(manifest, ensure_ascii=False, sort_keys=True).encode("utf-8")
            info = tarfile.TarInfo("manifest.json")
            info.size = len(data)
            info.mtime = int(time.time())
            import io
            archive.addfile(info, io.BytesIO(data))
            archive.add(database_dump, arcname="database/database.dump", recursive=False)
            if storage_root.exists():
                for path in sorted(storage_root.rglob("*")):
                    if path.is_file():
                        archive.add(path, arcname=f"storage/{path.relative_to(storage_root).as_posix()}", recursive=False)
        writer.close()
        os.replace(temporary, target)
    except Exception:
        try:
            writer.stream.close()
        finally:
            temporary.unlink(missing_ok=True)
        raise
    return target


def decrypt_to_temp(bundle: Path, encoded_key: str, directory: Path) -> Path:
    payload = bundle.read_bytes()
    if not payload.startswith(MAGIC) or len(payload) < len(MAGIC) + NONCE_SIZE + TAG_SIZE:
        raise ValueError("Invalid DR bundle")
    nonce_start = len(MAGIC)
    nonce_end = nonce_start + NONCE_SIZE
    nonce = payload[nonce_start:nonce_end]
    ciphertext, tag = payload[nonce_end:-TAG_SIZE], payload[-TAG_SIZE:]
    decryptor = Cipher(algorithms.AES(decode_key(encoded_key)), modes.GCM(nonce, tag)).decryptor()
    decryptor.authenticate_additional_data(MAGIC)
    output = directory / "bundle.tar.gz"
    output.write_bytes(decryptor.update(ciphertext) + decryptor.finalize())
    return output


def verify_bundle(bundle: Path, encoded_key: str) -> dict:
    with tempfile.TemporaryDirectory(prefix="chakah-dr-verify-") as directory_name:
        directory = Path(directory_name)
        archive_path = decrypt_to_temp(bundle.resolve(), encoded_key, directory)
        with tarfile.open(archive_path, "r:gz") as archive:
            members = archive.getmembers()
            if any(not safe_archive_name(member.name) or member.issym() or member.islnk() for member in members):
                raise ValueError("Unsafe member in DR bundle")
            manifest_member = archive.getmember("manifest.json")
            manifest_stream = archive.extractfile(manifest_member)
            if manifest_stream is None:
                raise ValueError("Missing DR manifest")
            manifest = json.loads(manifest_stream.read().decode("utf-8"))
            by_name = {member.name: member for member in members if member.isfile()}
            for expected in manifest.get("files", []):
                member = by_name.get(expected["path"])
                if member is None or member.size != expected["size"]:
                    raise ValueError(f"Missing or invalid backup file: {expected['path']}")
                stream = archive.extractfile(member)
                if stream is None:
                    raise ValueError(f"Unreadable backup file: {expected['path']}")
                digest = hashlib.sha256()
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(chunk)
                if digest.hexdigest() != expected["sha256"]:
                    raise ValueError(f"Checksum mismatch: {expected['path']}")
            return manifest


def prune_backups(directory: Path, retention_days: int) -> int:
    cutoff = time.time() - retention_days * 86400
    removed = 0
    for path in directory.glob("chakah-dr-*.drbk"):
        if path.stat().st_mtime < cutoff:
            path.unlink()
            removed += 1
    return removed


def create_postgres_dump(target: Path) -> None:
    subprocess.run(["pg_dump", "--format=custom", "--compress=9", f"--file={target}"], check=True)
    subprocess.run(["pg_restore", "--list", str(target)], check=True, stdout=subprocess.DEVNULL)


def run_once(output: Path, storage: Path, key: str, retention_days: int) -> Path:
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="chakah-db-") as directory_name:
        dump = Path(directory_name) / "database.dump"
        create_postgres_dump(dump)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        bundle = create_bundle(dump, storage, output / f"chakah-dr-{stamp}.drbk", key)
    verify_bundle(bundle, key)
    prune_backups(output, retention_days)
    return bundle


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("/backups"))
    parser.add_argument("--storage", type=Path, default=Path("/storage"))
    parser.add_argument("--interval", type=int, default=int(os.getenv("BACKUP_INTERVAL_SECONDS", "86400")))
    parser.add_argument("--retention-days", type=int, default=int(os.getenv("BACKUP_RETENTION_DAYS", "14")))
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    key = os.environ.get("DR_ENCRYPTION_KEY", "")
    if not key:
        raise SystemExit("DR_ENCRYPTION_KEY is required")
    while True:
        bundle = run_once(args.output, args.storage, key, args.retention_days)
        print(f"Verified encrypted DR backup: {bundle}", flush=True)
        if args.once:
            break
        time.sleep(max(300, args.interval))


if __name__ == "__main__":
    main()
