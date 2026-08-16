from __future__ import annotations

import json

from app.core.config import get_settings
from app.documents.storage import EncryptedObjectStorage, LocalObjectStorage, create_storage


def main() -> None:
    settings = get_settings()
    storage = create_storage(settings)
    encrypted = isinstance(storage, EncryptedObjectStorage)
    result = {
        "environment": settings.environment,
        "storage_encryption_configured": bool(
            settings.storage_encryption_keys.strip()
        ),
        "storage_encryption_active": encrypted,
        "storage_encryption_roundtrip": False,
    }
    if encrypted and isinstance(storage.storage, LocalObjectStorage):
        key = ".codex/security-runtime-check"
        payload = b"chakah-storage-encryption-runtime-check"
        try:
            storage.put(key, payload, "application/octet-stream")
            raw = storage.storage.get(key)
            result["storage_encryption_roundtrip"] = (
                raw.startswith(EncryptedObjectStorage.MAGIC)
                and raw != payload
                and storage.get(key) == payload
            )
        finally:
            storage.delete(key)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
