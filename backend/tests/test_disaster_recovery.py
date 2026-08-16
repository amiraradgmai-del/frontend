from __future__ import annotations

import base64
import importlib.util
import os
from pathlib import Path

import pytest


MODULE_PATH = Path(__file__).parents[2] / "ops" / "disaster_recovery.py"
SPEC = importlib.util.spec_from_file_location("disaster_recovery", MODULE_PATH)
assert SPEC and SPEC.loader
dr = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(dr)


def key() -> str:
    return base64.b64encode(os.urandom(32)).decode()


def test_encrypted_bundle_round_trip_and_tamper_detection(tmp_path: Path) -> None:
    database = tmp_path / "database.dump"
    database.write_bytes(b"postgres-backup")
    storage = tmp_path / "storage"
    (storage / "documents").mkdir(parents=True)
    (storage / "documents" / "private.txt").write_bytes(b"private tax file")
    bundle = tmp_path / "backup.drbk"
    encryption_key = key()

    dr.create_bundle(database, storage, bundle, encryption_key)
    manifest = dr.verify_bundle(bundle, encryption_key)

    assert not bundle.read_bytes().find(b"private tax file") >= 0
    assert {item["path"] for item in manifest["files"]} == {
        "database/database.dump",
        "storage/documents/private.txt",
    }

    damaged = bytearray(bundle.read_bytes())
    damaged[len(damaged) // 2] ^= 1
    bundle.write_bytes(damaged)
    with pytest.raises(Exception):
        dr.verify_bundle(bundle, encryption_key)


def test_key_validation_and_retention(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        dr.decode_key(base64.b64encode(b"short").decode())

    old = tmp_path / "chakah-dr-old.drbk"
    recent = tmp_path / "chakah-dr-recent.drbk"
    old.write_bytes(b"old")
    recent.write_bytes(b"recent")
    os.utime(old, (1, 1))

    assert dr.prune_backups(tmp_path, 14) == 1
    assert not old.exists()
    assert recent.exists()
